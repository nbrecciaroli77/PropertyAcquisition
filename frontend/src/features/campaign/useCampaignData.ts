import { useCallback, useEffect, useState } from "react";
import { campaignApi, type AssessmentProfile, type CampaignConfig, type ConfigVersion, type UserDefaults } from "../../lib/campaigns";
import { sourcesApi, type ConnectorItem } from "../../lib/sources";

export interface CampaignData {
  config: CampaignConfig;
  versions: ConfigVersion[];
  defaults: UserDefaults;
  defaultVersions: ConfigVersion[];
  profiles: AssessmentProfile[];
  connectors: ConnectorItem[];
}

/** Everything the campaign settings page reads, scoped to one campaign. */
export function useCampaignData(journeyId: string | undefined) {
  const [data, setData] = useState<CampaignData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!journeyId) return;
    try {
      const [config, versions, defaults, defaultVersions, profiles, connectors] = await Promise.all([
        campaignApi.config(journeyId),
        campaignApi.versions(journeyId),
        campaignApi.defaults(),
        campaignApi.defaultVersions(),
        campaignApi.profiles(),
        sourcesApi.listConnectors().then((r) => r.items).catch(() => [] as ConnectorItem[]),
      ]);
      setData({ config, versions, defaults, defaultVersions, profiles, connectors });
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Campaign settings could not be loaded.");
    }
  }, [journeyId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, error, reload };
}
