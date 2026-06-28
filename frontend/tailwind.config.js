/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        baymax: {
          bg: "#0f1115",
          surface: "#171a21",
          surfaceAlt: "#1f2329",
          accent: "#5ec8d8",
          accentSoft: "#2b4b52",
          text: "#e8eaed",
          textMuted: "#9aa1ab",
          warn: "#e0a93a",
          danger: "#e0594a",
        },
      },
    },
  },
  plugins: [],
};
