/**
 * M4.1 intake API client.
 * No URL fetching, no AI — just form submission.
 */
import { apiFetch } from "./api";

export type IntakeMode = "structured_form" | "url_with_facts" | "pasted_text";

export interface FactsIn {
  beds?: number | null;
  baths?: number | null;
  cars?: number | null;
  land_sqm?: number | null;
  floor_sqm?: number | null;
  property_type?:
    | "house"
    | "townhouse"
    | "villa"
    | "unit"
    | "apartment"
    | "land"
    | "acreage"
    | null;
  detached?: boolean | null;
  condition?: "move_in_ready" | "usable_home" | "renovation" | null;
  location_tier?: "primary" | "strong_alternative" | "conditional" | null;
}

export interface PriceIn {
  price_kind:
    | "exact"
    | "range"
    | "from"
    | "offers_over"
    | "auction"
    | "contact_agent"
    | "expressions_of_interest"
    | "conflicting";
  raw_price: string;
  lower_minor?: number | null;
  upper_minor?: number | null;
}

export interface StructuredPayload {
  address_line: string;
  suburb: string;
  state: string;
  postcode?: string | null;
  facts: FactsIn;
  price?: PriceIn | null;
  notes?: string | null;
}

export interface UrlWithFactsPayload {
  source_url: string;
  address_line: string;
  suburb: string;
  state: string;
  postcode?: string | null;
  facts: FactsIn;
  price?: PriceIn | null;
  notes?: string | null;
}

export interface PastedTextPayload {
  raw_text: string;
  overrides: FactsIn;
  price_override?: PriceIn | null;
  notes?: string | null;
}

export interface IntakeRequest {
  mode: IntakeMode;
  structured?: StructuredPayload | null;
  url_with_facts?: UrlWithFactsPayload | null;
  pasted_text?: PastedTextPayload | null;
}

export interface ParsedFactsOut {
  address_line: string | null;
  suburb: string | null;
  state: string | null;
  postcode: string | null;
  beds: number | null;
  baths: number | null;
  cars: number | null;
  land_sqm: number | null;
  floor_sqm: number | null;
  property_type: string | null;
  price_kind: string | null;
  raw_price: string | null;
  lower_minor: number | null;
  upper_minor: number | null;
  review_reasons: string[];
  parser_version: string;
}

export interface IntakeResult {
  intake_id: string;
  state: "completed" | "duplicate" | "requires_review" | "failed";
  property_id: string | null;
  duplicate_property_id: string | null;
  duplicate_address: string | null;
  review_reasons: string[];
  parsed_facts: ParsedFactsOut | null;
  journey_id: string;
}

export const intakeApi = {
  submit: (journeyId: string, body: IntakeRequest): Promise<IntakeResult> =>
    apiFetch<IntakeResult>(`/journeys/${journeyId}/intake`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  parsePreview: (journeyId: string, rawText: string): Promise<ParsedFactsOut> =>
    apiFetch<ParsedFactsOut>(`/journeys/${journeyId}/intake/parse-preview`, {
      method: "POST",
      body: JSON.stringify({ raw_text: rawText }),
    }),

  get: (journeyId: string, intakeId: string): Promise<IntakeResult> =>
    apiFetch<IntakeResult>(`/journeys/${journeyId}/intake/${intakeId}`),
};

/** Human-readable review reason labels */
export const REVIEW_REASON_LABELS: Record<string, string> = {
  address_incomplete: "Address could not be fully extracted — please verify",
  price_ambiguous: "Price is ambiguous or uses a band — flagged for your review",
};

export function reviewReasonLabel(reason: string): string {
  return REVIEW_REASON_LABELS[reason] ?? reason.replace(/_/g, " ");
}
