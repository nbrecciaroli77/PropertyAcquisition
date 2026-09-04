import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AreaListEditor, STATE_OPTIONS } from "../../components/AreaListEditor";
import { Button } from "../../components/Button";
import { FormNotice, NumberField, SelectField, TextField } from "../../components/Form";
import { PageHeader } from "../../components/Page";
import { Skeleton } from "../../components/States";
import {
  ApiError,
  journeyApi,
  type Area,
  type BriefPayload,
  type BriefResponse,
  type PropertyType,
  type StateTerritory,
} from "../../lib/api";
import {
  POLICY_OPTIONS,
  PROPERTY_TYPE_OPTIONS,
  TIMEZONE_OPTIONS,
  TIMING_OPTIONS,
  labelFor,
} from "../../lib/briefOptions";
import { deepClone } from "../../lib/clone";
import { useJourneys } from "../../lib/journey";
import { dollarsToMinor, formatMinor, minorToDollars } from "../../lib/money";

const TOTAL_STEPS = 6;
const STEP_TITLES = [
  "Name your journey",
  "Purchase timing",
  "Property type",
  "Budget and price policy",
  "First locations",
  "Review and finish",
];

export default function NewJourneyPage() {
  const navigate = useNavigate();
  const { journeys, loading, reload } = useJourneys();

  const [journeyId, setJourneyId] = useState<string | null>(null);
  const [rowVersion, setRowVersion] = useState(1);
  const [draft, setDraft] = useState<BriefPayload | null>(null);
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("Australia/Perth");
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [resumed, setResumed] = useState(false);
  const [hydrating, setHydrating] = useState(true);

  const existing = useMemo(() => journeys.find((j) => j.status === "onboarding") ?? null, [journeys]);

  useEffect(() => {
    if (loading || draft !== null) return;
    if (existing === null) {
      setDraft(null);
      setHydrating(false);
      return;
    }
    void (async () => {
      const brief = await journeyApi.brief(existing.id);
      setJourneyId(brief.journey.id);
      setRowVersion(brief.journey.row_version);
      setDraft(brief.draft);
      setName(brief.journey.name);
      setTimezone(brief.journey.timezone);
      setStep(brief.journey.onboarding_step);
      setResumed(brief.journey.onboarding_step > 1);
      setHydrating(false);
    })();
  }, [existing, loading, draft]);

  const patch = useCallback((updater: (current: BriefPayload) => BriefPayload) => {
    setDraft((current) => (current === null ? current : updater(deepClone(current))));
  }, []);

  const saveStep = async (nextStep: number) => {
    setBusy(true);
    setError(null);
    try {
      let id = journeyId;
      let version = rowVersion;
      if (id === null) {
        const journey = await journeyApi.create(name.trim() || "My buying journey", timezone);
        id = journey.id;
        version = journey.row_version;
        setJourneyId(id);
        const fresh = await journeyApi.brief(id);
        setDraft(fresh.draft);
        version = fresh.journey.row_version;
      } else if (name.trim()) {
        const journey = await journeyApi.update(id, {
          expected_row_version: version,
          name: name.trim(),
          timezone,
        });
        version = journey.row_version;
      }

      const payload = draft ?? (await journeyApi.brief(id)).draft;
      let response: BriefResponse;
      try {
        response = await journeyApi.saveDraft(id, payload, version, nextStep);
      } catch (conflict) {
        // The journey moved on (another tab, or a save that raced this one): take the newest version and retry once.
        if (!(conflict instanceof ApiError) || conflict.status !== 409) throw conflict;
        const latest = await journeyApi.brief(id);
        response = await journeyApi.saveDraft(id, payload, latest.journey.row_version, nextStep);
      }
      setRowVersion(response.journey.row_version);
      setDraft(response.draft);
      setSavedAt(response.draft_updated_at);
      setStep(nextStep);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That step could not be saved.");
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    if (journeyId === null) return;
    setBusy(true);
    try {
      await journeyApi.completeOnboarding(journeyId);
      await reload();
      navigate("/app/brief");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Onboarding could not be completed.");
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-2/3" label="Loading your journeys" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const brief = draft;
  const setStates = (state: StateTerritory) =>
    patch((current) => {
      current.locations.states = [state];
      return current;
    });

  const toggleType = (type: PropertyType) =>
    patch((current) => {
      const types = current.property_profile.types;
      current.property_profile.types = types.includes(type) ? types.filter((t) => t !== type) : [...types, type];
      return current;
    });

  const setIncluded = (areas: Area[]) =>
    patch((current) => {
      current.locations.included = areas;
      return current;
    });

  return (
    <>
      <PageHeader
        eyebrow="Create buying journey"
        title="Set up your buying journey"
        description="Answer as much as you know. Everything can be skipped and resumed — Unknown is a valid answer and is never treated as a pass or a fail."
        testId="new-journey-header"
      />

      {resumed && (
        <FormNotice tone="info" testId="resume-notice">
          Welcome back — we resumed your setup at step {step} of {TOTAL_STEPS}.
        </FormNotice>
      )}

      <ol className="mb-6 mt-4 flex flex-wrap gap-2" data-testid="onboarding-steps">
        {STEP_TITLES.map((title, index) => {
          const number = index + 1;
          const state = number === step ? "current" : number < step ? "done" : "upcoming";
          return (
            <li key={title}>
              <span
                aria-current={state === "current" ? "step" : undefined}
                className={
                  state === "current"
                    ? "inline-flex items-center gap-2 rounded-full bg-navy px-3 py-1 text-xs font-semibold text-white"
                    : state === "done"
                      ? "inline-flex items-center gap-2 rounded-full bg-eucalyptus-soft px-3 py-1 text-xs font-semibold text-eucalyptus-deep"
                      : "inline-flex items-center gap-2 rounded-full border border-border px-3 py-1 text-xs font-semibold text-muted"
                }
                data-testid={`onboarding-step-${number}`}
              >
                {state === "done" && <Check className="h-3 w-3" aria-hidden="true" />}
                {number}. {title}
              </span>
            </li>
          );
        })}
      </ol>

      <section aria-labelledby="onboarding-step-heading" className="card max-w-[760px] p-5 md:p-6">
        <h2 id="onboarding-step-heading" className="text-h3 font-semibold" data-testid="onboarding-step-title">
          Step {step} of {TOTAL_STEPS} · {STEP_TITLES[step - 1]}
        </h2>

        <div className="mt-5 space-y-5">
          {step === 1 && (
            <>
              <TextField
                id="journey-name"
                label="Journey name"
                value={name}
                onChange={setName}
                placeholder="Perth family home 2026"
                helper="Only you and your household see this."
              />
              <SelectField
                id="journey-state"
                label="Main state or territory"
                value={brief?.locations.states[0] ?? "WA"}
                onChange={setStates}
                options={STATE_OPTIONS}
                helper="You can add more states and specific suburbs later."
                disabled={brief === null && journeyId !== null}
              />
              <SelectField
                id="journey-timezone"
                label="Timezone"
                value={timezone}
                onChange={setTimezone}
                options={TIMEZONE_OPTIONS}
                helper="Deadlines are shown in the property's local timezone and yours where they differ."
              />
            </>
          )}

          {step === 2 && brief && (
            <>
              <SelectField
                id="timing-horizon"
                label="When would you like to buy?"
                value={brief.timing.horizon ?? ("exploring" as const)}
                onChange={(horizon) =>
                  patch((current) => {
                    current.timing.horizon = horizon;
                    return current;
                  })
                }
                options={TIMING_OPTIONS}
              />
              <FormNotice tone="info">
                Timing stays a preference during setup. You can make it a hard rule in the buying brief.
              </FormNotice>
            </>
          )}

          {step === 3 && brief && (
            <>
              <fieldset className="min-w-0" data-testid="property-types">
                <legend className="text-sm font-semibold">Property types you would consider</legend>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {PROPERTY_TYPE_OPTIONS.map((option) => (
                    <label
                      key={option.value}
                      className="flex min-h-[44px] items-center gap-2 rounded-md border border-border bg-surface px-3 text-sm"
                    >
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-[var(--color-eucalyptus-deep)]"
                        checked={brief.property_profile.types.includes(option.value)}
                        onChange={() => toggleType(option.value)}
                        data-testid={`property-type-${option.value}`}
                      />
                      {option.label}
                    </label>
                  ))}
                </div>
              </fieldset>
              <SelectField
                id="detached-required"
                label="Does it need to be detached?"
                value={
                  brief.property_profile.detached_required === null
                    ? "unknown"
                    : brief.property_profile.detached_required
                      ? "yes"
                      : "no"
                }
                onChange={(value) =>
                  patch((current) => {
                    current.property_profile.detached_required = value === "unknown" ? null : value === "yes";
                    return current;
                  })
                }
                options={[
                  { value: "yes", label: "Yes, detached only" },
                  { value: "no", label: "No, attached is fine" },
                  { value: "unknown", label: "Unknown for now" },
                ]}
              />
            </>
          )}

          {step === 4 && brief && (
            <>
              <NumberField
                id="budget-ceiling"
                label="Budget ceiling (AUD)"
                value={minorToDollars(brief.budget.ceiling_minor)}
                onChange={(value) =>
                  patch((current) => {
                    current.budget.ceiling_minor = dollarsToMinor(value);
                    return current;
                  })
                }
                helper="The most you would pay. Leave blank if it is still unknown."
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <NumberField
                  id="budget-preferred-min"
                  label="Preferred range from"
                  value={minorToDollars(brief.budget.preferred_min_minor)}
                  onChange={(value) =>
                    patch((current) => {
                      current.budget.preferred_min_minor = dollarsToMinor(value);
                      return current;
                    })
                  }
                />
                <NumberField
                  id="budget-preferred-max"
                  label="Preferred range to"
                  value={minorToDollars(brief.budget.preferred_max_minor)}
                  onChange={(value) =>
                    patch((current) => {
                      current.budget.preferred_max_minor = dollarsToMinor(value);
                      return current;
                    })
                  }
                />
              </div>
              <SelectField
                id="policy-unpriced"
                label="Unpriced listings (Contact agent)"
                value={brief.policies.unpriced}
                onChange={(value) =>
                  patch((current) => {
                    current.policies.unpriced = value;
                    return current;
                  })
                }
                options={POLICY_OPTIONS}
                helper="Contact agent is unpriced — it is never guessed as a number."
              />
              <SelectField
                id="policy-early-access"
                label="Early-access and off-market mentions"
                value={brief.policies.early_access}
                onChange={(value) =>
                  patch((current) => {
                    current.policies.early_access = value;
                    return current;
                  })
                }
                options={POLICY_OPTIONS}
              />
            </>
          )}

          {step === 5 && brief && (
            <AreaListEditor
              idPrefix="onboarding-included"
              legend="Suburbs or postcodes to watch"
              description="Add the areas you already like. Excluded areas and travel anchors live in the buying brief."
              areas={brief.locations.included}
              onChange={setIncluded}
              defaultState={brief.locations.states[0] ?? "WA"}
            />
          )}

          {step === 6 && brief && (
            <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-[auto_minmax(0,1fr)]" data-testid="onboarding-review">
              <dt className="text-muted">Journey</dt>
              <dd className="font-semibold">{name || "My buying journey"}</dd>
              <dt className="text-muted">Timezone</dt>
              <dd>{timezone}</dd>
              <dt className="text-muted">Timing</dt>
              <dd>{labelFor(TIMING_OPTIONS, brief.timing.horizon)}</dd>
              <dt className="text-muted">Property types</dt>
              <dd>
                {brief.property_profile.types.length > 0
                  ? brief.property_profile.types
                      .map((t) => labelFor(PROPERTY_TYPE_OPTIONS, t))
                      .join(", ")
                  : "Unknown"}
              </dd>
              <dt className="text-muted">Budget ceiling</dt>
              <dd>{formatMinor(brief.budget.ceiling_minor)}</dd>
              <dt className="text-muted">Preferred range</dt>
              <dd>
                {brief.budget.preferred_min_minor === null && brief.budget.preferred_max_minor === null
                  ? "Unknown"
                  : `${formatMinor(brief.budget.preferred_min_minor)} – ${formatMinor(brief.budget.preferred_max_minor)}`}
              </dd>
              <dt className="text-muted">States</dt>
              <dd>{brief.locations.states.join(", ") || "Unknown"}</dd>
              <dt className="text-muted">Included areas</dt>
              <dd>
                {brief.locations.included.length > 0
                  ? brief.locations.included.map((a) => `${a.suburb}, ${a.state}`).join(" · ")
                  : "None yet"}
              </dd>
            </dl>
          )}
        </div>

        {error && (
          <div className="mt-5">
            <FormNotice tone="error" testId="onboarding-error">
              {error}
            </FormNotice>
          </div>
        )}

        <div className="mt-6 flex flex-col gap-2 border-t border-border pt-5 sm:flex-row sm:items-center">
          {step > 1 && (
            <Button
              variant="secondary"
              onClick={() => setStep(step - 1)}
              disabled={busy || hydrating}
              icon={<ArrowLeft className="h-4 w-4" aria-hidden="true" />}
              data-testid="onboarding-back"
            >
              Back
            </Button>
          )}
          {step < TOTAL_STEPS && (
            <>
              <Button onClick={() => void saveStep(step + 1)} disabled={busy || hydrating} data-testid="onboarding-next">
                {hydrating ? "Loading…" : busy ? "Saving…" : "Save and continue"}
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                variant="tertiary"
                onClick={() => void saveStep(step)}
                disabled={busy || hydrating}
                data-testid="onboarding-save-resume"
              >
                Save and finish later
              </Button>
            </>
          )}
          {step === TOTAL_STEPS && (
            <Button variant="success" onClick={() => void finish()} disabled={busy || hydrating} data-testid="onboarding-finish">
              {busy ? "Finishing…" : "Finish setup and open the brief"}
            </Button>
          )}
        </div>
        {savedAt && (
          <p className="mt-3 text-xs text-muted" role="status" data-testid="onboarding-saved-at">
            Draft saved. You can close this page and resume from Today.
          </p>
        )}
      </section>
    </>
  );
}
