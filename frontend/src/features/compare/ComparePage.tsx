import { Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { CompareRow } from "../../components/CompareRow";
import { EvidenceState } from "../../components/EvidenceState";
import { FitRing } from "../../components/FitRing";
import { MilestoneNote, PageHeader } from "../../components/Page";
import { PropertyImagePlaceholder } from "../../components/PropertyCard";
import { StatusChip, buyerTone, marketTone } from "../../components/StatusChip";
import { formatDate, triText } from "../../lib/format";
import { properties } from "../../lib/synthetic";

export default function ComparePage() {
  const selected = properties.filter((p) => ["demo-001", "demo-005", "demo-006"].includes(p.id));
  const columns = selected.map((p) => p.address);

  return (
    <>
      <PageHeader
        eyebrow="Compare"
        title="Compare properties"
        description={`${selected.length} of 4 selected. Gaps are never filled with invented values — Unknown stays Unknown.`}
        testId="compare-header"
      />

      <div className="card overflow-hidden" role="table" aria-label="Property comparison" data-testid="compare-table">
        <div role="row" className="hidden border-b border-border md:grid" style={{ gridTemplateColumns: `minmax(160px, 1.2fr) repeat(${selected.length}, minmax(0, 1fr))` }}>
          <div role="columnheader" className="label px-4 py-3 self-end">
            Properties
          </div>
          {selected.map((p) => (
            <div role="columnheader" key={p.id} className="flex gap-3 px-4 py-3">
              <PropertyImagePlaceholder className="h-14 w-20 shrink-0 rounded-sm" showLabel={false} />
              <div className="min-w-0">
                <Link to={`/app/properties/${p.id}`} className="block truncate text-sm font-semibold hover:underline underline-offset-4">
                  {p.address}
                </Link>
                <div className="truncate text-xs text-muted">
                  {p.suburb} {p.state}
                </div>
              </div>
            </div>
          ))}
        </div>

        <ul className="divide-y divide-border md:hidden" aria-label="Selected properties">
          {selected.map((p, i) => (
            <li key={p.id} className="flex items-center gap-3 px-4 py-3 text-sm">
              <span className="label w-6">{i + 1}</span>
              <span className="font-semibold">{p.address}</span>
              <span className="text-muted">{p.suburb}</span>
            </li>
          ))}
        </ul>

        <div role="rowgroup">
          <CompareRow attribute="Raw price guide" hint="As advertised" columns={columns} data-testid="compare-row-price" cells={selected.map((p) => ({ value: <span className="font-semibold">{p.rawPrice}</span> }))} />
          <CompareRow attribute="Price kind" columns={columns} cells={selected.map((p) => ({ value: p.priceKind }))} />
          <CompareRow
            attribute="Market status"
            columns={columns}
            cells={selected.map((p) => ({
              value: (
                <StatusChip tone={marketTone(p.marketState)} hideIcon>
                  {p.marketState}
                </StatusChip>
              ),
            }))}
          />
          <CompareRow
            attribute="Your status"
            columns={columns}
            cells={selected.map((p) => ({
              value: (
                <StatusChip tone={buyerTone(p.buyerState)} hideIcon>
                  {p.buyerState}
                </StatusChip>
              ),
            }))}
          />
          <CompareRow
            attribute="Beds / Baths / Cars"
            columns={columns}
            cells={selected.map((p) => ({ value: `${triText(p.beds, String)} / ${triText(p.baths, String)} / ${triText(p.cars, String)}` }))}
          />
          <CompareRow
            attribute="Land size"
            hint="Hard rule ≥ 400 m²"
            columns={columns}
            data-testid="compare-row-land"
            cells={selected.map((p) => ({ value: triText(p.landSqm, (v) => `${v} m²`), state: p.landSqm.state }))}
          />
          <CompareRow
            attribute="Hard rules"
            hint="Pass / Fail / Unknown"
            columns={columns}
            data-testid="compare-row-gates"
            cells={selected.map((p) => ({ value: <EvidenceState outcome={p.gate} compact /> }))}
          />
          <CompareRow
            attribute="Provisional fit"
            hint="How well it fits your brief"
            columns={columns}
            data-testid="compare-row-fit"
            cells={selected.map((p) => ({ value: <FitRing value={p.fit} label="Fit" size={40} />, state: p.fit.state }))}
          />
          <CompareRow
            attribute="Evidence coverage"
            hint="Breadth of assessed criteria"
            columns={columns}
            cells={selected.map((p) => ({ value: <FitRing value={p.coverage} label="Coverage" size={40} />, state: p.coverage.state }))}
          />
          <CompareRow attribute="Condition" columns={columns} cells={selected.map((p) => ({ value: p.condition ?? "", state: p.condition ? "known" : "unknown" }))} />
          <CompareRow attribute="Travel time" hint="Unknown until a provider exists" columns={columns} cells={selected.map(() => ({ value: "", state: "unknown" as const }))} />
          <CompareRow attribute="Source freshness" columns={columns} cells={selected.map((p) => ({ value: formatDate(p.lastChecked) }))} />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">{selected.length} of 4 properties selected</p>
        <button type="button" disabled className="inline-flex h-10 items-center gap-2 rounded-md border border-dashed border-border px-4 text-sm text-muted" title="Selection arrives in Milestone 3" data-testid="compare-add">
          <Plus className="h-4 w-4" aria-hidden="true" /> Add property
        </button>
      </div>

      <MilestoneNote milestone={3}>Choosing which properties to compare, total-cost assumptions and risks arrive with the matching engine.</MilestoneNote>
    </>
  );
}
