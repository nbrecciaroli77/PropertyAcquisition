import clsx from "clsx";
import { Clock3 } from "lucide-react";
import { displayNow } from "../lib/clock";
import { formatDate, relativeDays } from "../lib/format";

export type FreshnessBand = "fresh" | "ageing" | "stale";

export const freshnessBand = (iso: string, now: Date = displayNow()): FreshnessBand => {
  const days = (now.getTime() - new Date(iso).getTime()) / 86_400_000;
  if (days <= 2) return "fresh";
  if (days <= 7) return "ageing";
  return "stale";
};

const bandLabel: Record<FreshnessBand, string> = { fresh: "Fresh", ageing: "Ageing", stale: "Stale" };
const bandDot: Record<FreshnessBand, string> = { fresh: "bg-eucalyptus-deep", ageing: "bg-ochre", stale: "bg-risk" };

export function SourceFreshness({
  source,
  checkedAt,
  now,
  className,
  "data-testid": testId,
}: {
  source: string;
  checkedAt: string;
  now?: Date;
  className?: string;
  "data-testid"?: string;
}) {
  const band = freshnessBand(checkedAt, now);
  return (
    <div className={clsx("flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted", className)} data-testid={testId} data-band={band}>
      <span className="inline-flex items-center gap-1">
        <span className={clsx("h-1.5 w-1.5 rounded-full", bandDot[band])} aria-hidden="true" />
        <span className="font-semibold text-charcoal">{bandLabel[band]}</span>
      </span>
      <span aria-hidden="true">·</span>
      <span>{source}</span>
      <span aria-hidden="true">·</span>
      <span className="inline-flex items-center gap-1">
        <Clock3 className="h-3 w-3" aria-hidden="true" />
        <time dateTime={checkedAt}>
          Checked {formatDate(checkedAt)} ({relativeDays(checkedAt, now)})
        </time>
      </span>
    </div>
  );
}
