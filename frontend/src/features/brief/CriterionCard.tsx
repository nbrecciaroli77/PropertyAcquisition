import clsx from "clsx";
import type { ReactNode } from "react";
import { SelectField } from "../../components/Form";
import type { Mode } from "../../lib/api";
import { MODE_HELP, MODE_OPTIONS } from "../../lib/briefOptions";

export function CriterionCard({
  id,
  title,
  description,
  mode,
  onModeChange,
  children,
  className,
}: {
  id: string;
  title: string;
  description?: string;
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <section aria-labelledby={`${id}-heading`} className={clsx("card min-w-0 p-5", className)} data-testid={`criterion-${id}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h2 id={`${id}-heading`} className="text-base font-semibold md:text-lg">
            {title}
          </h2>
          {description && <p className="mt-1 text-sm text-muted">{description}</p>}
        </div>
        <SelectField
          id={`${id}-mode`}
          label="Treat as"
          value={mode}
          onChange={onModeChange}
          options={MODE_OPTIONS}
          className="sm:w-[190px] sm:shrink-0"
          testId={`${id}-mode`}
        />
      </div>
      <p className="mt-2 text-xs text-muted" data-testid={`${id}-mode-help`}>
        {MODE_HELP[mode]}
      </p>
      {mode !== "disabled" && mode !== "unknown" && children && <div className="mt-4 space-y-4">{children}</div>}
    </section>
  );
}
