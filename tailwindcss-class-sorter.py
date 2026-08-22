from base64 import standard_b64decode, standard_b64encode
from json import dumps as json_dumps
from json import loads as json_loads
from os import path
from re import compile as re_compile
from re import sub as re_sub
from shutil import rmtree
from subprocess import PIPE, Popen
from typing import (
	Any,
	Dict,
	Generator,
	List,
	Optional,
	Tuple,
	TypedDict,
	Union,
	cast,
)

import sublime
import sublime_plugin
from typing_extensions import override

PROJECT_NAME = "tailwindcss-class-sorter"
PROJECT_NAME_SHORT = "twcs"
SETTINGS_FILE = f"{PROJECT_NAME}.sublime-settings"
PLATFORM = sublime.platform()
KEYMAP_FILE = f"Default ({PLATFORM}).sublime-keymap"
IS_WINDOWS = PLATFORM == "windows"
CODE_COMMAND_NOT_FOUND = 127
VERSION = "4.2.0"

re_doublequote = re_compile(r'"')
re_multiline = re_compile(r"(?:/\*)|(?:\*/)")
re_singleline = re_compile(r"(?://)")
re_comma = re_compile(r"(?:,)")
re_is_trailing_comma = re_compile(r"^(?:,\s*[\}\]])")
re_remove_regex = re_compile(r", \"regex\": \[.*?\]}")
re_newline = re_compile(r"}, {")


def get_doublequote_pairs(content: str) -> List[Tuple[int, int]]:
	span_store: Union[Tuple[int, int], None] = None

	# find all doublequote pairs
	doublequote_pairs: List[Tuple[int, int]] = []
	for match in re_doublequote.finditer(content):
		span = match.span()

		# doublequote_start
		if span_store is None and content[span[0] - 1] != "\\":
			span_store = span
			continue

		# doublequote_end
		if span_store is not None and content[span[0] - 1] != "\\":
			doublequote_pairs.append((span_store[0], span[1]))
			span_store = None

	return doublequote_pairs


def sanatise_json(content: str) -> str:
	span_store: Union[Tuple[int, int], None]

	# remove multiline comments
	span_store = None
	multiline_spans: List[Tuple[int, int]] = []
	for match in re_multiline.finditer(content):
		span = match.span()

		# multiline_start
		if span_store is None and match[0] == r"/*":
			not_in_doublequotes: bool = True

			# ensure multiline_start not in doublequotes
			for doublequote in get_doublequote_pairs(content):
				# subsequent doublequotes passed match index
				if span[1] < doublequote[0]:
					break

				# doublequote is before match index
				if doublequote[1] < span[0]:
					continue

				# match index in doublequotes
				if doublequote[0] < span[0] and span[1] < doublequote[1]:
					not_in_doublequotes = False
					break

			if not_in_doublequotes:
				span_store = span

		# multiline_end
		if span_store is not None and match[0] == r"*/":
			multiline_spans.append((span_store[0], span[1]))
			span_store = None

	for span in reversed(multiline_spans):
		before = content[0 : span[0]]
		after = content[span[1] :]
		content = before + after

	# remove singleline comments
	span_store = None
	singleline_indices: List[int] = []
	for match in re_singleline.finditer(content):
		span = match.span()

		# singleline
		if span_store is None:
			not_in_doublequotes: bool = True

			# ensure singleline not in doublequotes
			for doublequote in get_doublequote_pairs(content):
				# subsequent doublequotes passed match index
				if span[1] < doublequote[0]:
					break

				# doublequote is before match index
				if doublequote[1] < span[0]:
					continue

				# match index in doublequotes
				if doublequote[0] < span[0] and span[1] < doublequote[1]:
					not_in_doublequotes = False
					break

			if not_in_doublequotes:
				singleline_indices.append(span[0])

	for index in reversed(singleline_indices):
		before = content[0:index]
		after = content[content.find("\n", index) :]
		content = before + after

	# remove trailing comma
	span_store = None
	trailing_comma_indices: List[int] = []
	for match in re_comma.finditer(content):
		span = match.span()

		# comma
		if span_store is None:
			not_in_doublequotes: bool = True

			# ensure comma not in doublequotes
			for doublequote in get_doublequote_pairs(content):
				# subsequent doublequotes passed match index
				if span[1] < doublequote[0]:
					break

				# doublequote is before match index
				if doublequote[1] < span[0]:
					continue

				# match index in doublequotes
				if doublequote[0] < span[0] and span[1] < doublequote[1]:
					not_in_doublequotes = False
					break

			if not_in_doublequotes:
				span_store = span

		# check if trailing comma
		if span_store is not None:
			if re_is_trailing_comma.match(content[span_store[0] :]) is not None:
				trailing_comma_indices.append(span_store[0])

			span_store = None

	for index in reversed(trailing_comma_indices):
		before = content[0:index]
		after = content[index + 1 :]
		content = before + after

	return content


