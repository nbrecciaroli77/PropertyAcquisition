import clsx from "clsx";
import { AlertTriangle, Check, CircleHelp, Minus, X } from "lucide-react";
import type { ReactNode } from "react";

export type ChipTone = "pass" | "fail" | "unknown" | "shortlisted" | "neutral" | "warning" | "info";

const tones: Record<ChipTone, { className: string; icon: ReactNode }> = {
  pass: { className: "bg-eucalyptus-soft text-eucalyptus-deep", icon: <Check className="h-3 w-3" aria-hidden="true" /> },
  fail: { className: "bg-risk-soft text-risk", icon: <X className="h-3 w-3" aria-hidden="true" /> },
  unknown: { className: "bg-canvas-deep text-charcoal", icon: <CircleHelp className="h-3 w-3" aria-hidden="true" /> },
  shortlisted: { className: "bg-navy-soft text-navy", icon: <Check className="h-3 w-3" aria-hidden="true" /> },
  warning: { className: "bg-ochre-soft text-ochre-deep", icon: <AlertTriangle className="h-3 w-3" aria-hidden="true" /> },
  info: { className: "bg-navy-soft text-navy", icon: <Minus className="h-3 w-3" aria-hidden="true" /> },
  neutral: { className: "bg-canvas-deep text-muted", icon: <Minus className="h-3 w-3" aria-hidden="true" /> },
};

export function StatusChip({
  tone,
  children,
  className,
  hideIcon = false,
  "data-testid": testId,
}: {
  tone: ChipTone;
  children: ReactNode;
  className?: string;
  hideIcon?: boolean;
  "data-testid"?: string;
}) {
  const t = tones[tone];
  return (
    <span
      data-testid={testId}
      data-tone={tone}
      className={clsx(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-label uppercase whitespace-nowrap",
        t.className,
        className,
      )}
    >
      {!hideIcon && <span data-testid={testId ? `${testId}-icon` : undefined} className="inline-flex">{t.icon}</span>}
      {children}
    </span>
  );
}

export const marketTone = (state: string): ChipTone =>
  state === "Active" ? "info" : state === "Under offer" ? "warning" : state === "Unknown" ? "unknown" : "neutral";

export const buyerTone = (state: string): ChipTone =>
  state === "Shortlisted" ? "shortlisted" : state === "Rejected" ? "fail" : state === "Archived" ? "neutral" : "info";
