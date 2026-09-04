import clsx from "clsx";
import { LayoutGrid, List, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import { Button, ButtonLink } from "../../components/Button";
import { MilestoneNote, PageHeader } from "../../components/Page";
import { PropertyCard } from "../../components/PropertyCard";
import { EmptyState } from "../../components/States";
import { properties } from "../../lib/synthetic";
import type { GateOutcome } from "../../lib/types";

type GateFilter = "All" | GateOutcome;
const filters: GateFilter[] = ["All", "Pass", "Unknown", "Fail"];
const filterLabel: Record<GateFilter, string> = { All: "All", Pass: "Gates pass", Unknown: "Verification required", Fail: "Known failure" };

export default function DiscoverPage() {
  const [gate, setGate] = useState<GateFilter>("All");
  const [view, setView] = useState<"cards" | "list">("cards");
  const queue = useMemo(() => properties.filter((p) => p.buyerState === "Reviewing" && (gate === "All" || p.gate === gate)), [gate]);

  return (
    <>
      <PageHeader
        eyebrow="Discover"
        title="Incoming review queue"
        description="Properties waiting for your first decision. Market state and your workflow state are shown separately."
        testId="discover-header"
        actions={
          <ButtonLink to="/app/sources" variant="secondary" size="sm" data-testid="discover-add-property">
            Add property
          </ButtonLink>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-2" role="toolbar" aria-label="Filters and view">
        <div role="group" aria-label="Filter by hard-gate outcome" className="flex flex-wrap gap-1.5">
          {filters.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setGate(f)}
              aria-pressed={gate === f}
              data-testid={`discover-filter-${f.toLowerCase()}`}
              className={clsx(
                "h-9 rounded-full border px-3 text-sm font-medium transition-colors duration-150",
                gate === f ? "border-navy bg-navy text-white" : "border-border bg-surface text-navy hover:border-navy",
              )}
            >
              {filterLabel[f]}
            </button>
          ))}
        </div>
        <Button variant="secondary" size="sm" className="ml-auto" icon={<SlidersHorizontal className="h-4 w-4" aria-hidden="true" />} disabled title="Arrives in Milestone 3">
          More filters
        </Button>
        <div role="group" aria-label="View" className="inline-flex rounded-md border border-border bg-surface p-0.5">
          <ViewButton active={view === "cards"} onClick={() => setView("cards")} label="Cards" icon={<LayoutGrid className="h-4 w-4" aria-hidden="true" />} testId="discover-view-cards" />
          <ViewButton active={view === "list"} onClick={() => setView("list")} label="List" icon={<List className="h-4 w-4" aria-hidden="true" />} testId="discover-view-list" />
        </div>
      </div>

      <p className="mb-3 text-sm text-muted" data-testid="discover-result-count">
        {queue.length} {queue.length === 1 ? "property" : "properties"} in queue · sorted by last checked
      </p>

      {queue.length === 0 ? (
        <EmptyState
          title="No properties match this filter"
          description={`Nothing in the review queue has the outcome "${filterLabel[gate]}". This is not a failed check — clear the filter to see everything.`}
          action={
            <Button variant="secondary" size="sm" onClick={() => setGate("All")} data-testid="discover-clear-filter">
              Clear filter
            </Button>
          }
        />
      ) : (
        <ul className={clsx("grid gap-4", view === "cards" ? "sm:grid-cols-2 xl:grid-cols-3" : "grid-cols-1")} data-testid="discover-grid">
          {queue.map((p) => (
            <li key={p.id}>
              <PropertyCard property={p} compact={view === "list"} headingLevel={2} />
            </li>
          ))}
        </ul>
      )}

      <MilestoneNote milestone={3}>Search, sort, saved views and the master-detail tablet layout arrive with the property domain.</MilestoneNote>
    </>
  );
}

function ViewButton({ active, onClick, label, icon, testId }: { active: boolean; onClick: () => void; label: string; icon: JSX.Element; testId: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      data-testid={testId}
      className={clsx("inline-flex h-8 items-center gap-1.5 rounded-sm px-2.5 text-sm font-medium", active ? "bg-eucalyptus-soft text-eucalyptus-deep" : "text-muted hover:text-navy")}
    >
      {icon}
      {label}
    </button>
  );
}