class SettingsData(TypedDict):
	initialised: Optional[bool]
	variables: Dict[str, Any]
	sublime_text_config: Dict[str, Any]
	tailwindcss_config: Dict[str, Any]
	indexed_order: Optional[str]
	binary_base64: str
	binary_path: str
	config_path: str


class Settings:
	data: SettingsData = {
		"initialised": False,
		"variables": {},
		"sublime_text_config": {},
		"tailwindcss_config": {},
		"indexed_order": None,
		"binary_base64": "",
		"binary_path": path.normpath(
			path.join(
				sublime.cache_path(),
				"..",
				"Package Storage",
				PROJECT_NAME,
				VERSION,
				PROJECT_NAME_SHORT,
			)
		),
		"config_path": path.normpath(
			path.join(
				sublime.cache_path(),
				"..",
				"Package Storage",
				PROJECT_NAME,
				VERSION,
				"config.json",
			)
		),
	}

	@classmethod
	def set_settings(cls, view: sublime.View, variables: Dict[str, str]) -> None:
		settings_default: Dict[str, Any] = sublime.load_settings(SETTINGS_FILE).to_dict()
		settings_default = {k: v for k, v in Settings.flatten_dict(settings_default)}
		cls.data["sublime_text_config"] = settings_default

		settings_user: Dict[str, Any] = view.settings().to_dict()
		settings_user = {k: v for k, v in settings_user.items() if PROJECT_NAME in k}
		settings_user = {k[25:]: v for k, v in Settings.flatten_dict(settings_user)}
		cls.data["sublime_text_config"].update(settings_user)

		variables.update(
			{k: v for k, v in cls.data["sublime_text_config"].items() if "." not in k and isinstance(v, str)}
		)
		cls.data["variables"] = variables

		for k, v in cls.data["sublime_text_config"].items():
			if isinstance(v, str) and "${" in v and "}" in v:
				v = sublime.expand_variables(v, cls.data["variables"])
				cls.data["sublime_text_config"][k] = v

			if isinstance(v, str) and "path" in k:
				v = path.normpath(path.expanduser(v))
				cls.data["sublime_text_config"][k] = v

		# get default config
		if path.exists(cls.data["config_path"]):
			with open(cls.data["config_path"]) as f:
				content = f.read()
				content = sanatise_json(content)
				json_content: Dict[str, Any] = json_loads(content)
				cls.data["tailwindcss_config"] = json_content

		# get user config
		if cls.data["sublime_text_config"]["config_path"] not in {"", ".", ".."} and not path.exists(
			cast(str, cls.data["sublime_text_config"]["config_path"])
		):
			print(f'>>> {PROJECT_NAME}: invalid "config_path"')
			cls.data["initialised"] = None
			return
		elif cls.data["sublime_text_config"]["config_path"] not in {"", ".", ".."} and path.exists(
			cast(str, cls.data["sublime_text_config"]["config_path"])
		):
			with open(cast(str, cls.data["sublime_text_config"]["config_path"])) as f:
				content = f.read()
				content = sanatise_json(content)
				json_content = json_loads(content)

				if cls.data["sublime_text_config"]["embedded_config"]:
					key = PROJECT_NAME.replace("-", "_")
					cls.data["tailwindcss_config"].update(cast(Dict[str, Any], json_content[key]))
				else:
					cls.data["tailwindcss_config"].update(json_content)
		else:
			pass

		# Apply config from .sublime-project
		for k in cls.data["tailwindcss_config"].keys():
			v = cls.data["sublime_text_config"].get(k, None)
			if v is not None:
				cls.data["tailwindcss_config"][k] = v

		# set config.extensions
		cls.data["sublime_text_config"]["extensions"] = list(
			cast(Dict[str, Any], cls.data["tailwindcss_config"].get("extensions_regex", {}))
		)

		# set base64 config
		b = bytes(json_dumps(cls.data["tailwindcss_config"]), "utf-8")
		cls.data["binary_base64"] = standard_b64encode(b).decode("utf-8")

		cls.data["initialised"] = True
		return

	@classmethod
	def flatten_dict(
		cls, obj: Union[Dict[str, Any], Any], keystring: str = ""
	) -> Generator[Tuple[str, Dict[str, Any]], Tuple[Dict[str, Any], str], None]:
		if isinstance(obj, dict):
			keystring = f"{keystring}." if keystring else keystring

			for k in obj:
				yield from Settings.flatten_dict(cast(Union[Dict[str, Any], Any], obj[k]), keystring + str(k))
		else:
			yield keystring, obj

	@staticmethod
	def get_settings(view: sublime.View) -> SettingsData:
		variables = cast(sublime.Window, view.window()).extract_variables()

		if (
			Settings.data["initialised"] is False
			or variables["file_extension"] == "sublime-project"
			or variables["file"] == Settings.data["sublime_text_config"]["config_path"]
			or Settings.data["variables"].get("file_extension", "") != variables["file_extension"]
		):
			Settings.set_settings(view, variables)

		return Settings.data


