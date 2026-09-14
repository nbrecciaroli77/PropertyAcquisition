import clsx from "clsx";
import { ArrowLeft, Bath, BedDouble, Car, Ruler } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ButtonLink } from "../../components/Button";
import { PropertyImage } from "../../components/PropertyCard";
import { SourceFreshness } from "../../components/SourceFreshness";
import { EmptyState, ErrorState, Skeleton } from "../../components/States";
import { StatusChip, buyerTone, marketTone } from "../../components/StatusChip";
import { formatDate, triText } from "../../lib/format";
import { buyerLabel, factText, factTri, humanise, marketLabel, priceKindLabel } from "../../lib/properties";
import { MatchEvidence } from "./MatchEvidence";
import { Activity, Notes, Tasks } from "./NotesTasksActivity";
import { InspectionFeedback, Workflow } from "./Workflow";
import { usePropertyDetail } from "./usePropertyDetail";

export default function PropertyDetailPage() {
  const { id = "" } = useParams();
  const [search] = useSearchParams();
  const view = search.get("view") === "match" ? "match" : "overview";
  const { status, data: p, message, busy, notice, reload, mutate } = usePropertyDetail(id);

  if (status === "loading") return <Skeleton className="h-64" label="Loading property" />;
  if (status === "error") return <ErrorState description={message ?? "This property could not be loaded."} onRetry={reload} />;
  if (status === "not-found" || status === "no-journey" || !p) {
    return (
      <>
        <h1 className="sr-only">Property not found</h1>
        <EmptyState
          title="Property not found"
          description="This property is not in your workspace. Deep links to other households return the same message."
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

  const market = marketLabel(p.campaign?.market_state);
  const buyer = buyerLabel(p.buyer_state);
  const verdict = p.evaluation?.verdict;

  return (
    <>
      <Link to="/app/discover" className="inline-flex items-center gap-1 text-sm font-semibold text-eucalyptus-deep hover:underline underline-offset-4" data-testid="back-to-discover">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to Discover
      </Link>

      <header className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between" data-testid="property-header" data-legacy-ref={p.legacy_ref ?? undefined}>
        <div className="min-w-0">
          <div className="flex flex-wrap gap-1.5">
            <StatusChip tone={marketTone(market)} hideIcon data-testid="detail-market-state">
              Market: {market}
            </StatusChip>
            <StatusChip tone={buyerTone(buyer)} hideIcon data-testid="detail-buyer-state">
              You: {buyer}
            </StatusChip>
            {p.synthetic && (
              <StatusChip tone="neutral" hideIcon>
                Synthetic fixture
              </StatusChip>
            )}
          </div>
          <h1 className="mt-2 text-display">
            {p.address_line}, {p.suburb} {p.state}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-charcoal">
            <span className="text-lg font-semibold text-navy" data-testid="detail-raw-price">
              {p.campaign?.raw_price ?? "No campaign recorded"}
            </span>
            <span className="text-xs text-muted">Raw guide · {priceKindLabel(p.campaign?.price_kind)} · not a valuation</span>
          </div>
          <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
            <Fact icon={<BedDouble className="h-4 w-4" aria-hidden="true" />} label="Bedrooms" value={triText(factTri(p, "beds"), String)} />
            <Fact icon={<Bath className="h-4 w-4" aria-hidden="true" />} label="Bathrooms" value={triText(factTri(p, "baths"), String)} />
            <Fact icon={<Car className="h-4 w-4" aria-hidden="true" />} label="Parking" value={triText(factTri(p, "cars"), String)} />
            <Fact icon={<Ruler className="h-4 w-4" aria-hidden="true" />} label="Land" value={triText(factTri(p, "land_sqm"), (v) => `${v} m²`)} />
          </dl>
        </div>
        {verdict === "unknown" && (
          <div className="rounded-md border border-ochre/40 bg-ochre-soft px-4 py-3 text-sm text-ochre-deep lg:max-w-xs" role="note" data-testid="unknown-not-pass-note">
            <strong className="font-semibold">Unknown is not Pass.</strong> Unknown means unverified — it may or may not meet the brief.
          </div>
        )}
        {verdict === "fail" && (
          <div className="rounded-md border border-risk/40 bg-risk-soft px-4 py-3 text-sm text-risk lg:max-w-xs" role="note" data-testid="known-failure-note">
            <strong className="font-semibold">Known hard-rule failure.</strong> A high fit cannot promote this property.
          </div>
        )}
      </header>

      {notice && (
        <p className="mt-4 rounded-md border border-border bg-canvas px-4 py-2 text-sm" role="status" data-testid="detail-notice">
          {notice}
        </p>
      )}

      <nav className="mt-6 flex gap-1 border-b border-border" aria-label="Property sections">
        <Tab to={`/app/properties/${p.id}`} label="Overview" active={view === "overview"} testId="tab-overview" />
        <Tab to={`/app/properties/${p.id}?view=match`} label="Match & evidence" active={view === "match"} testId="tab-match" />
      </nav>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(300px,1fr)]">
        <div className="min-w-0 space-y-6">
          {view === "overview" ? (
            <>
              <PropertyImage property={p} className="h-56 rounded-lg md:h-72" />
              <section aria-labelledby="facts-heading" className="card p-5" data-testid="facts-panel">
                <h2 id="facts-heading" className="text-h3 font-semibold">
                  Facts and their sources
                </h2>
                <p className="mt-1 text-sm text-muted">Every material fact carries its source or a user-entry label. Conflicts are shown, never averaged.</p>
                <div className="-mx-5 mt-3 overflow-x-auto px-5">
                  <table className="w-full min-w-[520px] text-sm">
                    <thead>
                      <tr className="label text-left">
                        <th scope="col" className="py-2 pr-3 font-semibold">Fact</th>
                        <th scope="col" className="py-2 pr-3 font-semibold">Value</th>
                        <th scope="col" className="py-2 pr-3 font-semibold">Source</th>
                        <th scope="col" className="py-2 font-semibold">Checked</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {Object.values(p.facts)
                        .sort((a, b) => a.key.localeCompare(b.key))
                        .map((f) => (
                          <tr key={f.key} data-testid={`fact-row-${f.key}`} data-state={f.value_state}>
                            <th scope="row" className="py-2 pr-3 text-left font-medium">{humanise(f.key.replace("_sqm", " (m²)"))}</th>
                            <td className={f.value_state === "known" ? "py-2 pr-3" : "py-2 pr-3 italic text-muted"}>
                              {factText(p, f.key)}
                              {f.conflict_note && <div className="text-xs not-italic text-ochre-deep">{f.conflict_note}</div>}
                            </td>
                            <td className="py-2 pr-3 text-charcoal">{f.source_label}</td>
                            <td className="py-2 text-muted">
                              {formatDate(f.checked_at)} · {f.freshness}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <Notes p={p} busy={busy} mutate={mutate} />
              <Tasks p={p} busy={busy} mutate={mutate} />
            </>
          ) : (
            <MatchEvidence p={p} busy={busy} mutate={mutate} />
          )}
        </div>

        <aside className="min-w-0 space-y-6">
          <Workflow p={p} busy={busy} mutate={mutate} />
          <InspectionFeedback p={p} busy={busy} mutate={mutate} />
          <section aria-labelledby="evidence-heading" className="card p-5" data-testid="observations-panel">
            <h2 id="evidence-heading" className="text-h3 font-semibold">
              Source observations
            </h2>
            {p.campaign && <SourceFreshness className="mt-3" source={`${p.campaign.source_label} · market ${market}`} checkedAt={p.campaign.last_checked_at} />}
            <ul className="mt-3 space-y-2 text-sm">
              {p.observations.map((o) => (
                <li key={o.id} className="rounded-md bg-canvas px-3 py-2" data-testid={`observation-${o.source_kind}`}>
                  <div className="font-medium">{o.source_label}</div>
                  <div className="text-xs text-muted">
                    {humanise(o.source_kind)} · observed {formatDate(o.observed_at)} · checked {formatDate(o.checked_at)} · {o.freshness}
                  </div>
                  {o.note && <div className="mt-1 text-xs text-ochre-deep">{o.note}</div>}
                </li>
              ))}
            </ul>
          </section>
          <Activity p={p} />
        </aside>
      </div>
    </>
  );
}

function Tab({ to, label, active, testId }: { to: string; label: string; active: boolean; testId: string }) {
  return (
    <Link
      to={to}
      replace
      aria-current={active ? "page" : undefined}
      data-testid={testId}
      className={clsx("-mb-px border-b-2 px-3 py-2 text-sm font-semibold transition-colors duration-150", active ? "border-navy text-navy" : "border-transparent text-muted hover:text-navy")}
    >
      {label}
    </Link>
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
