/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#07111d",
        panel: "#0f2136",
        line: "#1c3a58",
        text: "#e8f1fb",
        muted: "#8aa4bd",
        cyan: "#22d3ee",
        green: "#34d399",
        amber: "#fbbf24",
        red: "#f87171",
        violet: "#a78bfa",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
