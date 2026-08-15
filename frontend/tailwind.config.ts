import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#090A0F",
        surface: "#11131A",
        "surface-raised": "#171A24",
        border: "#232736",
        "border-subtle": "#1B1E2B",
        primary: {
          DEFAULT: "#8B5CF6",
          hover: "#7C3AED",
          subtle: "rgba(139, 92, 246, 0.1)",
        },
        blocking: {
          DEFAULT: "#EF4444",
          subtle: "rgba(239, 68, 68, 0.12)",
          border: "rgba(239, 68, 68, 0.3)",
        },
        suggestion: {
          DEFAULT: "#F59E0B",
          subtle: "rgba(245, 158, 11, 0.12)",
          border: "rgba(245, 158, 11, 0.3)",
        },
        nitpick: {
          DEFAULT: "#3B82F6",
          subtle: "rgba(59, 130, 246, 0.12)",
          border: "rgba(59, 130, 246, 0.3)",
        },
        success: {
          DEFAULT: "#10B981",
          subtle: "rgba(16, 185, 129, 0.12)",
          border: "rgba(16, 185, 129, 0.3)",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
