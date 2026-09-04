import clsx from "clsx";
import type { Tri } from "../lib/types";

/** Ring showing a percentage. Unknown renders a dashed ring with "—", never 0%. */
export function FitRing({
  value,
  label,
  size = 56,
  className,
  "data-testid": testId,
}: {
  value: Tri<number>;
  label: string;
  size?: number;
  className?: string;
  "data-testid"?: string;
}) {
  const stroke = 5;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = value.state === "known" ? Math.max(0, Math.min(100, value.value)) : 0;
  const isKnown = value.state === "known";
  const tone = !isKnown ? "stroke-muted" : pct >= 80 ? "stroke-eucalyptus-deep" : pct >= 60 ? "stroke-eucalyptus" : pct >= 40 ? "stroke-ochre" : "stroke-risk";
  const text = isKnown ? `${pct}%` : "—";
  const a11y = isKnown ? `${label} ${pct} percent` : `${label} unavailable`;

  return (
    <div className={clsx("inline-flex items-center gap-2", className)} data-testid={testId} data-state={value.state}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={a11y}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-canvas-deep)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          className={tone}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={isKnown ? `${(pct / 100) * c} ${c}` : "4 6"}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" className="fill-navy font-bold" fontSize={size * 0.26}>
          {text}
        </text>
      </svg>
      <div className="leading-tight">
        <div className="text-xs text-muted">{label}</div>
        <div className="text-sm font-semibold text-navy">{isKnown ? describe(pct, label) : "Unavailable"}</div>
      </div>
    </div>
  );
}

function describe(pct: number, label: string): string {
  if (label.toLowerCase().includes("coverage")) return pct >= 80 ? "Good" : pct >= 50 ? "Moderate" : "Limited";
  return pct >= 80 ? "Strong" : pct >= 60 ? "Good" : pct >= 40 ? "Weak" : "Poor";
}
