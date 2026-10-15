import { Ban, CircleHelp, Info } from "lucide-react";
import { StatusChip } from "../../components/StatusChip";
import { ceilingText, landStatusText, landTone, money, sqm, verificationText } from "../../lib/land";
import type { GateOut, LandAssessment as Land } from "../../lib/properties";

const tone = (o: GateOut["outcome"]) => (o === "pass" ? "pass" : o === "fail" ? "fail" : "unknown");
const outcomeText = (o: GateOut["outcome"]) => (o === "pass" ? "Supported" : o === "fail" ? "Documented failure" : "Unknown");

function Row({ label, value, testId }: { label: string; value: string; testId: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border/60 py-1.5 text-sm last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-medium text-navy" data-testid={testId}>{value}</dd>
    </div>
  );
}

function EvidenceList({ title, items, testId }: { title: string; items: GateOut[]; testId: string }) {
  return (
    <section className="card p-5" data-testid={testId}>
      <h3 className="text-h3 font-semibold">{title}</h3>
      <ul className="mt-3 space-y-2">
        {items.map((g) => (
          <li key={g.criterion} className="rounded-md bg-canvas px-3 py-2" data-testid={`land-item-${g.criterion}`} data-outcome={g.outcome}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold text-navy">{g.label}</span>
              <StatusChip tone={tone(g.outcome)} hideIcon>{outcomeText(g.outcome)}</StatusChip>
            </div>
            <p className="mt-1 text-sm text-muted">{g.reason}</p>
            <p className="mt-0.5 text-xs text-muted">Requirement: {g.brief_value} · Observed: {g.observed} · Source: {g.source_label || "None yet"}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function PriceAndArea({ land }: { land: Land }) {
  const p = land.price;
  return (
    <section className="card p-5" data-testid="land-price-area">
      <h3 className="text-h3 font-semibold">Price and area evidence</h3>
      <dl className="mt-3">
        <Row label="Advertised / package amount" value={p.advertised_raw || money(p.advertised_minor)} testId="land-advertised" />
        <Row label="Price kind" value={p.price_kind.replace(/_/g, " ")} testId="land-price-kind" />
        <Row label="Opportunity type" value={p.subtype ? p.subtype.replace(/_/g, " ") : "Unknown"} testId="land-subtype" />
        <Row label="Supported land component" value={money(p.land_component_minor)} testId="land-component" />
        <Row label="Supported land price (used for the cap)" value={money(p.supported_land_price_minor)} testId="land-supported-price" />
        <Row label="Seller ceiling" value={ceilingText(p.seller_ceiling)} testId="land-seller-ceiling" />
        <Row label="Total lot area" value={sqm(land.area.total_sqm)} testId="land-total-area" />
        <Row label="Usable area" value={sqm(land.area.usable_sqm)} testId="land-usable-area" />
      </dl>
      {verificationText(p.verification) && (
        <p className="mt-3 rounded-md border border-ochre/40 bg-ochre-soft px-3 py-2 text-sm text-ochre-deep" data-testid="land-price-verification">
          Price verification: {verificationText(p.verification)}
        </p>
      )}
    </section>
  );
}

function Travel({ land }: { land: Land }) {
  const t = land.travel;
  const state = t.state === "met" ? "Within preference" : t.state === "missed" ? "Soft preference missed" : "Unknown";
  return (
    <section className="card p-5" data-testid="land-travel">
      <h3 className="text-h3 font-semibold">Travel and location (preferences only)</h3>
      <dl className="mt-3">
        <Row label="Driving time" value={t.minutes === null ? "Unknown" : `${t.minutes} min`} testId="land-drive-minutes" />
        <Row label={`Preference (about ${t.preferred_minutes} min)`} value={state} testId="land-travel-state" />
        <Row label="Origin" value={t.origin ?? "Unknown"} testId="land-travel-origin" />
        <Row label="Location" value={land.location.tier === "priority_town" ? "Priority town" : "Surrounds / broader region"} testId="land-location-tier" />
      </dl>
      <p className="mt-2 text-xs text-muted" data-testid="land-travel-note">{t.note}</p>
    </section>
  );
}

export function LandAssessment({ land, gates }: { land: Land; gates: GateOut[] }) {
  return (
    <div className="space-y-6" data-testid="land-assessment">
      <section className="card p-5" data-testid="land-summary">
        <div className="flex flex-wrap items-center gap-3">
          <StatusChip tone={landTone(land)} data-testid="land-status-chip">{landStatusText(land)}</StatusChip>
          <span className="text-xs text-muted">Land feasibility v1 · ordinal research priority, not a score out of 100</span>
        </div>
        <p className="mt-3 text-sm" data-testid="land-explanation">{land.explanation}</p>
        {land.failures.length > 0 && (
          <ul className="mt-3 space-y-1 text-sm text-risk" data-testid="land-failures">
            {land.failures.map((f) => (<li key={f.criterion} className="flex gap-2"><Ban className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />{f.reason}</li>))}
          </ul>
        )}
        {land.gaps.length > 0 && (
          <div className="mt-3" data-testid="land-gaps">
            <p className="text-sm font-semibold text-navy">Named verification gaps ({land.gaps.length})</p>
            <ul className="mt-1 flex flex-wrap gap-2">
              {land.gaps.map((g) => (<li key={g.criterion} className="inline-flex items-center gap-1 rounded-full bg-canvas px-2.5 py-1 text-xs"><CircleHelp className="h-3 w-3" aria-hidden="true" />{g.label}</li>))}
            </ul>
          </div>
        )}
        {land.shed_note && (<p className="mt-3 rounded-md border border-ochre/40 bg-ochre-soft px-3 py-2 text-sm text-ochre-deep" data-testid="land-shed-note">{land.shed_note}</p>)}
        <p className="mt-3 flex gap-2 text-xs text-muted" data-testid="land-disclaimer">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          Evidence is recorded, but approval is never guaranteed. A shed or a listing claim is not permission to live on the land. Completed-project budget and Airbnb are inactive.
        </p>
      </section>
      <PriceAndArea land={land} />
      <EvidenceList title="Hard gates" items={gates} testId="land-gates" />
      <EvidenceList title="Title, approvals, hazards and services to verify" items={land.checks} testId="land-checks" />
      <Travel land={land} />
    </div>
  );
}
