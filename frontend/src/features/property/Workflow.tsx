import { Bookmark, CheckSquare, Scale, Square } from "lucide-react";
import { useState } from "react";
import { Button } from "../../components/Button";
import { formatDate } from "../../lib/format";
import { BUYER_STATES, buyerLabel, propertyApi, type PropertyDetail } from "../../lib/properties";
import { useCompareSelection } from "../properties/hooks";

interface Props {
  p: PropertyDetail;
  busy: boolean;
  mutate: (fn: (journeyId: string) => Promise<PropertyDetail>, notice?: string) => Promise<void>;
}

/** Buyer-owned workflow: stage transitions (allowed only), save, compare. Source updates never touch these. */
export function Workflow({ p, busy, mutate }: Props) {
  const [target, setTarget] = useState("");
  const compare = useCompareSelection();
  const inCompare = compare.ids.includes(p.id);
  return (
    <section aria-labelledby="workflow-heading" className="card p-5" data-testid="workflow-panel">
      <h2 id="workflow-heading" className="text-h3 font-semibold">
        Your workflow
      </h2>
      <p className="mt-1 text-sm text-muted">
        Currently <strong className="text-navy">{buyerLabel(p.buyer_state)}</strong>. Only allowed transitions are offered; each change records who and when.
      </p>
      <form
        className="mt-3 flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (!target) return;
          void mutate((j) => propertyApi.stage(j, p.id, target, p.buyer_row_version), `Moved to ${buyerLabel(target)}.`).then(() => setTarget(""));
        }}
      >
        <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
          <span className="label">Move to</span>
          <select value={target} onChange={(e) => setTarget(e.target.value)} className="h-10 rounded-md border border-border bg-surface px-2 text-sm" data-testid="stage-select">
            <option value="">Choose a stage…</option>
            {BUYER_STATES.filter((s) => p.allowed_transitions.includes(s.key)).map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <Button type="submit" size="sm" disabled={busy || !target} data-testid="stage-submit">
          Change stage
        </Button>
      </form>
      {p.evaluation?.verdict === "fail" && (
        <p className="mt-2 text-xs text-ochre-deep" data-testid="promotion-blocked-note">
          This property has a known hard-rule failure. It cannot move forward unless every failing rule carries a reasoned waiver — and even then the gate still reads Fail.
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant={p.saved ? "primary" : "secondary"} size="sm" disabled={busy} icon={<Bookmark className="h-4 w-4" fill={p.saved ? "currentColor" : "none"} aria-hidden="true" />} onClick={() => void mutate((j) => propertyApi.setSaved(j, p.id, !p.saved, p.buyer_row_version), p.saved ? "Removed from shortlist." : "Saved to shortlist.")} data-testid="toggle-saved" aria-pressed={p.saved}>
          {p.saved ? "Saved" : "Save to shortlist"}
        </Button>
        <Button variant={inCompare ? "primary" : "secondary"} size="sm" disabled={!inCompare && compare.full} icon={<Scale className="h-4 w-4" aria-hidden="true" />} onClick={() => compare.toggle(p.id)} data-testid="toggle-compare" aria-pressed={inCompare}>
          {inCompare ? "In compare" : compare.full ? "Compare full (4)" : "Add to compare"}
        </Button>
      </div>
      <dl className="mt-4 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 text-xs text-muted">
        <dt>Stage changed</dt>
        <dd>{p.activity.find((a) => a.kind === "stage_changed") ? formatDate(p.activity.find((a) => a.kind === "stage_changed")!.created_at) : "Not yet"}</dd>
        <dt>Record version</dt>
        <dd>{p.buyer_row_version}</dd>
      </dl>
      <ul className="mt-3 space-y-1 text-xs text-muted" aria-label="Safeguards">
        <li className="flex items-center gap-1.5">
          <CheckSquare className="h-3.5 w-3.5 text-eucalyptus-deep" aria-hidden="true" /> Nothing here contacts an agent or books anything.
        </li>
        <li className="flex items-center gap-1.5">
          <Square className="h-3.5 w-3.5" aria-hidden="true" /> Reminders and drafts arrive in Milestone 5.
        </li>
      </ul>
    </section>
  );
}
