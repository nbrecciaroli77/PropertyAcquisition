import { FileBarChart2, Printer, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "../../components/Button";
import { PageHeader } from "../../components/Page";
import { EmptyState, Skeleton } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";
import { campaignApi } from "../../lib/campaigns";
import { formatDate } from "../../lib/format";
import { useJourneys } from "../../lib/journey";
import { reportApi, type ReportRun, type ReportType } from "../../lib/reports";
import { ReportView } from "./ReportView";

const TABS: { value: ReportType; label: string }[] = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

export default function ReportsPage() {
  const { active, journeys, setActiveId, loading: journeyLoading } = useJourneys();
  const [params] = useSearchParams();
  const wantedRun = params.get("run");
  const [tab, setTab] = useState<ReportType>(() => TABS.find((t) => t.value === params.get("type"))?.value ?? "daily");
  const [linkNotice, setLinkNotice] = useState<string | null>(null);
  const runHandled = useRef(false);
  const [runs, setRuns] = useState<ReportRun[] | null>(null);
  const [selected, setSelected] = useState<ReportRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [releasing, setReleasing] = useState(false);

  const load = async () => {
    if (!active) return;
    try {
      const list = await reportApi.list(active.id, tab);
      const linked = !runHandled.current && wantedRun ? list.find((r) => r.id === wantedRun) : undefined;
      setRuns(list);
      setSelected(linked ?? list[0] ?? null);
      setError(null);
      if (wantedRun && !runHandled.current) {
        runHandled.current = true;
        if (!linked) void openLinkedRun(wantedRun);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reports could not be loaded.");
      setRuns([]);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, [active?.id, tab]);

  /** Older links carry only ?run=; a run opens only inside the campaign that owns it. */
  const openLinkedRun = async (runId: string) => {
    if (!active) return;
    try {
      const location = await campaignApi.locateRun(runId);
      if (location.journey_id !== active.id && journeys.some((j) => j.id === location.journey_id)) {
        setActiveId(location.journey_id);
        return;
      }
      if (location.journey_id === active.id && location.report_type !== tab) {
        runHandled.current = false;
        setTab(location.report_type as ReportType);
        return;
      }
    } catch {
      // Not found in this workspace: fall through to the notice.
    }
    setLinkNotice("That report is not part of this campaign, or it no longer exists.");
  };

  const generate = async () => {
    if (!active) return;
    setGenerating(true);
    setError(null);
    try {
      const run = await reportApi.generate(active.id, tab, "preview");
      await load();
      setSelected(run);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Report could not be generated.");
    } finally {
      setGenerating(false);
    }
  };

  const markReadyToSend = async () => {
    if (!active || !selected) return;
    setReleasing(true);
    setError(null);
    try {
      const run = await reportApi.markReadyToSend(active.id, selected.id);
      await load();
      setSelected(run);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Report could not be marked ready to send.");
    } finally {
      setReleasing(false);
    }
  };

  if (!active) {
    if (journeyLoading) {
      return <Skeleton className="h-56" label="Loading your journey" />;
    }
    return <EmptyState title="No buying journey yet" description="Create a journey to generate report previews." data-testid="reports-no-journey" />;
  }

  return (
    <>
      <PageHeader
        eyebrow="Reports"
        title="Report previews"
        description={`Previews for ${active.name}, generated from this campaign's data only. Nothing is emailed — every report opens here, on demand.`}
        testId="reports-header"
        actions={
          <Button variant="secondary" size="sm" icon={<Printer className="h-4 w-4" />} onClick={() => window.print()} className="print:hidden" data-testid="reports-print">
            Print / save as PDF
          </Button>
        }
      />

      <div className="mb-6 flex flex-wrap items-center gap-2 print:hidden" role="tablist" aria-label="Report period" data-testid="reports-tabs">
        {TABS.map((t) => (
          <button
            key={t.value}
            type="button"
            role="tab"
            aria-selected={tab === t.value}
            onClick={() => setTab(t.value)}
            className={`h-10 rounded-full px-4 text-sm font-semibold transition-colors ${tab === t.value ? "bg-navy text-white" : "bg-canvas-deep text-navy hover:bg-stone"}`}
            data-testid={`reports-tab-${t.value}`}
          >
            {t.label}
          </button>
        ))}
        <Button size="sm" onClick={() => void generate()} disabled={generating} icon={<RefreshCw className={`h-4 w-4 ${generating ? "animate-spin" : ""}`} />} data-testid="reports-generate">
          {generating ? "Generating…" : "Generate preview"}
        </Button>
      </div>

      {linkNotice && <p role="status" className="mb-4 rounded-md border border-border bg-canvas-deep p-3 text-sm" data-testid="reports-link-notice">{linkNotice}</p>}
      {error && <p role="alert" className="mb-4 rounded-md border border-risk/40 bg-risk-soft p-3 text-sm text-risk" data-testid="reports-error">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <section className="min-w-0" data-testid="reports-latest">
          {runs === null && <Skeleton className="h-56" label="Loading reports" />}
          {runs && runs.length === 0 && (
            <EmptyState
              icon={<FileBarChart2 className="h-6 w-6" />}
              title="No preview generated yet"
              description="Generate a preview to see what this report would show from your current data."
              data-testid="reports-empty"
            />
          )}
          {selected?.release_state === "ready" && (
            <div className="mb-3 flex items-center justify-between gap-3 rounded-md border border-border bg-canvas-deep px-4 py-2">
              <p className="text-sm text-muted">Freeze this snapshot as ready to send. Delivery stays disabled — no email is sent.</p>
              <Button size="sm" variant="secondary" disabled={releasing} onClick={() => void markReadyToSend()} data-testid="reports-mark-ready-to-send">
                {releasing ? "Marking…" : "Mark ready to send"}
              </Button>
            </div>
          )}
          {selected && <ReportView run={selected} />}
        </section>

        <aside className="print:hidden" data-testid="reports-history">
          <h2 className="text-sm font-semibold text-muted">Previous runs</h2>
          <ul className="mt-3 space-y-2">
            {(runs ?? []).map((run) => (
              <li key={run.id}>
                <button
                  type="button"
                  onClick={() => setSelected(run)}
                  className={`w-full rounded-md border p-3 text-left text-sm transition-colors ${selected?.id === run.id ? "border-navy bg-navy-soft" : "border-border bg-surface hover:border-navy"}`}
                  data-testid={`reports-history-${run.id}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold">{run.generated_at ? formatDate(run.generated_at) : "Not generated"}</span>
                    <StatusChip tone={run.release_state === "ready" ? "pass" : run.release_state === "failed" ? "fail" : "unknown"} hideIcon>
                      {run.release_state}
                    </StatusChip>
                  </div>
                  {run.idempotency_scope === "workspace_legacy" && (
                    <span className="mt-1 inline-block text-[11px] font-semibold text-navy" title="Created before campaign separation. Its ID and links are preserved." data-testid={`reports-history-legacy-${run.id}`}>
                      Historical run · ID preserved
                    </span>
                  )}
                  <div className="mt-1 text-xs text-muted">
                    {run.kind.replace("_", " ")} · {run.period_start ? formatDate(run.period_start) : "—"} → {run.period_end ? formatDate(run.period_end) : "—"}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </>
  );
}
