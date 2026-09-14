/**
 * M4.2 Sources & Coverage screen.
 *
 * Shows the synthetic provider catalogue with:
 * - Enabled / kill-switch state
 * - Connector readiness (unconfigured, ready, degraded, error, kill_switch)
 * - Source readiness (initialising, ready, degraded, offline, kill_switch)
 * - Requested vs effective filters (with deviation reason)
 * - Last successful activity or "Never"
 *
 * All entries are read-only in this milestone and labelled as synthetic / not connected.
 */
import {
  FileSpreadsheet,
  Globe,
  Inbox,
  Mail,
  PencilLine,
  RefreshCw,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { MilestoneNote, PageHeader } from "../../components/Page";
import { StatusChip, type ChipTone } from "../../components/StatusChip";
import { ErrorState, Skeleton } from "../../components/States";
import { sourcesApi, aliasesApi, type ConnectorItem, type AliasItem } from "../../lib/sources";
import { ApiError } from "../../lib/api";

// ── Chips ─────────────────────────────────────────────────────────────────────

const READINESS_TONE: Record<string, ChipTone> = {
  unconfigured: "neutral",
  ready: "pass",
  degraded: "warning",
  error: "fail",
  kill_switch: "fail",
  initialising: "info",
  offline: "fail",
};

const LICENCE_KIND_LABEL: Record<string, string> = {
  none_required: "No licence",
  commercial: "Commercial",
  licensed: "Licensed",
};

const MECHANISM_LABEL: Record<string, string> = {
  portal_api: "Portal API",
  portal_scrape: "Portal scrape",
  direct_api: "Direct API",
  manual: "Manual",
  inbound_email: "Inbound email",
};

const SLUG_ICON: Record<string, React.ReactNode> = {
  "email-inbound": <Mail className="h-5 w-5" aria-hidden />,
};

function connectorIcon(slug: string): React.ReactNode {
  if (SLUG_ICON[slug]) return SLUG_ICON[slug];
  if (slug.includes("manual") || slug.includes("csv")) return <PencilLine className="h-5 w-5" aria-hidden />;
  if (slug.includes("email")) return <Inbox className="h-5 w-5" aria-hidden />;
  if (slug.includes("spreadsheet") || slug.includes("csv")) return <FileSpreadsheet className="h-5 w-5" aria-hidden />;
  return <Globe className="h-5 w-5" aria-hidden />;
}

function FilterBlock({
  label,
  filters,
  empty = "—",
}: {
  label: string;
  filters: Record<string, unknown>;
  empty?: string;
}) {
  const entries = Object.entries(filters);
  if (entries.length === 0) return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className="text-charcoal">{empty}</dd>
    </div>
  );
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className="text-charcoal">
        {entries.map(([k, v]) => (
          <span key={k} className="mr-1.5 inline-block">
            <span className="text-muted">{k}:</span>{" "}
            {Array.isArray(v) ? (v as string[]).join(", ") : String(v)}
          </span>
        ))}
      </dd>
    </div>
  );
}

