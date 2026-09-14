/**
 * M4.2 Sources & Coverage API client.
 */
import { apiFetch } from "./api";

export interface ConnectorItem {
  id: string;
  slug: string;
  display_name: string;
  description?: string | null;
  acquisition_mechanism: string;
  capabilities: string[];
  jurisdiction_codes: string[];
  licence_kind: string;
  licence_state: string;
  kill_switch: boolean;
  version: string;
  // Workspace-specific instance state
  instance_id?: string | null;
  enabled: boolean;
  connector_readiness: string;
  health_checked_at?: string | null;
  health_detail?: string | null;
  // Source readiness
  source_readiness?: string | null;
  requested_filters: Record<string, unknown>;
  effective_filters: Record<string, unknown>;
  deviation_reason?: string | null;
  last_activity_at?: string | null;
  status_label: string;
}

export interface ConnectorListResponse {
  items: ConnectorItem[];
  total: number;
}

export interface AliasItem {
  id: string;
  canonical_email: string;
  alias_email: string;
  display_names_seen: string[];
  confidence: string;
  review_state: string;
  first_seen_at?: string | null;
  evidence_label: string;
  evidence_url?: string | null;
  reviewed_at?: string | null;
}

export interface AliasListResponse {
  items: AliasItem[];
  total: number;
}

export const sourcesApi = {
  listConnectors: (jurisdiction?: string): Promise<ConnectorListResponse> => {
    const qs = jurisdiction ? `?jurisdiction=${jurisdiction}` : "";
    return apiFetch<ConnectorListResponse>(`/sources/connectors${qs}`);
  },

  getConnector: (slug: string): Promise<ConnectorItem> =>
    apiFetch<ConnectorItem>(`/sources/connectors/${slug}`),
};

export const aliasesApi = {
  list: (): Promise<AliasListResponse> =>
    apiFetch<AliasListResponse>(`/workspaces/me/aliases`),

  update: (
    id: string,
    action: "confirm" | "reject",
  ): Promise<{ id: string; alias_email: string; review_state: string; reviewed_at?: string }> =>
    apiFetch(`/workspaces/me/aliases/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ action }),
    }),
};
