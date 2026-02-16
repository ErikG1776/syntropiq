import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0e1217",
        panel: "#151b23",
        panelAlt: "#1a222e",
        border: "#2a3442",
        text: "#d5dee8",
        textMuted: "#8d98a7",
        ok: "#2ea043",
        warn: "#d29922",
        danger: "#f85149",
        accent: "#1f6feb"
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Segoe UI", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "monospace"]
      },
      boxShadow: {
        panel: "0 0 0 1px rgba(42,52,66,0.9), 0 8px 24px rgba(0,0,0,0.24)",
      }
    },
  },
  plugins: [],
} satisfies Config;