function ConnectorCard({ item }: { item: ConnectorItem }) {
  const readiness = item.source_readiness ?? item.connector_readiness;
  const lastActivity = item.last_activity_at
    ? new Date(item.last_activity_at).toLocaleString("en-AU")
    : "Never";

  return (
    <li
      className="card flex min-w-0 flex-col gap-4 p-5"
      data-testid={`source-card-${item.slug}`}
    >
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-canvas-deep text-navy">
            {connectorIcon(item.slug)}
          </span>
          <div className="min-w-0">
            <h2 className="font-semibold">{item.display_name}</h2>
            <p className="text-xs text-muted">{MECHANISM_LABEL[item.acquisition_mechanism] ?? item.acquisition_mechanism}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <StatusChip
            tone={item.kill_switch ? "fail" : "neutral"}
            hideIcon={!item.kill_switch}
            data-testid={`source-kill-switch-${item.slug}`}
          >
            {item.kill_switch ? "Kill-switch ON" : item.enabled ? "Enabled" : "Disabled"}
          </StatusChip>
          <StatusChip
            tone={READINESS_TONE[readiness] ?? "neutral"}
            data-testid={`source-readiness-${item.slug}`}
          >
            {readiness ?? "unconfigured"}
          </StatusChip>
        </div>
      </div>

      {/* Description */}
      {item.description && (
        <p className="text-xs text-muted">{item.description}</p>
      )}

      {/* Key facts */}
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
        <dt className="text-muted">Jurisdiction</dt>
        <dd className="flex flex-wrap gap-1">
          {(item.jurisdiction_codes ?? []).map((j) => (
            <span key={j} className="rounded bg-canvas-deep px-1.5 py-0.5 text-xs font-medium">{j}</span>
          ))}
          {(!item.jurisdiction_codes || item.jurisdiction_codes.length === 0) && <span className="text-muted">—</span>}
        </dd>

        <dt className="text-muted">Capabilities</dt>
        <dd className="flex flex-wrap gap-1">
          {(item.capabilities ?? []).map((c) => (
            <span key={c} className="rounded bg-canvas-deep px-1.5 py-0.5 text-xs">{c.replace(/_/g, " ")}</span>
          ))}
          {(!item.capabilities || item.capabilities.length === 0) && <span className="text-muted">—</span>}
        </dd>

        <dt className="text-muted">Licence</dt>
        <dd>{LICENCE_KIND_LABEL[item.licence_kind] ?? item.licence_kind}</dd>

        <dt className="text-muted">Last activity</dt>
        <dd className={lastActivity === "Never" ? "text-muted" : ""}>{lastActivity}</dd>

        {item.connector_readiness && item.source_readiness && item.connector_readiness !== item.source_readiness && (
          <>
            <dt className="text-muted">Connector health</dt>
            <dd>
              <StatusChip tone={READINESS_TONE[item.connector_readiness] ?? "neutral"} hideIcon>
                {item.connector_readiness}
              </StatusChip>
            </dd>
          </>
        )}

        {item.health_detail && (
          <>
            <dt className="text-muted">Health note</dt>
            <dd className="text-xs">{item.health_detail}</dd>
          </>
        )}
      </dl>

      {/* Filters */}
      {(Object.keys(item.requested_filters ?? {}).length > 0 || Object.keys(item.effective_filters ?? {}).length > 0) && (
        <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1.5 border-t border-border pt-3 text-sm">
          <FilterBlock label="Requested filters" filters={item.requested_filters ?? {}} />
          <FilterBlock label="Effective filters" filters={item.effective_filters ?? {}} empty="None active" />
          {item.deviation_reason && (
            <>
              <dt className="flex items-center gap-1 text-muted">
                <AlertTriangle className="h-3.5 w-3.5 text-ochre-deep" />
                Deviation
              </dt>
              <dd className="text-xs text-ochre-deep">{item.deviation_reason}</dd>
            </>
          )}
        </dl>
      )}

      {/* Synthetic badge */}
      <p className="mt-auto text-xs text-muted">{item.status_label}</p>
    </li>
  );
}

// ── Alias review panel ────────────────────────────────────────────────────────

const CONF_TONE: Record<string, ChipTone> = {
  verified: "pass",
  high: "pass",
  medium: "warning",
  low: "neutral",
};

