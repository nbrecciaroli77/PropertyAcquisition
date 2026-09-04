import { Bookmark } from "lucide-react";
import { ButtonLink } from "../../components/Button";
import { PageHeader } from "../../components/Page";
import { PropertyCard } from "../../components/PropertyCard";
import { EmptyState, ErrorState, PropertyCardSkeleton } from "../../components/States";
import { useCompareSelection, useProperties } from "../properties/hooks";

export default function SavedPage() {
  const { status, items, message, reload } = useProperties({ saved: "true" });
  const compare = useCompareSelection();
  return (
    <>
      <PageHeader eyebrow="Saved" title="Shortlist" description="Properties you have saved. Saving is your decision; source updates never add or remove items here." testId="saved-header" />
      {status === "error" && <ErrorState description={message ?? "Saved properties could not be loaded."} onRetry={reload} />}
      {status === "loading" && (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-busy="true" aria-label="Loading saved properties">
          {[0, 1].map((i) => (
            <li key={i}>
              <PropertyCardSkeleton />
            </li>
          ))}
        </ul>
      )}
      {(status === "no-journey" || (status === "ready" && items.length === 0)) && (
        <EmptyState
          title="Nothing saved yet"
          description="Save a property from its detail page to keep it here."
          icon={<Bookmark className="h-5 w-5" aria-hidden="true" />}
          data-testid="saved-empty"
          action={
            <ButtonLink to="/app/discover" variant="secondary" size="sm">
              Go to Discover
            </ButtonLink>
          }
        />
      )}
      {status === "ready" && items.length > 0 && (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="saved-grid">
          {items.map((p) => (
            <li key={p.id}>
              <PropertyCard property={p} headingLevel={2} compareSelected={compare.ids.includes(p.id)} onToggleCompare={compare.toggle} compareDisabled={compare.full} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
