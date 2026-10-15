import { render, screen } from "@testing-library/react";
import { LandAssessment } from "../features/property/LandAssessment";
import { LandBriefEditor } from "../features/brief/LandBriefEditor";
import type { BriefPayload } from "../lib/api";
import type { GateOut, LandAssessment as Land } from "../lib/properties";
import { evaluationChip } from "../lib/land";

const gate = (criterion: string, outcome: GateOut["outcome"]): GateOut => ({
  criterion, label: criterion, outcome, brief_value: "Supported", observed: "Unknown", reason: `${criterion} reason`,
  fact_key: criterion, source_label: "Synthetic", what_would_change: "Evidence",
});

const LAND: Land = {
  status: "PROVISIONAL",
  priority: 2,
  explanation: "Priority 2: plausible, with named verification gaps.",
  price: {
    advertised_minor: 16_000_000, advertised_upper_minor: null, advertised_raw: "From $160,000", price_kind: "from",
    subtype: "vacant_land", land_component_minor: null, seller_ceiling: "opening_guide_unverified",
    supported_land_price_minor: null, basis: null, verification: "OPENING_GUIDE_NOT_CEILING",
  },
  area: { usable_sqm: null, total_sqm: 1000, min_usable_sqm: 250, max_usable_sqm: null },
  travel: {
    preferred_minutes: 240, minutes: 241, state: "missed", long_drive_exception: false, origin: "Home suburb (synthetic, approximate)",
    origin_precision: "approximate_suburb", note: "Soft preference only; never an exclusion.", source_label: "Synthetic",
  },
  location: { suburb: "Harvey", tier: "priority_town", broader_region: "Mandurah and south" },
  checks: [gate("bushfire", "unknown")],
  failures: [],
  gaps: [{ criterion: "usable_area", label: "Usable land area", reason: "Usable area is unknown." }],
  shed_note: "A shed or listing claim is not permission to live there; the dwelling pathway needs its own evidence.",
  inactive: { completed_project_budget: "inactive", airbnb: "inactive" },
};

describe("U2 land feasibility UI", () => {
  it("shows the ordinal priority, distinct price/area evidence, soft travel and the shed caveat", () => {
    render(<LandAssessment land={LAND} gates={[gate("usable_area", "unknown")]} />);
    expect(screen.getByTestId("land-status-chip")).toHaveTextContent("Priority 2 · provisional");
    expect(screen.getByTestId("land-seller-ceiling")).toHaveTextContent("Opening guide — not a ceiling");
    expect(screen.getByTestId("land-supported-price")).toHaveTextContent("Unknown");
    expect(screen.getByTestId("land-total-area")).toHaveTextContent("1,000 m²");
    expect(screen.getByTestId("land-usable-area")).toHaveTextContent("Unknown");
    expect(screen.getByTestId("land-travel-state")).toHaveTextContent("Soft preference missed");
    expect(screen.getByTestId("land-shed-note")).toHaveTextContent("not permission to live there");
    expect(screen.getByTestId("land-summary")).toHaveTextContent("not a score out of 100");
    expect(screen.queryByText(/\/100|% fit/i)).toBeNull();
  });

  it("labels land evaluations by priority and house by gate verdict", () => {
    const base = { id: "e", brief_version_no: 1, evaluation_version: "v", input_hash: "h", route: "r", gates: [], components: [], computed_at: "" };
    const fit = { state: "unavailable" as const, pct: null, achieved: 0, max_achievable: 0, reason: "" };
    const coverage = { state: "", pct: null, assessed_weight: 0, total_enabled_weight: 0 };
    expect(evaluationChip({ ...base, verdict: "unknown", fit, coverage, land: LAND }, () => "house")).toBe("Priority 2 · provisional");
    expect(evaluationChip({ ...base, verdict: "pass", fit, coverage }, () => "house")).toBe("house");
  });

  it("land brief editor starts empty: no archived defaults are pre-filled", () => {
    const draft = { land_feasibility: null } as unknown as BriefPayload;
    render(<LandBriefEditor draft={draft} setDraft={() => undefined} errorFor={() => undefined} />);
    expect(screen.getByTestId("land-cap-input")).toHaveValue(null);
    expect(screen.getByTestId("land-drive-input")).toHaveValue(null);
    expect(screen.getByTestId("land-inactive-notice")).toHaveTextContent("Airbnb are inactive");
  });
});
