import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Qarar brand — light tokens (dark handled via CSS vars in globals.css)
        bg: "var(--bg)",
        surface: "var(--surface)",
        cardAlt: "var(--cardAlt)",
        ink: "var(--text)",
        ink2: "var(--text2)",
        ink3: "var(--text3)",
        line: "var(--border)",
        hair: "var(--hair)",
        gold: "var(--gold)",
        goldDeep: "var(--goldDeep)",
        goldTint: "var(--goldTint)",
        onGold: "var(--onGold)",
      },
      fontFamily: {
        sans: ["var(--font-plex-sans)", "system-ui", "sans-serif"],
        serif: ["var(--font-plex-serif)", "Georgia", "serif"],
        mono: ["var(--font-plex-mono)", "monospace"],
        arabic: ["var(--font-plex-arabic)", "sans-serif"],
      },
      borderRadius: {
        xl2: "12px",
      },
    },
  },
  plugins: [],
};

export default config;
