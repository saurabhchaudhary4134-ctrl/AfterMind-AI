import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#0a0e1a",
          900: "#111729",
          800: "#1a2235",
          700: "#242d44",
          600: "#2e3a52",
        },
        cyan: {
          DEFAULT: "#22d3ee",
          dark: "#0e7490",
        },
        violet: {
          DEFAULT: "#a78bfa",
          dark: "#6d28d9",
        },
        border: "#1e293b",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
