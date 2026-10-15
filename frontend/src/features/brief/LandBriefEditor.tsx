import { FormNotice, NumberField, TextField } from "../../components/Form";
import type { BriefPayload, LandFeasibilityBrief, LandSubtype } from "../../lib/api";
import { dollarsToMinor, minorToDollars } from "../../lib/money";

type Props = {
  draft: BriefPayload;
  setDraft: (updater: (current: BriefPayload) => BriefPayload) => void;
  errorFor: (field: string) => string | undefined;
};

const EMPTY: LandFeasibilityBrief = {
  profile_version: "LAND_FEASIBILITY_V1",
  land_price_cap_minor: null,
  min_usable_sqm: null,
  max_usable_sqm: null,
  preferred_drive_minutes: null,
  drive_origin_label: null,
  drive_origin_precision: "approximate_suburb",
  priority_towns: [],
  include_surrounds: true,
  broader_region_label: null,
  long_drive_exceptions: [],
  subtypes: ["vacant_land", "house_and_land"],
  completed_project_budget: "inactive",
  airbnb: "inactive",
};

const list = (value: string) => value.split(",").map((v) => v.trim()).filter(Boolean);

/** Land campaign brief: explicit LAND_FEASIBILITY_V1 values. Nothing is pre-filled from archived defaults. */
export function LandBriefEditor({ draft, setDraft, errorFor }: Props) {
  const land = draft.land_feasibility ?? EMPTY;
  const update = (patch: Partial<LandFeasibilityBrief>) =>
    setDraft((current) => ({ ...current, land_feasibility: { ...(current.land_feasibility ?? EMPTY), ...patch } }));
  const err = (key: string) => errorFor(`land_feasibility.${key}`) ?? (key === "land_price_cap_minor" ? errorFor("land_feasibility") : undefined);
  const toggleSubtype = (s: LandSubtype) =>
    update({ subtypes: land.subtypes.includes(s) ? land.subtypes.filter((x) => x !== s) : [...land.subtypes, s] });

  return (
    <section className="card mt-4 max-w-[760px] space-y-4 p-5" data-testid="land-brief-editor">
      <h2 className="text-h3 font-semibold">Land feasibility profile (LAND_FEASIBILITY_V1)</h2>
      <p className="text-sm text-muted">
        Research priorities are ordinal (Priority 1 / Priority 2 / Excluded), never a score out of 100. Only a documented failure excludes;
        unknown evidence stays provisional. Required values must be entered — archived defaults are never used.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <NumberField id="land-cap" testId="land-cap-input" label="Land purchase price cap (inclusive)" suffix="AUD"
          value={minorToDollars(land.land_price_cap_minor)} error={err("land_price_cap_minor")}
          onChange={(v) => update({ land_price_cap_minor: dollarsToMinor(v) })} />
        <NumberField id="land-min-usable" testId="land-min-usable-input" label="Minimum usable area" suffix="m²"
          value={land.min_usable_sqm} error={err("min_usable_sqm")} onChange={(v) => update({ min_usable_sqm: v })} />
        <NumberField id="land-max-usable" testId="land-max-usable-input" label="Maximum usable area (blank = no maximum)" suffix="m²"
          value={land.max_usable_sqm} error={err("max_usable_sqm")} onChange={(v) => update({ max_usable_sqm: v })} />
        <NumberField id="land-drive" testId="land-drive-input" label="Preferred driving time (soft preference)" suffix="min"
          value={land.preferred_drive_minutes} error={err("preferred_drive_minutes")} onChange={(v) => update({ preferred_drive_minutes: v })} />
      </div>
      <TextField id="land-origin" testId="land-origin-input" label="Driving-time origin" value={land.drive_origin_label ?? ""}
        helper="A suburb-level origin is labelled approximate until an exact home anchor is authorised."
        error={err("drive_origin_label")} onChange={(v) => update({ drive_origin_label: v || null })} />
      <TextField id="land-towns" testId="land-towns-input" label="Priority towns (comma separated, WA) — surrounds included"
        value={land.priority_towns.map((t) => t.suburb).join(", ")} error={err("priority_towns")}
        onChange={(v) => update({ priority_towns: list(v).map((suburb) => ({ suburb, state: "WA", postcode: null })) })} />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField id="land-region" testId="land-region-input" label="Broader region" value={land.broader_region_label ?? ""}
          onChange={(v) => update({ broader_region_label: v || null })} />
        <TextField id="land-exceptions" testId="land-exceptions-input" label="Explicit longer-drive options"
          value={land.long_drive_exceptions.join(", ")} onChange={(v) => update({ long_drive_exceptions: list(v) })} />
      </div>
      <fieldset data-testid="land-subtypes">
        <legend className="text-sm font-semibold text-navy">Opportunity types</legend>
        {(["vacant_land", "house_and_land"] as LandSubtype[]).map((s) => (
          <label key={s} className="mr-5 inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={land.subtypes.includes(s)} onChange={() => toggleSubtype(s)} data-testid={`land-subtype-${s}`} />
            {s === "vacant_land" ? "Vacant land" : "House-and-land"}
          </label>
        ))}
        {err("subtypes") && <p className="text-sm text-risk">{err("subtypes")}</p>}
      </fieldset>
      <FormNotice tone="info" testId="land-inactive-notice">
        Completed-project budget and Airbnb are inactive for this profile.
      </FormNotice>
    </section>
  );
}
