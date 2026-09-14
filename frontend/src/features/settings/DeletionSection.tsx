import { useEffect, useState } from "react";
import { Button } from "../../components/Button";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { FormNotice, SelectField, TextField } from "../../components/Form";
import { Skeleton } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { formatDate } from "../../lib/format";
import { accountApi, type DeletionRequest, type DeletionRequestType } from "../../lib/privacy";

const TYPE_LABEL: Record<DeletionRequestType, string> = {
  leave_workspace: "Leave this workspace",
  delete_account: "Delete my account",
  delete_workspace: "Delete this workspace",
};

export function DeletionSection() {
  const { me } = useAuth();
  const [requests, setRequests] = useState<DeletionRequest[] | null>(null);
  const [requestType, setRequestType] = useState<DeletionRequestType>("delete_account");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      setRequests(await accountApi.listDeletionRequests());
    } catch {
      setRequests([]);
    }
  };
  useEffect(() => { void load(); }, []);

  const consequence: Record<DeletionRequestType, string> = {
    leave_workspace: "You lose access to this workspace. Its data is not deleted for other members.",
    delete_account: "Your account is permanently deleted, every session is revoked, and any workspace you solely own is deleted with its data.",
    delete_workspace: "This workspace and all of its data — properties, brief, tasks, notifications and reports — is permanently deleted.",
  };

  const submit = async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const targetWorkspaceId = requestType === "delete_account" ? null : me?.workspace.id ?? null;
      await accountApi.requestDeletion({ request_type: requestType, password, typed_confirmation: confirmation, target_workspace_id: targetWorkspaceId });
      setPassword("");
      setConfirmation("");
      setNotice("Deletion request submitted. It enters a 72-hour cooling-off period and can be cancelled at any time before then.");
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Deletion request could not be submitted.");
    } finally {
      setBusy(false);
    }
  };

  const cancel = async (id: string) => {
    try {
      await accountApi.cancelDeletion(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request could not be cancelled.");
    }
  };

  const pending = (requests ?? []).filter((r) => r.state === "pending_cooloff");

  return (
    <section aria-labelledby="deletion-heading" className="card min-w-0 p-5" data-testid="deletion-section">
      <h2 id="deletion-heading" className="text-h3 font-semibold">Account and workspace deletion</h2>
      <p className="mt-2 text-sm text-muted">
        Deletion requests need your password, a typed confirmation, and go through a 72-hour cooling-off period during which
        you can cancel. Execution is manual/test-only in this prototype — no production deletion schedule runs automatically.
      </p>

      {requests === null && <Skeleton className="mt-4 h-16" label="Loading deletion requests" />}
      {pending.length > 0 && (
        <ul className="mt-4 space-y-2" data-testid="pending-deletion-requests">
          {pending.map((r) => (
            <li key={r.id} className="rounded-md border border-risk/40 bg-risk-soft p-3 text-sm" data-testid={`pending-deletion-${r.id}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold">{TYPE_LABEL[r.request_type]}</span>
                <StatusChip tone="warning" hideIcon>Pending — executes {formatDate(r.scheduled_execute_at)}</StatusChip>
              </div>
              <p className="mt-1 text-charcoal">{String(r.detail?.consequence ?? "")}</p>
              <Button size="sm" variant="secondary" className="mt-2" onClick={() => void cancel(r.id)} data-testid={`cancel-deletion-${r.id}`}>Cancel request</Button>
            </li>
          ))}
        </ul>
      )}

      {notice && <FormNotice tone="success" testId="deletion-notice">{notice}</FormNotice>}
      {error && <FormNotice tone="error" testId="deletion-error">{error}</FormNotice>}

      <div className="mt-4 space-y-3">
        <SelectField
          id="deletion-request-type"
          label="What do you want to do?"
          value={requestType}
          onChange={(v) => setRequestType(v as DeletionRequestType)}
          options={Object.entries(TYPE_LABEL).map(([value, label]) => ({ value: value as DeletionRequestType, label }))}
        />
        <p className="rounded-md bg-canvas px-3 py-2 text-xs text-muted" data-testid="deletion-consequence">{consequence[requestType]}</p>
        <TextField id="deletion-password" label="Confirm your password" type="password" value={password} onChange={setPassword} autoComplete="current-password" />
        <TextField id="deletion-confirmation" label='Type "DELETE" to confirm' value={confirmation} onChange={setConfirmation} placeholder="DELETE" />
        <ConfirmDialog
          title="Submit this deletion request?"
          description="This starts a 72-hour cooling-off period. You can cancel any time before it executes."
          confirmLabel="Submit request"
          destructive
          onConfirm={() => void submit()}
          trigger={
            <Button variant="destructive" disabled={busy || !password || confirmation !== "DELETE"} data-testid="deletion-submit">
              {busy ? "Submitting…" : "Request deletion"}
            </Button>
          }
        />
      </div>
    </section>
  );
}
