import { useEffect, useState } from "react";
import { Button } from "../../components/Button";
import { FormNotice } from "../../components/Form";
import { Skeleton } from "../../components/States";
import { reportApi, type ReportPreference, type ReportPreferences as Prefs, type ReportType } from "../../lib/reports";

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function ReportPreferences() {
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<ReportType | null>(null);

  useEffect(() => {
    void reportApi.preferences().then(setPrefs).catch((e) => setError(e instanceof Error ? e.message : "Report preferences could not be loaded."));
  }, []);

  if (!prefs) return error ? <FormNotice tone="error" testId="report-preferences-error">{error}</FormNotice> : <Skeleton className="mt-4 h-24" label="Loading report preferences" />;

  const update = (type: ReportType, patch: Partial<ReportPreference>) => setPrefs({ ...prefs, [type]: { ...prefs[type], ...patch } });

  const save = async (type: ReportType) => {
    setSaving(type);
    setError(null);
    const p = prefs[type];
    try {
      const updated = await reportApi.updatePreference(type, {
        enabled: p.enabled, local_time: p.local_time, weekdays: p.weekdays, day_of_week: p.day_of_week,
        day_of_month: p.day_of_month, timezone: p.timezone, requested_channel: p.requested_channel,
      });
      setPrefs({ ...prefs, [type]: updated });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Report preference could not be saved.");
    } finally {
      setSaving(null);
    }
  };

  const toggleWeekday = (day: number) => {
    const current = prefs.daily.weekdays;
    update("daily", { weekdays: current.includes(day) ? current.filter((d) => d !== day) : [...current, day].sort() });
  };

  return (
    <div className="mt-5 border-t border-border pt-4" data-testid="report-preferences">
      <h3 className="text-sm font-semibold">Report generation preferences</h3>
      <p className="mt-1 text-xs text-muted">Manual and on-demand generation are active now. These schedule preferences are saved for a future automatic scheduler — nothing runs automatically yet.</p>
      {error && <FormNotice tone="error" testId="report-preferences-save-error">{error}</FormNotice>}

      <div className="mt-3 space-y-4">
        <div data-testid="report-preference-daily">
          <label className="flex items-center gap-2 text-sm font-semibold">
            <input type="checkbox" checked={prefs.daily.enabled} onChange={(e) => update("daily", { enabled: e.target.checked })} data-testid="report-daily-enabled" />Daily digest
          </label>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <input type="time" value={prefs.daily.local_time} onChange={(e) => update("daily", { local_time: e.target.value })} className="h-9 rounded-md border border-border bg-surface px-2 text-sm" data-testid="report-daily-time" />
            <div className="flex gap-1">
              {WEEKDAY_LABELS.map((label, day) => (
                <button key={day} type="button" onClick={() => toggleWeekday(day)} className={`h-8 w-10 rounded-md text-xs font-semibold ${prefs.daily.weekdays.includes(day) ? "bg-navy text-white" : "bg-canvas-deep text-muted"}`} data-testid={`report-daily-weekday-${day}`}>
                  {label}
                </button>
              ))}
            </div>
          </div>
          <Button size="sm" variant="secondary" className="mt-2" onClick={() => void save("daily")} disabled={saving === "daily"} data-testid="report-daily-save">{saving === "daily" ? "Saving…" : "Save"}</Button>
        </div>

        <div data-testid="report-preference-weekly">
          <label className="flex items-center gap-2 text-sm font-semibold">
            <input type="checkbox" checked={prefs.weekly.enabled} onChange={(e) => update("weekly", { enabled: e.target.checked })} data-testid="report-weekly-enabled" />Weekly effectiveness report
          </label>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <select value={prefs.weekly.day_of_week ?? 6} onChange={(e) => update("weekly", { day_of_week: Number(e.target.value) })} className="h-9 rounded-md border border-border bg-surface px-2 text-sm" data-testid="report-weekly-day">
              {WEEKDAY_LABELS.map((label, day) => <option key={day} value={day}>{label}</option>)}
            </select>
            <input type="time" value={prefs.weekly.local_time} onChange={(e) => update("weekly", { local_time: e.target.value })} className="h-9 rounded-md border border-border bg-surface px-2 text-sm" data-testid="report-weekly-time" />
          </div>
          <Button size="sm" variant="secondary" className="mt-2" onClick={() => void save("weekly")} disabled={saving === "weekly"} data-testid="report-weekly-save">{saving === "weekly" ? "Saving…" : "Save"}</Button>
        </div>

        <div data-testid="report-preference-monthly">
          <label className="flex items-center gap-2 text-sm font-semibold">
            <input type="checkbox" checked={prefs.monthly.enabled} onChange={(e) => update("monthly", { enabled: e.target.checked })} data-testid="report-monthly-enabled" />Monthly assessment
          </label>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <select value={prefs.monthly.day_of_month ?? 1} onChange={(e) => update("monthly", { day_of_month: Number(e.target.value) })} className="h-9 rounded-md border border-border bg-surface px-2 text-sm" data-testid="report-monthly-day">
              {Array.from({ length: 28 }, (_, i) => i + 1).map((day) => <option key={day} value={day}>Day {day}</option>)}
            </select>
            <input type="time" value={prefs.monthly.local_time} onChange={(e) => update("monthly", { local_time: e.target.value })} className="h-9 rounded-md border border-border bg-surface px-2 text-sm" data-testid="report-monthly-time" />
          </div>
          <Button size="sm" variant="secondary" className="mt-2" onClick={() => void save("monthly")} disabled={saving === "monthly"} data-testid="report-monthly-save">{saving === "monthly" ? "Saving…" : "Save"}</Button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-4 text-xs text-muted">
        <span>Delivery channel: In-app (active).</span>
        <span className="opacity-60" data-testid="report-channel-email-disabled">Email — provider not connected</span>
        <span className="opacity-60" data-testid="report-channel-both-disabled">Both — provider not connected</span>
      </div>
    </div>
  );
}
