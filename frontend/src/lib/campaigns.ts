import { apiFetch } from "./api";

export const INHERIT = "INHERIT" as const;
export type Inherit = typeof INHERIT;

export interface DailyCadence { enabled: boolean; local_time: string; weekdays: number[] }
export interface WeeklyCadence { enabled: boolean; local_time: string; day_of_week: number }
export interface MonthlyCadence { enabled: boolean; local_time: string; day_of_month: number }
export interface Cadence { daily: DailyCadence; weekly: WeeklyCadence; monthly: MonthlyCadence }

/** One configuration layer. Every key may defer to the next layer with INHERIT. */
export interface CampaignLayer {
  assessment_profile: Inherit | string;
  activation_at: Inherit | string | null;
  timezone: Inherit | string;
  intake_connection_ref: Inherit | string | null;
  recipient_user_id: Inherit | string;
  delivery_mode: Inherit | "separate" | "combined";
  cadence: Inherit | Cadence;
}
export type SettingKey = keyof CampaignLayer;
export const SETTING_KEYS: SettingKey[] = [
  "assessment_profile", "activation_at", "timezone", "intake_connection_ref", "recipient_user_id", "delivery_mode", "cadence",
];

export type SettingSource = "campaign_override" | "user_default" | "system_default";

export interface EffectiveSetting {
  override: unknown;
  user_default: unknown;
  requested: unknown;
  source: SettingSource;
  effective: unknown;
  state: string;
  note: string | null;
  effective_label: string | null;
}

export interface ScheduleSync {
  report_type: "daily" | "weekly" | "monthly";
  requested_cron: string | null;
  configured_cron: string | null;
  configured_enabled: boolean;
  config_drift: boolean;
  effective_cron: string | null;
  next_due_at: string | null;
  sync_state: string;
}

export interface CampaignConfig {
  journey_id: string;
  campaign_kind: "house" | "land";
  campaign_enabled: boolean;
  settings_owner_user_id: string;
  campaign_version: number;
  user_default_version: number;
  settings: Record<SettingKey, EffectiveSetting>;
  schedule: ScheduleSync[];
  production_scheduler_enabled: boolean;
  resolved_at: string;
}

export interface ConfigVersion {
  id: string;
  scope: "user_default" | "campaign";
  version_no: number;
  settings: Partial<CampaignLayer>;
  reason: string;
  actor_user_id: string | null;
  created_at: string;
}

export interface UserDefaults { version: number; settings: Partial<CampaignLayer> }

export interface AssessmentProfile {
  id: string;
  label: string;
  campaign_kinds: string[];
  available: boolean;
  engine_version: string | null;
  note: string;
}

export interface ReportLocation { report_run_id: string; journey_id: string; report_type: string }

const put = (body: { settings: Partial<CampaignLayer>; expected_version: number; reason: string }) => ({
  method: "PUT",
  body: JSON.stringify(body),
});

export const campaignApi = {
  config: (journeyId: string) => apiFetch<CampaignConfig>(`/journeys/${journeyId}/campaign`),
  versions: (journeyId: string) => apiFetch<ConfigVersion[]>(`/journeys/${journeyId}/campaign/versions`),
  saveOverrides: (journeyId: string, body: { settings: Partial<CampaignLayer>; expected_version: number; reason: string }) =>
    apiFetch<CampaignConfig>(`/journeys/${journeyId}/campaign/overrides`, put(body)),
  defaults: () => apiFetch<UserDefaults>("/campaign-defaults"),
  defaultVersions: () => apiFetch<ConfigVersion[]>("/campaign-defaults/versions"),
  saveDefaults: (body: { settings: Partial<CampaignLayer>; expected_version: number; reason: string }) =>
    apiFetch<UserDefaults>("/campaign-defaults", put(body)),
  profiles: () => apiFetch<AssessmentProfile[]>("/assessment-profiles"),
  locateRun: (reportRunId: string) => apiFetch<ReportLocation>(`/reports/runs/${reportRunId}/location`),
};

export const layerFrom = (settings: Partial<CampaignLayer> | undefined): CampaignLayer => {
  const layer = {} as Record<SettingKey, unknown>;
  for (const key of SETTING_KEYS) layer[key] = settings && key in settings ? settings[key] : INHERIT;
  return layer as unknown as CampaignLayer;
};
