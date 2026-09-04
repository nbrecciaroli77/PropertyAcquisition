import { CalendarPlus, CheckSquare, Square } from "lucide-react";
import { useState } from "react";
import { Button } from "../../components/Button";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { MilestoneNote, PageHeader } from "../../components/Page";
import { SourceFreshness } from "../../components/SourceFreshness";
import { StatusChip } from "../../components/StatusChip";
import { properties } from "../../lib/synthetic";

const tasks = [
  { id: "t1", title: "Verify land size for 81C Sample Street", due: "Due Fri 21 Jun", propertyId: "demo-006", done: false, tone: "unknown" as const },
  { id: "t2", title: "Confirm price guide for 22 Jarrah Road", due: "Due Sat 22 Jun", propertyId: "demo-004", done: false, tone: "warning" as const },
  { id: "t3", title: "Read strata / title notes for 12 Banksia Crescent", due: "Done 18 Jun", propertyId: "demo-001", done: true, tone: "pass" as const },
];

const inspections = [
  { id: "i1", propertyId: "demo-001", when: "Sat 22 Jun · 10:00–10:30 AWST", advertisedAt: "2026-06-18T07:42:00+08:00" },
  { id: "i2", propertyId: "demo-005", when: "Sat 22 Jun · 11:15–11:45 AWST", advertisedAt: "2026-06-15T12:30:00+08:00" },
];

export default function TasksPage() {
  const [reminderNotice, setReminderNotice] = useState<string | null>(null);
  return (
    <>
      <PageHeader eyebrow="Tasks" title="Inspections and tasks" description="Advertised open times are not confirmed attendance. Reminders never book anything." testId="tasks-header" />

      <div className="grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="inspections-heading" className="card p-5">
          <h2 id="inspections-heading" className="text-h3 font-semibold">
            Advertised open homes
          </h2>
          <ul className="mt-3 divide-y divide-border">
            {inspections.map((i) => {
              const p = properties.find((x) => x.id === i.propertyId)!;
              return (
                <li key={i.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between" data-testid={`inspection-${i.id}`}>
                  <div>
                    <div className="font-semibold">{p.address}</div>
                    <div className="text-sm text-charcoal">{i.when}</div>
                    <SourceFreshness className="mt-1" source={p.sourceLabel} checkedAt={i.advertisedAt} />
                  </div>
                  <ConfirmDialog
                    title="Add a reminder?"
                    description="This creates a calendar reminder for you only. It does not book, register or notify anyone — advertised times can change, so check the listing before you go."
                    confirmLabel="Add reminder"
                    onConfirm={() => setReminderNotice(`Reminder noted for ${p.address}. ICS download arrives in Milestone 5 — nothing was booked.`)}
                    trigger={
                      <Button variant="secondary" size="sm" icon={<CalendarPlus className="h-4 w-4" aria-hidden="true" />} data-testid={`add-reminder-${i.id}`}>
                        Add reminder
                      </Button>
                    }
                  />
                </li>
              );
            })}
          </ul>
          {reminderNotice && (
            <p role="status" className="mt-3 rounded-md bg-eucalyptus-soft px-3 py-2 text-sm text-eucalyptus-deep" data-testid="reminder-notice">
              {reminderNotice}
            </p>
          )}
        </section>

        <section aria-labelledby="tasks-heading" className="card p-5">
          <h2 id="tasks-heading" className="text-h3 font-semibold">
            Tasks
          </h2>
          <ul className="mt-3 divide-y divide-border">
            {tasks.map((t) => (
              <li key={t.id} className="flex items-start gap-3 py-3" data-testid={`task-${t.id}`}>
                {t.done ? <CheckSquare className="mt-0.5 h-5 w-5 text-eucalyptus-deep" aria-label="Done" /> : <Square className="mt-0.5 h-5 w-5 text-muted" aria-label="Not done" />}
                <div className="min-w-0 flex-1">
                  <div className={t.done ? "text-sm text-muted line-through" : "text-sm font-semibold"}>{t.title}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
                    <StatusChip tone={t.tone}>{t.tone === "pass" ? "Done" : t.tone === "warning" ? "Verify" : "Unknown fact"}</StatusChip>
                    {t.due}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <MilestoneNote milestone={5}>Task ownership, ICS download after explicit action, and the notification centre with quiet hours arrive in Milestone 5.</MilestoneNote>
    </>
  );
}
