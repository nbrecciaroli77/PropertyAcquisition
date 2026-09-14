import { apiFetch } from "./api";

export interface DataExport {
  id: string;
  export_type: "personal" | "workspace";
  state: string;
  file_size_bytes: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  manifest: Record<string, any>;
  failure_reason: string | null;
  expires_at: string;
  downloaded_at: string | null;
  download_count: number;
  created_at: string;
}

export type DeletionRequestType = "leave_workspace" | "delete_account" | "delete_workspace";

export interface DeletionRequest {
  id: string;
  request_type: DeletionRequestType;
  target_workspace_id: string | null;
  state: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  detail: Record<string, any>;
  scheduled_execute_at: string;
  executed_at: string | null;
  cancelled_at: string | null;
  failure_reason: string | null;
  created_at: string;
}

const base = process.env.REACT_APP_BACKEND_URL;

export const exportApi = {
  list: () => apiFetch<DataExport[]>("/exports"),
  requestPersonal: () => apiFetch<DataExport>("/exports/personal", { method: "POST" }),
  requestWorkspace: () => apiFetch<DataExport>("/exports/workspace", { method: "POST" }),
  downloadUrl: (id: string) => `${base}/api/exports/${id}/download`,
};

export const accountApi = {
  listDeletionRequests: () => apiFetch<DeletionRequest[]>("/account/deletion-requests"),
  requestDeletion: (body: { request_type: DeletionRequestType; password: string; typed_confirmation: string; target_workspace_id?: string | null }) =>
    apiFetch<DeletionRequest>("/account/deletion-requests", { method: "POST", body: JSON.stringify(body) }),
  cancelDeletion: (id: string) => apiFetch<DeletionRequest>(`/account/deletion-requests/${id}/cancel`, { method: "POST" }),
};
