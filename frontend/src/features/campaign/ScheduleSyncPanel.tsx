import { CalendarClock } from "lucide-react";
import { StatusChip, type ChipTone } from "../../components/StatusChip";
import type { Cadence, CampaignConfig, ScheduleSync } from "../../lib/campaigns";
import { cadenceSummary } from "./settingFormat";

const SYNC: Record<string, { label: string; tone: ChipTone }> = {
  campaign_disabled: { label: "Campaign paused", tone: "warning" },
  cadence_off: { label: "Cadence off", tone: "neutral" },
  awaiting_activation: { label: "Waiting for activation", tone: "unknown" },
  worker_disabled: { label: "Worker disabled", tone: "neutral" },
  in_sync: { label: "In sync", tone: "pass" },
  out_of_sync: { label: "Out of sync", tone: "warning" },
};
const ORDER = { daily: 0, weekly: 1, monthly: 2 } as const;

/** Scheduler synchronisation, kept apart from the settings: saving never starts a worker. */
export function ScheduleSyncPanel({ config }: { config: CampaignConfig }) {
  const requested = cadenceSummary(config.settings.cadence.requested as Cadence);
  return (
    <section aria-labelledby="schedule-heading" className="card min-w-0 p-5" data-testid="campaign-schedule-sync">
      <h2 id="schedule-heading" className="flex items-center gap-2 text-h3 font-semibold">
        <CalendarClock className="h-5 w-5 text-eucalyptus-deep" aria-hidden="true" /> Scheduler synchronisation
      </h2>
      <p className="mt-1 text-sm text-muted" data-testid="schedule-worker-state">
        {config.production_scheduler_enabled
          ? "Production scheduler is enabled."
          : "Production scheduler is off in this build. Changing settings never activates a worker, sends anything or connects an integration."}
      </p>
      <ul className="mt-4 space-y-3">
        {config.schedule.map((row) => (
          <SyncRow key={row.report_type} row={row} requested={requested[ORDER[row.report_type]]} />
        ))}
      </ul>
    </section>
  );
}

function SyncRow({ row, requested }: { row: ScheduleSync; requested: string }) {
  const sync = SYNC[row.sync_state] ?? { label: row.sync_state, tone: "unknown" as ChipTone };
  return (
    <li className="rounded-md border border-border bg-canvas p-3" data-testid={`schedule-${row.report_type}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold capitalize text-navy">{row.report_type}</span>
        <StatusChip tone={sync.tone} hideIcon data-testid={`schedule-${row.report_type}-state`}>
          {sync.label}
        </StatusChip>
      </div>
      <p className="mt-1 text-xs text-charcoal">Requested: {requested}</p>
      <p className="mt-0.5 text-xs text-muted">
        Workspace job: {row.configured_cron ? <code className="font-mono">{row.configured_cron}</code> : "none"} ·{" "}
        {row.configured_enabled ? "enabled" : "disabled"} · next run: {row.next_due_at ?? "not scheduled"}
      </p>
      {row.config_drift && (
        <p className="mt-1 text-xs text-ochre-deep" data-testid={`schedule-${row.report_type}-drift`}>
          The workspace job does not match this cadence yet; it is reconciled only when production scheduling is activated.
        </p>
      )}
    </li>
  );
}
