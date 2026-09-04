import { Bookmark } from "lucide-react";
import { ButtonLink } from "../../components/Button";
import { MilestoneNote, PageHeader } from "../../components/Page";
import { PropertyCard } from "../../components/PropertyCard";
import { EmptyState } from "../../components/States";
import { properties } from "../../lib/synthetic";

export default function SavedPage() {
  const saved = properties.filter((p) => p.saved);
  return (
    <>
      <PageHeader eyebrow="Saved" title="Shortlist" description="Properties you have saved. Saving is your decision; source updates never add or remove items here." testId="saved-header" />
      {saved.length === 0 ? (
        <EmptyState
          title="Nothing saved yet"
          description="Save a property from Discover to keep it here."
          icon={<Bookmark className="h-5 w-5" aria-hidden="true" />}
          action={
            <ButtonLink to="/app/discover" variant="secondary" size="sm">
              Go to Discover
            </ButtonLink>
          }
        />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="saved-grid">
          {saved.map((p) => (
            <li key={p.id}>
              <PropertyCard property={p} headingLevel={2} />
            </li>
          ))}
        </ul>
      )}
      <MilestoneNote milestone={3}>The full shortlist board with stage transitions arrives with the property domain.</MilestoneNote>
    </>
  );
}
