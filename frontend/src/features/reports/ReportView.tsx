import { Link } from "react-router-dom";
import { StatusChip } from "../../components/StatusChip";
import { EmptyState } from "../../components/States";
import type { ReportRun } from "../../lib/reports";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Snap = Record<string, any>;

export function DailyDigest({ snapshot }: { snapshot: Snap }) {
  const candidates = snapshot.current_candidates ?? [];
  return (
    <div className="space-y-6" data-testid="daily-digest-body">
      {snapshot.quiet_day ? (
        <EmptyState title="A quiet day" description={snapshot.quiet_day_message ?? "No material changes were recorded in this period."} data-testid="daily-quiet-day" />
      ) : (
        <p className="text-sm text-muted" data-testid="daily-material-changes">{snapshot.material_changes_count ?? 0} material change(s) recorded in this period.</p>
      )}

      <section aria-labelledby="daily-candidates-heading">
        <h3 id="daily-candidates-heading" className="text-h3 font-semibold">Current top candidates</h3>
        {candidates.length === 0 ? (
          <p className="mt-2 text-sm text-muted">No current candidates to show.</p>
        ) : (
          <ul className="mt-3 space-y-3">
            {candidates.map((c: Snap) => (
              <li key={c.property_id} className="rounded-md border border-border p-4" data-testid={`daily-candidate-${c.property_id}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Link to={c.property_link} className="font-semibold hover:underline underline-offset-4">{c.address}</Link>
                  <StatusChip tone={c.fit?.state === "known" ? "pass" : "unknown"} hideIcon>{c.fit?.pct != null ? `Fit ${c.fit.pct}%` : "Fit unavailable"}</StatusChip>
                </div>
                <p className="mt-1 text-sm text-muted">{c.raw_price} · Coverage {c.coverage?.pct != null ? `${c.coverage.pct}%` : "Unknown"} · Freshness: {c.freshness}</p>
                <p className="mt-2 text-sm"><span className="font-semibold">Why it fits: </span>{c.why_fits}</p>
                <p className="mt-1 text-sm"><span className="font-semibold">Main risk: </span>{c.main_risk}</p>
                {c.travel_line && <p className="mt-1 text-xs text-muted" data-testid={`daily-candidate-travel-${c.property_id}`}>{c.travel_line}</p>}
                <Link to={c.evidence_link} className="mt-2 inline-block text-xs font-semibold text-eucalyptus-deep hover:underline">View evidence →</Link>
              </li>
            ))}
          </ul>
        )}
        {snapshot.matching_beyond_top_count > 0 && (
          <p className="mt-2 text-sm text-muted">+{snapshot.matching_beyond_top_count} more matching propert{snapshot.matching_beyond_top_count === 1 ? "y" : "ies"} beyond the top candidates.</p>
        )}
      </section>

      <SnapshotSection title="New leads / material changes" items={snapshot.new_leads} render={(l: Snap) => `${l.source_label} · ${l.channel}`} />
      <SnapshotSection title="Price-verification opportunities" items={snapshot.price_verification_opportunities} render={(p: Snap) => `${p.address} — ${p.raw_price}`} />
      <section>
        <h3 className="text-h3 font-semibold">Upcoming home opens</h3>
        <p className="mt-2 text-sm text-muted">{snapshot.upcoming_home_opens_note}</p>
      </section>
      <SnapshotSection title="Upcoming deadlines / decisions" items={snapshot.upcoming_deadlines} render={(t: Snap) => `${t.title} — due ${new Date(t.due_at).toLocaleDateString()}`} />

      <section>
        <h3 className="text-h3 font-semibold">Source and evidence health</h3>
        <p className="mt-2 text-sm text-muted">
          {snapshot.source_evidence_health?.total_connectors ?? 0} connector(s) tracked
          {Object.keys(snapshot.source_evidence_health?.connector_states ?? {}).length > 0
            ? `: ${Object.entries(snapshot.source_evidence_health.connector_states).map(([k, v]) => `${k} (${v})`).join(", ")}.`
            : "."}
        </p>
      </section>
    </div>
  );
}

function SnapshotSection({ title, items, render }: { title: string; items: Snap[] | undefined; render: (item: Snap) => string }) {
  return (
    <section>
      <h3 className="text-h3 font-semibold">{title}</h3>
      {!items || items.length === 0 ? (
        <p className="mt-2 text-sm text-muted">Nothing to show.</p>
      ) : (
        <ul className="mt-2 space-y-1 text-sm">
          {items.map((item, i) => <li key={i}>{render(item)}</li>)}
        </ul>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="text-h2 font-bold">{value}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}

export function WeeklyReport({ snapshot }: { snapshot: Snap }) {
  const funnel: Snap[] = snapshot.source_channel_funnel ?? [];
  const suburbs = Object.entries(snapshot.suburb_outcome_view ?? {});
  return (
    <div className="space-y-6" data-testid="weekly-report-body">
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="First discoveries" value={snapshot.unique_first_discoveries?.total ?? 0} />
        <Metric label="Later-channel changes" value={snapshot.later_channel_material_changes ?? 0} />
        <Metric label="High-priority candidates" value={snapshot.high_priority_candidates ?? 0} />
        <Metric label="Fully verified" value={snapshot.fully_verified_eligibility ?? 0} />
        <Metric label="Provisional (Unknown)" value={snapshot.provisional_opportunities ?? 0} />
        <Metric label="Hard failures" value={snapshot.hard_failures ?? 0} />
      </div>

      <section>
        <h3 className="text-h3 font-semibold">Source/channel funnel</h3>
        {funnel.length === 0 ? (
          <p className="mt-2 text-sm text-muted">No first-discovery evidence recorded this period.</p>
        ) : (
          <ul className="mt-2 space-y-1 text-sm">
            {funnel.map((f) => (
              <li key={f.channel}>{f.channel}: {f.first_discoveries} discovered → {f.reached_pass} passed ({f.conversion_rate != null ? `${f.conversion_rate}%` : "not enough data"})</li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3 className="text-h3 font-semibold">Suburb / outcome view</h3>
        {suburbs.length === 0 ? (
          <p className="mt-2 text-sm text-muted">No evaluations recorded this period.</p>
        ) : (
          <ul className="mt-2 space-y-1 text-sm">
            {suburbs.map(([suburb, counts]) => {
              const c = counts as Snap;
              return <li key={suburb}>{suburb}: pass {c.pass}, unknown {c.unknown}, fail {c.fail}</li>;
            })}
          </ul>
        )}
      </section>

      <section>
        <h3 className="text-h3 font-semibold">Actions, duplicates and source health</h3>
        <p className="mt-2 text-sm text-muted">
          {snapshot.actions_replies_completed_tasks?.activity_events ?? 0} recorded action(s) · {snapshot.actions_replies_completed_tasks?.completed_tasks ?? 0} task(s) completed · {snapshot.duplicates?.detected ?? 0} duplicate(s) detected, {snapshot.duplicates?.resolved ?? 0} resolved.
        </p>
        <p className="mt-1 text-sm text-muted">
          Processing/evidence latency: {snapshot.processing_evidence_latency_seconds != null ? `${Math.round(snapshot.processing_evidence_latency_seconds / 60)} min average` : "not enough data"}.
        </p>
      </section>

      <section>
        <h3 className="text-h3 font-semibold">Daily trend</h3>
        <ul className="mt-2 flex flex-wrap gap-3 text-sm">
          {(snapshot.daily_trend ?? []).map((d: Snap) => <li key={d.date} className="rounded-md bg-canvas-deep px-2 py-1">{d.date}: {d.first_discoveries}</li>)}
        </ul>
      </section>
    </div>
  );
}

export function MonthlyReport({ snapshot }: { snapshot: Snap }) {
  const discoveries = Object.entries(snapshot.source_value_unique_discoveries ?? {});
  return (
    <div className="space-y-6" data-testid="monthly-report-body">
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Properties added" value={snapshot.overall_activity?.properties_added ?? 0} />
        <Metric label="Evaluations run" value={snapshot.overall_activity?.evaluations_run ?? 0} />
        <Metric label="Stage changes" value={snapshot.candidate_progression_stage_changes ?? 0} />
      </div>

      <section>
        <h3 className="text-h3 font-semibold">Source value / unique discoveries</h3>
        <ul className="mt-2 space-y-1 text-sm">
          {discoveries.length === 0 && <li className="text-muted">No discoveries recorded this period.</li>}
          {discoveries.map(([channel, count]) => <li key={channel}>{channel}: {String(count)}</li>)}
        </ul>
      </section>

      <section>
        <h3 className="text-h3 font-semibold">Verdict distribution</h3>
        <p className="mt-2 text-sm">Pass {snapshot.verdict_distribution?.pass ?? 0} · Fail {snapshot.verdict_distribution?.fail ?? 0} · Unknown {snapshot.verdict_distribution?.unknown ?? 0}</p>
      </section>

      <section>
        <h3 className="text-h3 font-semibold">Material constraints</h3>
        {(snapshot.material_constraints ?? []).length === 0 ? (
          <p className="mt-2 text-sm text-muted">No recurring hard-rule failure identified.</p>
        ) : (
          <ul className="mt-2 space-y-1 text-sm">
            {snapshot.material_constraints.map((m: Snap) => <li key={m.criterion}>{String(m.criterion).replace(/_/g, " ")}: {m.count}</li>)}
          </ul>
        )}
      </section>

      <section>
        <h3 className="text-h3 font-semibold">Improvement priorities</h3>
        <ul className="mt-2 space-y-1 text-sm">
          {(snapshot.improvement_priorities ?? []).map((p: string, i: number) => <li key={i}>• {p}</li>)}
        </ul>
      </section>
    </div>
  );
}

export function ReportView({ run }: { run: ReportRun }) {
  const s: Snap = run.snapshot ?? {};
  return (
    <article className="card p-5" data-testid={`report-view-${run.report_type}`}>
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4">
        <div>
          <h2 className="text-h2 font-bold" data-testid="report-title">{s.title ?? "Report preview"}</h2>
          <p className="mt-1 text-sm text-muted">
            {run.period_start ? new Date(run.period_start).toLocaleString() : "—"} → {run.period_end ? new Date(run.period_end).toLocaleString() : "—"} · {run.timezone}
            {run.cutoff_at && <> · cutoff {new Date(run.cutoff_at).toLocaleString()}</>}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusChip tone="info" hideIcon data-testid="report-badge-preview">{run.kind === "production" ? "Production" : "Preview / test data"}</StatusChip>
          <StatusChip tone={run.release_state === "ready" ? "pass" : run.release_state === "failed" ? "fail" : "unknown"} hideIcon data-testid="report-state">{run.release_state}</StatusChip>
        </div>
      </header>

      {run.is_partial_period && (
        <p className="mb-4 rounded-md border border-ochre/40 bg-ochre-soft px-3 py-2 text-sm text-ochre-deep" data-testid="report-partial-period">
          Partial-period preview — the database does not yet contain a full period. Actual coverage starts {s.actual_coverage_start ? new Date(s.actual_coverage_start).toLocaleDateString() : "unknown"}.
        </p>
      )}
      {run.release_state === "failed" && (
        <p className="mb-4 rounded-md border border-risk/40 bg-risk-soft px-3 py-2 text-sm text-risk" role="alert" data-testid="report-failure">
          Generation failed: {run.failure_reason ?? "Unknown error"}
        </p>
      )}

      {run.report_type === "daily" && <DailyDigest snapshot={s} />}
      {run.report_type === "weekly" && <WeeklyReport snapshot={s} />}
      {run.report_type === "monthly" && <MonthlyReport snapshot={s} />}
    </article>
  );
}
