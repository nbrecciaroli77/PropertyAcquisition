import { StatusChip } from "../../components/StatusChip";
import { SETTING_KEYS, type AssessmentProfile, type CampaignConfig } from "../../lib/campaigns";
import { SETTING_LABELS, effectiveText, sourceChip } from "./settingFormat";

/** Read-only view: what this campaign runs with, and where each value comes from. */
export function EffectiveSettings({
  config,
  profiles,
  ownDefaults,
}: {
  config: CampaignConfig;
  profiles: AssessmentProfile[];
  ownDefaults: boolean;
}) {
  const tz = String(config.settings.timezone.effective);
  return (
    <section aria-labelledby="effective-heading" className="card min-w-0 p-5" data-testid="campaign-effective-settings">
      <h2 id="effective-heading" className="text-h3 font-semibold">
        Settings in force
      </h2>
      <p className="mt-1 text-sm text-muted">
        Each value is either overridden for this campaign or inherited — from your defaults, then the system default.
      </p>
      <dl className="mt-4 divide-y divide-border">
        {SETTING_KEYS.map((key) => {
          const s = config.settings[key];
          const chip = sourceChip(s.source, ownDefaults);
          const unavailable = key === "assessment_profile" && s.state === "unavailable";
          return (
            <div key={key} className="grid gap-1 py-3 sm:grid-cols-[180px_minmax(0,1fr)_auto] sm:items-start sm:gap-4" data-testid={`effective-${key}`}>
              <dt className="text-sm font-semibold text-navy">{SETTING_LABELS[key]}</dt>
              <dd className="min-w-0 text-sm">
                <span className={unavailable ? "font-semibold text-ochre-deep" : "text-charcoal"} data-testid={`effective-${key}-value`}>
                  {effectiveText(key, s, profiles, tz)}
                </span>
                {s.note && <span className="mt-1 block text-xs text-muted" data-testid={`effective-${key}-note`}>{s.note}</span>}
              </dd>
              <dd className="flex flex-wrap items-center gap-2 sm:justify-end">
                <StatusChip tone={chip.tone} hideIcon data-testid={`effective-${key}-source`}>
                  {chip.label}
                </StatusChip>
                <span className="text-xs text-muted" data-testid={`effective-${key}-source-detail`}>{chip.detail}</span>
              </dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}
