import { apiFetch } from "./api";

export type NotificationChannel = "off" | "in_app" | "email" | "both";
export interface NotificationItem {
  id: string; event_id: string; category: string; title: string; message: string; priority: string;
  safe_deep_link: string; property_id: string | null; property_address: string | null; property_image_url: string | null;
  task_id: string | null; source_event_id: string | null; report_run_id: string | null; evidence_ref: Record<string, unknown>;
  created_at: string; read_at: string | null; dismissed_at: string | null; expires_at: string | null; is_expired: boolean;
}
export interface NotificationPreference {
  category: string | null; requested_channel: NotificationChannel; effective_channel: NotificationChannel;
  global_in_app_enabled: boolean; quiet_hours_start: string | null; quiet_hours_end: string | null; timezone: string;
  due_soon_minutes: number; report_daily_enabled: boolean; report_weekly_enabled: boolean; report_monthly_enabled: boolean;
  report_preferences_active: boolean; email_provider_connected: boolean;
}
export interface Preferences { global_settings: NotificationPreference; categories: NotificationPreference[]; }

export const notificationApi = {
  list: (params: { unread_only?: boolean; category?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.unread_only) query.set("unread_only", "true");
    if (params.category) query.set("category", params.category);
    return apiFetch<{ items: NotificationItem[]; unread_count: number }>(`/notifications${query.size ? `?${query}` : ""}`);
  },
  update: (id: string, body: { read?: boolean; dismissed?: boolean }) =>
    apiFetch<{ items: NotificationItem[]; unread_count: number }>(`/notifications/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  markAllRead: () => apiFetch<{ items: NotificationItem[]; unread_count: number }>("/notifications/mark-all-read", { method: "POST" }),
  preferences: () => apiFetch<Preferences>("/notifications/preferences"),
  updateGlobal: (body: { in_app_enabled: boolean; quiet_hours_start: string | null; quiet_hours_end: string | null; timezone: string; due_soon_minutes: number; report_daily_enabled: boolean; report_weekly_enabled: boolean; report_monthly_enabled: boolean }) =>
    apiFetch<NotificationPreference>("/notifications/preferences/global", { method: "PUT", body: JSON.stringify(body) }),
  updateCategory: (category: string, requested_channel: NotificationChannel) =>
    apiFetch<NotificationPreference>(`/notifications/preferences/${category}`, { method: "PUT", body: JSON.stringify({ requested_channel }) }),
};