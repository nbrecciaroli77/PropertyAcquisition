import clsx from "clsx";
import { Check, CircleHelp, X } from "lucide-react";
import type { GateOutcome } from "../lib/types";

const outcomes: Record<GateOutcome, { className: string; icon: JSX.Element; helper: string }> = {
  Pass: { className: "bg-eucalyptus-soft text-eucalyptus-deep", icon: <Check className="h-3.5 w-3.5" aria-hidden="true" />, helper: "Evidence supports this rule" },
  Fail: { className: "bg-risk-soft text-risk", icon: <X className="h-3.5 w-3.5" aria-hidden="true" />, helper: "Known fact breaks this rule" },
  Unknown: { className: "bg-canvas-deep text-charcoal border border-dashed border-muted", icon: <CircleHelp className="h-3.5 w-3.5" aria-hidden="true" />, helper: "Unknown is not Pass — needs verification" },
};

/** Tri-state gate outcome. Unknown is visually and semantically distinct from Fail. */
export function EvidenceState({
  outcome,
  reason,
  compact = false,
  className,
  "data-testid": testId,
}: {
  outcome: GateOutcome;
  reason?: string;
  compact?: boolean;
  className?: string;
  "data-testid"?: string;
}) {
  const o = outcomes[outcome];
  return (
    <div className={clsx("flex items-start gap-2", className)} data-testid={testId} data-outcome={outcome}>
      <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-label uppercase", o.className)}>
        {o.icon}
        {outcome}
      </span>
      {!compact && <span className="text-sm text-muted leading-5">{reason ?? o.helper}</span>}
    </div>
  );
}
