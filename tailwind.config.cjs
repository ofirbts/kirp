/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Gilroy", "Outfit", "Plus Jakarta Sans", "system-ui", "sans-serif"],
      },
      colors: {
        bg: 'var(--color-bg)',
        surface1: 'var(--color-surface-1)',
        surface2: 'var(--color-surface-2)',
        surface3: 'var(--color-surface-3)',
        primary: {
          DEFAULT: 'var(--color-primary)',
          foreground: '#050509',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          foreground: '#050509',
        },
        accent: {
          DEFAULT: 'var(--color-accent)',
          foreground: '#050509',
        },
        coral: {
          DEFAULT: 'var(--color-coral)',
          foreground: '#ffffff',
        },
        textMain: 'var(--color-text-main)',
        textMuted: 'var(--color-text-muted)',
        textSoft: 'var(--color-text-soft)',
        // תמיכה ב-Shadcn הקיים
        border: "var(--color-border-subtle)",
        input: "var(--color-border-subtle)",
        ring: "var(--color-primary)",
      },
      borderRadius: {
        'lg': 'var(--radius-lg)',
        'xl': 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
        '3xl': '32px',
      },
      boxShadow: {
        soft: 'var(--shadow-soft)',
        hover: '0 22px 60px rgba(0, 0, 0, 0.7)',
      },
    },
  },
  plugins: [],
};
