import clsx from "clsx";
import type { ReactNode } from "react";

/** One setting in an editable layer: inherit from the next layer, or set a value here. */
export function LayerRow({
  id,
  label,
  inherited,
  inheritLabel,
  setLabel,
  onInherit,
  onSet,
  hint,
  children,
}: {
  id: string;
  label: string;
  inherited: boolean;
  inheritLabel: string;
  setLabel: string;
  onInherit: () => void;
  onSet: () => void;
  hint?: ReactNode;
  children: ReactNode;
}) {
  const option = (active: boolean, text: string, onClick: () => void, testId: string) => (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      onClick={onClick}
      data-testid={testId}
      className={clsx(
        "h-8 rounded px-3 text-xs font-semibold transition-colors duration-150",
        active ? "bg-navy text-white" : "text-navy hover:bg-canvas-deep",
      )}
    >
      {text}
    </button>
  );
  return (
    <div className="border-b border-border py-4 last:border-b-0" data-testid={id}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span id={`${id}-label`} className="text-sm font-semibold text-navy">
          {label}
        </span>
        <div role="radiogroup" aria-labelledby={`${id}-label`} className="inline-flex rounded-md border border-border bg-surface p-0.5">
          {option(inherited, inheritLabel, onInherit, `${id}-inherit`)}
          {option(!inherited, setLabel, onSet, `${id}-set`)}
        </div>
      </div>
      {!inherited && <div className="mt-3">{children}</div>}
      {hint && <p className="mt-2 text-xs text-muted">{hint}</p>}
    </div>
  );
}
