/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#16232B",
          soft: "#2A3B44",
        },
        paper: {
          DEFAULT: "#EEF2EF",
          card: "#F8FAF8",
        },
        highlighter: {
          DEFAULT: "#F2B705",
          soft: "#FBE7A6",
        },
        clinical: {
          DEFAULT: "#3E7C8C",
          soft: "#DCE9EA",
        },
        flag: {
          DEFAULT: "#C1443C",
          soft: "#F5DAD8",
        },
        muted: "#5B6B70",
      },
      fontFamily: {
        display: ["'Source Serif 4'", "serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      borderRadius: {
        sheet: "2px",
      },
      boxShadow: {
        sheet: "0 1px 0 rgba(22,35,43,0.06), 0 8px 24px -12px rgba(22,35,43,0.18)",
      },
      keyframes: {
        markHighlight: {
          "0%": { backgroundSize: "0% 100%" },
          "100%": { backgroundSize: "100% 100%" },
        },
        fadeUp: {
          "0%": { opacity: 0, transform: "translateY(8px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: 0.35 },
          "50%": { opacity: 1 },
        },
      },
      animation: {
        markHighlight: "markHighlight 0.6s ease-out forwards",
        fadeUp: "fadeUp 0.5s ease-out forwards",
        pulseDot: "pulseDot 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
}
