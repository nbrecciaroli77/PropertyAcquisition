const base = process.env.REACT_APP_BACKEND_URL;

export interface Meta {
  app_name: string;
  working_name_status: string;
  gate: string;
  milestone: number;
  synthetic_data_only: boolean;
  email_delivery: string;
  flags: Record<string, "off" | "on" | "locked_off">;
}

export interface FieldError {
  field: string;
  message: string;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  fieldErrors: FieldError[];
  constructor(status: number, message: string, code?: string, fieldErrors: FieldError[] = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.fieldErrors = fieldErrors;
  }
}

type Detail = unknown;

function messageFromDetail(detail: Detail): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => (e && typeof e === "object" && "msg" in e ? String((e as { msg: unknown }).msg) : ""))
      .filter(Boolean)
      .join(" ");
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  return "Something went wrong. Please try again.";
}

function fieldErrorsFromDetail(detail: Detail): FieldError[] {
  if (detail && typeof detail === "object" && "errors" in detail) {
    const errors = (detail as { errors: unknown }).errors;
    if (Array.isArray(errors)) return errors as FieldError[];
  }
  if (Array.isArray(detail)) {
    return detail
      .filter((e): e is { loc: unknown[]; msg: string } => !!e && typeof e === "object" && "loc" in e)
      .map((e) => ({
        field: e.loc.slice(1).filter((p) => typeof p === "string").join("."),
        message: e.msg,
      }));
  }
  return [];
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${base}/api${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (body as { detail?: Detail }).detail;
    const code =
      detail && typeof detail === "object" && "code" in detail
        ? String((detail as { code: unknown }).code)
        : undefined;
    throw new ApiError(response.status, messageFromDetail(detail), code, fieldErrorsFromDetail(detail));
  }
  return body as T;
}

export const fetchMeta = (): Promise<Meta> => apiFetch<Meta>("/meta");

/* ---------------- accounts ---------------- */

export interface UserOut {
  id: string;
  email: string;
  display_name: string;
  timezone: string;
  locale: string;
  email_verified: boolean;
}

export interface WorkspaceOut {
  id: string;
  name: string;
  timezone: string;
  currency: string;
  role: string;
}

export interface MeResponse {
  user: UserOut;
  workspace: WorkspaceOut;
  session_count: number;
}

export interface SessionOut {
  id: string;
  user_agent: string;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  current: boolean;
}

