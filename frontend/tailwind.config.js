/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}", "./public/index.html"],
  theme: {
    screens: { sm: "640px", md: "768px", lg: "1024px", xl: "1280px", "2xl": "1440px" },
    colors: {
      transparent: "transparent",
      current: "currentColor",
      canvas: "var(--color-canvas)",
      "canvas-deep": "var(--color-canvas-deep)",
      navy: "var(--color-navy)",
      "navy-soft": "var(--color-navy-soft)",
      eucalyptus: {
        DEFAULT: "var(--color-eucalyptus)",
        deep: "var(--color-eucalyptus-deep)",
        soft: "var(--color-eucalyptus-soft)",
        tint: "var(--color-eucalyptus-tint)",
      },
      ochre: {
        DEFAULT: "var(--color-ochre)",
        deep: "var(--color-ochre-deep)",
        soft: "var(--color-ochre-soft)",
      },
      surface: "var(--color-surface)",
      border: "var(--color-border)",
      stone: "var(--color-stone)",
      muted: "var(--color-muted-text)",
      charcoal: "var(--color-charcoal)",
      risk: { DEFAULT: "var(--color-risk)", soft: "var(--color-risk-soft)" },
      white: "#FFFFFF",
    },
    fontFamily: { sans: ["var(--font-sans)"] },
    borderRadius: {
      none: "0",
      sm: "var(--radius-small)",
      DEFAULT: "var(--radius-medium)",
      md: "var(--radius-medium)",
      lg: "var(--radius-large)",
      full: "9999px",
    },
    extend: {
      fontSize: {
        display: ["34px", { lineHeight: "40px", letterSpacing: "-0.5px", fontWeight: "600" }],
        h2: ["24px", { lineHeight: "32px", fontWeight: "700" }],
        h3: ["18px", { lineHeight: "24px", fontWeight: "500" }],
        body: ["16px", { lineHeight: "24px" }],
        label: ["12px", { lineHeight: "16px", letterSpacing: "0.4px", fontWeight: "600" }],
      },
      boxShadow: {
        card: "0 1px 2px rgba(16, 42, 54, 0.04), 0 4px 16px rgba(16, 42, 54, 0.05)",
        raised: "0 8px 30px rgba(16, 42, 54, 0.12)",
      },
      minWidth: { viewport: "var(--viewport-min)" },
    },
  },
  plugins: [],
};
