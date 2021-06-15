/**
 * @type {import("prettier").Config}
 * @see https://prettier.io/docs/configuration
 */
export default {
	// ---Options--- //

	// printWidth: 120,
	// tabWidth: 2,
	// useTabs: true,
	semi: false,
	singleQuote: false,
	quoteProps: "consistent",
	jsxSingleQuote: false,
	trailingComma: "all",
	bracketSpacing: true,
	objectWrap: "preserve",
	bracketSameLine: true,
	arrowParens: "always",
	rangeStart: 0,
	rangeEnd: Infinity,
	// parser: "",
	// filepath: "",
	requirePragma: false,
	insertPragma: false,
	proseWrap: "preserve",
	htmlWhitespaceSensitivity: "css",
	vueIndentScriptAndStyle: false,
	// endOfLine: "lf",
	embeddedLanguageFormatting: "auto",
	singleAttributePerLine: true,

	// ---Overrides--- //

	/*
	overrides: [
		{
			files: ["*.html"],
			options: {},
		},
	],
	*/
}