function AliasRow({
  alias: initial,
  onUpdate,
}: {
  alias: AliasItem;
  onUpdate: (a: AliasItem) => void;
}) {
  const [alias, setAlias] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const act = async (action: "confirm" | "reject") => {
    setLoading(true);
    setErr(null);
    try {
      const r = await aliasesApi.update(alias.id, action);
      const updated = { ...alias, review_state: r.review_state, reviewed_at: r.reviewed_at };
      setAlias(updated);
      onUpdate(updated);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <tr className="border-b border-border last:border-0 text-sm" data-testid={`alias-row-${alias.id}`}>
      <td className="py-3 pr-4">
        <p className="font-medium">{alias.alias_email}</p>
        <p className="text-xs text-muted">{alias.display_names_seen.join(", ")}</p>
      </td>
      <td className="py-3 pr-4 text-xs text-muted">{alias.canonical_email}</td>
      <td className="py-3 pr-4">
        <StatusChip tone={CONF_TONE[alias.confidence] ?? "neutral"} hideIcon>
          {alias.confidence}
        </StatusChip>
      </td>
      <td className="py-3 pr-4">
        {alias.review_state === "pending" ? (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => act("confirm")}
              disabled={loading}
              className="rounded bg-eucalyptus-soft px-2.5 py-1 text-xs font-medium text-eucalyptus-deep hover:bg-eucalyptus-deep/10 disabled:opacity-50"
              data-testid={`alias-confirm-${alias.id}`}
            >
              Confirm
            </button>
            <button
              type="button"
              onClick={() => act("reject")}
              disabled={loading}
              className="rounded bg-canvas-deep px-2.5 py-1 text-xs font-medium text-muted hover:text-navy disabled:opacity-50"
              data-testid={`alias-reject-${alias.id}`}
            >
              Reject
            </button>
          </div>
        ) : (
          <span className={alias.review_state === "confirmed" ? "text-eucalyptus-deep text-xs font-medium" : "text-muted text-xs"}>
            {alias.review_state}
          </span>
        )}
        {err && <p className="mt-0.5 text-xs text-risk">{err}</p>}
      </td>
    </tr>
  );
}

function AliasSection() {
  const [aliases, setAliases] = useState<AliasItem[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error" | "empty">("loading");

  useEffect(() => {
    aliasesApi.list()
      .then((r) => {
        setAliases(r.items);
        setState(r.items.length === 0 ? "empty" : "ready");
      })
      .catch(() => setState("error"));
  }, []);

  const handleUpdate = (updated: AliasItem) => {
    setAliases((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
  };

  if (state === "loading") return <Skeleton className="h-24" label="Loading aliases" />;
  if (state === "error") return null; // non-demo workspaces: silently absent
  if (state === "empty") return null;

  return (
    <section className="mt-10" data-testid="alias-section">
      <h2 className="mb-1 text-lg font-semibold">Sender-alias review</h2>
      <p className="mb-4 text-sm text-muted">
        Synthetic aliases for the demo workspace only. Pending aliases require manual confirmation or rejection.
      </p>
      <div className="card overflow-x-auto">
        <table className="w-full" data-testid="alias-table">
          <thead>
            <tr className="border-b border-border bg-canvas-deep text-left text-xs font-semibold text-muted">
              <th className="px-4 py-2.5">Alias email</th>
              <th className="px-4 py-2.5">Canonical</th>
              <th className="px-4 py-2.5">Confidence</th>
              <th className="px-4 py-2.5">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border px-4">
            {aliases.map((a) => (
              <AliasRow key={a.id} alias={a} onUpdate={handleUpdate} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SourcesPage() {
  const [items, setItems] = useState<ConnectorItem[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const load = async () => {
    setLoadState("loading");
    try {
      const r = await sourcesApi.listConnectors();
      setItems(r.items);
      setLoadState("ready");
    } catch (e) {
      setErrMsg(e instanceof ApiError ? e.message : String(e));
      setLoadState("error");
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <>
      <PageHeader
        eyebrow="Sources"
        title="Sources & Coverage"
        description="Provider-neutral connector catalogue. All entries are read-only in this milestone. Every entry is labelled truthfully as synthetic / not connected."
        testId="sources-header"
        actions={
          <button
            type="button"
            onClick={load}
            disabled={loadState === "loading"}
            className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-muted hover:text-navy disabled:opacity-50"
            data-testid="sources-refresh"
          >
            {loadState === "loading" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Refresh
          </button>
        }
      />

      {loadState === "loading" && <Skeleton className="h-64" label="Loading connectors" />}
      {loadState === "error" && <ErrorState description={errMsg ?? "Could not load connectors."} onRetry={load} />}

      {loadState === "ready" && (
        <>
          <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="sources-list">
            {items.map((item) => (
              <ConnectorCard key={item.slug} item={item} />
            ))}
          </ul>

          <AliasSection />

          <MilestoneNote milestone={4}>
            All connector entries are synthetic demonstration data only. No live source is connected
            in this prototype. Enable and configuration controls arrive in a future milestone.
          </MilestoneNote>
        </>
      )}
    </>
  );
}
