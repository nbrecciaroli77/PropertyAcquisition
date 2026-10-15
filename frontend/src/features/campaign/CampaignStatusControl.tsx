import { Button } from "../../components/Button";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { StatusChip } from "../../components/StatusChip";
import { journeyApi, type Journey } from "../../lib/api";

/** Pausing blocks new intake and production reports; history stays readable. */
export function CampaignStatusControl({ journey, onChanged }: { journey: Journey; onChanged: () => Promise<void> }) {
  const pause = journey.campaign_enabled;
  const toggle = async () => {
    await journeyApi.update(journey.id, { expected_row_version: journey.row_version, campaign_enabled: !pause });
    await onChanged();
  };
  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusChip tone={pause ? "pass" : "warning"} hideIcon data-testid="campaign-enabled-state">
        {pause ? "Enabled" : "Paused"}
      </StatusChip>
      <ConfirmDialog
        title={pause ? "Pause this campaign?" : "Resume this campaign?"}
        description={
          pause
            ? "New intake and production reports are blocked while paused. Existing properties, reports and history stay readable. Nothing else changes."
            : "The campaign accepts new intake again. No worker, delivery or integration is started."
        }
        confirmLabel={pause ? "Pause campaign" : "Resume campaign"}
        destructive={pause}
        onConfirm={() => void toggle()}
        trigger={
          <Button variant="secondary" size="sm" data-testid="campaign-toggle-enabled">
            {pause ? "Pause campaign" : "Resume campaign"}
          </Button>
        }
      />
    </div>
  );
}
