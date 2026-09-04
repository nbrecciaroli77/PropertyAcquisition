import { ArrowLeft, Bath, BedDouble, Car, Ruler } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { ButtonLink } from "../../components/Button";
import { EvidenceState } from "../../components/EvidenceState";
import { FitRing } from "../../components/FitRing";
import { MilestoneNote } from "../../components/Page";
import { PropertyImagePlaceholder } from "../../components/PropertyCard";
import { SourceFreshness } from "../../components/SourceFreshness";
import { EmptyState } from "../../components/States";
import { StatusChip, buyerTone, marketTone } from "../../components/StatusChip";
import { triText } from "../../lib/format";
import { brief, findProperty } from "../../lib/synthetic";
import type { GateOutcome } from "../../lib/types";

export default function PropertyDetailPage() {
  const { id = "" } = useParams();
  const p = findProperty(id);
  if (!p) {
    return (
      <>
        <h1 className="sr-only">Property not found</h1>
        <EmptyState
          title="Property not found"
          description="This synthetic property does not exist in the fixture. Deep links to other workspaces will return the same message."
          data-testid="property-not-found"
          action={
            <ButtonLink to="/app/discover" variant="secondary" size="sm" data-testid="property-not-found-back">
              Back to Discover
            </ButtonLink>
          }
        />
      </>
    );
  }

  const gates: { rule: string; briefValue: string; observed: string; outcome: GateOutcome }[] = [
    { rule: "Price ceiling", briefValue: `≤ $${(brief.hardRules.maxPrice / 1_000_000).toFixed(1)}m`, observed: p.rawPrice, outcome: p.priceKind === "Contact agent" || p.priceKind === "Conflicting" || p.priceKind === "Expressions of interest" ? "Unknown" : (p.lowerPrice ?? 0) <= brief.hardRules.maxPrice ? "Pass" : "Fail" },
    { rule: "Property type", briefValue: brief.hardRules.propertyType, observed: "Detached house (synthetic)", outcome: "Pass" },
    { rule: "Bedrooms", briefValue: `≥ ${brief.hardRules.minBeds}`, observed: triText(p.beds, String), outcome: p.beds.state === "known" ? (p.beds.value >= brief.hardRules.minBeds ? "Pass" : "Fail") : "Unknown" },
    { rule: "Bathrooms", briefValue: `≥ ${brief.hardRules.minBaths}`, observed: triText(p.baths, String), outcome: p.baths.state === "known" ? (p.baths.value >= brief.hardRules.minBaths ? "Pass" : "Fail") : "Unknown" },
    { rule: "Land size", briefValue: `≥ ${brief.hardRules.minLandSqm} m²`, observed: triText(p.landSqm, (v) => `${v} m²`), outcome: p.landSqm.state === "known" ? (p.landSqm.value >= brief.hardRules.minLandSqm ? "Pass" : "Fail") : "Unknown" },
  ];

  return (
    <>
      <Link to="/app/discover" className="inline-flex items-center gap-1 text-sm font-semibold text-eucalyptus-deep hover:underline underline-offset-4" data-testid="back-to-discover">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to Discover
      </Link>

      <header className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between" data-testid="property-header">
        <div>
          <div className="flex flex-wrap gap-1.5">
            <StatusChip tone={marketTone(p.marketState)} hideIcon>
              Market: {p.marketState}
            </StatusChip>
            <StatusChip tone={buyerTone(p.buyerState)} hideIcon>
              You: {p.buyerState}
            </StatusChip>
          </div>
          <h1 className="mt-2 text-display">
            {p.address}, {p.suburb} {p.state}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-charcoal">
            <span className="text-lg font-semibold text-navy">{p.rawPrice}</span>
            <span className="text-xs text-muted">Raw guide · {p.priceKind} · not a valuation</span>
          </div>
          <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
            <Fact icon={<BedDouble className="h-4 w-4" aria-hidden="true" />} label="Bedrooms" value={triText(p.beds, String)} />
            <Fact icon={<Bath className="h-4 w-4" aria-hidden="true" />} label="Bathrooms" value={triText(p.baths, String)} />
            <Fact icon={<Car className="h-4 w-4" aria-hidden="true" />} label="Parking" value={triText(p.cars, String)} />
            <Fact icon={<Ruler className="h-4 w-4" aria-hidden="true" />} label="Land" value={triText(p.landSqm, (v) => `${v} m²`)} />
          </dl>
        </div>
        {p.gate === "Unknown" && (
          <div className="rounded-md border border-ochre/40 bg-ochre-soft px-4 py-3 text-sm text-ochre-deep lg:max-w-xs" role="note" data-testid="unknown-not-pass-note">
            <strong className="font-semibold">Unknown is not Pass.</strong> Unknown means unverified — it may or may not meet the brief.
          </div>
        )}
      </header>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(300px,1fr)]">
        <div className="min-w-0 space-y-6">
          <PropertyImagePlaceholder className="h-56 rounded-lg md:h-72" />

          <section aria-labelledby="gates-heading" className="card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 id="gates-heading" className="text-h3 font-semibold">
                Hard rules
              </h2>
              <div className="flex gap-4">
                <FitRing value={p.fit} label="Provisional fit" size={48} data-testid="detail-fit" />
                <FitRing value={p.coverage} label="Evidence coverage" size={48} data-testid="detail-coverage" />
              </div>
            </div>
            <p className="mt-3 text-xs text-muted md:hidden" id="rules-scroll-hint">
              Scroll sideways to see every column.
            </p>
            <div className="-mx-5 mt-2 overflow-x-auto px-5" role="region" aria-label="Hard rules table" aria-describedby="rules-scroll-hint" tabIndex={0}>
              <table className="w-full min-w-[520px] text-sm">
                <thead>
                  <tr className="label text-left">
                    <th scope="col" className="py-2 pr-3 font-semibold">
                      Criterion
                    </th>
                    <th scope="col" className="py-2 pr-3 font-semibold">
                      Brief
                    </th>
                    <th scope="col" className="py-2 pr-3 font-semibold">
                      Observed
                    </th>
                    <th scope="col" className="py-2 font-semibold">
                      Outcome
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {gates.map((g) => (
                    <tr key={g.rule} data-testid={`gate-row-${g.rule.toLowerCase().replace(/\s+/g, "-")}`}>
                      <th scope="row" className="py-2.5 pr-3 text-left font-medium">
                        {g.rule}
                      </th>
                      <td className="py-2.5 pr-3 text-charcoal">{g.briefValue}</td>
                      <td className={g.observed === "Unknown" ? "py-2.5 pr-3 italic text-muted" : "py-2.5 pr-3"}>{g.observed}</td>
                      <td className="py-2.5">
                        <EvidenceState outcome={g.outcome} compact />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-sm text-muted">{p.gateReason}. Brief v{brief.version} · display-only evaluation until Milestone 3.</p>
          </section>
        </div>

        <aside className="min-w-0 space-y-6">
          <section aria-labelledby="evidence-heading" className="card p-5">
            <h2 id="evidence-heading" className="text-h3 font-semibold">
              Source evidence
            </h2>
            <SourceFreshness className="mt-3" source={p.sourceLabel} checkedAt={p.lastChecked} />
            <p className="mt-3 text-sm text-muted">Every critical fact above carries its source or a user-entry label. Conflicts are shown, never averaged.</p>
          </section>
          <section aria-labelledby="context-heading" className="card p-5">
            <h2 id="context-heading" className="text-h3 font-semibold">
              Context
            </h2>
            <dl className="mt-3 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 text-sm">
              <dt className="text-muted">Condition</dt>
              <dd className={p.condition ? "" : "italic text-muted"}>{p.condition ?? "Unknown"}</dd>
              <dt className="text-muted">Location tier</dt>
              <dd>{p.locationTier}</dd>
              <dt className="text-muted">Legacy ref</dt>
              <dd>{p.legacyRef}</dd>
            </dl>
          </section>
        </aside>
      </div>

      <MilestoneNote milestone={3}>Notes, tasks, inspections, contacts, documents, activity history and the versioned matching engine arrive with the property domain.</MilestoneNote>
    </>
  );
}

function Fact({ icon, label, value }: { icon: JSX.Element; label: string; value: string }) {
  return (
    <div className="inline-flex items-center gap-1.5">
      <dt className="text-muted">
        {icon}
        <span className="sr-only">{label}</span>
      </dt>
      <dd className={value === "Unknown" ? "italic text-muted" : ""}>{value}</dd>
    </div>
  );
}
