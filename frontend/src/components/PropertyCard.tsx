import clsx from "clsx";
import { Bath, BedDouble, Bookmark, Car, Home, Ruler } from "lucide-react";
import { Link } from "react-router-dom";
import { triText } from "../lib/format";
import type { SyntheticProperty } from "../lib/types";
import { EvidenceState } from "./EvidenceState";
import { FitRing } from "./FitRing";
import { SourceFreshness } from "./SourceFreshness";
import { StatusChip, buyerTone, marketTone } from "./StatusChip";

export function PropertyImagePlaceholder({ className, showLabel = true }: { className?: string; showLabel?: boolean }) {
  return (
    <div
      className={clsx(
        "relative flex items-center justify-center bg-eucalyptus-tint text-eucalyptus-deep overflow-hidden",
        "[background-image:radial-gradient(var(--color-stone)_1px,transparent_1px)] [background-size:14px_14px]",
        className,
      )}
      role="img"
      aria-label="No licensed image. Synthetic listing placeholder."
    >
      <Home className="h-8 w-8" strokeWidth={1.5} aria-hidden="true" />
      {showLabel && (
        <span className="absolute bottom-2 right-2 rounded-sm bg-surface/90 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
          No image · synthetic
        </span>
      )}
    </div>
  );
}

export function PropertyCard({ property, compact = false, headingLevel = 3 }: { property: SyntheticProperty; compact?: boolean; headingLevel?: 2 | 3 }) {
  const p = property;
  const Heading = headingLevel === 2 ? "h2" : "h3";
  return (
    <article
      data-testid={`property-card-${p.id}`}
      className="card group flex flex-col overflow-hidden transition-[box-shadow,transform] duration-200 hover:shadow-raised hover:-translate-y-0.5 focus-within:shadow-raised"
      aria-labelledby={`pc-title-${p.id}`}
    >
      <div className="relative">
        <PropertyImagePlaceholder className={compact ? "h-28" : "h-40"} />
        <div className="absolute left-3 top-3 flex gap-1.5">
          <StatusChip tone={p.gate === "Pass" ? "pass" : p.gate === "Fail" ? "fail" : "unknown"} data-testid={`property-card-gate-${p.id}`}>
            {p.gate === "Pass" ? "Gates pass" : p.gate === "Fail" ? "Known failure" : "Verification required"}
          </StatusChip>
        </div>
        <span
          className={clsx(
            "absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-md bg-surface/90",
            p.saved ? "text-navy" : "text-muted",
          )}
          aria-label={p.saved ? "Saved to shortlist" : "Not saved"}
          role="img"
        >
          <Bookmark className="h-4 w-4" fill={p.saved ? "currentColor" : "none"} aria-hidden="true" />
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <Heading id={`pc-title-${p.id}`} className="text-h3 font-semibold leading-6">
            <Link to={`/app/properties/${p.id}`} className="rounded-sm hover:underline underline-offset-4" data-testid={`property-card-link-${p.id}`}>
              {p.address}
            </Link>
          </Heading>
          <p className="text-sm text-muted">
            {p.suburb} {p.state}
          </p>
        </div>

        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="font-semibold text-navy" data-testid={`property-card-price-${p.id}`}>
            {p.rawPrice}
          </span>
          <span className="text-xs text-muted">Raw guide · {p.priceKind}</span>
        </div>

        <dl className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-charcoal">
          <Fact icon={<BedDouble className="h-4 w-4" aria-hidden="true" />} label="Bedrooms" value={triText(p.beds, String)} />
          <Fact icon={<Bath className="h-4 w-4" aria-hidden="true" />} label="Bathrooms" value={triText(p.baths, String)} />
          <Fact icon={<Car className="h-4 w-4" aria-hidden="true" />} label="Parking" value={triText(p.cars, String)} />
          <Fact icon={<Ruler className="h-4 w-4" aria-hidden="true" />} label="Land" value={triText(p.landSqm, (v) => `${v} m²`)} />
        </dl>

        <div className="flex flex-wrap gap-1.5">
          <StatusChip tone={marketTone(p.marketState)} hideIcon data-testid={`property-card-market-${p.id}`}>
            Market: {p.marketState}
          </StatusChip>
          <StatusChip tone={buyerTone(p.buyerState)} hideIcon data-testid={`property-card-buyer-${p.id}`}>
            You: {p.buyerState}
          </StatusChip>
        </div>

        {!compact && (
          <>
            <div className="grid grid-cols-2 gap-2 border-t border-border pt-3">
              <FitRing value={p.fit} label="Provisional fit" size={44} data-testid={`property-card-fit-${p.id}`} />
              <FitRing value={p.coverage} label="Evidence coverage" size={44} data-testid={`property-card-coverage-${p.id}`} />
            </div>
            <EvidenceState outcome={p.gate} reason={p.gateReason} />
            <SourceFreshness source={p.sourceLabel} checkedAt={p.lastChecked} />
          </>
        )}
      </div>
    </article>
  );
}

function Fact({ icon, label, value }: { icon: JSX.Element; label: string; value: string }) {
  return (
    <div className="inline-flex items-center gap-1">
      <dt className="text-muted">
        {icon}
        <span className="sr-only">{label}</span>
      </dt>
      <dd className={clsx(value === "Unknown" && "italic text-muted")}>{value}</dd>
    </div>
  );
}
