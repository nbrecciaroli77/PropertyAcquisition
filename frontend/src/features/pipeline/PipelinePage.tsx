import { Link } from "react-router-dom";
import { PageHeader } from "../../components/Page";
import { PropertyImage } from "../../components/PropertyCard";
import { EmptyState, ErrorState, Skeleton } from "../../components/States";
import { StatusChip, marketTone } from "../../components/StatusChip";
import { ButtonLink } from "../../components/Button";
import { BUYER_STATES, marketLabel, verdictText } from "../../lib/properties";
import { useProperties } from "../properties/hooks";

export default function PipelinePage() {
  const { status, items, message, reload } = useProperties();
  return (
    <>
      <PageHeader
        eyebrow="Pipeline"
        title="Your ongoing work"
        description="Buyer workflow stages you own. A source status update can never move a property between these columns; open a property to change its stage."
        testId="pipeline-header"
        actions={
          <ButtonLink to="/app/properties/add" variant="secondary" size="sm" data-testid="pipeline-add-property">
            Add property
          </ButtonLink>
        }
      />
      {status === "error" && <ErrorState description={message ?? "The pipeline could not be loaded."} onRetry={reload} />}
      {status === "no-journey" && (
        <EmptyState title="No buying journey yet" description="Create a journey to start a pipeline." action={<ButtonLink to="/app/journeys/new" size="sm">Create a journey</ButtonLink>} />
      )}
      {status === "loading" && <Skeleton className="h-64" label="Loading pipeline" />}
      {status === "ready" && (
        <>
          <p className="mb-2 text-xs text-muted lg:hidden" id="pipeline-scroll-hint">
            Scroll sideways to see every stage.
          </p>
          <div className="-mx-4 overflow-x-auto px-4 pb-2 md:-mx-6 md:px-6 lg:-mx-8 lg:px-8" role="region" aria-label="Pipeline stages" aria-describedby="pipeline-scroll-hint" tabIndex={0} data-testid="pipeline-board">
            <ol className="flex w-max gap-3">
              {BUYER_STATES.map((stage) => {
                const inStage = items.filter((p) => p.buyer_state === stage.key);
                return (
                  <li key={stage.key} className="w-[240px] shrink-0 rounded-lg border border-border bg-canvas-deep/60 p-2" data-testid={`pipeline-stage-${stage.key.replace(/_/g, "-")}`}>
                    <h2 className="flex items-center justify-between px-1 py-1.5 text-sm font-semibold">
                      {stage.label}
                      <span className="rounded-full bg-surface px-2 text-xs text-muted" aria-label={`${inStage.length} properties`}>
                        {inStage.length}
                      </span>
                    </h2>
                    <ul className="mt-1 space-y-2">
                      {inStage.map((p) => (
                        <li key={p.id} className="card p-3" data-testid={`pipeline-card-${p.id}`} data-legacy-ref={p.legacy_ref ?? undefined}>
                          <PropertyImage property={p} className="h-16 rounded-sm" showLabel={false} />
                          <Link to={`/app/properties/${p.id}`} className="mt-2 block text-sm font-semibold hover:underline underline-offset-4">
                            {p.address_line}
                          </Link>
                          <div className="text-xs text-muted">
                            {p.suburb} · {p.campaign?.raw_price ?? "No campaign"}
                          </div>
                          <div className="mt-2 flex flex-wrap gap-1">
                            <StatusChip tone={marketTone(marketLabel(p.campaign?.market_state))} hideIcon>
                              Market: {marketLabel(p.campaign?.market_state)}
                            </StatusChip>
                            <StatusChip tone={p.evaluation?.verdict === "pass" ? "pass" : p.evaluation?.verdict === "fail" ? "fail" : "unknown"} hideIcon>
                              {p.evaluation ? verdictText(p.evaluation.verdict) : "Not evaluated"}
                            </StatusChip>
                          </div>
                        </li>
                      ))}
                      {inStage.length === 0 && <li className="px-1 py-3 text-xs italic text-muted">Empty</li>}
                    </ul>
                  </li>
                );
              })}
            </ol>
          </div>
        </>
      )}
    </>
  );
}
