/**
 * M4.2 Duplicate Review centre.
 *
 * Rules:
 * - Never auto-merges. All actions are user-initiated.
 * - Older property (property_a) is default survivor.
 * - 81A vs 81C always shows a unit-suffix warning — never auto-merges.
 * - Undo restores only the originally moved relationships (from merge_snapshot).
 * - Split in M4.2 is equivalent to undo-merge (reversal only, no new records).
 */
import {
  AlertTriangle,
  ArrowLeftRight,
  CheckCircle,
  GitMerge,
  Loader2,
  RefreshCw,
  RotateCcw,
  Scissors,
  Search,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "../../components/Button";
import { PageHeader } from "../../components/Page";
import { StatusChip, type ChipTone } from "../../components/StatusChip";
import { ErrorState, Skeleton } from "../../components/States";
import { duplicatesApi, type DuplicateProposal, type PropertySummary } from "../../lib/duplicates";
import { ApiError } from "../../lib/api";

// ── State chips ───────────────────────────────────────────────────────────────

const STATE_TONE: Record<string, ChipTone> = {
  pending: "warning",
  confirmed: "pass",
  rejected: "fail",
  undone: "neutral",
};

function StateChip({ state }: { state: string }) {
  return (
    <StatusChip tone={STATE_TONE[state] ?? "neutral"} hideIcon>
      {state}
    </StatusChip>
  );
}

// ── Property side-by-side card ────────────────────────────────────────────────

function PropCard({
  prop,
  role,
}: {
  prop: PropertySummary;
  role: "survivor" | "duplicate";
}) {
  return (
    <div
      className={`flex-1 rounded-md border p-4 text-sm ${
        role === "survivor"
          ? "border-eucalyptus-deep/40 bg-eucalyptus-soft/20"
          : "border-border bg-canvas-deep"
      }`}
      data-testid={`prop-${role}`}
    >
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
        {role === "survivor" ? "Survivor (primary)" : "Duplicate (to merge)"}
      </p>
      <p className="font-semibold">{prop.address_line}</p>
      <p className="text-muted">
        {prop.suburb} {prop.state} {prop.postcode ?? ""}
      </p>
      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs text-muted">
        <dt>Facts</dt>
        <dd className="font-medium text-charcoal">{prop.fact_count}</dd>
        {prop.earliest_discovery && (
          <>
            <dt>First seen</dt>
            <dd className="font-medium text-charcoal">
              {new Date(prop.earliest_discovery).toLocaleDateString("en-AU")}
            </dd>
          </>
        )}
        {prop.merged_into_id && (
          <>
            <dt>Merged into</dt>
            <dd className="font-medium text-risk">another property</dd>
          </>
        )}
      </dl>
    </div>
  );
}

// ── Action row ────────────────────────────────────────────────────────────────

type ActionKey = "confirm" | "reject" | "undo" | "split" | "swap";

function ActionBar({
  proposal,
  loading,
  onAction,
}: {
  proposal: DuplicateProposal;
  loading: boolean;
  onAction: (action: ActionKey, reason?: string) => void;
}) {
  const [reason, setReason] = useState("");
  const isPending = proposal.state === "pending" || proposal.state === "undone";
  const isConfirmed = proposal.state === "confirmed";

  if (!isPending && !isConfirmed) return null;

  return (
    <div className="space-y-3 border-t border-border pt-3">
      <input
        type="text"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Optional reason (recorded in audit)"
        maxLength={300}
        className="w-full rounded-md border border-border bg-surface px-3 py-1.5 text-sm focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
        data-testid="dup-reason-input"
      />
      <div className="flex flex-wrap gap-2">
        {isPending && (
          <>
            <Button
              size="sm"
              onClick={() => onAction("confirm", reason || undefined)}
              disabled={loading}
              data-testid="dup-action-confirm"
            >
              <GitMerge className="h-3.5 w-3.5" />
              Confirm merge
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onAction("swap")}
              disabled={loading}
              title="Swap which property will survive before confirming"
              data-testid="dup-action-swap"
            >
              <ArrowLeftRight className="h-3.5 w-3.5" />
              Swap survivor
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onAction("reject", reason || undefined)}
              disabled={loading}
              data-testid="dup-action-reject"
            >
              <XCircle className="h-3.5 w-3.5" />
              Reject
            </Button>
          </>
        )}
        {isConfirmed && (
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onAction("undo", reason || undefined)}
              disabled={loading}
              title="Restore only the originally moved relationships"
              data-testid="dup-action-undo"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Undo merge
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onAction("split", reason || undefined)}
              disabled={loading}
              title="Reverse the merge — restores original non-survivor from merge snapshot"
              data-testid="dup-action-split"
            >
              <Scissors className="h-3.5 w-3.5" />
              Split
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

// ── Single proposal card ──────────────────────────────────────────────────────

function ProposalCard({
  proposal: initial,
  onUpdated,
}: {
  proposal: DuplicateProposal;
  onUpdated: (updated: DuplicateProposal) => void;
}) {
  const [proposal, setProposal] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const handle = async (action: ActionKey, reason?: string) => {
    setLoading(true);
    setErr(null);
    try {
      let updated: DuplicateProposal;
      switch (action) {
        case "confirm":
          updated = await duplicatesApi.confirm(proposal.id, proposal.row_version, undefined, reason);
          break;
        case "reject":
          updated = await duplicatesApi.reject(proposal.id, proposal.row_version, reason);
          break;
        case "undo":
          updated = await duplicatesApi.undo(proposal.id, proposal.row_version, reason);
          break;
        case "split":
          updated = await duplicatesApi.split(proposal.id, proposal.row_version, reason);
          break;
        case "swap":
          updated = await duplicatesApi.swapPrimary(proposal.id, proposal.row_version);
          break;
        default:
          return;
      }
      setProposal(updated);
      onUpdated(updated);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const reasonLabel =
    proposal.proposal_reason === "exact_address_intake"
      ? "Exact address match on intake"
      : proposal.proposal_reason === "address_scan"
      ? "Address scan match"
      : "User-proposed";

  return (
    <li
      className="card space-y-4 p-5"
      data-testid={`dup-proposal-${proposal.id}`}
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm">
          <StateChip state={proposal.state} />
          <span className="text-muted">{reasonLabel}</span>
        </div>
        {loading && <Loader2 className="h-4 w-4 animate-spin text-muted" />}
      </div>

      {/* Unit-suffix warning */}
      {proposal.unit_suffix_warning && (
        <div
          className="flex items-start gap-2 rounded-md border border-ochre-deep/30 bg-ochre-soft px-4 py-3 text-sm text-ochre-deep"
          data-testid="dup-unit-suffix-warning"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            <strong>Different unit suffixes detected</strong> (e.g. 81A vs 81C). These properties
            must not be merged automatically. Review carefully before confirming.
          </span>
        </div>
      )}

      {/* Side-by-side */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <PropCard prop={proposal.property_a} role="survivor" />
        <PropCard prop={proposal.property_b} role="duplicate" />
      </div>

      {/* Evidence */}
      {proposal.evidence && Object.keys(proposal.evidence).length > 0 && (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer hover:text-navy">Evidence details</summary>
          <pre className="mt-1 overflow-x-auto rounded bg-canvas-deep p-2 font-mono text-xs">
            {JSON.stringify(proposal.evidence, null, 2)}
          </pre>
        </details>
      )}

      {/* Review note */}
      {proposal.review_reason && (
        <p className="text-xs text-muted">
          Review note: <em>{proposal.review_reason}</em>
        </p>
      )}
      {proposal.reviewed_at && (
        <p className="text-xs text-muted">
          Actioned {new Date(proposal.reviewed_at).toLocaleString("en-AU")}
        </p>
      )}

      {/* Actions */}
      {err && (
        <p className="rounded bg-risk-soft px-3 py-2 text-xs text-risk" data-testid="dup-action-error">
          {err}
        </p>
      )}
      <ActionBar proposal={proposal} loading={loading} onAction={handle} />
    </li>
  );
}

// ── Filter tabs ───────────────────────────────────────────────────────────────

type Filter = "all" | "pending" | "confirmed" | "rejected" | "undone";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "pending", label: "Pending" },
  { key: "confirmed", label: "Confirmed" },
  { key: "rejected", label: "Rejected" },
  { key: "undone", label: "Undone" },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DuplicatesPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [items, setItems] = useState<DuplicateProposal[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState<string | null>(null);

  const load = useCallback(async (stateFilter?: Filter) => {
    setLoadState("loading");
    setErrMsg(null);
    try {
      const f = stateFilter ?? filter;
      const resp = await duplicatesApi.list(f === "all" ? undefined : f);
      setItems(resp.items);
      setLoadState("ready");
    } catch (e) {
      setErrMsg(e instanceof ApiError ? e.message : String(e));
      setLoadState("error");
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const handleFilterChange = (f: Filter) => {
    setFilter(f);
    load(f);
  };

  const handleScan = async () => {
    setScanning(true);
    setScanMsg(null);
    try {
      const r = await duplicatesApi.scan();
      setScanMsg(
        r.proposals_created > 0
          ? `Scan complete — ${r.proposals_created} new proposal${r.proposals_created !== 1 ? "s" : ""} found.`
          : "Scan complete — no new candidates found.",
      );
      await load();
    } catch (e) {
      setScanMsg(e instanceof ApiError ? e.message : String(e));
    } finally {
      setScanning(false);
    }
  };

  const handleUpdated = (updated: DuplicateProposal) => {
    setItems((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  const pendingCount = items.filter((p) => p.state === "pending").length;
  const displayed =
    filter === "all" ? items : items.filter((p) => p.state === filter);

  return (
    <>
      <PageHeader
        eyebrow="Duplicate Review"
        title="Proposed matches"
        description="Properties that may be duplicates. Review each pair carefully before confirming or rejecting a merge. All merges are reversible via Undo or Split."
        testId="duplicates-header"
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => load()}
              disabled={loadState === "loading"}
              data-testid="dup-refresh"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={handleScan}
              disabled={scanning}
              data-testid="dup-scan"
            >
              {scanning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
              Scan for matches
            </Button>
          </div>
        }
      />

      {scanMsg && (
        <div className="mb-4 rounded-md border border-border bg-canvas-deep px-4 py-3 text-sm" data-testid="dup-scan-msg">
          {scanMsg}
        </div>
      )}

      {/* Filter tabs */}
      <div
        className="mb-6 flex gap-1 overflow-x-auto rounded-lg border border-border bg-surface p-1"
        role="tablist"
        data-testid="dup-filter-bar"
      >
        {FILTERS.map((f) => {
          const count = f.key === "all" ? items.length : items.filter((p) => p.state === f.key).length;
          return (
            <button
              key={f.key}
              role="tab"
              aria-selected={filter === f.key}
              onClick={() => handleFilterChange(f.key)}
              data-testid={`dup-filter-${f.key}`}
              className={`flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                filter === f.key ? "bg-navy text-white shadow-sm" : "text-muted hover:text-navy"
              }`}
            >
              {f.label}
              {count > 0 && (
                <span className={`rounded-full px-1.5 text-xs ${filter === f.key ? "bg-white/20" : "bg-canvas-deep"}`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {loadState === "loading" && <Skeleton className="h-48" label="Loading proposals" />}
      {loadState === "error" && (
        <ErrorState description={errMsg ?? "Could not load proposals."} onRetry={() => load()} />
      )}

      {loadState === "ready" && (
        <>
          {displayed.length === 0 ? (
            <div className="rounded-lg border border-border bg-canvas-deep p-10 text-center" data-testid="dup-empty">
              {filter === "pending" && pendingCount === 0 ? (
                <>
                  <CheckCircle className="mx-auto h-10 w-10 text-eucalyptus-deep/40" />
                  <p className="mt-3 font-medium">No pending proposals</p>
                  <p className="mt-1 text-sm text-muted">
                    Run a scan to check for near-duplicate properties in your workspace.
                  </p>
                </>
              ) : (
                <>
                  <p className="font-medium">No {filter === "all" ? "" : filter} proposals</p>
                  {filter === "all" && (
                    <p className="mt-1 text-sm text-muted">
                      Run a scan to check for near-duplicate properties.
                    </p>
                  )}
                </>
              )}
            </div>
          ) : (
            <ul className="space-y-4" data-testid="dup-list">
              {displayed.map((p) => (
                <ProposalCard key={p.id} proposal={p} onUpdated={handleUpdated} />
              ))}
            </ul>
          )}
        </>
      )}
    </>
  );
}
