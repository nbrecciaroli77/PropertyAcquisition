import { RotateCcw } from "lucide-react";
import { Button } from "../../components/Button";
import { FormNotice } from "../../components/Form";
import type { BriefPayload } from "../../lib/api";

type WeightKey = "price" | "land" | "location" | "condition";

const ROWS: { key: WeightKey; label: string; help: string }[] = [
  { key: "price", label: "Price", help: "How close the guide is to your preferred range." },
  { key: "land", label: "Land", help: "Land area against your preferred range." },
  { key: "location", label: "Location", help: "Suburb and area preference tiers." },
  { key: "condition", label: "Condition", help: "Renovation tolerance against reported condition." },
];

export function WeightsEditor({
  weights,
  totalEnabled,
  error,
  onChange,
  onReset,
  busy,
}: {
  weights: BriefPayload["weights"];
  totalEnabled: number;
  error?: string;
  onChange: (key: WeightKey, value: number | null, enabled?: boolean) => void;
  onReset: () => void;
  busy: boolean;
}) {
  return (
    <section aria-labelledby="weights-heading" className="card min-w-0 p-5" data-testid="weights-editor">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 id="weights-heading" className="text-base font-semibold md:text-lg">
            Preference weights
          </h2>
          <p className="mt-1 text-sm text-muted">
            Preferences are scored separately from hard rules and from evidence coverage. A weight never overrides a
            known hard failure.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={onReset}
          disabled={busy}
          icon={<RotateCcw className="h-4 w-4" aria-hidden="true" />}
          data-testid="weights-reset"
        >
          Reset to 30 / 30 / 20 / 20
        </Button>
      </div>

      <ul className="mt-4 space-y-4">
        {ROWS.map(({ key, label, help }) => {
          const enabled = weights[`${key}_enabled`];
          return (
            <li key={key} className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
              <div className="min-w-0">
                <label htmlFor={`weight-${key}`} className="text-sm font-semibold">
                  {label}
                </label>
                <p className="text-xs text-muted">{help}</p>
              </div>
              <div className="flex items-center gap-3">
                <input
                  id={`weight-${key}`}
                  type="number"
                  min={0}
                  max={100}
                  value={String(weights[key])}
                  disabled={!enabled}
                  onChange={(e) => onChange(key, e.target.value === "" ? 0 : Number(e.target.value))}
                  className="h-11 w-20 rounded-md border border-border bg-surface px-3 text-sm disabled:bg-canvas disabled:text-muted"
                  data-testid={`weight-${key}`}
                />
                <label className="flex items-center gap-2 text-xs font-semibold">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(e) => onChange(key, null, e.target.checked)}
                    className="h-4 w-4 accent-[var(--color-eucalyptus-deep)]"
                    data-testid={`weight-${key}-enabled`}
                  />
                  Enabled
                </label>
              </div>
            </li>
          );
        })}
      </ul>

      <p className="mt-4 text-sm" data-testid="weights-total">
        Enabled weight total: <strong className="font-semibold">{totalEnabled}</strong>
        {totalEnabled !== 100 && totalEnabled > 0 && (
          <span className="text-muted"> · scores are normalised against this total</span>
        )}
      </p>
      {error && (
        <div className="mt-3">
          <FormNotice tone="error" testId="weights-error">
            {error}
          </FormNotice>
        </div>
      )}
    </section>
  );
}
