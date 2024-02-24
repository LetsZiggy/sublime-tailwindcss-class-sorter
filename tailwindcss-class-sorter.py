from base64 import standard_b64decode, standard_b64encode
from json import dumps as json_dumps
from json import loads as json_loads
from os import path
from re import compile as re_compile
from re import sub as re_sub
from subprocess import PIPE, Popen
from typing import (
	Any,
	Dict,
	Optional,
	TypedDict,
	cast,
)

import sublime
import sublime_plugin

PROJECT_NAME = "tailwindcss-class-sorter"
SETTINGS_FILE = f"{PROJECT_NAME}.sublime-settings"
PLATFORM = sublime.platform()
KEYMAP_FILE = f"Default ({PLATFORM}).sublime-keymap"
IS_WINDOWS = PLATFORM == "windows"
CODE_COMMAND_NOT_FOUND = 127
VERSION = "3.4.0"


class SettingsData(TypedDict):
	initialised: bool
	variables: Dict[str, Any]
	config: Dict[str, Any]
	binary: Dict[str, Any]
	indexed_order: Optional[str]
	binary_base64: str
	binary_path: str
	config_path: str


class Settings:
	data: SettingsData = {
		"initialised": False,
		"variables": {},
		"config": {},
		"binary": {},
		"indexed_order": None,
		"binary_base64": "",
		"binary_path": path.normpath(
			path.join(
				sublime.cache_path(),
				"..",
				"Package Storage",
				PROJECT_NAME,
				VERSION,
				PROJECT_NAME,
			)
		),
		"config_path": path.normpath(
			path.join(
				sublime.cache_path(),
				"..",
				"Package Storage",
				PROJECT_NAME,
				VERSION,
				"config.min.json",
			)
		),
	}

	@classmethod
	def set_settings(cls, view: sublime.View, variables: Dict[str, str]) -> None:
		if not path.exists(cls.data["binary_path"]) or not path.exists(cls.data["config_path"]):
			cls.data["initialised"] = False
			return

		settings_default = sublime.load_settings(SETTINGS_FILE).to_dict()
		settings_default = {k: v for k, v in Settings.flatten_dict(settings_default)}
		cls.data["config"] = settings_default

		settings_user = view.settings().to_dict()
		settings_user = {k: v for k, v in settings_user.items() if "tailwindcss-class-sorter" in k}
		settings_user = {k[25:]: v for k, v in Settings.flatten_dict(settings_user)}
		cls.data["config"].update(settings_user)

		variables.update({k: v for k, v in cls.data["config"].items() if "." not in k and isinstance(v, str)})
		cls.data["variables"] = variables

		for k, v in cls.data["config"].items():
			if isinstance(v, str) and "${" in v and "}" in v:
				v = sublime.expand_variables(v, cls.data["variables"])
				cls.data["config"][k] = v

			if isinstance(v, str) and "path" in k:
				v = path.normpath(path.expanduser(v))
				cls.data["config"][k] = v

		# remove comments from config
		re_comments = re_compile(r"(?:[\t ]*?\/\*(?:.|\n)*?\*\/)|(?:[\t ]*?(?<![\w:@])\/\/.*?(?=\n))")

		# get default config
		with open(cls.data["config_path"]) as f:
			content = re_sub(re_comments, "", f.read())
			json_content = json_loads(content)
			cls.data["binary"] = json_content

		# get user config
		if cls.data["config"]["config_path"] not in {"", ".", ".."} and path.exists(cls.data["config"]["config_path"]):
			with open(cls.data["config"]["config_path"]) as f:
				content = re_sub(re_comments, "", f.read())
				json_content = json_loads(content)

				if cls.data["config"]["embedded_config"]:
					key = PROJECT_NAME.replace("-", "_")
					cls.data["binary"].update(json_content[key])
				else:
					cls.data["binary"].update(json_content)
		else:
			print(f'>>> {PROJECT_NAME}: invalid "config_path"')

		# set config.extensions
		cls.data["config"]["extensions"] = list(cls.data["binary"]["extensions_regex"])

		# set base64 config
		b = bytes(json_dumps(cls.data["binary"]), "utf-8")
		cls.data["binary_base64"] = standard_b64encode(b).decode("utf-8")

		cls.data["initialised"] = True
		return

	@classmethod
	def flatten_dict(cls, obj: Dict[str, Any], keystring: str = ""):
		if isinstance(obj, dict):
			keystring = f"{keystring}." if keystring else keystring

			for k in obj:
				yield from Settings.flatten_dict(obj[k], keystring + str(k))
		else:
			yield keystring, obj

	@staticmethod
	def get_settings(view: sublime.View) -> SettingsData:
		variables = cast(sublime.Window, view.window()).extract_variables()

		if (
			not Settings.data["initialised"]
			or variables["file_extension"] == "sublime-project"
			or variables["file"] == Settings.data["config"].get("config_path", "")
			or Settings.data["variables"].get("file_extension", "") != variables["file_extension"]
		):
			Settings.set_settings(view, variables)

		return Settings.data


