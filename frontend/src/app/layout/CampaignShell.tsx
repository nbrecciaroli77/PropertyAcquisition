import { CirclePause, LandPlot } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useJourneys } from "../../lib/journey";

/** Honours ?campaign=<id> on deep links (notifications, reports) once per distinct value. */
export function CampaignParamSync() {
  const [params] = useSearchParams();
  const { journeys, active, setActiveId } = useJourneys();
  const wanted = params.get("campaign");
  const handled = useRef<string | null>(null);
  useEffect(() => {
    if (!wanted || journeys.length === 0 || handled.current === wanted) return;
    handled.current = wanted;
    if (wanted !== active?.id && journeys.some((j) => j.id === wanted)) setActiveId(wanted);
  }, [wanted, journeys, active, setActiveId]);
  return null;
}

/** States that change what a campaign may do, shown on every screen of that campaign. */
export function CampaignNotice() {
  const { active } = useJourneys();
  if (!active) return null;
  return (
    <>
      {!active.assessment_available && (
        <div role="note" className="flex items-start gap-2 border-b border-navy/15 bg-navy-soft px-4 py-2 text-xs text-navy md:px-6 lg:px-8" data-testid="campaign-assessment-unavailable">
          <LandPlot className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>
            <strong className="font-semibold">Land assessment: not yet available — planned for U2.</strong> Properties in
            this campaign keep their evidence but are not assessed. House rules, gates and fit scores are never applied.{" "}
            <Link to="/app/campaign" className="font-semibold underline underline-offset-2" data-testid="campaign-notice-settings-link">
              Campaign settings
            </Link>
          </span>
        </div>
      )}
      {!active.campaign_enabled && (
        <div role="note" className="flex items-start gap-2 border-b border-ochre/40 bg-ochre-soft px-4 py-2 text-xs text-ochre-deep md:px-6 lg:px-8" data-testid="campaign-paused-notice">
          <CirclePause className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>
            <strong className="font-semibold">This campaign is paused.</strong> New intake and production reports are
            blocked; its history stays readable.
          </span>
        </div>
      )}
    </>
  );
}
