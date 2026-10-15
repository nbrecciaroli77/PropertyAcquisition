import { ButtonLink } from "../../components/Button";
import { StatusChip } from "../../components/StatusChip";
import { CampaignKindIcon, campaignKindLabel } from "../../app/layout/CampaignSwitcher";
import { useJourneys } from "../../lib/journey";

/** Every buyer campaign in this workspace, each with its own settings. */
export function CampaignsSection() {
  const { journeys, active } = useJourneys();
  return (
    <section aria-labelledby="campaigns-heading" className="card min-w-0 p-5" data-testid="settings-campaigns">
      <h2 id="campaigns-heading" className="text-h3 font-semibold">
        Buyer campaigns
      </h2>
      <p className="mt-1 text-sm text-muted">
        Each campaign keeps its own properties, reports and settings. Your defaults apply wherever a campaign has no override.
      </p>
      <ul className="mt-3 divide-y divide-border text-sm">
        {journeys.map((j) => (
          <li key={j.id} className="flex flex-wrap items-center justify-between gap-2 py-3" data-testid={`settings-campaign-${j.id}`}>
            <span className="flex min-w-0 items-center gap-2">
              <CampaignKindIcon kind={j.campaign_kind} className="h-4 w-4 shrink-0 text-eucalyptus-deep" />
              <span className="min-w-0">
                <span className="block truncate font-semibold">{j.name}</span>
                <span className="block text-xs text-muted">
                  {campaignKindLabel(j.campaign_kind)} · {j.campaign_enabled ? "enabled" : "paused"}
                  {j.assessment_available ? "" : " · assessment not yet available (U2)"}
                </span>
              </span>
            </span>
            <span className="flex items-center gap-2">
              {active?.id === j.id && <StatusChip tone="shortlisted" hideIcon>Current</StatusChip>}
              <ButtonLink to={`/app/campaign?campaign=${j.id}`} variant="secondary" size="sm" data-testid={`settings-campaign-open-${j.id}`}>
                Settings
              </ButtonLink>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
