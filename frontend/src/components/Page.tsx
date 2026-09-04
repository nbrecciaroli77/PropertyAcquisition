import clsx from "clsx";
import { FlaskConical } from "lucide-react";
import type { ReactNode } from "react";

export function SyntheticBanner({ className }: { className?: string }) {
  return (
    <div
      data-testid="synthetic-data-banner"
      className={clsx(
        "flex items-center gap-2 border-b border-ochre/40 bg-ochre-soft px-4 py-1.5 text-xs text-ochre-deep",
        className,
      )}
      role="note"
    >
      <FlaskConical className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span>
        <strong className="font-semibold">Synthetic display data.</strong> Fictional properties from the demo fixture — not current
        listings. No sources are connected.
      </span>
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  testId,
}: {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  testId?: string;
}) {
  return (
    <header className="mb-6 flex flex-col gap-4 md:mb-8 md:flex-row md:items-end md:justify-between" data-testid={testId}>
      <div>
        {eyebrow && <p className="label mb-1 text-eucalyptus-deep">{eyebrow}</p>}
        <h1 className="text-display">{title}</h1>
        {description && <p className="mt-2 max-w-prose text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function MetricCard({
  value,
  label,
  helper,
  tone = "neutral",
  icon,
  testId,
}: {
  value: ReactNode;
  label: string;
  helper: string;
  tone?: "neutral" | "good" | "warning" | "risk" | "info";
  icon: ReactNode;
  testId?: string;
}) {
  const tones = {
    neutral: "bg-canvas-deep text-navy",
    good: "bg-eucalyptus-soft text-eucalyptus-deep",
    warning: "bg-ochre-soft text-ochre-deep",
    risk: "bg-risk-soft text-risk",
    info: "bg-navy-soft text-navy",
  } as const;
  return (
    <div className="card flex items-center gap-4 p-4" data-testid={testId}>
      <span className={clsx("inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full", tones[tone])}>{icon}</span>
      <div className="min-w-0">
        <div className="text-h2 leading-7">{value}</div>
        <div className="text-sm font-semibold text-navy">{label}</div>
        <div className="text-xs text-muted">{helper}</div>
      </div>
    </div>
  );
}

export function MilestoneNote({ milestone, children }: { milestone: number; children: ReactNode }) {
  return (
    <p className="card mt-8 border-dashed p-4 text-sm text-muted" data-testid="milestone-note">
      <span className="label mr-2 text-navy">Milestone {milestone}</span>
      {children}
    </p>
  );
}
