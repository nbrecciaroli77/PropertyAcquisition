import type { ChipTone } from "../../components/StatusChip";
import { formatDate } from "../../lib/format";
import type { AssessmentProfile, Cadence, EffectiveSetting, SettingKey, SettingSource } from "../../lib/campaigns";

export const SETTING_LABELS: Record<SettingKey, string> = {
  assessment_profile: "Assessment profile",
  activation_at: "Activation time",
  timezone: "Timezone",
  intake_connection_ref: "Intake connection",
  recipient_user_id: "Report recipient",
  delivery_mode: "Delivery mode",
  cadence: "Report cadence",
};

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export const sourceChip = (source: SettingSource, ownDefaults: boolean): { label: string; detail: string; tone: ChipTone } => {
  if (source === "campaign_override") return { label: "Overridden", detail: "Set for this campaign", tone: "shortlisted" };
  if (source === "user_default")
    return { label: "Inherited", detail: ownDefaults ? "From your defaults" : "From the campaign creator's defaults", tone: "info" };
  return { label: "Inherited", detail: "System default", tone: "neutral" };
};

export const cadenceSummary = (cadence: Cadence): string[] => [
  cadence.daily.enabled ? `Daily ${cadence.daily.weekdays.map((d) => WEEKDAYS[d]).join(", ")} at ${cadence.daily.local_time}` : "Daily off",
  cadence.weekly.enabled ? `Weekly ${WEEKDAYS[cadence.weekly.day_of_week]} at ${cadence.weekly.local_time}` : "Weekly off",
  cadence.monthly.enabled ? `Monthly day ${cadence.monthly.day_of_month} at ${cadence.monthly.local_time}` : "Monthly off",
];

export const formatDateTime = (iso: string, timeZone: string): string => {
  const time = new Intl.DateTimeFormat("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone }).format(new Date(iso));
  return `${formatDate(iso, timeZone)}, ${time} (${timeZone})`;
};

const profileLabel = (id: unknown, profiles: AssessmentProfile[]): string => {
  const p = profiles.find((x) => x.id === id);
  return p ? p.label : String(id);
};

/** The value the campaign actually runs with, in words. Disabled capabilities are never shown as active. */
export function effectiveText(key: SettingKey, s: EffectiveSetting, profiles: AssessmentProfile[], timeZone: string): string {
  switch (key) {
    case "assessment_profile":
      return s.state === "available" ? profileLabel(s.effective, profiles) : `${profileLabel(s.requested, profiles)} — Unavailable: required configuration missing or invalid`;
    case "activation_at":
      return s.effective ? `${formatDateTime(String(s.effective), timeZone)} · ${s.state === "active" ? "active" : "pending"}` : "Not activated";
    case "timezone":
      return String(s.effective);
    case "intake_connection_ref":
      return s.state === "none" ? "None" : s.state === "missing" ? "Missing reference" : "Reference only — connectors disabled";
    case "recipient_user_id":
      return s.effective_label ?? "Campaign creator";
    case "delivery_mode":
      return s.requested === "combined" ? "Separate (combined requested — arrives in U6)" : "Separate";
    case "cadence":
      return cadenceSummary(s.requested as Cadence).join(" · ");
  }
}