class TailwindcssClassSorterEventListeners(sublime_plugin.EventListener):
	@staticmethod
	def should_run_command(view: sublime.View, settings: SettingsData) -> bool:
		extensions: List[str] = settings["sublime_text_config"]["extensions"]
		extension: str = (
			settings["variables"]["file_extension"] or cast(str, settings["variables"]["file_name"]).split(".")[-1]
		)

		if (not extensions or extension in extensions) and (
			not path.exists(settings["binary_path"]) or not path.exists(settings["config_path"])
		):
			sublime.error_message(
				f'Couldn\'t find "{PROJECT_NAME}" binary. Restarting Sublime Text will reinstall "{PROJECT_NAME}" binary.'
			)

			return False

		if settings["initialised"] is None:
			return False

		return not extensions or extension in extensions

	@staticmethod
	def on_pre_save(view: sublime.View) -> None:
		settings = Settings.get_settings(view)

		if settings["initialised"] is False:
			variables = cast(sublime.Window, view.window()).extract_variables()
			Settings.set_settings(view, variables)
			settings = Settings.data

		if (
			TailwindcssClassSorterEventListeners.should_run_command(view, settings)
			and settings["sublime_text_config"]["format_on_save"]
		):
			view.run_command("sort_tailwindcss")


class ClearCacheTailwindcssCommand(sublime_plugin.TextCommand):
	"""
	To run
	------
	- Open console (Default key: `crtl+~`)
	- `view.run_command("clear_cache_tailwindcss")`
	"""

	@override
	def run(self, edit: sublime.Edit) -> None:
		versioned_cache_path = path.normpath(
			path.join(
				sublime.cache_path(),
				"..",
				"Package Storage",
				PROJECT_NAME,
				VERSION,
			)
		)

		if path.exists(versioned_cache_path):
			rmtree(versioned_cache_path, ignore_errors=True)

		sublime.message_dialog(
			f'"{PROJECT_NAME}" binary has been deleted. Restarting Sublime Text will reinstall "{PROJECT_NAME}" binary.'
		)


