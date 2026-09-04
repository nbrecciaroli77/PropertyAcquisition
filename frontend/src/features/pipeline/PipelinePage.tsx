import { Link } from "react-router-dom";
import { MilestoneNote, PageHeader } from "../../components/Page";
import { PropertyImagePlaceholder } from "../../components/PropertyCard";
import { StatusChip, marketTone } from "../../components/StatusChip";
import { properties } from "../../lib/synthetic";
import type { BuyerState } from "../../lib/types";

const stages: BuyerState[] = [
  "Reviewing",
  "Shortlisted",
  "Inspection considered",
  "Inspected",
  "Due diligence",
  "Offer preparation",
  "Offer submitted",
  "Under contract",
  "Settled",
  "Rejected",
  "Archived",
];

export default function PipelinePage() {
  return (
    <>
      <PageHeader
        eyebrow="Pipeline"
        title="Your ongoing work"
        description="Buyer workflow stages you own. A source status update can never move a property between these columns."
        testId="pipeline-header"
      />
      <p className="mb-2 text-xs text-muted lg:hidden" id="pipeline-scroll-hint">
        Scroll sideways to see every stage.
      </p>
      <div className="-mx-4 overflow-x-auto px-4 pb-2 md:-mx-6 md:px-6 lg:-mx-8 lg:px-8" role="region" aria-label="Pipeline stages" aria-describedby="pipeline-scroll-hint" tabIndex={0} data-testid="pipeline-board">
        <ol className="flex w-max gap-3">
          {stages.map((stage) => {
            const items = properties.filter((p) => p.buyerState === stage);
            return (
              <li key={stage} className="w-[240px] shrink-0 rounded-lg border border-border bg-canvas-deep/60 p-2" data-testid={`pipeline-stage-${stage.toLowerCase().replace(/\s+/g, "-")}`}>
                <h2 className="flex items-center justify-between px-1 py-1.5 text-sm font-semibold">
                  {stage}
                  <span className="rounded-full bg-surface px-2 text-xs text-muted" aria-label={`${items.length} properties`}>
                    {items.length}
                  </span>
                </h2>
                <ul className="mt-1 space-y-2">
                  {items.map((p) => (
                    <li key={p.id} className="card p-3" data-testid={`pipeline-card-${p.id}`}>
                      <PropertyImagePlaceholder className="h-16 rounded-sm" showLabel={false} />
                      <Link to={`/app/properties/${p.id}`} className="mt-2 block text-sm font-semibold hover:underline underline-offset-4">
                        {p.address}
                      </Link>
                      <div className="text-xs text-muted">
                        {p.suburb} · {p.rawPrice}
                      </div>
                      <StatusChip tone={marketTone(p.marketState)} hideIcon className="mt-2">
                        Market: {p.marketState}
                      </StatusChip>
                    </li>
                  ))}
                  {items.length === 0 && <li className="px-1 py-3 text-xs italic text-muted">Empty</li>}
                </ul>
              </li>
            );
          })}
        </ol>
      </div>
      <MilestoneNote milestone={3}>Allowed transitions with actor/time recording, filters and saved views arrive with the shortlist board.</MilestoneNote>
    </>
  );
}
