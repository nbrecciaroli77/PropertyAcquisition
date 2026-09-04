import { readFileSync, readdirSync, statSync } from "fs";
import { join } from "path";

/** Safety suite: no UI copy may offer to send to an agent, book an inspection, or show a Value Score. */
const FORBIDDEN = [/book inspection/i, /send to agent/i, /send enquiry/i, /value score/i, /indicative value/i, /estimated value/i];

function walk(dir: string, acc: string[] = []): string[] {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) walk(p, acc);
    else if (/\.(tsx|ts)$/.test(f) && !p.includes("__tests__")) acc.push(p);
  }
  return acc;
}

describe("forbidden pathways", () => {
  it("no source file contains send/book/value-score copy", () => {
    const files = walk(join(__dirname, ".."));
    const hits: string[] = [];
    for (const f of files) {
      const text = readFileSync(f, "utf8");
      for (const re of FORBIDDEN) if (re.test(text)) hits.push(`${f}: ${re}`);
    }
    expect(hits).toEqual([]);
  });
});
