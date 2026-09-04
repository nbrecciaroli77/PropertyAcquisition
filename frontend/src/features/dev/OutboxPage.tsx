import { Inbox, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "../../components/Button";
import { FormNotice } from "../../components/Form";
import { EmptyState, ErrorState, Skeleton } from "../../components/States";
import { devApi, type OutboxMessage } from "../../lib/api";
import { formatDate } from "../../lib/format";

/** Development-only view of the durable outbox. No provider is configured, so nothing is delivered. */
export default function OutboxPage() {
  const [params] = useSearchParams();
  const email = params.get("email") ?? "";
  const [messages, setMessages] = useState<OutboxMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setMessages(await devApi.outbox(email || undefined));
    } catch (e) {
      setError(e instanceof Error ? e.message : "The outbox could not be read.");
    }
  }, [email]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto w-full max-w-[900px] px-4 py-10" data-testid="dev-outbox-page">
      <p className="label text-ochre-deep">Development only</p>
      <h1 className="mt-1 text-display">Email outbox</h1>
      <p className="mt-3 max-w-prose text-muted">
        Every message the prototype would send is stored here instead. Delivery is suppressed because no transactional
        provider is configured, so verification and reset links are opened from this page.
      </p>

      <FormNotice tone="info" testId="outbox-scope-notice">
        This page exists so the owner can complete account flows without a mailbox. It is disabled outside the
        development environment and will be removed before any private preview.
      </FormNotice>

      <div className="mt-6 flex items-center justify-between gap-3">
        <p className="text-sm text-muted" data-testid="outbox-filter">
          {email ? `Filtered to ${email}` : "Showing the 50 most recent messages"}
        </p>
        <Button
          variant="secondary"
          size="sm"
          onClick={load}
          icon={<RefreshCw className="h-4 w-4" aria-hidden="true" />}
          data-testid="outbox-refresh"
        >
          Refresh
        </Button>
      </div>

      {error && <ErrorState className="mt-4" description={error} onRetry={load} />}

      {!error && messages === null && (
        <div className="mt-4 space-y-3">
          <Skeleton className="h-24" label="Loading the outbox" />
          <Skeleton className="h-24" />
        </div>
      )}

      {!error && messages !== null && messages.length === 0 && (
        <EmptyState
          className="mt-4"
          title="No messages yet"
          description="Create an account or request a password reset and the message will appear here."
          icon={<Inbox className="h-5 w-5" aria-hidden="true" />}
          data-testid="outbox-empty"
        />
      )}

      {!error && messages !== null && messages.length > 0 && (
        <ul className="mt-4 space-y-3" data-testid="outbox-list">
          {messages.map((m) => (
            <li key={m.id} className="card p-4" data-testid={`outbox-message-${m.kind}`}>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-base font-semibold md:text-lg">{m.subject}</h2>
                <span className="text-xs text-muted">{formatDate(m.created_at)}</span>
              </div>
              <p className="mt-1 text-sm text-muted">
                To {m.to_email} · {m.kind.replace(/_/g, " ")} · delivery {m.delivery_state.replace(/_/g, " ")}
              </p>
              <p className="mt-2 whitespace-pre-line text-sm text-charcoal">{m.body_text}</p>
              {m.action_url && (
                <Link
                  to={new URL(m.action_url).pathname + new URL(m.action_url).search}
                  className="mt-3 inline-block break-all text-sm font-semibold text-eucalyptus-deep hover:underline underline-offset-4"
                  data-testid={`outbox-action-${m.kind}`}
                >
                  Open this link
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
