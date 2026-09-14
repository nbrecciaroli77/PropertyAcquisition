/**
 * M4.2 duplicate review API client.
 */
import { apiFetch } from "./api";

export interface PropertySummary {
  id: string;
  address_line: string;
  suburb: string;
  state: string;
  postcode?: string | null;
  normalised_address: string;
  created_at?: string | null;
  earliest_discovery?: string | null;
  fact_count: number;
  merged_into_id?: string | null;
}

export interface DuplicateProposal {
  id: string;
  workspace_id: string;
  property_a: PropertySummary;
  property_b: PropertySummary;
  state: "pending" | "confirmed" | "rejected" | "undone";
  proposal_reason: string;
  evidence: Record<string, unknown>;
  unit_suffix_warning: boolean;
  review_reason?: string | null;
  actor_user_id?: string | null;
  reviewed_at?: string | null;
  row_version: number;
  created_at?: string | null;
}

export interface DuplicateListResponse {
  items: DuplicateProposal[];
  pending_count: number;
  total_count: number;
}

export const duplicatesApi = {
  list: (state?: string): Promise<DuplicateListResponse> => {
    const qs = state ? `?state=${state}` : "";
    return apiFetch<DuplicateListResponse>(`/workspaces/me/duplicates${qs}`);
  },

  get: (id: string): Promise<DuplicateProposal> =>
    apiFetch<DuplicateProposal>(`/workspaces/me/duplicates/${id}`),

  scan: (): Promise<{ proposals_created: number }> =>
    apiFetch<{ proposals_created: number }>(`/workspaces/me/duplicates/scan`, {
      method: "POST",
    }),

  confirm: (
    id: string,
    rowVersion: number,
    primaryPropertyId?: string,
    reason?: string,
  ): Promise<DuplicateProposal> =>
    apiFetch<DuplicateProposal>(`/workspaces/me/duplicates/${id}/confirm`, {
      method: "POST",
      body: JSON.stringify({
        primary_property_id: primaryPropertyId ?? null,
        reason: reason ?? null,
        row_version: rowVersion,
      }),
    }),

  reject: (id: string, rowVersion: number, reason?: string): Promise<DuplicateProposal> =>
    apiFetch<DuplicateProposal>(`/workspaces/me/duplicates/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason: reason ?? null, row_version: rowVersion }),
    }),

  undo: (id: string, rowVersion: number, reason?: string): Promise<DuplicateProposal> =>
    apiFetch<DuplicateProposal>(`/workspaces/me/duplicates/${id}/undo`, {
      method: "POST",
      body: JSON.stringify({ reason: reason ?? null, row_version: rowVersion }),
    }),

  split: (id: string, rowVersion: number, reason?: string): Promise<DuplicateProposal> =>
    apiFetch<DuplicateProposal>(`/workspaces/me/duplicates/${id}/split`, {
      method: "POST",
      body: JSON.stringify({ reason: reason ?? null, row_version: rowVersion }),
    }),

  swapPrimary: (id: string, rowVersion: number): Promise<DuplicateProposal> =>
    apiFetch<DuplicateProposal>(`/workspaces/me/duplicates/${id}/swap-primary`, {
      method: "POST",
      body: JSON.stringify({ row_version: rowVersion }),
    }),
};
