import { Activity, CheckSquare, CircleHelp, Home, ShieldAlert, Square } from "lucide-react";
import { Link } from "react-router-dom";
import { ButtonLink } from "../../components/Button";
import { FitRing } from "../../components/FitRing";
import { MetricCard, MilestoneNote, PageHeader } from "../../components/Page";
import { PropertyImagePlaceholder } from "../../components/PropertyCard";
import { SourceFreshness } from "../../components/SourceFreshness";
import { EmptyState } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";
import { known } from "../../lib/format";
import { displayUser, properties, workspace } from "../../lib/synthetic";

const changes = [
  { id: "demo-001", kind: "New match", tone: "pass" as const, why: "Passes every hard rule on original-source facts; land 690 m² is well above the 400 m² rule." },
  { id: "demo-004", kind: "Price guide conflict", tone: "warning" as const, why: "Index says $1.20m, detail says From $1.35m. Verification required before fit can be assessed." },
  { id: "demo-002", kind: "Waiting for evidence", tone: "unknown" as const, why: "Unpriced (Contact agent) and condition unknown. Unknown is not Pass." },
];

const nextActions = [
  { label: "Verify 2 items", helper: "Unverified facts may change outcomes", to: "/app/discover", done: false },
  { label: "Add reminder: 12 Banksia Crescent open home", helper: "Advertised Sat 10:00 — not a booking", to: "/app/tasks", done: false },
  { label: "Review draft to agent (UNSENT)", helper: "Drafts never send from this app", to: "/app/agents", done: true },
];

export default function TodayPage() {
  const needsVerification = properties.filter((p) => p.gate === "Unknown").length;
  const newMatches = properties.filter((p) => p.gate === "Pass" && p.buyerState === "Reviewing").length;
  return (
    <>
      <PageHeader
        eyebrow="Today"
        title={`Good morning, ${displayUser.name}`}
        description={
          <>
            Here's what changed in <strong className="text-navy">{workspace.name}</strong>. Local time {workspace.timezone}.
          </>
        }
        testId="today-header"
      />

      <section aria-label="Snapshot" className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-4">
        <MetricCard value={newMatches} label="New matches" helper="Since your last check" tone="good" icon={<Home className="h-5 w-5" aria-hidden="true" />} testId="metric-new-matches" />
        <MetricCard value={needsVerification} label="Need verification" helper="Unknown is not Pass" tone="warning" icon={<CircleHelp className="h-5 w-5" aria-hidden="true" />} testId="metric-verification" />
        <MetricCard value={1} label="Material change" helper="Price guide conflict" tone="info" icon={<Activity className="h-5 w-5" aria-hidden="true" />} testId="metric-changes" />
        <MetricCard value={0} label="Source failures" helper="No sources connected yet" tone="neutral" icon={<ShieldAlert className="h-5 w-5" aria-hidden="true" />} testId="metric-source-failures" />
      </section>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(300px,1fr)]">
        <section aria-labelledby="whats-new-heading" className="card p-5">
          <h2 id="whats-new-heading" className="label mb-4">
            What changed
          </h2>
          <ol className="relative space-y-3 border-l border-border pl-5">
            {changes.map((c) => {
              const p = properties.find((x) => x.id === c.id);
              if (!p) return null;
              return (
                <li key={c.id} className="relative" data-testid={`change-${c.id}`}>
                  <span className="absolute -left-[26px] top-4 h-2.5 w-2.5 rounded-full bg-eucalyptus-deep ring-4 ring-surface" aria-hidden="true" />
                  <div className="card flex flex-col gap-3 p-4 sm:flex-row">
                    <PropertyImagePlaceholder className="h-24 w-full shrink-0 rounded-md sm:h-28 sm:w-36 sm:self-start" />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusChip tone={c.tone}>{c.kind}</StatusChip>
                        <Link to={`/app/properties/${p.id}`} className="font-semibold hover:underline underline-offset-4">
                          {p.address}, {p.suburb} {p.state}
                        </Link>
                      </div>
                      <p className="mt-2 rounded-md bg-canvas px-3 py-2 text-sm">
                        <span className="font-semibold">Why it matters: </span>
                        {c.why}
                      </p>
                      <SourceFreshness className="mt-2" source={p.sourceLabel} checkedAt={p.lastChecked} />
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
          <Link to="/app/discover" className="mt-4 inline-block text-sm font-semibold text-eucalyptus-deep hover:underline underline-offset-4" data-testid="view-all-changes">
            View all changes →
          </Link>
        </section>

        <div className="space-y-6">
          <section aria-labelledby="journey-health-heading" className="card p-5">
            <h2 id="journey-health-heading" className="text-h3 font-semibold">
              Journey health
            </h2>
            <div className="mt-4 space-y-4">
              <FitRing value={known(78)} label="Brief coverage" size={52} />
              <FitRing value={known(100)} label="Source health (2 manual sources)" size={52} />
              <div className="flex items-center gap-2 text-sm">
                <span className="inline-flex h-[52px] w-[52px] items-center justify-center rounded-full border-2 border-border font-bold">{needsVerification}</span>
                <div>
                  <div className="text-xs text-muted">Review queue</div>
                  <div className="font-semibold">Needs your attention</div>
                </div>
              </div>
            </div>
          </section>

          <section aria-labelledby="next-actions-heading" className="card p-5">
            <h2 id="next-actions-heading" className="text-h3 font-semibold">
              Next actions
            </h2>
            <ul className="mt-3 divide-y divide-border">
              {nextActions.map((a) => (
                <li key={a.label} className="flex items-start gap-3 py-3">
                  {a.done ? <CheckSquare className="mt-0.5 h-5 w-5 text-eucalyptus-deep" aria-label="Done" /> : <Square className="mt-0.5 h-5 w-5 text-muted" aria-label="Not done" />}
                  <div className="min-w-0 flex-1">
                    <Link to={a.to} className="text-sm font-semibold hover:underline underline-offset-4">
                      {a.label}
                    </Link>
                    <div className="text-xs text-muted">{a.helper}</div>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <EmptyState
            title="Quiet since last check"
            description="No source failures. This is a genuine 'no changes' state, not a failed check — a failed check would show as an error."
            data-testid="quiet-state"
            action={
              <ButtonLink to="/app/sources" variant="tertiary" size="sm">
                Review sources
              </ButtonLink>
            }
          />
        </div>
      </div>

      <MilestoneNote milestone={3}>Live change detection, deadlines and source health arrive with the property domain and matching engine.</MilestoneNote>
    </>
  );
}
