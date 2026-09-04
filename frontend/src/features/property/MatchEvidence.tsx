import { ShieldOff } from "lucide-react";
import { useState } from "react";
import { Button } from "../../components/Button";
import { EvidenceState } from "../../components/EvidenceState";
import { FitRing } from "../../components/FitRing";
import { formatDate } from "../../lib/format";
import {
  coverageTri,
  fitTri,
  gateLabel,
  humanise,
  propertyApi,
  type PropertyDetail,
} from "../../lib/properties";

interface Props {
  p: PropertyDetail;
  busy: boolean;
  mutate: (
    fn: (journeyId: string) => Promise<PropertyDetail>,
    notice?: string,
  ) => Promise<void>;
}

/** Hard gates per rule, preference components, assessed fit beside coverage, versions and waivers. */
export function MatchEvidence({ p, busy, mutate }: Props) {
  const e = p.evaluation;
  const [waiving, setWaiving] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  if (!e) {
    return (
      <section
        aria-labelledby="gates-heading"
        className="card p-5"
        data-testid="match-not-evaluated"
      >
        <h2 id="gates-heading" className="text-h3 font-semibold">
          Hard rules and fit
        </h2>
        <p className="mt-2 text-sm text-muted">
          No published brief exists for this journey yet, so nothing has been
          evaluated. Publish the buying brief and every property will be
          assessed against that version.
        </p>
      </section>
    );
  }

  const submitWaiver = async (criterion: string) => {
    await mutate(
      (j) => propertyApi.addWaiver(j, p.id, criterion, reason),
      "Waiver recorded for this property only. The gate still shows its real outcome.",
    );
    setWaiving(null);
    setReason("");
  };

  return (
    <>
      <section
        aria-labelledby="gates-heading"
        className="card p-5"
        data-testid="match-gates"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="gates-heading" className="text-h3 font-semibold">
              Hard rules
            </h2>
            <p className="mt-1 text-sm text-muted" data-testid="match-verdict">
              {e.verdict === "fail" &&
                "A known hard-rule failure excludes this property from ordinary matches, however high the fit."}
              {e.verdict === "unknown" &&
                "At least one hard rule is Unknown, so this property is routed to verification. Unknown is not Pass."}
              {e.verdict === "pass" &&
                "Every enabled hard rule passes on the recorded facts."}
            </p>
          </div>
          <div className="flex flex-wrap gap-4">
            <FitRing
              value={fitTri(p)}
              label="Assessed fit"
              size={52}
              data-testid="detail-fit"
            />
            <FitRing
              value={coverageTri(p)}
              label="Evidence coverage"
              size={52}
              data-testid="detail-coverage"
            />
          </div>
        </div>
        <p className="mt-3 text-xs text-muted md:hidden" id="rules-scroll-hint">
          Scroll sideways to see every column.
        </p>
        <div
          className="-mx-5 mt-2 overflow-x-auto px-5"
          role="region"
          aria-label="Hard rules table"
          aria-describedby="rules-scroll-hint"
          tabIndex={0}
        >
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="label text-left">
                <th scope="col" className="py-2 pr-3 font-semibold">
                  Criterion
                </th>
                <th scope="col" className="py-2 pr-3 font-semibold">
                  Brief
                </th>
                <th scope="col" className="py-2 pr-3 font-semibold">
                  Observed
                </th>
                <th scope="col" className="py-2 pr-3 font-semibold">
                  Outcome
                </th>
                <th scope="col" className="py-2 font-semibold">
                  What would change it
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {e.gates.map((g) => {
                const waived = p.waived_criteria.includes(g.criterion);
                return (
                  <tr
                    key={g.criterion}
                    data-testid={`gate-row-${g.criterion}`}
                    data-outcome={g.outcome}
                  >
                    <th
                      scope="row"
                      className="py-2.5 pr-3 text-left font-medium align-top"
                    >
                      {g.label}
                      <div className="text-xs font-normal text-muted">
                        {g.source_label || "Address"}
                      </div>
                    </th>
                    <td className="py-2.5 pr-3 align-top text-charcoal">
                      {g.brief_value}
                    </td>
                    <td
                      className={
                        g.observed === "Unknown"
                          ? "py-2.5 pr-3 align-top italic text-muted"
                          : "py-2.5 pr-3 align-top"
                      }
                    >
                      {g.observed}
                    </td>
                    <td className="py-2.5 pr-3 align-top">
                      <EvidenceState outcome={gateLabel(g.outcome)} compact />
                      {waived && (
                        <span
                          className="mt-1 block text-xs font-semibold text-ochre-deep"
                          data-testid={`gate-waived-${g.criterion}`}
                        >
                          Waived by you · gate unchanged
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 align-top text-xs text-muted">
                      <div>{g.reason}</div>
                      {g.outcome !== "pass" && (
                        <div className="mt-1 text-charcoal">
                          {g.what_would_change}
                        </div>
                      )}
                      {g.outcome !== "pass" && !waived && (
                        <button
                          type="button"
                          onClick={() =>
                            setWaiving(
                              waiving === g.criterion ? null : g.criterion,
                            )
                          }
                          className="mt-1 text-xs font-semibold text-eucalyptus-deep hover:underline underline-offset-4"
                          data-testid={`gate-waive-${g.criterion}`}
                        >
                          Record a waiver for this property
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {waiving && (
          <form
            className="mt-4 rounded-md border border-ochre/40 bg-ochre-soft p-4"
            onSubmit={(ev) => {
              ev.preventDefault();
              void submitWaiver(waiving);
            }}
            data-testid="waiver-form"
          >
            <label
              htmlFor="waiver-reason"
              className="block text-sm font-semibold text-ochre-deep"
            >
              Why are you waiving “
              {e.gates.find((g) => g.criterion === waiving)?.label}” for this
              property only?
            </label>
            <p className="mt-1 text-xs text-ochre-deep">
              This never changes your published brief and never turns the gate
              into a Pass. It is recorded with your name and time.
            </p>
            <textarea
              id="waiver-reason"
              value={reason}
              onChange={(ev) => setReason(ev.target.value)}
              minLength={5}
              required
              rows={2}
              className="mt-2 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm"
              data-testid="waiver-reason"
            />
            <div className="mt-2 flex gap-2">
              <Button
                type="submit"
                size="sm"
                disabled={busy || reason.trim().length < 5}
                data-testid="waiver-submit"
              >
                Record waiver
              </Button>
              <Button
                type="button"
                size="sm"
                variant="tertiary"
                onClick={() => setWaiving(null)}
              >
                Cancel
              </Button>
            </div>
          </form>
        )}
        {p.waivers.length > 0 && (
          <ul
            className="mt-4 space-y-2"
            aria-label="Recorded waivers"
            data-testid="waiver-list"
          >
            {p.waivers.map((w) => (
              <li
                key={w.id}
                className="flex items-start gap-2 rounded-md bg-canvas px-3 py-2 text-sm"
              >
                <ShieldOff
                  className="mt-0.5 h-4 w-4 shrink-0 text-ochre-deep"
                  aria-hidden="true"
                />
                <div className="min-w-0 flex-1">
                  <span className="font-semibold">{humanise(w.criterion)}</span>{" "}
                  — {w.reason}
                  <div className="text-xs text-muted">
                    {w.actor_email} · {formatDate(w.created_at)}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    void mutate(
                      (j) => propertyApi.revokeWaiver(j, p.id, w.id),
                      "Waiver revoked.",
                    )
                  }
                  disabled={busy}
                  className="text-xs font-semibold text-risk hover:underline underline-offset-4"
                  data-testid={`waiver-revoke-${w.id}`}
                >
                  Revoke
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        aria-labelledby="fit-heading"
        className="card p-5"
        data-testid="match-components"
      >
        <h2 id="fit-heading" className="text-h3 font-semibold">
          Preference fit and evidence coverage
        </h2>
        <p className="mt-1 text-sm text-muted">
          Fit = achieved points ÷ maximum achievable for the assessed
          components. Coverage = assessed enabled weight ÷ total enabled weight.
          They are shown side by side and never blended. Fit is a preference
          measure, not a valuation.
        </p>
        <dl
          className="mt-3 grid gap-2 sm:grid-cols-2"
          data-testid="fit-summary"
        >
          <div className="rounded-md bg-canvas px-3 py-2 text-sm">
            <dt className="text-xs text-muted">Assessed fit</dt>
            <dd className="font-semibold" data-state={e.fit.state}>
              {e.fit.state === "known"
                ? `${e.fit.pct}% · ${e.fit.achieved} of ${e.fit.max_achievable} points`
                : "Fit unavailable — nothing could be assessed"}
            </dd>
          </div>
          <div className="rounded-md bg-canvas px-3 py-2 text-sm">
            <dt className="text-xs text-muted">Evidence coverage</dt>
            <dd className="font-semibold">
              {e.coverage.pct !== null
                ? `${e.coverage.pct}% · weight ${e.coverage.assessed_weight} of ${e.coverage.total_enabled_weight}`
                : "No enabled preferences"}
            </dd>
          </div>
        </dl>
        <div className="-mx-5 mt-4 overflow-x-auto px-5">
          <table className="w-full min-w-[480px] text-sm">
            <thead>
              <tr className="label text-left">
                <th scope="col" className="py-2 pr-3 font-semibold">
                  Component
                </th>
                <th scope="col" className="py-2 pr-3 font-semibold">
                  Weight
                </th>
                <th scope="col" className="py-2 pr-3 font-semibold">
                  Score
                </th>
                <th scope="col" className="py-2 font-semibold">
                  Why
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {e.components.map((c) => (
                <tr
                  key={c.name}
                  data-testid={`component-${c.name}`}
                  data-assessed={c.assessed}
                >
                  <th
                    scope="row"
                    className="py-2 pr-3 text-left font-medium align-top"
                  >
                    {humanise(c.name)}
                  </th>
                  <td className="py-2 pr-3 align-top">
                    {c.enabled ? c.weight : "Off"}
                  </td>
                  <td
                    className={
                      c.assessed
                        ? "py-2 pr-3 align-top"
                        : "py-2 pr-3 align-top italic text-muted"
                    }
                  >
                    {c.assessed
                      ? `${c.score} → ${c.points} / ${c.max_points}`
                      : c.enabled
                        ? "Not assessed"
                        : "Disabled"}
                  </td>
                  <td className="py-2 align-top text-xs text-muted">
                    {c.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-muted" data-testid="evaluation-meta">
          Brief version {e.brief_version_no} · {e.evaluation_version} · last
          recalculated {formatDate(e.computed_at)} · input hash{" "}
          <span className="break-all">{e.input_hash.slice(0, 12)}</span>
        </p>
      </section>
    </>
  );
}
