import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/lib/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/services/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/store/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"]
      },
      colors: {
        cosmic: {
          950: "#050914",
          900: "#09101b",
          800: "#101a2a",
          700: "#142136"
        },
        neon: {
          cyan: "#63f5e4",
          violet: "#8ab6ff",
          coral: "#ff5d78",
          amber: "#ffd36e"
        }
      },
      boxShadow: {
        panel: "0 32px 90px rgba(2, 7, 20, 0.65), inset 0 1px 0 rgba(255,255,255,0.06)"
      },
      backgroundImage: {
        "mesh-orbit":
          "radial-gradient(circle at 16% 12%, rgba(138, 182, 255, .18) 0, transparent 32%), radial-gradient(circle at 84% 8%, rgba(99, 245, 228, .14) 0, transparent 28%), linear-gradient(160deg, #040811 0%, #08101a 38%, #091120 100%)"
      }
    }
  },
  plugins: []
};

export default config;
