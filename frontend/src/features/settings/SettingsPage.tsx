import { useState } from "react";
import { Button } from "../../components/Button";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { MilestoneNote, PageHeader } from "../../components/Page";
import { StatusChip } from "../../components/StatusChip";
import { displayUser, workspace } from "../../lib/synthetic";

export default function SettingsPage() {
  const [notice, setNotice] = useState<string | null>(null);
  return (
    <>
      <PageHeader eyebrow="Settings" title="Settings, privacy and household" description="Profile, timezone, notification cadence, household roles, sessions, export and deletion." testId="settings-header" />

      <div className="grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="profile-heading" className="card min-w-0 p-5">
          <h2 id="profile-heading" className="text-h3 font-semibold">
            Profile
          </h2>
          <form className="mt-4 space-y-4" onSubmit={(e) => e.preventDefault()}>
            <Field id="display-name" label="Display name" defaultValue={displayUser.name} />
            <Field id="email" label="Email" type="email" defaultValue={displayUser.email} readOnly helper="Sign-in and verification arrive in Milestone 2." />
            <Field id="timezone" label="Timezone (IANA)" defaultValue={workspace.timezone} readOnly />
            <Field id="locale" label="Locale" defaultValue="en-AU · AUD · m²" readOnly />
          </form>
        </section>

        <section aria-labelledby="notif-heading" className="card min-w-0 p-5">
          <h2 id="notif-heading" className="text-h3 font-semibold">
            Notifications
          </h2>
          <dl className="mt-4 grid grid-cols-1 gap-x-4 gap-y-2 text-sm sm:grid-cols-[auto_minmax(0,1fr)]">
            <dt className="text-muted">Daily digest</dt>
            <dd className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span>07:00 local</span>
              <StatusChip tone="neutral">Delivery not configured</StatusChip>
            </dd>
            <dt className="text-muted">Quiet hours</dt>
            <dd>21:00–07:00</dd>
            <dt className="text-muted">Promotion</dt>
            <dd>Strong match immediate · Potential match in digest</dd>
          </dl>
        </section>

        <section aria-labelledby="household-heading" className="card min-w-0 p-5">
          <h2 id="household-heading" className="text-h3 font-semibold">
            Household
          </h2>
          <ul className="mt-3 divide-y divide-border text-sm">
            <li className="flex items-center justify-between py-2">
              <span>
                {displayUser.name} <span className="text-muted">· {displayUser.email}</span>
              </span>
              <StatusChip tone="info" hideIcon>
                Owner
              </StatusChip>
            </li>
          </ul>
          <p className="mt-3 text-xs text-muted">Tenant-ready roles arrive in Milestone 2. Privileged access will require a separate role and an audit event.</p>
        </section>

        <section aria-labelledby="privacy-heading" className="card min-w-0 p-5">
          <h2 id="privacy-heading" className="text-h3 font-semibold">
            Privacy and data
          </h2>
          <p className="mt-2 text-sm text-muted">Google sign-in and any Gmail connection are separate decisions — the first never implies the second, and no mailbox is connected.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" disabled title="Arrives in Milestone 6">
              Export my data
            </Button>
            <ConfirmDialog
              title="Request deletion?"
              description="In the finished prototype this revokes sessions, stops jobs and deletes your workspace data without recreating it. In Milestone 1 nothing is stored, so nothing happens."
              confirmLabel="Request deletion"
              destructive
              onConfirm={() => setNotice("Deletion request noted. No data exists in Milestone 1.")}
              trigger={
                <Button variant="destructive" size="sm" data-testid="request-deletion">
                  Request deletion
                </Button>
              }
            />
          </div>
          {notice && (
            <p role="status" className="mt-3 text-sm text-muted" data-testid="settings-notice">
              {notice}
            </p>
          )}
        </section>
      </div>

      <MilestoneNote milestone={6}>Sessions list, export, deletion, audit and retention controls arrive in Milestone 6.</MilestoneNote>
    </>
  );
}

function Field({ id, label, type = "text", defaultValue, readOnly, helper }: { id: string; label: string; type?: string; defaultValue: string; readOnly?: boolean; helper?: string }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-semibold">
        {label}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        defaultValue={defaultValue}
        readOnly={readOnly}
        aria-describedby={helper ? `${id}-help` : undefined}
        className="h-11 w-full rounded-md border border-border bg-surface px-3 text-sm read-only:bg-canvas read-only:text-muted"
        data-testid={`settings-${id}`}
      />
      {helper && (
        <p id={`${id}-help`} className="mt-1 text-xs text-muted">
          {helper}
        </p>
      )}
    </div>
  );
}
