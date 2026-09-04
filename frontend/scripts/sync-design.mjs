import { readFileSync, writeFileSync, copyFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const fixtures = resolve(root, "..", "fixtures");

const tokens = JSON.parse(readFileSync(resolve(fixtures, "design-tokens.json"), "utf8"));

// Derived, documented and reversible. Base tokens come verbatim from design-tokens.json.
const derived = {
  "eucalyptus-deep": "#3D6B51", // accessible text/button variant of eucalyptus (>= 4.5:1 on surface)
  "eucalyptus-soft": "#E7EFE6",
  "eucalyptus-tint": "#F1F6F2",
  "ochre-deep": "#8A5A2B", // accessible text variant of ochre
  "ochre-soft": "#F7EBDD",
  "risk-soft": "#F5E4E0",
  "navy-soft": "#E4EAEE",
  "charcoal": "#2A2E33",
  "stone": "#D9DDD7",
  "canvas-deep": "#EFEAE1",
};

const lines = [":root {"];
for (const [k, v] of Object.entries(tokens.colors)) lines.push(`  --color-${kebab(k)}: ${v};`);
for (const [k, v] of Object.entries(derived)) lines.push(`  --color-${k}: ${v};`);
lines.push(`  --font-sans: "${tokens.typography.preferred}", ${tokens.typography.fallback};`);
for (const [k, v] of Object.entries(tokens.radius)) lines.push(`  --radius-${k}: ${v}px;`);
lines.push(`  --viewport-min: ${tokens.layout.minimumViewportCssPx}px;`);
// 4px spacing scale (derived — tokens file has no spacing scale)
[1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24].forEach((n) => lines.push(`  --space-${n}: ${n * 4}px;`));
lines.push("}");

mkdirSync(resolve(root, "src/design"), { recursive: true });
writeFileSync(
  resolve(root, "src/design/tokens.css"),
  `/* GENERATED from fixtures/design-tokens.json by scripts/sync-design.mjs — do not edit by hand */\n${lines.join("\n")}\n`,
);
writeFileSync(
  resolve(root, "src/design/tokens.json"),
  JSON.stringify({ ...tokens, derivedColors: derived }, null, 2) + "\n",
);
mkdirSync(resolve(root, "src/data"), { recursive: true });
copyFileSync(resolve(fixtures, "demo-data.json"), resolve(root, "src/data/demo-data.json"));

function kebab(s) {
  return s.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());
}
console.log("design tokens + fixtures synced");
