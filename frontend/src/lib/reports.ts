import { apiFetch } from "./api";

export type ReportType = "daily" | "weekly" | "monthly";
export type ReleaseKind = "preview" | "on_demand" | "production";

export interface ReportRun {
  id: string;
  journey_id: string | null;
  report_type: ReportType;
  kind: ReleaseKind;
  release_state: string;
  idempotency_key: string;
  period_start: string | null;
  period_end: string | null;
  cutoff_at: string | null;
  timezone: string;
  generation_version: string;
  is_partial_period: boolean;
  failure_reason: string | null;
  generated_at: string | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  snapshot: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  detail: Record<string, any>;
  created_at: string;
}

export interface ReportPreference {
  report_type: ReportType;
  enabled: boolean;
  local_time: string;
  weekdays: number[];
  day_of_week: number | null;
  day_of_month: number | null;
  timezone: string;
  requested_channel: string;
  effective_channel: string;
}

export interface ReportPreferences {
  daily: ReportPreference;
  weekly: ReportPreference;
  monthly: ReportPreference;
}

export const reportApi = {
  generate: (journeyId: string, reportType: ReportType, releaseKind: ReleaseKind = "preview") =>
    apiFetch<ReportRun>(`/journeys/${journeyId}/reports/${reportType}/generate`, {
      method: "POST",
      body: JSON.stringify({ release_kind: releaseKind }),
    }),
  list: (journeyId: string, reportType?: ReportType) =>
    apiFetch<ReportRun[]>(`/journeys/${journeyId}/reports${reportType ? `?report_type=${reportType}` : ""}`),
  get: (journeyId: string, reportRunId: string) => apiFetch<ReportRun>(`/journeys/${journeyId}/reports/${reportRunId}`),
  preferences: () => apiFetch<ReportPreferences>("/reports/preferences"),
  updatePreference: (
    reportType: ReportType,
    body: { enabled: boolean; local_time: string; weekdays: number[]; day_of_week: number | null; day_of_month: number | null; timezone: string; requested_channel: string },
  ) => apiFetch<ReportPreference>(`/reports/preferences/${reportType}`, { method: "PUT", body: JSON.stringify(body) }),
};
