# tailwindcss Class Sorter for Sublime Text

Please note the plugin **uses binaries** from [tailwindcss-class-sorter](https://github.com/LetsZiggy/tailwindcss-class-sorter).

*Please note the plugin hasn't been submitted to [packagecontrol.io](https://packagecontrol.io/). Thus has to be installed manually.*

<br>

### Installation

#### Installing plugin

- `Package Control: Add Repository` Method (Recommended)
	1. Open `Command Palette` (Default: `Primary + Shift + p`)
	2. `Package Control: Add Repository`
	3. `https://raw.githubusercontent.com/LetsZiggy/sublime-tailwindcss-class-sorter/main/repository-package.json`
	4. Open `Command Palette`
	5. `Package Control: Install Package`
	6. `tailwindcss-class-sorter`
- "Manual" Method (Requires manual update)
	1. Download this repository through `Download ZIP`
	2. Rename folder to `tailwindcss-class-sorter`
	3. Move folder to `[SublimeText]/Packages` folder
		- To access `[SublimeText]/Packages` folder:
			1. Open/Restart `Sublime Text`
			2. Open the `Command Palette` (Default: `Primary + Shift + p`)
			3. `Preferences: Browse Packages`
	4. Restart `Sublime Text`

---

### Commands

#### Command palette:

- `tailwindcss class sorter: Format this file`
- `tailwindcss class sorter: Get Group Index List`
	- Prints current state of [order_list] with index to `Console Panel` (Default: `` Primary + ` ``)
	- eg: [{"index": int, "group_name": str}, ...]

#### Shortcut key:

- `tailwindcss class sorter: Format this file`
	- Default: `Primary + Shift + .`

---

### Usage

#### Using default settings ({ format_on_save: false })

1. Save current changes
2. Use `tailwindcss class sorter: Format this file`

---

### Configuring Settings

#### To access and modify settings file

Go to `Preferences -> Package Settings -> tailwindcss-class-sorter -> Settings`

#### To override settings per project basis

To override global plugin configuration for a specific project, add a settings object with a `tailwindcss-class-sorter` key in your `.sublime-project`. This file is accessible via `Project -> Edit Project`.

```javascript
/* EXAMPLE */
{
	"folders": [
		{
			"path": ".",
		},
	],
	"settings": {
		"tailwindcss-class-sorter": {
			"format_on_save": true,
		},
	},
}
```

#### Default settings:

```javascript
{
	/**
	 * Automatically format when a file is saved
	 */
	"format_on_save": false,

	/**
	 * Indicate if config is embedded in another config json/jsonc file
	 * Config will be expected to be in "tailwindcss_class_sorter" key/value
	 */
	"embedded_config": false,

	/**
	 * Path to config json/jsonc file
	 * see https://github.com/LetsZiggy/tailwindcss-class-sorter/blob/main/dist/config.json
	 *
	 * To use default config, set "config_path": ""
	 */
	"config_path": "",
}
```
