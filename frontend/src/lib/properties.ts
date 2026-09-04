import { apiFetch } from "./api";
import { known, unknown } from "./format";
import type { BuyerState, GateOutcome, MarketState, PriceKind, Tri } from "./types";

export interface FactOut {
  key: string;
  value_state: "known" | "unknown" | "not_applicable" | "conflict";
  value_int: number | null;
  value_text: string | null;
  value_bool: boolean | null;
  source_kind: string;
  source_label: string;
  observed_at: string;
  checked_at: string;
  freshness: "fresh" | "ageing" | "stale";
  confidence: string;
  conflict_note: string | null;
}

export interface CampaignOut {
  id: string;
  source_label: string;
  market_state: string;
  price_kind: string;
  raw_price: string;
  lower_minor: number | null;
  upper_minor: number | null;
  currency: string;
  price_source: string;
  last_checked_at: string;
  freshness: string;
}

export interface GateOut {
  criterion: string;
  label: string;
  outcome: "pass" | "fail" | "unknown";
  brief_value: string;
  observed: string;
  reason: string;
  fact_key: string | null;
  source_label: string;
  what_would_change: string;
}

export interface ComponentOut {
  name: string;
  weight: number;
  enabled: boolean;
  assessed: boolean;
  score: number | null;
  points: number;
  max_points: number;
  reason: string;
}

export interface EvaluationOut {
  id: string;
  brief_version_no: number;
  evaluation_version: string;
  input_hash: string;
  verdict: "pass" | "fail" | "unknown";
  route: string;
  fit: { state: "known" | "unavailable"; pct: number | null; achieved: number; max_achievable: number; reason: string };
  coverage: { state: string; pct: number | null; assessed_weight: number; total_enabled_weight: number };
  gates: GateOut[];
  components: ComponentOut[];
  computed_at: string;
}

export interface PropertySummary {
  id: string;
  legacy_ref: string | null;
  address_line: string;
  unit: string | null;
  suburb: string;
  state: string;
  postcode: string | null;
  synthetic: boolean;
  image_url: string | null;
  image_attribution: string | null;
  campaign: CampaignOut | null;
  facts: Record<string, FactOut>;
  buyer_state: string;
  saved: boolean;
  buyer_row_version: number;
  evaluation: EvaluationOut | null;
  waived_criteria: string[];
  allowed_transitions: string[];
  updated_at: string;
}

export interface WaiverOut {
  id: string;
  criterion: string;
  reason: string;
  actor_email: string;
  created_at: string;
}
export interface NoteOut {
  id: string;
  body: string;
  author_email: string;
  row_version: number;
  created_at: string;
  updated_at: string;
}
export interface TaskOut {
  id: string;
  title: string;
  done: boolean;
  done_at: string | null;
  row_version: number;
  created_at: string;
}
export interface ActivityOut {
  id: string;
  kind: string;
  summary: string;
  detail: Record<string, unknown>;
  actor_email: string | null;
  property_id: string | null;
  created_at: string;
}
export interface ObservationOut {
  id: string;
  source_kind: string;
  source_label: string;
  observed_at: string;
  checked_at: string;
  freshness: string;
  note: string | null;
}

export interface PropertyDetail extends PropertySummary {
  observations: ObservationOut[];
  waivers: WaiverOut[];
  notes: NoteOut[];
  tasks: TaskOut[];
  activity: ActivityOut[];
  row_version: number;
}

export interface TodayOut {
  journey_id: string;
  brief_version_no: number | null;
  total_properties: number;
  eligible_reviewing: number;
  verification_required: number;
  known_failures: number;
  fit_available: number;
  under_offer_market: number;
  changes: ActivityOut[];
  open_tasks: number;
  attention: PropertySummary[];
}

const post = <T,>(path: string, body: unknown, method = "POST") =>
  apiFetch<T>(path, { method, body: JSON.stringify(body) });

export const propertyApi = {
  list: (journeyId: string, params: Record<string, string | undefined> = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== "") as [string, string][]);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return apiFetch<PropertySummary[]>(`/journeys/${journeyId}/properties${suffix}`);
  },
  compare: (journeyId: string, ids: string[]) =>
    apiFetch<PropertySummary[]>(`/journeys/${journeyId}/properties/compare?ids=${encodeURIComponent(ids.join(","))}`),
  today: (journeyId: string) => apiFetch<TodayOut>(`/journeys/${journeyId}/today`),
  get: (journeyId: string, id: string) => apiFetch<PropertyDetail>(`/journeys/${journeyId}/properties/${id}`),
  stage: (journeyId: string, id: string, to_state: string, expected_row_version: number) =>
    post<PropertyDetail>(`/journeys/${journeyId}/properties/${id}/stage`, { to_state, expected_row_version }),
  setSaved: (journeyId: string, id: string, saved: boolean, expected_row_version: number) =>
    post<PropertyDetail>(`/journeys/${journeyId}/properties/${id}/saved`, { saved, expected_row_version }),
  addWaiver: (journeyId: string, id: string, criterion: string, reason: string) =>
    post<PropertyDetail>(`/journeys/${journeyId}/properties/${id}/waivers`, { criterion, reason }),
  revokeWaiver: (journeyId: string, id: string, waiverId: string) =>
    apiFetch<PropertyDetail>(`/journeys/${journeyId}/properties/${id}/waivers/${waiverId}`, { method: "DELETE" }),
  addNote: (journeyId: string, id: string, body: string) =>
    post<PropertyDetail>(`/journeys/${journeyId}/properties/${id}/notes`, { body }),
  editNote: (journeyId: string, id: string, noteId: string, body: string, expected_row_version: number) =>
    post<PropertyDetail>(`/journeys/${journeyId}/properties/${id}/notes/${noteId}`, { body, expected_row_version }, "PATCH"),
  addTask: (journeyId: string, id: string, title: string) =>
    post<PropertyDetail>(`/journeys/${journeyId}/properties/${id}/tasks`, { title }),
  updateTask: (journeyId: string, id: string, taskId: string, done: boolean, expected_row_version: number) =>
    post<PropertyDetail>(`/journeys/${journeyId}/properties/${id}/tasks/${taskId}`, { done, expected_row_version }, "PATCH"),
  loadDemo: (journeyId: string) =>
    post<{ created: number; evaluated_against: number | string }>("/dev/load-demo-properties", { journey_id: journeyId }),
};

