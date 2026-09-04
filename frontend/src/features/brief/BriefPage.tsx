import { History, Save, Send } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, ButtonLink } from "../../components/Button";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { FormNotice, NumberField, SelectField, TextField } from "../../components/Form";
import { PageHeader } from "../../components/Page";
import { EmptyState, ErrorState, Skeleton } from "../../components/States";
import { journeyApi, type BriefVersion, type NumericRule, type PropertyType } from "../../lib/api";
import {
  POLICY_OPTIONS,
  PROPERTY_TYPE_OPTIONS,
  RENOVATION_OPTIONS,
  TIMING_OPTIONS,
  labelFor,
} from "../../lib/briefOptions";
import { formatDate } from "../../lib/format";
import { dollarsToMinor, formatMinor, minorToDollars } from "../../lib/money";
import { CriterionCard } from "./CriterionCard";
import { WeightsEditor } from "./WeightsEditor";
import { errorLookup, useBrief } from "./useBrief";

export default function BriefPage() {
  const brief = useBrief();
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | undefined>();
  const [versions, setVersions] = useState<BriefVersion[] | null>(null);

  if (brief.status === "loading") {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-1/2" label="Loading your buying brief" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (brief.status === "no-journey") {
    return (
      <>
        <PageHeader eyebrow="Buying brief" title="Your buying brief" testId="brief-header" />
        <EmptyState
          title="No buying journey yet"
          description="Create a buying journey first — the brief belongs to a journey so you can run more than one search."
          action={
            <ButtonLink to="/app/journeys/new" variant="success" data-testid="brief-create-journey">
              Create a buying journey
            </ButtonLink>
          }
          data-testid="brief-empty"
        />
      </>
    );
  }

  if (brief.status === "error" || !brief.data || !brief.draft) {
    return (
      <>
        <PageHeader eyebrow="Buying brief" title="Your buying brief" testId="brief-header" />
        <ErrorState description={brief.message ?? "The brief could not be loaded."} onRetry={brief.reload} />
      </>
    );
  }

  const { data, draft } = brief;
  const allErrors = brief.publishErrors.length > 0 ? brief.publishErrors : data.validation;
  const errorFor = errorLookup(allErrors);
  const published = data.current_version;

  const numeric = (
    key: "beds" | "baths" | "parking" | "land_sqm" | "floor_sqm",
    label: string,
    suffix?: string,
  ) => {
    const rule: NumericRule = draft[key];
    const fieldId = key.replace("_", "-");
    return (
      <CriterionCard
        id={fieldId}
        title={label}
        mode={rule.mode}
        onModeChange={(mode) =>
          brief.setDraft((current) => {
            current[key].mode = mode;
            return current;
          })
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <NumberField
            id={`${fieldId}-min`}
            label="Minimum"
            value={rule.min}
            suffix={suffix}
            error={errorFor(`${key}.min`)}
            onChange={(value) =>
              brief.setDraft((current) => {
                current[key].min = value;
                return current;
              })
            }
          />
          <NumberField
            id={`${fieldId}-max`}
            label="Maximum"
            value={rule.max}
            suffix={suffix}
            error={errorFor(`${key}.max`)}
            onChange={(value) =>
              brief.setDraft((current) => {
                current[key].max = value;
                return current;
              })
            }
          />
        </div>
      </CriterionCard>
    );
  };

  const onPublish = async () => {
    if (reason.trim().length < 3) {
      setReasonError("Give a short reason so the version history stays useful.");
      return;
    }
    setReasonError(undefined);
    const ok = await brief.publish(reason.trim());
    if (ok) {
      setReason("");
      setVersions(null);
    }
  };

  const toggleVersions = async () => {
    if (versions !== null) {
      setVersions(null);
      return;
    }
    setVersions(await journeyApi.versions(data.journey.id));
  };

  return (
    <>
      <PageHeader
        eyebrow="Buying brief"
        title={data.journey.name}
        description={
          published
            ? `Published version ${published.version_no} · ${formatDate(published.published_at)} · re-evaluation ${published.reevaluation_state}`
            : "Nothing published yet. Publishing creates an immutable version with your name, the time and your reason."
        }
        actions={
          <ButtonLink to="/app/brief/locations" variant="secondary" data-testid="brief-locations-link">
            Locations and anchors
          </ButtonLink>
        }
        testId="brief-header"
      />

      {data.journey.status === "onboarding" && (
        <FormNotice tone="info" testId="brief-onboarding-notice">
          Setup is still open at step {data.journey.onboarding_step}.{" "}
          <Link to="/app/journeys/new" className="font-semibold underline underline-offset-4">
            Finish the guided setup
          </Link>
          .
        </FormNotice>
      )}

      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <CriterionCard
          id="budget"
          title="Budget"
          description="Money is recorded in Australian dollars. A missing bound stays Unknown — it is never inferred."
          mode={draft.budget.mode}
          onModeChange={(mode) =>
            brief.setDraft((current) => {
              current.budget.mode = mode;
              return current;
            })
          }
        >
          <NumberField
            id="budget-ceiling"
            label="Ceiling"
            value={minorToDollars(draft.budget.ceiling_minor)}
            suffix="AUD"
            error={errorFor("budget.ceiling_minor")}
            onChange={(value) =>
              brief.setDraft((current) => {
                current.budget.ceiling_minor = dollarsToMinor(value);
                return current;
              })
            }
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <NumberField
              id="budget-preferred-min"
              label="Preferred from"
              value={minorToDollars(draft.budget.preferred_min_minor)}
              error={errorFor("budget.preferred_min_minor")}
              onChange={(value) =>
                brief.setDraft((current) => {
                  current.budget.preferred_min_minor = dollarsToMinor(value);
                  return current;
                })
              }
            />
            <NumberField
              id="budget-preferred-max"
              label="Preferred to"
              value={minorToDollars(draft.budget.preferred_max_minor)}
              error={errorFor("budget.preferred_max_minor")}
              onChange={(value) =>
                brief.setDraft((current) => {
                  current.budget.preferred_max_minor = dollarsToMinor(value);
                  return current;
                })
              }
            />
          </div>
        </CriterionCard>

        <CriterionCard
          id="property-types"
          title="Property type"
          mode={draft.property_profile.types_mode}
          onModeChange={(mode) =>
            brief.setDraft((current) => {
              current.property_profile.types_mode = mode;
              return current;
            })
          }
        >
          <fieldset className="min-w-0">
            <legend className="text-sm font-semibold">Types you would consider</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {PROPERTY_TYPE_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className="flex min-h-[44px] items-center gap-2 rounded-md border border-border bg-surface px-3 text-sm"
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[var(--color-eucalyptus-deep)]"
                    checked={draft.property_profile.types.includes(option.value)}
                    onChange={() =>
                      brief.setDraft((current) => {
                        const types = current.property_profile.types;
                        current.property_profile.types = types.includes(option.value as PropertyType)
                          ? types.filter((t) => t !== option.value)
                          : [...types, option.value];
                        return current;
                      })
                    }
                    data-testid={`brief-type-${option.value}`}
                  />
                  {option.label}
                </label>
              ))}
            </div>
            {errorFor("property_profile.types") && (
              <p className="mt-2 text-xs font-semibold text-risk" data-testid="property-types-error">
                {errorFor("property_profile.types")}
              </p>
            )}
          </fieldset>
        </CriterionCard>

        <CriterionCard
          id="detached"
          title="Detached requirement"
          mode={draft.property_profile.detached_mode}
          onModeChange={(mode) =>
            brief.setDraft((current) => {
              current.property_profile.detached_mode = mode;
              return current;
            })
          }
        >
          <SelectField
            id="detached-required"
            label="Detached only?"
            value={
              draft.property_profile.detached_required === null
                ? "unknown"
                : draft.property_profile.detached_required
                  ? "yes"
                  : "no"
            }
            error={errorFor("property_profile.detached_required")}
            onChange={(value) =>
              brief.setDraft((current) => {
                current.property_profile.detached_required = value === "unknown" ? null : value === "yes";
                return current;
              })
            }
            options={[
              { value: "yes", label: "Yes, detached only" },
              { value: "no", label: "No, attached is fine" },
              { value: "unknown", label: "Unknown" },
            ]}
          />
        </CriterionCard>

        {numeric("beds", "Bedrooms")}
        {numeric("baths", "Bathrooms")}
        {numeric("parking", "Parking")}
        {numeric("land_sqm", "Land area", "m²")}
        {numeric("floor_sqm", "Floor area", "m²")}

        <CriterionCard
          id="renovation"
          title="Renovation tolerance"
          mode={draft.renovation.mode}
          onModeChange={(mode) =>
            brief.setDraft((current) => {
              current.renovation.mode = mode;
              return current;
            })
          }
        >
          <SelectField
            id="renovation-level"
            label="How much work would you take on?"
            value={draft.renovation.level ?? ("cosmetic" as const)}
            error={errorFor("renovation.level")}
            onChange={(level) =>
              brief.setDraft((current) => {
                current.renovation.level = level;
                return current;
              })
            }
            options={RENOVATION_OPTIONS}
          />
        </CriterionCard>

        <CriterionCard
          id="timing"
          title="Purchase timing"
          mode={draft.timing.mode}
          onModeChange={(mode) =>
            brief.setDraft((current) => {
              current.timing.mode = mode;
              return current;
            })
          }
        >
          <SelectField
            id="timing-horizon"
            label="Target horizon"
            value={draft.timing.horizon ?? ("exploring" as const)}
            error={errorFor("timing.horizon")}
            onChange={(horizon) =>
              brief.setDraft((current) => {
                current.timing.horizon = horizon;
                return current;
              })
            }
            options={TIMING_OPTIONS}
          />
        </CriterionCard>

        <section aria-labelledby="policies-heading" className="card min-w-0 p-5" data-testid="criterion-policies">
          <h2 id="policies-heading" className="text-base font-semibold md:text-lg">
            Price and access policy
          </h2>
          <p className="mt-1 text-sm text-muted">
            Contact agent is unpriced and an aggregator band is not an advertised guide. Neither is ever converted into
            a number.
          </p>
          <div className="mt-4 space-y-4">
            <SelectField
              id="policy-unpriced"
              label="Unpriced listings"
              value={draft.policies.unpriced}
              onChange={(value) =>
                brief.setDraft((current) => {
                  current.policies.unpriced = value;
                  return current;
                })
              }
              options={POLICY_OPTIONS}
            />
            <SelectField
              id="policy-early-access"
              label="Early access and off-market mentions"
              value={draft.policies.early_access}
              onChange={(value) =>
                brief.setDraft((current) => {
                  current.policies.early_access = value;
                  return current;
                })
              }
              options={POLICY_OPTIONS}
            />
          </div>
        </section>

        <section aria-labelledby="locations-summary-heading" className="card min-w-0 p-5" data-testid="locations-summary">
          <h2 id="locations-summary-heading" className="text-base font-semibold md:text-lg">
            Locations
          </h2>
          <dl className="mt-3 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
            <dt className="text-muted">States</dt>
            <dd>{draft.locations.states.join(", ") || "Unknown"}</dd>
            <dt className="text-muted">Included</dt>
            <dd>{draft.locations.included.length > 0 ? `${draft.locations.included.length} area(s)` : "None"}</dd>
            <dt className="text-muted">Excluded</dt>
            <dd>{draft.locations.excluded.length > 0 ? `${draft.locations.excluded.length} area(s)` : "None"}</dd>
            <dt className="text-muted">Travel anchors</dt>
            <dd>
              {draft.locations.anchors.length > 0
                ? `${draft.locations.anchors.length} anchor(s) · travel time Unknown`
                : "None"}
            </dd>
          </dl>
          <ButtonLink to="/app/brief/locations" variant="secondary" size="sm" className="mt-4" data-testid="locations-edit-link">
            Edit locations
          </ButtonLink>
        </section>

        <WeightsEditor
          weights={draft.weights}
          totalEnabled={
            (draft.weights.price_enabled ? draft.weights.price : 0) +
            (draft.weights.land_enabled ? draft.weights.land : 0) +
            (draft.weights.location_enabled ? draft.weights.location : 0) +
            (draft.weights.condition_enabled ? draft.weights.condition : 0)
          }
          error={errorFor("weights")}
          busy={brief.busy}
          onReset={() => void brief.resetWeights()}
          onChange={(key, value, enabled) =>
            brief.setDraft((current) => {
              if (enabled !== undefined) current.weights[`${key}_enabled`] = enabled;
              if (value !== null) current.weights[key] = value;
              return current;
            })
          }
        />
      </div>

      <section aria-labelledby="publish-heading" className="card mt-6 max-w-[760px] p-5" data-testid="publish-panel">
        <h2 id="publish-heading" className="text-h3 font-semibold">
          Publish this brief
        </h2>
        <p className="mt-1 text-sm text-muted">
          Publishing stores an immutable version with your email, the time and your reason, then queues re-evaluation.
        </p>

        {allErrors.length > 0 && (
          <div className="mt-4" data-testid="publish-blockers">
            <FormNotice tone="error">
              {allErrors.length} item{allErrors.length === 1 ? "" : "s"} must be fixed before publishing.
            </FormNotice>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-risk">
              {allErrors.map((e) => (
                <li key={`${e.field}-${e.message}`} data-testid={`blocker-${e.field}`}>
                  {e.message}
                </li>
              ))}
            </ul>
          </div>
        )}

        {brief.notice && (
          <div className="mt-4">
            <FormNotice tone="success" testId="brief-notice">
              {brief.notice}
            </FormNotice>
          </div>
        )}
        {brief.message && allErrors.length === 0 && (
          <div className="mt-4">
            <FormNotice tone="error" testId="brief-error">
              {brief.message}
            </FormNotice>
          </div>
        )}

        <div className="mt-4">
          <TextField
            id="publish-reason"
            label="Reason for this version"
            value={reason}
            onChange={setReason}
            placeholder="Raised the ceiling after the loan pre-approval"
            error={reasonError}
          />
        </div>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <Button
            variant="secondary"
            onClick={() => void brief.save()}
            disabled={brief.busy}
            icon={<Save className="h-4 w-4" aria-hidden="true" />}
            data-testid="brief-save-draft"
          >
            {brief.busy ? "Saving…" : "Save draft"}
          </Button>
          <ConfirmDialog
            title="Publish this brief version?"
            description="The published version becomes immutable and re-evaluation is queued. Nothing is sent to anyone."
            confirmLabel="Publish version"
            onConfirm={() => void onPublish()}
            trigger={
              <Button
                variant="success"
                disabled={brief.busy || allErrors.length > 0}
                icon={<Send className="h-4 w-4" aria-hidden="true" />}
                data-testid="brief-publish"
              >
                Publish version
              </Button>
            }
          />
          <Button
            variant="tertiary"
            onClick={() => void toggleVersions()}
            icon={<History className="h-4 w-4" aria-hidden="true" />}
            data-testid="brief-toggle-versions"
          >
            {versions === null ? `Version history (${data.journey.published_versions})` : "Hide version history"}
          </Button>
        </div>
        {brief.dirty && (
          <p className="mt-3 text-xs text-muted" role="status" data-testid="brief-dirty">
            You have unsaved changes. Publishing saves them first.
          </p>
        )}

        {versions !== null && (
          <ol className="mt-5 divide-y divide-border border-t border-border" data-testid="version-history">
            {versions.length === 0 && <li className="py-3 text-sm text-muted">No versions published yet.</li>}
            {versions.map((v) => (
              <li key={v.id} className="py-3 text-sm" data-testid={`version-${v.version_no}`}>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <strong className="font-semibold">Version {v.version_no}</strong>
                  <span className="text-xs text-muted">
                    {formatDate(v.published_at)} · {v.actor_email}
                  </span>
                </div>
                <p className="text-muted">{v.reason}</p>
                <p className="mt-1 text-xs text-muted">
                  Ceiling {formatMinor(v.payload.budget.ceiling_minor)} · land minimum{" "}
                  {v.payload.land_sqm.min === null ? "Unknown" : `${v.payload.land_sqm.min} m²`} · timing{" "}
                  {labelFor(TIMING_OPTIONS, v.payload.timing.horizon)}
                </p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  );
}
