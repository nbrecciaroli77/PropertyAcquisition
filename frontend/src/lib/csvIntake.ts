/**
 * M4.2 CSV intake API client.
 * Preview calls are for convenience only — the backend re-parses and re-validates
 * the raw file independently on every import request.
 */
import { apiFetch } from "./api";

export interface CsvPreviewRow {
  row_index: number;
  address_line: string | null;
  suburb: string | null;
  state: string | null;
  postcode?: string | null;
  beds?: number | null;
  baths?: number | null;
  cars?: number | null;
  land_sqm?: number | null;
  floor_sqm?: number | null;
  property_type?: string | null;
  raw_price?: string | null;
  price_kind?: string | null;
  notes?: string | null;
  errors: string[];
  warnings: string[];
  formula_flags: string[];
  skippable: boolean;
  status: "ok" | "warning" | "error";
}

export interface CsvPreviewResponse {
  batch_key: string;
  filename: string;
  total_rows: number;
  valid_rows: number;
  warning_rows: number;
  error_rows: number;
  preview_rows: CsvPreviewRow[];
  headers_found: string[];
  headers_missing: string[];
}

export interface CsvRowResult {
  row_index: number;
  address?: string;
  outcome: "created" | "matched_existing" | "requires_review" | "failed" | "skipped";
  property_id?: string;
  existing_property_id?: string;
  formula_flags?: string[];
  errors?: string[];
  review_reasons?: string[];
  error?: string;
}

export interface CsvBatchResult {
  batch_id: string;
  batch_key: string;
  filename: string;
  state: string;
  total_rows: number;
  created: number;
  matched_existing: number;
  requires_review: number;
  failed: number;
  skipped: number;
  row_results: CsvRowResult[];
}

export const csvIntakeApi = {
  /** Returns a direct URL for the template download (uses cookies for auth). */
  templateUrl: (journeyId: string): string =>
    `${process.env.REACT_APP_BACKEND_URL}/api/journeys/${journeyId}/intake/csv-template`,

  /** Parse + validate file server-side without writing anything. */
  preview: (journeyId: string, file: File): Promise<CsvPreviewResponse> => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch<CsvPreviewResponse>(`/journeys/${journeyId}/intake/csv-preview`, {
      method: "POST",
      body: fd,
    });
  },

  /** Import the file; backend independently re-parses + validates the raw bytes. */
  import: (
    journeyId: string,
    file: File,
    skipIndices: number[] = [],
  ): Promise<CsvBatchResult> => {
    const fd = new FormData();
    fd.append("file", file);
    const qs = skipIndices.length ? `?skip_indices=${skipIndices.join(",")}` : "";
    return apiFetch<CsvBatchResult>(`/journeys/${journeyId}/intake/csv-import${qs}`, {
      method: "POST",
      body: fd,
    });
  },

  getBatch: (journeyId: string, batchId: string): Promise<CsvBatchResult> =>
    apiFetch<CsvBatchResult>(`/journeys/${journeyId}/intake/batches/${batchId}`),
};
