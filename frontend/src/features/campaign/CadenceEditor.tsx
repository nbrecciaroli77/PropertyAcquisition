import type { Cadence } from "../../lib/campaigns";
import { WEEKDAYS } from "./settingFormat";

const input = "h-9 rounded-md border border-border bg-surface px-2 text-sm";

/** Daily, weekly and monthly cadence for one layer. Times are local to the campaign timezone. */
export function CadenceEditor({ id, value, onChange }: { id: string; value: Cadence; onChange: (next: Cadence) => void }) {
  const patch = <K extends keyof Cadence>(k: K, part: Partial<Cadence[K]>) => onChange({ ...value, [k]: { ...value[k], ...part } });
  const toggleDay = (d: number) => {
    const days = value.daily.weekdays.includes(d) ? value.daily.weekdays.filter((x) => x !== d) : [...value.daily.weekdays, d];
    if (days.length > 0) patch("daily", { weekdays: days.sort((a, b) => a - b) });
  };
  const head = (k: keyof Cadence, title: string) => (
    <label className="flex items-center gap-2 text-sm font-semibold">
      <input type="checkbox" checked={value[k].enabled} onChange={(e) => patch(k, { enabled: e.target.checked })} data-testid={`${id}-${k}-enabled`} className="h-4 w-4 accent-[var(--color-eucalyptus-deep)]" />
      {title}
    </label>
  );
  const time = (k: keyof Cadence) => (
    <input type="time" aria-label={`${k} local time`} value={value[k].local_time} onChange={(e) => e.target.value && patch(k, { local_time: e.target.value })} className={input} data-testid={`${id}-${k}-time`} />
  );
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <div className="rounded-md border border-border p-3">
        {head("daily", "Daily")}
        <div className="mt-2 flex flex-wrap gap-1" role="group" aria-label="Daily weekdays">
          {WEEKDAYS.map((label, d) => (
            <button key={label} type="button" aria-pressed={value.daily.weekdays.includes(d)} onClick={() => toggleDay(d)} data-testid={`${id}-daily-day-${d}`}
              className={`h-8 w-10 rounded text-xs font-semibold ${value.daily.weekdays.includes(d) ? "bg-navy text-white" : "bg-canvas-deep text-navy"}`}>
              {label}
            </button>
          ))}
        </div>
        <div className="mt-2">{time("daily")}</div>
      </div>
      <div className="rounded-md border border-border p-3">
        {head("weekly", "Weekly")}
        <div className="mt-2 flex flex-wrap gap-2">
          <select aria-label="Weekly day" value={value.weekly.day_of_week} onChange={(e) => patch("weekly", { day_of_week: Number(e.target.value) })} className={input} data-testid={`${id}-weekly-day`}>
            {WEEKDAYS.map((label, d) => <option key={label} value={d}>{label}</option>)}
          </select>
          {time("weekly")}
        </div>
      </div>
      <div className="rounded-md border border-border p-3">
        {head("monthly", "Monthly")}
        <div className="mt-2 flex flex-wrap gap-2">
          <select aria-label="Day of month" value={value.monthly.day_of_month} onChange={(e) => patch("monthly", { day_of_month: Number(e.target.value) })} className={input} data-testid={`${id}-monthly-day`}>
            {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => <option key={d} value={d}>Day {d}</option>)}
          </select>
          {time("monthly")}
        </div>
      </div>
    </div>
  );
}