class TailwindcssClassSorterEventListeners(sublime_plugin.EventListener):
	@staticmethod
	def should_run_command(view: sublime.View, settings: SettingsData) -> bool:
		extensions = Settings.data["config"].get("extensions", [])
		extension = settings["variables"]["file_extension"] or settings["variables"]["file_name"].split(".")[-1]

		return not extensions or extension in extensions

	@staticmethod
	def on_pre_save(view: sublime.View) -> None:
		settings = Settings.get_settings(view)

		if not settings["initialised"]:
			variables = cast(sublime.Window, view.window()).extract_variables()
			Settings.set_settings(view, variables)
			settings = Settings.data

		if settings["config"]["format_on_save"] and TailwindcssClassSorterEventListeners.should_run_command(
			view, settings
		):
			view.run_command("sort_tailwindcss")


class SortTailwindcssCommand(sublime_plugin.TextCommand):
	def run(self, edit) -> None:
		settings = Settings.get_settings(self.view)

		if not settings["initialised"]:
			variables = cast(sublime.Window, self.view.window()).extract_variables()
			Settings.set_settings(self.view, variables)
			settings = Settings.data

		buffer_region = sublime.Region(0, self.view.size())
		content = self.view.substr(buffer_region)
		content = standard_b64encode(content.encode("utf-8")).decode("utf-8")
		cmd = [
			settings["binary_path"],
			"format",
			"--base64-config",
			"--config",
			settings["binary_base64"],
			"--code-ext",
			settings["variables"]["file_extension"],
			"--code",
			content,
		]

		try:
			p = Popen(
				cmd,
				stdout=PIPE,
				stdin=PIPE,
				stderr=PIPE,
				cwd=settings["variables"]["project_path"],
				shell=IS_WINDOWS,
			)
		except OSError:
			sublime.error_message("Couldn't find tailwindcss-class-sorter. See console output.")
			raise Exception(
				"\n>>> Couldn't find tailwindcss-class-sorter. Try reinstalling this plugin.",
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

		if stdout != content:
			res = standard_b64decode(stdout).decode("utf-8")
			self.view.replace(edit, buffer_region, res)


class GetDefaultGroupIndexListTailwindcssCommand(sublime_plugin.TextCommand):
	def run(self, edit) -> None:
		settings = Settings.get_settings(self.view)

		if not settings["initialised"]:
			variables = cast(sublime.Window, self.view.window()).extract_variables()
			Settings.set_settings(self.view, variables)
			settings = Settings.data

		if settings["indexed_order"] is None:
			cmd = [
				settings["binary_path"],
				"list",
				"--base64-config",
				"--config",
				settings["binary_base64"],
				"--base64-output",
			]

			try:
				p = Popen(
					cmd,
					stdout=PIPE,
					stdin=PIPE,
					stderr=PIPE,
					cwd=settings["variables"]["project_path"],
					shell=IS_WINDOWS,
				)
			except OSError:
				sublime.error_message("Couldn't find tailwindcss-class-sorter. See console output.")
				raise Exception(
					"\n>>> Couldn't find tailwindcss-class-sorter. Try reinstalling this plugin.",
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
				re_remove_regex = re_compile(r", \"regex\": \[.*?\]}")
				re_newline = re_compile(r"}, {")
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
