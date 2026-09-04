import { Activity, CircleHelp, Home, ShieldAlert, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ButtonLink } from "../../components/Button";
import { FitRing } from "../../components/FitRing";
import { MetricCard, PageHeader } from "../../components/Page";
import { PropertyImage } from "../../components/PropertyCard";
import { SourceFreshness } from "../../components/SourceFreshness";
import { EmptyState, ErrorState, Skeleton } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";
import { useAuth } from "../../lib/auth";
import { formatDate, known, unknown } from "../../lib/format";
import { useJourneys } from "../../lib/journey";
import { fullAddress, gateReason, propertyApi, type TodayOut } from "../../lib/properties";
import { LoadDemoButton } from "../properties/LoadDemoButton";

export default function TodayPage() {
  const { me } = useAuth();
  const { active, loading } = useJourneys();
  const [state, setState] = useState<{ status: "loading" | "ready" | "error"; data: TodayOut | null; message: string | null }>({ status: "loading", data: null, message: null });

  const load = () => {
    if (!active) return;
    propertyApi
      .today(active.id)
      .then((data) => setState({ status: "ready", data, message: null }))
      .catch((e: unknown) => setState({ status: "error", data: null, message: e instanceof Error ? e.message : "Today could not load." }));
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [active?.id]);

  const d = state.data;
  return (
    <>
      <PageHeader
        eyebrow="Today"
        title={`Good morning, ${me?.user.display_name ?? "there"}`}
        description={
          <>
            Here's what changed in <strong className="text-navy">{me?.workspace.name ?? "your workspace"}</strong>. Local time {me?.user.timezone ?? "Australia/Perth"}.
          </>
        }
        testId="today-header"
      />

      <section aria-labelledby="brief-status-heading" className="card mb-6 flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between" data-testid="today-brief-status">
        <div className="min-w-0">
          <h2 id="brief-status-heading" className="text-h3 font-semibold">
            {active ? active.name : "No buying journey yet"}
          </h2>
          <p className="mt-1 text-sm text-muted">
            {!active
              ? "Create a journey and publish a buying brief to start matching."
              : active.status === "onboarding"
                ? `Setup is paused at step ${active.onboarding_step} of 6. Nothing is lost — resume whenever you like.`
                : active.current_version_no === null
                  ? "Your brief has never been published. Publishing creates an immutable version and evaluates every property against it."
                  : `Brief version ${active.current_version_no} is current · ${active.published_versions} version(s) published · every property is evaluated against it.`}
          </p>
        </div>
        <ButtonLink to={!active ? "/app/journeys/new" : active.status === "onboarding" ? "/app/journeys/new" : "/app/brief"} variant="success" className="shrink-0" data-testid="today-brief-cta">
          {!active ? "Create a journey" : active.status === "onboarding" ? "Resume setup" : "Open the buying brief"}
        </ButtonLink>
      </section>

      {!loading && active && state.status === "loading" && <Skeleton className="h-40" label="Loading today" />}
      {state.status === "error" && <ErrorState description={state.message ?? ""} onRetry={load} data-testid="today-error" />}

      {d && (
        <>
          <section aria-label="Snapshot" className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-4">
            <MetricCard value={d.eligible_reviewing} label="Eligible, awaiting decision" helper="Gates pass, still in Reviewing" tone="good" icon={<Home className="h-5 w-5" aria-hidden="true" />} testId="metric-new-matches" />
            <MetricCard value={d.verification_required} label="Need verification" helper="Unknown is not Pass" tone="warning" icon={<CircleHelp className="h-5 w-5" aria-hidden="true" />} testId="metric-verification" />
            <MetricCard value={d.known_failures} label="Known failures" helper="Cannot be promoted by fit" tone="info" icon={<XCircle className="h-5 w-5" aria-hidden="true" />} testId="metric-failures" />
            <MetricCard value={0} label="Source failures" helper="No sources connected yet" tone="neutral" icon={<ShieldAlert className="h-5 w-5" aria-hidden="true" />} testId="metric-source-failures" />
          </section>

          <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(300px,1fr)]">
            <section aria-labelledby="attention-heading" className="card p-5">
              <h2 id="attention-heading" className="label mb-4">
                Waiting for evidence
              </h2>
              {d.total_properties === 0 ? (
                <EmptyState
                  title="No properties in this journey"
                  description="Structured intake arrives in Milestone 4. Until then you can load the synthetic fixture set to exercise matching."
                  data-testid="today-no-properties"
                  action={active ? <LoadDemoButton journeyId={active.id} onLoaded={load} /> : undefined}
                />
              ) : d.attention.length === 0 ? (
                <EmptyState title="Nothing waiting for evidence" description="Every property in review has every hard rule decided. This is a genuine quiet state, not a failed check." data-testid="today-quiet" />
              ) : (
                <ol className="relative space-y-3 border-l border-border pl-5">
                  {d.attention.map((p) => (
                    <li key={p.id} className="relative" data-testid={`attention-${p.legacy_ref ?? p.id}`}>
                      <span className="absolute -left-[26px] top-4 h-2.5 w-2.5 rounded-full bg-ochre ring-4 ring-surface" aria-hidden="true" />
                      <div className="card flex flex-col gap-3 p-4 sm:flex-row">
                        <PropertyImage property={p} className="h-24 w-full shrink-0 rounded-md sm:h-28 sm:w-36 sm:self-start" />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <StatusChip tone="unknown">Verification required</StatusChip>
                            <Link to={`/app/properties/${p.id}?view=match`} className="font-semibold hover:underline underline-offset-4">
                              {fullAddress(p)}
                            </Link>
                          </div>
                          <p className="mt-2 rounded-md bg-canvas px-3 py-2 text-sm">
                            <span className="font-semibold">Why it matters: </span>
                            {gateReason(p)}
                          </p>
                          {p.campaign && <SourceFreshness className="mt-2" source={p.campaign.source_label} checkedAt={p.campaign.last_checked_at} />}
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
              <Link to="/app/discover" className="mt-4 inline-block text-sm font-semibold text-eucalyptus-deep hover:underline underline-offset-4" data-testid="view-all-changes">
                Open the review queue →
              </Link>
            </section>

            <div className="space-y-6">
              <section aria-labelledby="journey-health-heading" className="card p-5">
                <h2 id="journey-health-heading" className="text-h3 font-semibold">
                  Journey health
                </h2>
                <div className="mt-4 space-y-4">
                  <FitRing value={d.total_properties ? known(Math.round((100 * d.fit_available) / d.total_properties)) : unknown()} label="Properties with an assessable fit" size={52} data-testid="health-fit-available" />
                  <div className="flex items-center gap-2 text-sm">
                    <span className="inline-flex h-[52px] w-[52px] items-center justify-center rounded-full border-2 border-border font-bold">{d.open_tasks}</span>
                    <div>
                      <div className="text-xs text-muted">Open tasks</div>
                      <div className="font-semibold">Across this journey</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="inline-flex h-[52px] w-[52px] items-center justify-center rounded-full border-2 border-border font-bold">{d.under_offer_market}</span>
                    <div>
                      <div className="text-xs text-muted">Market: under offer</div>
                      <div className="font-semibold">Source state, not your offer</div>
                    </div>
                  </div>
                </div>
              </section>

              <section aria-labelledby="changes-heading" className="card p-5">
                <h2 id="changes-heading" className="text-h3 font-semibold">
                  What changed
                </h2>
                <ul className="mt-3 divide-y divide-border" data-testid="today-changes">
                  {d.changes.length === 0 && <li className="py-2 text-sm italic text-muted">No activity yet.</li>}
                  {d.changes.map((c) => (
                    <li key={c.id} className="flex items-start gap-3 py-3">
                      <Activity className="mt-0.5 h-4 w-4 shrink-0 text-eucalyptus-deep" aria-hidden="true" />
                      <div className="min-w-0 flex-1">
                        {c.property_id ? (
                          <Link to={`/app/properties/${c.property_id}`} className="text-sm font-semibold hover:underline underline-offset-4">
                            {c.summary}
                          </Link>
                        ) : (
                          <span className="text-sm font-semibold">{c.summary}</span>
                        )}
                        <div className="text-xs text-muted">
                          {c.actor_email ?? "System"} · {formatDate(c.created_at)}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </div>
        </>
      )}
    </>
  );
}
