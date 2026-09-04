import clsx from "clsx";
import { LayoutGrid, List } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, ButtonLink } from "../../components/Button";
import { PageHeader } from "../../components/Page";
import { PropertyCard } from "../../components/PropertyCard";
import { EmptyState, ErrorState, PropertyCardSkeleton } from "../../components/States";
import { useProperties, useCompareSelection } from "../properties/hooks";
import { LoadDemoButton } from "../properties/LoadDemoButton";

type GateFilter = "all" | "pass" | "unknown" | "fail";
const filters: GateFilter[] = ["all", "pass", "unknown", "fail"];
const filterLabel: Record<GateFilter, string> = { all: "All", pass: "Gates pass", unknown: "Verification required", fail: "Known failure" };
type Sort = "checked" | "fit" | "address";

export default function DiscoverPage() {
  const [gate, setGate] = useState<GateFilter>("all");
  const [view, setView] = useState<"cards" | "list">("cards");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<Sort>("checked");
  const { status, items, message, journey, reload } = useProperties({
    buyer_state: "reviewing",
    verdict: gate === "all" ? undefined : gate,
    q: q.trim() || undefined,
    sort,
  });
  const compare = useCompareSelection();

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

      <div className="mb-5 flex flex-wrap items-center gap-2" role="toolbar" aria-label="Filters, search and view">
        <div role="group" aria-label="Filter by hard-gate outcome" className="flex flex-wrap gap-1.5">
          {filters.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setGate(f)}
              aria-pressed={gate === f}
              data-testid={`discover-filter-${f}`}
              className={clsx(
                "h-9 rounded-full border px-3 text-sm font-medium transition-colors duration-150",
                gate === f ? "border-navy bg-navy text-white" : "border-border bg-surface text-navy hover:border-navy",
              )}
            >
              {filterLabel[f]}
            </button>
          ))}
        </div>
        <label className="ml-auto flex min-w-0 items-center gap-2 text-sm">
          <span className="sr-only">Search address, suburb or guide</span>
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search address or suburb"
            data-testid="discover-search"
            className="h-9 w-44 rounded-md border border-border bg-surface px-3 text-sm sm:w-56"
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <span className="sr-only">Sort</span>
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} data-testid="discover-sort" className="h-9 rounded-md border border-border bg-surface px-2 text-sm">
            <option value="checked">Last checked</option>
            <option value="fit">Assessed fit</option>
            <option value="address">Address</option>
          </select>
        </label>
        <div role="group" aria-label="View" className="inline-flex rounded-md border border-border bg-surface p-0.5">
          <ViewButton active={view === "cards"} onClick={() => setView("cards")} label="Cards" icon={<LayoutGrid className="h-4 w-4" aria-hidden="true" />} testId="discover-view-cards" />
          <ViewButton active={view === "list"} onClick={() => setView("list")} label="List" icon={<List className="h-4 w-4" aria-hidden="true" />} testId="discover-view-list" />
        </div>
      </div>

      {status === "error" && <ErrorState description={message ?? "Properties could not be loaded."} onRetry={reload} data-testid="discover-error" />}
      {status === "no-journey" && (
        <EmptyState title="No buying journey yet" description="Create a journey and publish a brief before reviewing properties." action={<ButtonLink to="/app/journeys/new" size="sm">Create a journey</ButtonLink>} />
      )}
      {status === "loading" && (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-busy="true" aria-label="Loading properties">
          {[0, 1, 2].map((i) => (
            <li key={i}>
              <PropertyCardSkeleton />
            </li>
          ))}
        </ul>
      )}

      {status === "ready" && (
        <>
          <p className="mb-3 flex flex-wrap items-center gap-x-3 text-sm text-muted" data-testid="discover-result-count">
            <span>
              {items.length} {items.length === 1 ? "property" : "properties"} in queue
            </span>
            {compare.ids.length > 0 && (
              <Link to="/app/compare" className="font-semibold text-eucalyptus-deep hover:underline underline-offset-4" data-testid="discover-compare-link">
                Compare {compare.ids.length} selected →
              </Link>
            )}
          </p>
          {items.length === 0 ? (
            gate === "all" && !q ? (
              <EmptyState
                title="Nothing waiting for review"
                description="No properties are in the Reviewing stage. This is a genuine empty queue, not a failed check. Structured intake arrives in Milestone 4; for now you can load the synthetic fixture set."
                data-testid="discover-empty"
                action={journey ? <LoadDemoButton journeyId={journey.id} onLoaded={reload} /> : undefined}
              />
            ) : (
              <EmptyState
                title="No properties match"
                description={`Nothing in the review queue has the outcome "${filterLabel[gate]}"${q ? ` matching "${q}"` : ""}. This is not a failed check — clear the filter to see everything.`}
                action={
                  <Button variant="secondary" size="sm" onClick={() => { setGate("all"); setQ(""); }} data-testid="discover-clear-filter">
                    Clear filter
                  </Button>
                }
              />
            )
          ) : (
            <ul className={clsx("grid gap-4", view === "cards" ? "sm:grid-cols-2 xl:grid-cols-3" : "grid-cols-1")} data-testid="discover-grid">
              {items.map((p) => (
                <li key={p.id}>
                  <PropertyCard property={p} compact={view === "list"} headingLevel={2} compareSelected={compare.ids.includes(p.id)} onToggleCompare={compare.toggle} compareDisabled={compare.full} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
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
