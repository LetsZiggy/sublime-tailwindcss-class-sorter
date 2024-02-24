from gzip import open as gzip_open
from os import chmod, listdir, makedirs, path
from shutil import rmtree
from urllib import request

import sublime

PROJECT_NAME = "tailwindcss-class-sorter"
PROJECT_NAME_SHORT = "twcs"
VERSION = "3.3.0"
PLATFORM = sublime.platform()  # Literal["osx", "linux", "windows"]
ARCH = sublime.arch()  # Literal["x32", "x64", "arm64"]
BINARY_TYPE = "darwin-" if PLATFORM == "osx" else f"{PLATFORM}-"

if ARCH == "arm64":
	BINARY_TYPE = BINARY_TYPE + "arm-64"
elif ARCH == "x64":
	BINARY_TYPE = BINARY_TYPE + "x86-64"
else:
	BINARY_TYPE = BINARY_TYPE + "x86-32"

CACHE_PATH = path.normpath(path.join(sublime.cache_path(), "..", "Package Storage", PROJECT_NAME))
BINARY_FOLDER_PATH = path.join(CACHE_PATH, VERSION)
CONFIG_FILE_PATH = path.join(CACHE_PATH, VERSION, "config.min.json")
ORDER_LIST_FILE_PATH = path.join(CACHE_PATH, VERSION, "order_list.json")
GZIP_FILE_PATH = (
	path.join(CACHE_PATH, VERSION, f"{PROJECT_NAME_SHORT}.exe.gz")
	if PLATFORM == "windows"
	else path.join(CACHE_PATH, VERSION, f"{PROJECT_NAME_SHORT}.gz")
)
BINARY_FILE_PATH = (
	path.join(CACHE_PATH, VERSION, f"{PROJECT_NAME_SHORT}.exe")
	if PLATFORM == "windows"
	else path.join(CACHE_PATH, VERSION, PROJECT_NAME_SHORT)
)

URL_BASE = f"https://raw.githubusercontent.com/LetsZiggy/{PROJECT_NAME}/refs/tags/v{VERSION}/dist"
CONFIG_URL = f"{URL_BASE}/config.min.json"
ORDER_LIST_URL = f"{URL_BASE}/order_list.json"
GZIP_URL = (
	f"{URL_BASE}/{VERSION}/{BINARY_TYPE}/{PROJECT_NAME_SHORT}.exe.gz"
	if PLATFORM == "windows"
	else f"{URL_BASE}/{VERSION}/{BINARY_TYPE}/{PROJECT_NAME_SHORT}.gz"
)


def plugin_loaded():
	# from package_control import events

	# if events.install(PROJECT_NAME) or events.post_upgrade(PROJECT_NAME):
	#     pass

	if not path.isdir(CACHE_PATH):
		# print(f">>> {PROJECT_NAME}: makedirs({CACHE_PATH})")
		makedirs(CACHE_PATH, mode=0o777, exist_ok=True)

	if not path.isdir(BINARY_FOLDER_PATH):
		for directory in listdir(CACHE_PATH):
			rmtree(path.join(CACHE_PATH, directory), ignore_errors=True)

		# print(f">>> {PROJECT_NAME}: makedirs({BINARY_FOLDER_PATH})")
		makedirs(BINARY_FOLDER_PATH, mode=0o777, exist_ok=True)

		sublime.status_message(f">>> {PROJECT_NAME}: downloading v{VERSION}...")
		print(f">>> {PROJECT_NAME}: downloading v{VERSION}...")

		req = request.Request(CONFIG_URL)
		with open(CONFIG_FILE_PATH, mode="wb") as f, request.urlopen(req) as r:
			f.write(r.read())
		chmod(CONFIG_FILE_PATH, 0o755)

		# req = request.Request(ORDER_LIST_URL)
		# with open(ORDER_LIST_FILE_PATH, mode="wb") as f, request.urlopen(req) as r:
		# 	f.write(r.read())
		# chmod(ORDER_LIST_FILE_PATH, 0o755)

		req = request.Request(GZIP_URL)
		with open(GZIP_FILE_PATH, mode="wb") as f, request.urlopen(req) as r:
			f.write(r.read())
		chmod(GZIP_FILE_PATH, 0o755)
		with open(BINARY_FILE_PATH, mode="wb") as f, gzip_open(GZIP_FILE_PATH, "rb") as g:
			f.write(g.read())
		chmod(BINARY_FILE_PATH, 0o755)

		### -----OLD_METHOD----- ###
		# request.urlretrieve(CONFIG_URL, CONFIG_FILE_PATH)
		# request.urlcleanup()
		# chmod(CONFIG_FILE_PATH, 0o755)

		# request.urlretrieve(ORDER_LIST_URL, ORDER_LIST_FILE_PATH)
		# request.urlcleanup()
		# chmod(ORDER_LIST_FILE_PATH, 0o755)

		# request.urlretrieve(GZIP_URL, GZIP_FILE_PATH)
		# request.urlcleanup()
		# chmod(GZIP_FILE_PATH, 0o755)
		# with open(BINARY_FILE_PATH, mode="wb") as f, gzip_open(GZIP_FILE_PATH, "rb") as g:
		# 	f.write(g.read())
		# chmod(BINARY_FILE_PATH, 0o755)
		### -----OLD_METHOD----- ###

		sublime.status_message(f">>> {PROJECT_NAME}: finished downloading v{VERSION}")
		print(f">>> {PROJECT_NAME}: finished downloading v{VERSION}")


def plugin_unloaded():
	# from package_control import events

	# if events.pre_upgrade(PROJECT_NAME) or events.remove(PROJECT_NAME):
	# 	pass

	pass