/* ---------------- labels ---------------- */

export const BUYER_STATES: { key: string; label: BuyerState }[] = [
  { key: "reviewing", label: "Reviewing" },
  { key: "shortlisted", label: "Shortlisted" },
  { key: "inspection_considered", label: "Inspection considered" },
  { key: "inspected", label: "Inspected" },
  { key: "due_diligence", label: "Due diligence" },
  { key: "offer_preparation", label: "Offer preparation" },
  { key: "offer_submitted", label: "Offer submitted" },
  { key: "under_contract", label: "Under contract" },
  { key: "settled", label: "Settled" },
  { key: "rejected", label: "Rejected" },
  { key: "archived", label: "Archived" },
];

export const buyerLabel = (key: string): BuyerState =>
  BUYER_STATES.find((s) => s.key === key)?.label ?? ("Reviewing" as BuyerState);

const MARKET: Record<string, MarketState> = {
  active: "Active",
  under_offer: "Under offer",
  withdrawn: "Withdrawn",
  sold: "Sold",
  unknown: "Unknown",
};
export const marketLabel = (key: string | undefined): MarketState => (key ? MARKET[key] ?? "Unknown" : "Unknown");

const PRICE: Record<string, PriceKind> = {
  exact: "Exact",
  range: "Range",
  from: "From",
  offers_over: "Offers over",
  auction: "Auction",
  contact_agent: "Contact agent",
  expressions_of_interest: "Expressions of interest",
  conflicting: "Conflicting",
};
export const priceKindLabel = (key: string | undefined): PriceKind => (key ? PRICE[key] ?? "Contact agent" : "Contact agent");

export const gateLabel = (verdict: "pass" | "fail" | "unknown" | undefined): GateOutcome =>
  verdict === "pass" ? "Pass" : verdict === "fail" ? "Fail" : "Unknown";

export const verdictText = (verdict: "pass" | "fail" | "unknown" | undefined): string =>
  verdict === "pass" ? "Gates pass" : verdict === "fail" ? "Known failure" : "Verification required";

export const factTri = (p: PropertySummary, key: string): Tri<number> => {
  const f = p.facts[key];
  if (!f) return unknown();
  if (f.value_state === "not_applicable") return { state: "not-applicable" };
  if (f.value_state === "known" && f.value_int !== null) return known(f.value_int);
  return unknown();
};

export const factText = (p: PropertySummary, key: string): string => {
  const f = p.facts[key];
  if (!f || f.value_state === "unknown") return "Unknown";
  if (f.value_state === "conflict") return "Conflicting";
  if (f.value_state === "not_applicable") return "Not applicable";
  if (f.value_int !== null) return String(f.value_int);
  if (f.value_bool !== null) return f.value_bool ? "Yes" : "No";
  return humanise(f.value_text ?? "Unknown");
};

export const humanise = (s: string): string => {
  const t = s.replace(/_/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
};

export const fitTri = (p: PropertySummary): Tri<number> =>
  p.evaluation && p.evaluation.fit.state === "known" && p.evaluation.fit.pct !== null ? known(p.evaluation.fit.pct) : unknown();

export const coverageTri = (p: PropertySummary): Tri<number> =>
  p.evaluation && p.evaluation.coverage.pct !== null ? known(p.evaluation.coverage.pct) : unknown();

export const gateReason = (p: PropertySummary): string => {
  const e = p.evaluation;
  if (!e) return "No published brief yet — publish the buying brief to evaluate this property.";
  const fail = e.gates.filter((g) => g.outcome === "fail");
  if (fail.length) return fail.map((g) => g.reason).join(" ");
  const unk = e.gates.filter((g) => g.outcome === "unknown");
  if (unk.length) return `${unk.map((g) => g.label).join(", ")} unknown — verification required. Unknown is not Pass.`;
  return `All ${e.gates.length} hard rules pass on the recorded facts.`;
};

export const fullAddress = (p: PropertySummary): string => `${p.address_line}, ${p.suburb} ${p.state}`;

/* ---------------- compare selection (client-side, max four) ---------------- */

const COMPARE_KEY = "pa.compare";
export const MAX_COMPARE = 4;

export const readCompare = (): string[] => {
  try {
    const raw = JSON.parse(localStorage.getItem(COMPARE_KEY) ?? "[]");
    return Array.isArray(raw) ? raw.filter((x): x is string => typeof x === "string").slice(0, MAX_COMPARE) : [];
  } catch {
    return [];
  }
};

export const writeCompare = (ids: string[]): void => {
  localStorage.setItem(COMPARE_KEY, JSON.stringify(ids.slice(0, MAX_COMPARE)));
  window.dispatchEvent(new Event("pa.compare"));
};
