import { render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../app/router";
import { AuthProvider } from "../lib/auth";
import type { BriefResponse, Journey, MeResponse } from "../lib/api";

export const OWNER_ME: MeResponse = {
  user: {
    id: "11111111-1111-1111-1111-111111111111",
    email: "owner@propertyacquisition-demo.com",
    display_name: "Nick",
    timezone: "Australia/Perth",
    locale: "en-AU",
    email_verified: true,
  },
  workspace: {
    id: "22222222-2222-2222-2222-222222222222",
    name: "Brecciaroli household",
    timezone: "Australia/Perth",
    currency: "AUD",
    role: "owner",
  },
  session_count: 1,
};

export const JOURNEY: Journey = {
  id: "33333333-3333-3333-3333-333333333333",
  name: "Perth family home 2026",
  status: "active",
  timezone: "Australia/Perth",
  onboarding_step: 6,
  onboarding_complete: true,
  row_version: 3,
  current_version_no: 1,
  published_versions: 1,
  created_at: "2026-06-01T00:00:00+08:00",
  updated_at: "2026-06-18T00:00:00+08:00",
};

const DRAFT: BriefResponse["draft"] = {
  schema_version: 1,
  currency: "AUD",
  budget: { mode: "hard", ceiling_minor: 125000000, preferred_min_minor: null, preferred_max_minor: null },
  property_profile: { types_mode: "preference", types: ["house"], detached_mode: "preference", detached_required: true },
  beds: { mode: "preference", min: 4, max: null },
  baths: { mode: "preference", min: 2, max: null },
  parking: { mode: "preference", min: 2, max: null },
  land_sqm: { mode: "hard", min: 400, max: null },
  floor_sqm: { mode: "preference", min: null, max: null },
  renovation: { mode: "preference", level: "cosmetic" },
  timing: { mode: "preference", horizon: "6_months" },
  locations: { mode: "hard", states: ["WA"], included: [], excluded: [], radius_km: null, anchors: [] },
  policies: { unpriced: "flag", early_access: "flag" },
  weights: {
    price: 30,
    land: 30,
    location: 20,
    condition: 20,
    price_enabled: true,
    land_enabled: true,
    location_enabled: true,
    condition_enabled: true,
  },
};

export const BRIEF: BriefResponse = {
  journey: JOURNEY,
  draft: DRAFT,
  draft_updated_at: "2026-06-18T00:00:00+08:00",
  validation: [],
  current_version: null,
  weight_total_enabled: 100,
};

type Handler = { status?: number; body: unknown };

export const TODAY_EMPTY = {
  journey_id: "33333333-3333-3333-3333-333333333333",
  brief_version_no: null,
  total_properties: 0,
  eligible_reviewing: 0,
  verification_required: 0,
  known_failures: 0,
  fit_available: 0,
  under_offer_market: 0,
  changes: [],
  open_tasks: 0,
  attention: [],
};

export type FetchStub = ((input: RequestInfo | URL, init?: RequestInit) => Promise<Response>) & {
  calls: string[];
};

/** Stubs the API so router-level providers resolve deterministically. */
export function mockApi(overrides: Record<string, Handler> = {}): FetchStub {
  const handlers: Record<string, Handler> = {
    "/api/auth/me": { body: OWNER_ME },
    "/api/auth/refresh": { status: 401, body: { detail: "Not authenticated" } },
    "/api/journeys/33333333-3333-3333-3333-333333333333/brief": { body: BRIEF },
    "/api/journeys/33333333-3333-3333-3333-333333333333/today": { body: TODAY_EMPTY },
    "/api/journeys/33333333-3333-3333-3333-333333333333/properties": { body: [] },
    "/api/journeys": { body: [JOURNEY] },
    ...overrides,
  };
  const keys = Object.keys(handlers).sort((a, b) => b.length - a.length);
  const calls: string[] = [];
  const stub = async (input: RequestInfo | URL): Promise<Response> => {
    const url = String(input);
    calls.push(url);
    const key = keys.find((k) => url.includes(k));
    const handler = key ? handlers[key] : { status: 404, body: { detail: "Not found" } };
    const status = handler.status ?? 200;
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => handler.body,
    } as Response;
  };
  const mock = Object.assign(stub, { calls }) as FetchStub;
  (globalThis as unknown as { fetch: unknown }).fetch = mock;
  document.cookie = "pa_signed_in=1";
  return mock;
}

export function mockAnonymous(): FetchStub {
  const mock = mockApi({
    "/api/auth/me": { status: 401, body: { detail: "Not authenticated" } },
    "/api/auth/refresh": { status: 401, body: { detail: "Not authenticated" } },
  });
  document.cookie = "pa_signed_in=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  return mock;
}

export const renderAt = (path: string) => {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>,
  );
};

export { screen, waitFor, within };
