import { Plus, Save, Trash2 } from "lucide-react";
import { useState } from "react";
import { AreaListEditor, STATE_OPTIONS } from "../../components/AreaListEditor";
import { Button, ButtonLink } from "../../components/Button";
import { FormNotice, NumberField, SelectField, TextField } from "../../components/Form";
import { PageHeader } from "../../components/Page";
import { EmptyState, ErrorState, Skeleton } from "../../components/States";
import type { StateTerritory } from "../../lib/api";
import { MODE_HELP, MODE_OPTIONS } from "../../lib/briefOptions";
import { errorLookup, useBrief } from "./useBrief";

export default function BriefLocationsPage() {
  const brief = useBrief();
  const [anchorLabel, setAnchorLabel] = useState("");
  const [anchorAddress, setAnchorAddress] = useState("");

  if (brief.status === "loading") {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-1/2" label="Loading locations" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (brief.status === "no-journey") {
    return (
      <>
        <PageHeader eyebrow="Buying brief" title="Locations and anchors" testId="locations-header" />
        <EmptyState
          title="No buying journey yet"
          description="Locations belong to a journey's brief. Create a journey to set them."
          action={
            <ButtonLink to="/app/journeys/new" variant="success" data-testid="locations-create-journey">
              Create a buying journey
            </ButtonLink>
          }
          data-testid="locations-empty"
        />
      </>
    );
  }

  if (brief.status === "error" || !brief.data || !brief.draft) {
    return (
      <>
        <PageHeader eyebrow="Buying brief" title="Locations and anchors" testId="locations-header" />
        <ErrorState description={brief.message ?? "Locations could not be loaded."} onRetry={brief.reload} />
      </>
    );
  }

  const { draft } = brief;
  const errorFor = errorLookup(brief.publishErrors.length > 0 ? brief.publishErrors : brief.data.validation);

  const toggleState = (state: StateTerritory) =>
    brief.setDraft((current) => {
      const states = current.locations.states;
      current.locations.states = states.includes(state) ? states.filter((s) => s !== state) : [...states, state];
      return current;
    });

  const addAnchor = () => {
    if (!anchorLabel.trim() || !anchorAddress.trim()) return;
    brief.setDraft((current) => {
      current.locations.anchors = [
        ...current.locations.anchors,
        { label: anchorLabel.trim(), address: anchorAddress.trim(), max_minutes: null },
      ];
      return current;
    });
    setAnchorLabel("");
    setAnchorAddress("");
  };

  return (
    <>
      <PageHeader
        eyebrow="Buying brief"
        title="Locations and anchors"
        description="States and territories, included and excluded areas, an optional radius and travel anchors."
        actions={
          <ButtonLink to="/app/brief" variant="secondary" data-testid="locations-back-link">
            Back to the brief
          </ButtonLink>
        }
        testId="locations-header"
      />

      <div className="grid min-w-0 max-w-[900px] gap-5">
        <section aria-labelledby="states-heading" className="card min-w-0 p-5" data-testid="states-section">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 id="states-heading" className="text-h3 font-semibold">
                States and territories
              </h2>
              <p className="mt-1 text-sm text-muted">Every Australian state and territory is supported.</p>
            </div>
            <SelectField
              id="locations-mode"
              label="Treat as"
              value={draft.locations.mode}
              onChange={(mode) =>
                brief.setDraft((current) => {
                  current.locations.mode = mode;
                  return current;
                })
              }
              options={MODE_OPTIONS}
              className="sm:w-[190px]"
            />
          </div>
          <p className="mt-2 text-xs text-muted">{MODE_HELP[draft.locations.mode]}</p>

          <fieldset className="mt-4 min-w-0">
            <legend className="sr-only">States and territories</legend>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {STATE_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className="flex min-h-[44px] items-center gap-2 rounded-md border border-border bg-surface px-3 text-sm"
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[var(--color-eucalyptus-deep)]"
                    checked={draft.locations.states.includes(option.value)}
                    onChange={() => toggleState(option.value)}
                    data-testid={`state-${option.value}`}
                  />
                  {option.value}
                  <span className="sr-only">{option.label}</span>
                </label>
              ))}
            </div>
            {errorFor("locations.states") && (
              <p className="mt-2 text-xs font-semibold text-risk" data-testid="states-error">
                {errorFor("locations.states")}
              </p>
            )}
          </fieldset>
        </section>

        <section aria-labelledby="areas-heading" className="card min-w-0 space-y-6 p-5" data-testid="areas-section">
          <h2 id="areas-heading" className="text-h3 font-semibold">
            Included and excluded areas
          </h2>
          <AreaListEditor
            idPrefix="included"
            legend="Included areas"
            description="Suburbs or postcodes you want to see. Suburb, postcode and state together identify an area."
            areas={draft.locations.included}
            onChange={(areas) =>
              brief.setDraft((current) => {
                current.locations.included = areas;
                return current;
              })
            }
            defaultState={draft.locations.states[0] ?? "WA"}
          />
          <AreaListEditor
            idPrefix="excluded"
            legend="Excluded areas"
            description="Areas to keep out of matching. An area cannot be included and excluded at the same time."
            areas={draft.locations.excluded}
            onChange={(areas) =>
              brief.setDraft((current) => {
                current.locations.excluded = areas;
                return current;
              })
            }
            defaultState={draft.locations.states[0] ?? "WA"}
            error={errorFor("locations.excluded")}
          />
          <NumberField
            id="locations-radius"
            label="Optional radius around included areas"
            value={draft.locations.radius_km}
            suffix="km"
            error={errorFor("locations.radius_km")}
            helper="Leave blank to match only the listed areas."
            onChange={(value) =>
              brief.setDraft((current) => {
                current.locations.radius_km = value;
                return current;
              })
            }
          />
        </section>

        <section aria-labelledby="anchors-heading" className="card min-w-0 p-5" data-testid="anchors-section">
          <h2 id="anchors-heading" className="text-h3 font-semibold">
            Travel anchors
          </h2>
          <FormNotice tone="info" testId="anchors-unknown-notice">
            Travel time stays <strong className="font-semibold">Unknown</strong> until a provider and its assumptions
            exist. Anchors are recorded as places you care about, not as estimated commutes.
          </FormNotice>

          {draft.locations.anchors.length > 0 && (
            <ul className="mt-4 space-y-2" data-testid="anchors-list">
              {draft.locations.anchors.map((anchor, index) => (
                <li
                  key={`${anchor.label}-${index}`}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-surface px-3 py-2 text-sm"
                  data-testid={`anchor-item-${index}`}
                >
                  <span className="min-w-0">
                    <strong className="font-semibold">{anchor.label}</strong> · {anchor.address} · travel time{" "}
                    {anchor.max_minutes === null ? "Unknown" : `${anchor.max_minutes} min target`}
                  </span>
                  <Button
                    variant="tertiary"
                    size="sm"
                    onClick={() =>
                      brief.setDraft((current) => {
                        current.locations.anchors = current.locations.anchors.filter((_, i) => i !== index);
                        return current;
                      })
                    }
                    aria-label={`Remove anchor ${anchor.label}`}
                    icon={<Trash2 className="h-4 w-4" aria-hidden="true" />}
                    data-testid={`anchor-remove-${index}`}
                  >
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          )}

          <div className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto] sm:items-end">
            <TextField id="anchor-label" label="Anchor name" value={anchorLabel} onChange={setAnchorLabel} />
            <TextField id="anchor-address" label="Address or place" value={anchorAddress} onChange={setAnchorAddress} />
            <Button
              variant="secondary"
              onClick={addAnchor}
              icon={<Plus className="h-4 w-4" aria-hidden="true" />}
              data-testid="anchor-add"
            >
              Add anchor
            </Button>
          </div>
        </section>

        {brief.notice && (
          <FormNotice tone="success" testId="locations-notice">
            {brief.notice}
          </FormNotice>
        )}
        {brief.message && (
          <FormNotice tone="error" testId="locations-error">
            {brief.message}
          </FormNotice>
        )}

        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            onClick={() => void brief.save("Locations saved to your draft brief.")}
            disabled={brief.busy}
            icon={<Save className="h-4 w-4" aria-hidden="true" />}
            data-testid="locations-save"
          >
            {brief.busy ? "Saving…" : "Save locations"}
          </Button>
          <ButtonLink to="/app/brief" variant="secondary" data-testid="locations-publish-link">
            Go to publish
          </ButtonLink>
        </div>
      </div>
    </>
  );
}