export const authApi = {
  signup: (body: { email: string; password: string; display_name: string; workspace_name?: string }) =>
    apiFetch<{ status: string; email: string; message: string }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  reissueVerification: (email: string) =>
    apiFetch<{ status: string; message: string }>("/auth/reissue-verification", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  verifyEmail: (token: string) =>
    apiFetch<{ status: string; email: string }>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  login: (email: string, password: string) =>
    apiFetch<MeResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => apiFetch<MeResponse>("/auth/me"),
  updateProfile: (body: { display_name: string; timezone: string }) =>
    apiFetch<MeResponse>("/auth/me", { method: "PATCH", body: JSON.stringify(body) }),
  refresh: () => apiFetch<MeResponse>("/auth/refresh", { method: "POST" }),
  logout: () => apiFetch<{ status: string }>("/auth/logout", { method: "POST" }),
  logoutAll: () => apiFetch<{ status: string }>("/auth/logout-all", { method: "POST" }),
  sessions: () => apiFetch<SessionOut[]>("/auth/sessions"),
  revokeSession: (id: string) => apiFetch<{ status: string }>(`/auth/sessions/${id}`, { method: "DELETE" }),
  forgotPassword: (email: string) =>
    apiFetch<{ status: string; message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token: string, password: string) =>
    apiFetch<{ status: string; email: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),
};

/* ---------------- brief ---------------- */

export type Mode = "hard" | "preference" | "disabled" | "unknown";
export type StateTerritory = "WA" | "SA" | "NT" | "QLD" | "NSW" | "ACT" | "VIC" | "TAS";
export type PropertyType = "house" | "townhouse" | "villa" | "unit" | "apartment" | "land" | "acreage";
export type RenovationLevel = "none" | "cosmetic" | "moderate" | "structural";
export type TimingHorizon = "asap" | "3_months" | "6_months" | "12_months" | "exploring";
export type PolicyChoice = "include" | "exclude" | "flag";

export interface NumericRule {
  mode: Mode;
  min: number | null;
  max: number | null;
}

export interface Area {
  suburb: string;
  state: StateTerritory;
  postcode: string | null;
}

export interface Anchor {
  label: string;
  address: string;
  max_minutes: number | null;
}

export interface BriefPayload {
  schema_version: 1;
  currency: "AUD";
  budget: {
    mode: Mode;
    ceiling_minor: number | null;
    preferred_min_minor: number | null;
    preferred_max_minor: number | null;
  };
  property_profile: {
    types_mode: Mode;
    types: PropertyType[];
    detached_mode: Mode;
    detached_required: boolean | null;
  };
  beds: NumericRule;
  baths: NumericRule;
  parking: NumericRule;
  land_sqm: NumericRule;
  floor_sqm: NumericRule;
  renovation: { mode: Mode; level: RenovationLevel | null };
  timing: { mode: Mode; horizon: TimingHorizon | null };
  locations: {
    mode: Mode;
    states: StateTerritory[];
    included: Area[];
    excluded: Area[];
    radius_km: number | null;
    anchors: Anchor[];
  };
  policies: { unpriced: PolicyChoice; early_access: PolicyChoice };
  weights: {
    price: number;
    land: number;
    location: number;
    condition: number;
    price_enabled: boolean;
    land_enabled: boolean;
    location_enabled: boolean;
    condition_enabled: boolean;
  };
}

export interface Journey {
  id: string;
  name: string;
  status: "onboarding" | "active" | "archived";
  timezone: string;
  onboarding_step: number;
  onboarding_complete: boolean;
  row_version: number;
  current_version_no: number | null;
  published_versions: number;
  created_at: string;
  updated_at: string;
}

export interface BriefVersion {
  id: string;
  version_no: number;
  reason: string;
  published_at: string;
  actor_email: string;
  reevaluation_state: string;
  payload: BriefPayload;
}

export interface BriefResponse {
  journey: Journey;
  draft: BriefPayload;
  draft_updated_at: string;
  validation: FieldError[];
  current_version: BriefVersion | null;
  weight_total_enabled: number;
}

export const journeyApi = {
  list: () => apiFetch<Journey[]>("/journeys"),
  create: (name: string, timezone: string) =>
    apiFetch<Journey>("/journeys", { method: "POST", body: JSON.stringify({ name, timezone }) }),
  get: (id: string) => apiFetch<Journey>(`/journeys/${id}`),
  update: (
    id: string,
    body: { expected_row_version: number; name?: string; timezone?: string; onboarding_step?: number; status?: string },
  ) => apiFetch<Journey>(`/journeys/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  completeOnboarding: (id: string) =>
    apiFetch<Journey>(`/journeys/${id}/complete-onboarding`, { method: "POST" }),
  brief: (id: string) => apiFetch<BriefResponse>(`/journeys/${id}/brief`),
  saveDraft: (id: string, payload: BriefPayload, expected_row_version: number, onboarding_step?: number) =>
    apiFetch<BriefResponse>(`/journeys/${id}/brief/draft`, {
      method: "PUT",
      body: JSON.stringify({ payload, expected_row_version, onboarding_step: onboarding_step ?? null }),
    }),
  resetWeights: (id: string) => apiFetch<BriefResponse>(`/journeys/${id}/brief/reset-weights`, { method: "POST" }),
  publish: (id: string, reason: string, expected_row_version: number) =>
    apiFetch<BriefResponse>(`/journeys/${id}/brief/publish`, {
      method: "POST",
      body: JSON.stringify({ reason, expected_row_version }),
    }),
  versions: (id: string) => apiFetch<BriefVersion[]>(`/journeys/${id}/brief/versions`),
};

export interface OutboxMessage {
  id: string;
  to_email: string;
  kind: string;
  subject: string;
  body_text: string;
  action_url: string | null;
  delivery_state: string;
  created_at: string;
}

export const devApi = {
  outbox: (email?: string) =>
    apiFetch<OutboxMessage[]>(`/dev/outbox${email ? `?email=${encodeURIComponent(email)}` : ""}`),
};
