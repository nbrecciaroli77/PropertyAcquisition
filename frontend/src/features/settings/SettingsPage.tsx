import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/Button";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { FormNotice, SelectField, TextField } from "../../components/Form";
import { MilestoneNote, PageHeader } from "../../components/Page";
import { Skeleton } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";
import { authApi, type SessionOut } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { TIMEZONE_OPTIONS } from "../../lib/briefOptions";
import { formatDate } from "../../lib/format";
import { NotificationSettings } from "./NotificationSettings";

export default function SettingsPage() {
  const { me, reload, signOutEverywhere } = useAuth();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState(me?.user.display_name ?? "");
  const [timezone, setTimezone] = useState(me?.user.timezone ?? "Australia/Perth");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sessions, setSessions] = useState<SessionOut[] | null>(null);

  const loadSessions = useCallback(async () => {
    try {
      setSessions(await authApi.sessions());
    } catch {
      setSessions([]);
    }
  }, []);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    if (!me) return;
    setDisplayName(me.user.display_name);
    setTimezone(me.user.timezone);
  }, [me]);

  const saveProfile = async () => {
    setBusy(true);
    setError(null);
    try {
      await authApi.updateProfile({ display_name: displayName.trim(), timezone });
      await reload();
      setNotice("Profile saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Your profile could not be saved.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Settings"
        title="Settings, privacy and household"
        description="Profile, timezone, notification cadence, household roles, sessions, export and deletion."
        testId="settings-header"
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="profile-heading" className="card min-w-0 p-5">
          <h2 id="profile-heading" className="text-h3 font-semibold">
            Profile
          </h2>
          <form
            className="mt-4 space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              void saveProfile();
            }}
          >
            <TextField id="settings-display-name" label="Display name" value={displayName} onChange={setDisplayName} />
            <TextField
              id="settings-email"
              label="Email"
              type="email"
              value={me?.user.email ?? ""}
              onChange={() => undefined}
              disabled
              helper={me?.user.email_verified ? "Verified." : "Not verified yet."}
            />
            <SelectField
              id="settings-timezone"
              label="Timezone (IANA)"
              value={timezone}
              onChange={setTimezone}
              options={TIMEZONE_OPTIONS}
            />
            <TextField id="settings-locale" label="Locale" value="en-AU · AUD · m²" onChange={() => undefined} disabled />
            {notice && (
              <FormNotice tone="success" testId="settings-notice">
                {notice}
              </FormNotice>
            )}
            {error && (
              <FormNotice tone="error" testId="settings-error">
                {error}
              </FormNotice>
            )}
            <Button type="submit" disabled={busy} data-testid="settings-save-profile">
              {busy ? "Saving…" : "Save profile"}
            </Button>
          </form>
        </section>

        <section aria-labelledby="sessions-heading" className="card min-w-0 p-5">
          <h2 id="sessions-heading" className="text-h3 font-semibold">
            Sessions
          </h2>
          <p className="mt-1 text-sm text-muted">
            Sessions are revocable on the server. Signing out everywhere ends this device too.
          </p>
          {sessions === null && <Skeleton className="mt-4 h-20" label="Loading sessions" />}
          {sessions !== null && (
            <ul className="mt-4 divide-y divide-border text-sm" data-testid="sessions-list">
              {sessions.map((s) => (
                <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-3" data-testid={`session-${s.id}`}>
                  <div className="min-w-0">
                    <div className="truncate font-semibold">{s.user_agent}</div>
                    <div className="text-xs text-muted">
                      Started {formatDate(s.created_at)} · last seen {formatDate(s.last_seen_at)}
                    </div>
                  </div>
                  {s.current ? (
                    <StatusChip tone="pass" hideIcon>
                      This device
                    </StatusChip>
                  ) : (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={async () => {
                        await authApi.revokeSession(s.id);
                        await loadSessions();
                      }}
                      data-testid={`revoke-session-${s.id}`}
                    >
                      Revoke
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
          <ConfirmDialog
            title="Sign out of every device?"
            description="Every session is revoked immediately, including this one. You will need to sign in again."
            confirmLabel="Sign out everywhere"
            destructive
            onConfirm={async () => {
              await signOutEverywhere();
              navigate("/", { replace: true });
            }}
            trigger={
              <Button variant="destructive" size="sm" className="mt-4" data-testid="logout-all-devices">
                Sign out of all devices
              </Button>
            }
          />
        </section>

        <section aria-labelledby="household-heading" className="card min-w-0 p-5">
          <h2 id="household-heading" className="text-h3 font-semibold">
            Household
          </h2>
          <ul className="mt-3 divide-y divide-border text-sm">
            <li className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span className="min-w-0 break-words">
                {me?.user.display_name} <span className="break-all text-muted">· {me?.user.email}</span>
              </span>
              <StatusChip tone="info" hideIcon>
                {me?.workspace.role ?? "member"}
              </StatusChip>
            </li>
          </ul>
          <p className="mt-3 text-xs text-muted">
            Workspace <strong className="font-semibold">{me?.workspace.name}</strong>. Invitations and additional
            household roles arrive in Milestone 6; privileged access will require a separate role and an audit event.
          </p>
        </section>

        <NotificationSettings />

        <section aria-labelledby="privacy-heading" className="card min-w-0 p-5">
          <h2 id="privacy-heading" className="text-h3 font-semibold">
            Privacy and data
          </h2>
          <p className="mt-2 text-sm text-muted">
            Google sign-in and any Gmail connection are separate decisions — the first never implies the second, and no
            mailbox is connected.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" disabled title="Arrives in Milestone 6">
              Export my data
            </Button>
            <ConfirmDialog
              title="Request deletion?"
              description="In the finished prototype this revokes sessions, stops jobs and deletes your workspace data without recreating it. The deletion job itself arrives in Milestone 6."
              confirmLabel="Request deletion"
              destructive
              onConfirm={() => setNotice("Deletion request noted. The deletion job arrives in Milestone 6.")}
              trigger={
                <Button variant="destructive" size="sm" data-testid="request-deletion">
                  Request deletion
                </Button>
              }
            />
          </div>
        </section>
      </div>

      <MilestoneNote milestone={6}>
        Export, deletion jobs, audit browsing, retention controls and household invitations arrive in Milestone 6.
      </MilestoneNote>
    </>
  );
}
