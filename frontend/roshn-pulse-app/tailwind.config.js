/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        roshn: {
          background: "#000000",
          surface: "#111827",
          surfaceAlt: "#0b1117",
          surfaceSubtle: "#1f293714",
          primary: "#22c55e",
          primaryDark: "#16a34a",
          accent: "#34d399",
          accentLight: "#6ee7b7",
          highlight: "#10b981",
          ink: "#F9FAFB",
          muted: "#9CA3AF",
          border: "#1f2937",
          borderSoft: "#374151",
          warn: "#facc15",
          warnBorder: "rgba(250, 204, 21, 0.3)",
          danger: "#f87171",
          dangerBorder: "rgba(248, 113, 113, 0.3)",
          dataBlue: "#3b82f6",
          dataPurple: "#a855f7",
        },
      },
      fontFamily: {
        sans: [
          "Outfit",
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "sans-serif",
        ],
        display: [
          "Outfit",
          "Alexandria",
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "sans-serif",
        ],
      },
      boxShadow: {
        soft: "0 28px 60px rgba(2, 6, 23, 0.55)",
      },
    },
  },
  plugins: [],
};
