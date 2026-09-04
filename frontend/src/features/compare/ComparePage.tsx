import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ButtonLink } from "../../components/Button";
import { CompareRow } from "../../components/CompareRow";
import { EvidenceState } from "../../components/EvidenceState";
import { FitRing } from "../../components/FitRing";
import { PageHeader } from "../../components/Page";
import { PropertyImage } from "../../components/PropertyCard";
import { EmptyState, ErrorState, Skeleton } from "../../components/States";
import { StatusChip, buyerTone, marketTone } from "../../components/StatusChip";
import { formatDate, triText } from "../../lib/format";
import { useJourneys } from "../../lib/journey";
import {
  MAX_COMPARE,
  buyerLabel,
  coverageTri,
  factText,
  factTri,
  fitTri,
  gateLabel,
  marketLabel,
  priceKindLabel,
  propertyApi,
  type PropertySummary,
} from "../../lib/properties";
import { useCompareSelection } from "../properties/hooks";

export default function ComparePage() {
  const { active, loading } = useJourneys();
  const { ids, remove } = useCompareSelection();
  const [state, setState] = useState<{ status: "loading" | "ready" | "error"; items: PropertySummary[]; message: string | null }>({ status: "loading", items: [], message: null });
  const key = ids.join(",");

  useEffect(() => {
    if (loading || !active) return;
    if (!key) {
      setState({ status: "ready", items: [], message: null });
      return;
    }
    let cancelled = false;
    propertyApi
      .compare(active.id, key.split(","))
      .then((items) => !cancelled && setState({ status: "ready", items, message: null }))
      .catch((e: unknown) => !cancelled && setState({ status: "error", items: [], message: e instanceof Error ? e.message : "Compare could not load." }));
    return () => {
      cancelled = true;
    };
  }, [active, loading, key]);

  const selected = state.items;
  const columns = selected.map((p) => p.address_line);
  const landRule = selected[0]?.evaluation?.gates.find((g) => g.criterion === "land_sqm")?.brief_value;

  return (
    <>
      <PageHeader
        eyebrow="Compare"
        title="Compare properties"
        description={`${ids.length} of ${MAX_COMPARE} selected. Gaps are never filled with invented values — Unknown stays Unknown and is never a low score.`}
        testId="compare-header"
      />

      {state.status === "error" && <ErrorState description={state.message ?? ""} onRetry={() => setState({ status: "loading", items: [], message: null })} />}
      {state.status === "loading" && key && <Skeleton className="h-64" label="Loading comparison" />}
      {state.status === "ready" && selected.length === 0 && (
        <EmptyState
          title="Nothing selected to compare"
          description="Choose up to four properties from Discover, Saved or a property page with 'Add to compare'."
          data-testid="compare-empty"
          action={
            <ButtonLink to="/app/discover" variant="secondary" size="sm">
              Go to Discover
            </ButtonLink>
          }
        />
      )}

      {selected.length > 0 && (
        <>
          <div className="card overflow-hidden" role="table" aria-label="Property comparison" data-testid="compare-table">
            <div role="row" className="hidden border-b border-border md:grid" style={{ gridTemplateColumns: `minmax(160px, 1.2fr) repeat(${selected.length}, minmax(0, 1fr))` }}>
              <div role="columnheader" className="label self-end px-4 py-3">
                Properties
              </div>
              {selected.map((p) => (
                <div role="columnheader" key={p.id} className="flex gap-3 px-4 py-3">
                  <PropertyImage property={p} className="h-14 w-20 shrink-0 rounded-sm" showLabel={false} />
                  <div className="min-w-0 flex-1">
                    <Link to={`/app/properties/${p.id}`} className="block truncate text-sm font-semibold hover:underline underline-offset-4">
                      {p.address_line}
                    </Link>
                    <div className="truncate text-xs text-muted">
                      {p.suburb} {p.state}
                    </div>
                  </div>
                  <button type="button" onClick={() => remove(p.id)} aria-label={`Remove ${p.address_line} from compare`} className="h-7 w-7 shrink-0 rounded-md text-muted hover:bg-canvas hover:text-navy" data-testid={`compare-remove-${p.id}`}>
                    <X className="mx-auto h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
              ))}
            </div>

            <ul className="divide-y divide-border md:hidden" aria-label="Selected properties">
              {selected.map((p, i) => (
                <li key={p.id} className="flex items-center gap-3 px-4 py-3 text-sm">
                  <span className="label w-6">{i + 1}</span>
                  <span className="min-w-0 flex-1 truncate font-semibold">{p.address_line}</span>
                  <button type="button" onClick={() => remove(p.id)} aria-label={`Remove ${p.address_line} from compare`} className="h-7 w-7 rounded-md text-muted" data-testid={`compare-remove-m-${p.id}`}>
                    <X className="mx-auto h-4 w-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>

            <div role="rowgroup">
              <CompareRow attribute="Raw price guide" hint="As advertised — never converted" columns={columns} data-testid="compare-row-price" cells={selected.map((p) => ({ value: <span className="font-semibold">{p.campaign?.raw_price ?? "No campaign"}</span> }))} />
              <CompareRow attribute="Price kind" columns={columns} cells={selected.map((p) => ({ value: priceKindLabel(p.campaign?.price_kind) }))} />
              <CompareRow attribute="Market status" hint="From the source" columns={columns} cells={selected.map((p) => ({ value: <StatusChip tone={marketTone(marketLabel(p.campaign?.market_state))} hideIcon>{marketLabel(p.campaign?.market_state)}</StatusChip> }))} />
              <CompareRow attribute="Your status" hint="Buyer workflow" columns={columns} cells={selected.map((p) => ({ value: <StatusChip tone={buyerTone(buyerLabel(p.buyer_state))} hideIcon>{buyerLabel(p.buyer_state)}</StatusChip> }))} />
              <CompareRow attribute="Beds / Baths / Cars" columns={columns} cells={selected.map((p) => ({ value: `${triText(factTri(p, "beds"), String)} / ${triText(factTri(p, "baths"), String)} / ${triText(factTri(p, "cars"), String)}` }))} />
              <CompareRow attribute="Land size" hint={landRule ? `Hard rule ${landRule}` : undefined} columns={columns} data-testid="compare-row-land" cells={selected.map((p) => ({ value: triText(factTri(p, "land_sqm"), (v) => `${v} m²`), state: factTri(p, "land_sqm").state }))} />
              <CompareRow attribute="Hard rules" hint="Pass / Fail / Unknown" columns={columns} data-testid="compare-row-gates" cells={selected.map((p) => ({ value: <EvidenceState outcome={p.evaluation ? gateLabel(p.evaluation.verdict) : "Unknown"} compact /> }))} />
              <CompareRow attribute="Unknowns and risks" hint="What still needs verifying" columns={columns} data-testid="compare-row-unknowns" cells={selected.map((p) => {
                const open = p.evaluation?.gates.filter((g) => g.outcome !== "pass") ?? [];
                return { value: open.length ? open.map((g) => `${g.label}: ${g.outcome}`).join(" · ") : "No open hard-rule questions" };
              })} />
              <CompareRow attribute="Assessed fit" hint="Preferences only — never a value" columns={columns} data-testid="compare-row-fit" cells={selected.map((p) => ({ value: <FitRing value={fitTri(p)} label="Fit" size={40} />, state: fitTri(p).state }))} />
              <CompareRow attribute="Evidence coverage" hint="Share of enabled weight assessed" columns={columns} cells={selected.map((p) => ({ value: <FitRing value={coverageTri(p)} label="Coverage" size={40} />, state: coverageTri(p).state }))} />
              <CompareRow attribute="Condition" columns={columns} cells={selected.map((p) => ({ value: factText(p, "condition"), state: p.facts.condition?.value_state === "known" ? "known" : "unknown" }))} />
              <CompareRow attribute="Total-cost assumptions" hint="No assumptions are made in this prototype" columns={columns} cells={selected.map(() => ({ value: "", state: "unknown" as const }))} />
              <CompareRow attribute="Travel time" hint="Unknown until a provider exists" columns={columns} cells={selected.map(() => ({ value: "", state: "unknown" as const }))} />
              <CompareRow attribute="Source freshness" columns={columns} cells={selected.map((p) => ({ value: p.campaign ? `${formatDate(p.campaign.last_checked_at)} · ${p.campaign.freshness}` : "", state: p.campaign ? "known" : "unknown" }))} />
              <CompareRow attribute="Brief / evaluation version" columns={columns} cells={selected.map((p) => ({ value: p.evaluation ? `v${p.evaluation.brief_version_no} · ${p.evaluation.evaluation_version}` : "", state: p.evaluation ? "known" : "unknown" }))} />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted">{selected.length} of {MAX_COMPARE} properties selected</p>
            {selected.length < MAX_COMPARE && (
              <ButtonLink to="/app/discover" variant="secondary" size="sm" data-testid="compare-add">
                Add another from Discover
              </ButtonLink>
            )}
          </div>
        </>
      )}
    </>
  );
}
