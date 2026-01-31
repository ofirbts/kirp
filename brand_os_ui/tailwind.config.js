/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#0A2540",
        secondary: "#00D4AA",
        neutral: { 50: "#F7F9FC", 100: "#E6EAEF", 200: "#425466" },
        accent: "#FF6B35",
      },
    },
  },
  plugins: [],
};
