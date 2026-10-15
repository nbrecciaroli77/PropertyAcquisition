import { useState } from "react";
import { PageHeader } from "../../components/Page";
import { EmptyState, ErrorState, Skeleton } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";
import { useAuth } from "../../lib/auth";
import { campaignApi, layerFrom, SETTING_KEYS, type CampaignLayer, type SettingKey } from "../../lib/campaigns";
import { useJourneys } from "../../lib/journey";
import { CampaignKindIcon, campaignKindLabel } from "../../app/layout/CampaignSwitcher";
import { CampaignStatusControl } from "./CampaignStatusControl";
import { EffectiveSettings } from "./EffectiveSettings";
import { LayerForm } from "./LayerForm";
import { ScheduleSyncPanel } from "./ScheduleSyncPanel";
import { useCampaignData, type CampaignData } from "./useCampaignData";
import type { EditorOptions } from "./ValueEditor";
import { VersionHistory } from "./VersionHistory";

type Tab = "overrides" | "defaults";

export default function CampaignSettingsPage() {
  const { active, loading, reload: reloadJourneys } = useJourneys();
  const { data, error, reload } = useCampaignData(active?.id);

  if (!active) {
    if (loading) return <Skeleton className="h-56" label="Loading your campaign" />;
    return <EmptyState title="No buyer campaign yet" description="Create a campaign to configure it." data-testid="campaign-settings-none" />;
  }
  return (
    <>
      <PageHeader
        eyebrow="Campaign settings"
        title={active.name}
        description="Settings resolve in order: this campaign's override, then your defaults, then the system default."
        testId="campaign-settings-header"
        actions={<CampaignStatusControl journey={active} onChanged={async () => { await reloadJourneys(); await reload(); }} />}
      />
      <div className="mb-6 flex flex-wrap items-center gap-2" data-testid="campaign-identity">
        <StatusChip tone="info" hideIcon data-testid="campaign-kind-chip">
          <CampaignKindIcon kind={active.campaign_kind} className="h-3 w-3" /> {campaignKindLabel(active.campaign_kind)} campaign
        </StatusChip>
        <StatusChip tone={active.assessment_available ? "pass" : "warning"} hideIcon data-testid="campaign-assessment-chip">
          {active.assessment_available ? "Assessment available" : "Assessment: not yet available — planned for U2"}
        </StatusChip>
      </div>
      {error && <ErrorState title="Campaign settings could not be loaded" description={error} data-testid="campaign-settings-error" />}
      {!error && !data && <Skeleton className="h-96" label="Loading campaign settings" />}
      {data && <CampaignSettingsBody data={data} onSaved={async () => { await reload(); await reloadJourneys(); }} />}
    </>
  );
}

function CampaignSettingsBody({ data, onSaved }: { data: CampaignData; onSaved: () => Promise<void> }) {
  const { me } = useAuth();
  const { active } = useJourneys();
  const [tab, setTab] = useState<Tab>("overrides");
  const { config } = data;
  const ownDefaults = me?.user.id === config.settings_owner_user_id;
  const seeds = Object.fromEntries(SETTING_KEYS.map((k) => [k, config.settings[k].requested])) as Record<SettingKey, unknown>;
  const options = editorOptions(data, tab === "overrides" ? config.campaign_kind : null, me?.user.id, me?.user.display_name);

  const saveOverrides = async (layer: CampaignLayer, reason: string, expected: number) => {
    const saved = await campaignApi.saveOverrides(config.journey_id, { settings: layer, expected_version: expected, reason });
    await onSaved();
    return `Saved as campaign version ${saved.campaign_version}. No worker, delivery or integration was started.`;
  };
  const saveDefaults = async (layer: CampaignLayer, reason: string, expected: number) => {
    const saved = await campaignApi.saveDefaults({ settings: layer, expected_version: expected, reason });
    await onSaved();
    return `Saved your defaults as version ${saved.version}. Campaigns you created inherit them wherever they have no override.`;
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="min-w-0 space-y-6">
        <EffectiveSettings config={config} profiles={data.profiles} ownDefaults={ownDefaults} />
        <section aria-labelledby="edit-heading" className="card min-w-0 p-5" data-testid="campaign-edit">
          <h2 id="edit-heading" className="text-h3 font-semibold">Edit settings</h2>
          <div className="mt-3 inline-flex rounded-full bg-canvas-deep p-1" role="tablist" aria-label="Settings layer">
            {(["overrides", "defaults"] as Tab[]).map((t) => (
              <button key={t} type="button" role="tab" aria-selected={tab === t} onClick={() => setTab(t)} data-testid={`campaign-edit-tab-${t}`}
                className={`h-9 rounded-full px-4 text-sm font-semibold transition-colors duration-150 ${tab === t ? "bg-navy text-white" : "text-navy hover:bg-stone"}`}>
                {t === "overrides" ? `Overrides for ${active?.name ?? "this campaign"}` : "My defaults"}
              </button>
            ))}
          </div>
          <p className="mt-3 text-sm text-muted">
            {tab === "overrides"
              ? "Set a value here to override it for this campaign only. Inherit defers to your defaults."
              : "Your defaults apply to every campaign you created, unless that campaign overrides the setting."}
          </p>
          {tab === "overrides" ? (
            <LayerForm key="overrides" prefix="override" initial={layerFrom(data.versions[0]?.settings)} seeds={seeds} version={config.campaign_version} options={options} inheritLabel="Inherit" onSave={saveOverrides} />
          ) : (
            <LayerForm key="defaults" prefix="defaults" initial={layerFrom(data.defaults.settings)} seeds={seeds} version={data.defaults.version} options={options} inheritLabel="Not set" onSave={saveDefaults} />
          )}
        </section>
      </div>
      <div className="min-w-0 space-y-6">
        <ScheduleSyncPanel config={config} />
        <VersionHistory title="Campaign versions" versions={data.versions} testId="campaign-versions" />
        <VersionHistory title="My default versions" versions={data.defaultVersions} testId="default-versions" />
      </div>
    </div>
  );
}

function editorOptions(data: CampaignData, kind: string | null, myId?: string, myName?: string): EditorOptions {
  const recipient = data.config.settings.recipient_user_id;
  const recipients = myId ? [{ value: myId, label: `${myName ?? "Me"} (you)` }] : [];
  if (recipient.effective && recipient.effective !== myId) recipients.push({ value: String(recipient.effective), label: recipient.effective_label ?? "Campaign creator" });
  return {
    profiles: data.profiles
      .filter((p) => kind === null || p.campaign_kinds.includes(kind))
      .map((p) => ({ value: p.id, label: p.available ? p.label : `${p.label} — not yet available (U2)` })),
    connections: data.connectors
      .filter((c) => c.instance_id)
      .map((c) => ({ value: String(c.instance_id), label: `${c.display_name} · ${c.status_label}` })),
    recipients,
  };
}
