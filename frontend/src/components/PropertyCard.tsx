import clsx from "clsx";
import { Bath, BedDouble, Bookmark, Car, Home, Ruler, Scale } from "lucide-react";
import { Link } from "react-router-dom";
import { triText } from "../lib/format";
import {
  buyerLabel,
  coverageTri,
  factTri,
  fitTri,
  gateLabel,
  gateReason,
  marketLabel,
  priceKindLabel,
  verdictText,
  type PropertySummary,
} from "../lib/properties";
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

/** Optional image with source attribution; text-only fallback when none is licensed. */
export function PropertyImage({ property, className, showLabel = true }: { property: PropertySummary; className?: string; showLabel?: boolean }) {
  if (!property.image_url) return <PropertyImagePlaceholder className={className} showLabel={showLabel} />;
  return (
    <figure className={clsx("relative overflow-hidden", className)}>
      <img src={property.image_url} alt={`${property.address_line}, ${property.suburb}`} className="h-full w-full object-cover" />
      {showLabel && (
        <figcaption className="absolute bottom-2 right-2 rounded-sm bg-surface/90 px-1.5 py-0.5 text-[10px] font-semibold text-muted">
          {property.image_attribution ?? "Source not recorded"}
        </figcaption>
      )}
    </figure>
  );
}

export function PropertyCard({
  property,
  compact = false,
  headingLevel = 3,
  compareSelected,
  onToggleCompare,
  compareDisabled,
}: {
  property: PropertySummary;
  compact?: boolean;
  headingLevel?: 2 | 3;
  compareSelected?: boolean;
  onToggleCompare?: (id: string) => void;
  compareDisabled?: boolean;
}) {
  const p = property;
  const Heading = headingLevel === 2 ? "h2" : "h3";
  const verdict = p.evaluation?.verdict;
  const market = marketLabel(p.campaign?.market_state);
  const buyer = buyerLabel(p.buyer_state);
  const rawPrice = p.campaign?.raw_price ?? "No campaign";
  return (
    <article
      data-testid={`property-card-${p.id}`}
      data-legacy-ref={p.legacy_ref ?? undefined}
      className="card group flex flex-col overflow-hidden transition-[box-shadow,transform] duration-200 hover:shadow-raised hover:-translate-y-0.5 focus-within:shadow-raised"
      aria-labelledby={`pc-title-${p.id}`}
    >
      <div className="relative">
        <PropertyImage property={p} className={compact ? "h-28" : "h-40"} />
        <div className="absolute left-3 top-3 flex gap-1.5">
          <StatusChip tone={verdict === "pass" ? "pass" : verdict === "fail" ? "fail" : "unknown"} data-testid={`property-card-gate-${p.id}`}>
            {p.evaluation ? verdictText(verdict) : "Not evaluated"}
          </StatusChip>
        </div>
        <span
          className={clsx("absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-md bg-surface/90", p.saved ? "text-navy" : "text-muted")}
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
              {p.address_line}
            </Link>
          </Heading>
          <p className="text-sm text-muted">
            {p.suburb} {p.state}
            {p.synthetic && <span className="ml-2 text-[11px] uppercase tracking-wide">synthetic</span>}
          </p>
        </div>

        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="font-semibold text-navy" data-testid={`property-card-price-${p.id}`}>
            {rawPrice}
          </span>
          <span className="text-xs text-muted">Raw guide · {priceKindLabel(p.campaign?.price_kind)}</span>
        </div>

        <dl className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-charcoal">
          <Fact icon={<BedDouble className="h-4 w-4" aria-hidden="true" />} label="Bedrooms" value={triText(factTri(p, "beds"), String)} />
          <Fact icon={<Bath className="h-4 w-4" aria-hidden="true" />} label="Bathrooms" value={triText(factTri(p, "baths"), String)} />
          <Fact icon={<Car className="h-4 w-4" aria-hidden="true" />} label="Parking" value={triText(factTri(p, "cars"), String)} />
          <Fact icon={<Ruler className="h-4 w-4" aria-hidden="true" />} label="Land" value={triText(factTri(p, "land_sqm"), (v) => `${v} m²`)} />
        </dl>

        <div className="flex flex-wrap gap-1.5">
          <StatusChip tone={marketTone(market)} hideIcon data-testid={`property-card-market-${p.id}`}>
            Market: {market}
          </StatusChip>
          <StatusChip tone={buyerTone(buyer)} hideIcon data-testid={`property-card-buyer-${p.id}`}>
            You: {buyer}
          </StatusChip>
        </div>

        {!compact && (
          <>
            <div className="grid grid-cols-2 gap-2 border-t border-border pt-3">
              <FitRing value={fitTri(p)} label="Assessed fit" size={44} data-testid={`property-card-fit-${p.id}`} />
              <FitRing value={coverageTri(p)} label="Evidence coverage" size={44} data-testid={`property-card-coverage-${p.id}`} />
            </div>
            <EvidenceState outcome={p.evaluation ? gateLabel(verdict) : "Unknown"} reason={gateReason(p)} />
            {p.campaign && <SourceFreshness source={p.campaign.source_label} checkedAt={p.campaign.last_checked_at} />}
          </>
        )}

        {onToggleCompare && (
          <button
            type="button"
            onClick={() => onToggleCompare(p.id)}
            disabled={!compareSelected && compareDisabled}
            aria-pressed={compareSelected}
            data-testid={`property-card-compare-${p.id}`}
            className={clsx(
              "mt-auto inline-flex h-9 items-center justify-center gap-1.5 rounded-md border px-3 text-sm font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50",
              compareSelected ? "border-navy bg-navy text-white" : "border-border bg-surface text-navy hover:border-navy",
            )}
          >
            <Scale className="h-4 w-4" aria-hidden="true" />
            {compareSelected ? "In compare" : compareDisabled ? "Compare full (4)" : "Add to compare"}
          </button>
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
