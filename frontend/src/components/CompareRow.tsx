import clsx from "clsx";
import type { ReactNode } from "react";
import type { Tri } from "../lib/types";

export interface CompareCell {
  /** Rendered value. Use `unknown` for Unknown so the cell is visually and semantically distinct. */
  value: ReactNode;
  state?: Tri<unknown>["state"];
  tone?: "neutral" | "good" | "bad";
}

/**
 * One attribute row of a comparison. Desktop: grid row. Phone: stacked block with the attribute as heading.
 * Unknown cells never show a dash that could be read as "none" — they say "Unknown".
 */
export function CompareRow({
  attribute,
  hint,
  cells,
  columns,
  className,
  "data-testid": testId,
}: {
  attribute: string;
  hint?: string;
  cells: CompareCell[];
  columns: string[];
  className?: string;
  "data-testid"?: string;
}) {
  return (
    <div
      role="row"
      data-testid={testId}
      className={clsx("border-b border-border last:border-b-0 md:grid md:items-center", className)}
      style={{ gridTemplateColumns: `minmax(160px, 1.2fr) repeat(${cells.length}, minmax(0, 1fr))` }}
    >
      <div role="rowheader" className="px-4 pt-3 md:py-3">
        <div className="text-sm font-semibold text-navy">{attribute}</div>
        {hint && <div className="text-xs text-muted">{hint}</div>}
      </div>
      {cells.map((cell, i) => {
        const isUnknown = cell.state === "unknown";
        const isNa = cell.state === "not-applicable";
        return (
          <div
            role="cell"
            key={columns[i]}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 text-sm md:py-3",
              isUnknown && "italic text-muted",
              cell.tone === "good" && "text-eucalyptus-deep",
              cell.tone === "bad" && "text-risk",
            )}
            data-state={cell.state ?? "known"}
          >
            <span className="w-24 shrink-0 text-xs text-muted md:hidden" aria-hidden="true">
              {columns[i]}
            </span>
            {isUnknown ? (
              <span className="inline-flex items-center gap-1 rounded-sm border border-dashed border-muted px-1.5 py-0.5 text-xs not-italic text-charcoal">
                Unknown
              </span>
            ) : isNa ? (
              <span className="text-xs text-muted">Not applicable</span>
            ) : (
              cell.value
            )}
          </div>
        );
      })}
    </div>
  );
}
