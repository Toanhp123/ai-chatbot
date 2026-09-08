/** @type {import('tailwindcss').Config} */
export default {
	content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
	darkMode: "class",
	theme: {
		extend: {
			colors: {
				paper: {
					50: "#f4f3ed",
					100: "#ebe8df",
					200: "#e3e0d5",
					300: "#dad6cb",
					card: "#faf8f5",
					cardHover: "#f4f1e8",
				},
				brand: {
					50: "#fffbeb",
					100: "#fef3c7",
					200: "#fde68a",
					300: "#fcd34d",
					400: "#fbbf24",
					500: "#f59e0b",
					600: "#d97706",
					700: "#b45309",
					800: "#92400e",
					900: "#78350f",
					950: "#451a03",
				},
			},
			fontFamily: {
				sans: [
					'"Plus Jakarta Sans"',
					"system-ui",
					"-apple-system",
					"BlinkMacSystemFont",
					'"Segoe UI"',
					"Roboto",
					"sans-serif",
				],
				serif: [
					'"Newsreader"',
					'"Lora"',
					'"Merriweather"',
					'"Charter"',
					'"Palatino Linotype"',
					"Georgia",
					"serif",
				],
			},
			boxShadow: {
				"warm-sm": "0 1px 2px rgba(28, 25, 23, 0.04)",
				"warm-md":
					"0 3px 6px -1px rgba(28, 25, 23, 0.06), 0 2px 4px -2px rgba(28, 25, 23, 0.04)",
				"warm-lg":
					"0 10px 15px -3px rgba(28, 25, 23, 0.06), 0 4px 6px -4px rgba(28, 25, 23, 0.04)",
			},
		},
	},
	plugins: [],
};