class SortTailwindcssCommand(sublime_plugin.TextCommand):
	@override
	def run(self, edit: sublime.Edit) -> None:
		settings = Settings.get_settings(self.view)

		if TailwindcssClassSorterEventListeners.should_run_command(self.view, settings) is False:
			return

		buffer_region = sublime.Region(0, self.view.size())
		content = self.view.substr(buffer_region)
		content = standard_b64encode(content.encode("utf-8")).decode("utf-8")
		cmd = [
			settings["binary_path"],
			"format",
			"--config",
			settings["binary_base64"],
			"--base64-config",
			"--stdin",
			"--ext",
			settings["variables"]["file_extension"],
		]

		try:
			p = Popen(
				cmd,
				stdout=PIPE,
				stdin=PIPE,
				stderr=PIPE,
				cwd=cast(str, settings["variables"]["project_path"]),
				shell=IS_WINDOWS,
			)
		except OSError:
			sublime.error_message(
				f'Couldn\'t find "{PROJECT_NAME}" binary. Restarting Sublime Text will reinstall "{PROJECT_NAME}" binary.'
			)
			raise Exception(
				f'\n>>> Couldn\'t find "{PROJECT_NAME}" binary. Restarting Sublime Text will reinstall "{PROJECT_NAME}" binary.',
			)

		stdout, stderr = p.communicate(content.encode("utf-8"))
		stdout = stdout.decode("utf-8")
		stderr = stderr.decode("utf-8")

		if stderr:
			sublime.error_message(stderr)
			raise Exception(f"Error: {stderr}")
		elif p.returncode == CODE_COMMAND_NOT_FOUND:
			sublime.error_message(stderr or stdout)
			raise Exception(f"Error: {stderr or stdout}")
		elif stdout is None or len(stdout) < 1:
			return

		if stdout != content:
			res = standard_b64decode(stdout).decode("utf-8")
			self.view.replace(edit, buffer_region, res)


class GetDefaultGroupIndexListTailwindcssCommand(sublime_plugin.TextCommand):
	@override
	def run(self, edit: sublime.Edit) -> None:
		settings = Settings.get_settings(self.view)

		if TailwindcssClassSorterEventListeners.should_run_command(self.view, settings) is False:
			return

		if settings["indexed_order"] is None:
			cmd = [
				settings["binary_path"],
				"list",
				"--config",
				settings["binary_base64"],
				"--base64-config",
				"--base64-output",
			]

			try:
				p = Popen(
					cmd,
					stdout=PIPE,
					stdin=PIPE,
					stderr=PIPE,
					cwd=cast(str, settings["variables"]["project_path"]),
					shell=IS_WINDOWS,
				)
			except OSError:
				sublime.error_message(
					f'Couldn\'t find "{PROJECT_NAME}" binary. Restarting Sublime Text will reinstall "{PROJECT_NAME}" binary.'
				)
				raise Exception(
					f'\n>>> Couldn\'t find "{PROJECT_NAME}" binary. Restarting Sublime Text will reinstall "{PROJECT_NAME}" binary.',
				)

			stdout, stderr = p.communicate()
			stdout = stdout.decode("utf-8")
			stderr = stderr.decode("utf-8")

			if stderr:
				sublime.error_message(stderr)
				raise Exception(f"Error: {stderr}")
			elif p.returncode == CODE_COMMAND_NOT_FOUND:
				sublime.error_message(stderr or stdout)
				raise Exception(f"Error: {stderr or stdout}")
			elif stdout is None or len(stdout) < 1:
				return
			else:
				json_content = json_dumps(json_loads(standard_b64decode(stdout).decode("utf-8")))
				settings["indexed_order"] = json_content
				settings["indexed_order"] = re_sub(re_remove_regex, "}", settings["indexed_order"])
				settings["indexed_order"] = re_sub(re_newline, "},\n{", settings["indexed_order"])
				settings["indexed_order"] = (
					settings["indexed_order"][:1]
					+ "\n"
					+ settings["indexed_order"][1:-1]
					+ "\n"
					+ settings["indexed_order"][-1]
				)

		print(settings["indexed_order"])
