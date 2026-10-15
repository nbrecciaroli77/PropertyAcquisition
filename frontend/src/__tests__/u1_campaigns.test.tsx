import userEvent from "@testing-library/user-event";
import type { Journey } from "../lib/api";
import type { CampaignConfig, EffectiveSetting, SettingKey } from "../lib/campaigns";
import { BRIEF, JOURNEY, OWNER_ME, TODAY_EMPTY, mockApi, renderAt, screen, waitFor } from "../test/helpers";

const LAND: Journey = {
  ...JOURNEY,
  id: "44444444-4444-4444-4444-444444444444",
  name: "Synthetic down-south land",
  campaign_kind: "land",
  assessment_profile: "LAND_FEASIBILITY_V1",
  assessment_available: false,
};

const setting = (source: EffectiveSetting["source"], value: unknown, extra: Partial<EffectiveSetting> = {}): EffectiveSetting => ({
  override: source === "campaign_override" ? value : "INHERIT",
  user_default: source === "user_default" ? value : "INHERIT",
  requested: value,
  source,
  effective: value,
  state: "ok",
  note: null,
  effective_label: null,
  ...extra,
});

const CADENCE = {
  daily: { enabled: true, local_time: "07:00", weekdays: [0, 2, 4] },
  weekly: { enabled: true, local_time: "19:00", day_of_week: 6 },
  monthly: { enabled: true, local_time: "07:00", day_of_month: 1 },
};

const LAND_CONFIG: CampaignConfig = {
  journey_id: LAND.id,
  campaign_kind: "land",
  campaign_enabled: true,
  settings_owner_user_id: OWNER_ME.user.id,
  campaign_version: 1,
  user_default_version: 1,
  settings: {
    assessment_profile: setting("campaign_override", "LAND_FEASIBILITY_V1", { effective: null, state: "unavailable" }),
    activation_at: setting("system_default", null, { state: "not_activated" }),
    timezone: setting("user_default", "Australia/Sydney"),
    intake_connection_ref: setting("system_default", null, { state: "none" }),
    recipient_user_id: setting("system_default", OWNER_ME.user.id, { effective_label: "Nick", state: "member" }),
    delivery_mode: setting("campaign_override", "separate"),
    cadence: setting("system_default", CADENCE, { effective: null, state: "not_scheduled" }),
  } as Record<SettingKey, EffectiveSetting>,
  schedule: (["daily", "weekly", "monthly"] as const).map((report_type) => ({
    report_type, requested_cron: null, configured_cron: null, configured_enabled: false, config_drift: false,
    effective_cron: null, next_due_at: null, sync_state: "awaiting_activation",
  })),
  production_scheduler_enabled: false,
  resolved_at: "2026-10-15T00:00:00Z",
};

const landHandlers = {
  "/api/journeys": { body: [JOURNEY, LAND] },
  [`/api/journeys/${LAND.id}/brief`]: { body: { ...BRIEF, journey: LAND } },
  [`/api/journeys/${LAND.id}/today`]: { body: { ...TODAY_EMPTY, journey_id: LAND.id } },
  [`/api/journeys/${LAND.id}/properties`]: { body: [] },
  [`/api/journeys/${LAND.id}/campaign/versions`]: { body: [] },
  [`/api/journeys/${LAND.id}/campaign`]: { body: LAND_CONFIG },
  "/api/campaign-defaults/versions": { body: [] },
  "/api/campaign-defaults": { body: { version: 1, settings: { timezone: "Australia/Sydney" } } },
  "/api/assessment-profiles": {
    body: [
      { id: "HOUSE_V1", label: "House acquisition v1", campaign_kinds: ["house"], available: true, engine_version: "gates_v1", note: "" },
      { id: "LAND_FEASIBILITY_V1", label: "Land feasibility v1", campaign_kinds: ["land"], available: false, engine_version: null, note: "" },
    ],
  },
  "/api/sources/connectors": { body: { items: [], total: 0 } },
};

describe("U1 campaign selector and settings", () => {
  beforeEach(() => {
    localStorage.clear();
    mockApi(landHandlers);
  });

  it("switching campaigns changes the active campaign and clears campaign-specific selections", async () => {
    localStorage.setItem("pa.journey", JOURNEY.id);
    localStorage.setItem("pa.compare", JSON.stringify(["house-property-1"]));
    renderAt("/app/today");
    expect(await screen.findByTestId("campaign-switcher-active-name")).toHaveTextContent(JOURNEY.name);
    expect(screen.queryByTestId("campaign-assessment-unavailable")).not.toBeInTheDocument();

    const user = userEvent.setup({ pointerEventsCheck: 0 });
    screen.getByTestId("campaign-switcher").focus();
    await user.keyboard("{Enter}");
    // Radix menu content mounts slowly under jsdom (the account menu behaves the same).
    await user.click(await screen.findByTestId(`campaign-option-${LAND.id}`, {}, { timeout: 45000 }));

    await waitFor(() => expect(screen.getByTestId("campaign-switcher-active-name")).toHaveTextContent(LAND.name));
    expect(localStorage.getItem("pa.journey")).toBe(LAND.id);
    expect(JSON.parse(localStorage.getItem("pa.compare") ?? "null")).toEqual([]);
    expect(screen.getByTestId("campaign-assessment-unavailable")).toHaveTextContent("not yet available — planned for U2");
  }, 60000);

  it("a ?campaign= deep link opens the owning campaign", async () => {
    localStorage.setItem("pa.journey", JOURNEY.id);
    renderAt(`/app/today?campaign=${LAND.id}`);
    await waitFor(() => expect(screen.getByTestId("campaign-switcher-active-name")).toHaveTextContent(LAND.name));
  });

  it("campaign settings label each value as overridden or inherited and keep land assessment blocked", async () => {
    localStorage.setItem("pa.journey", LAND.id);
    renderAt("/app/campaign");
    expect(await screen.findByTestId("campaign-effective-settings")).toBeInTheDocument();
    expect(screen.getByTestId("effective-timezone-source")).toHaveTextContent("Inherited");
    expect(screen.getByTestId("effective-timezone-source-detail")).toHaveTextContent("From your defaults");
    expect(screen.getByTestId("effective-delivery_mode-source")).toHaveTextContent("Overridden");
    expect(screen.getByTestId("effective-activation_at-source-detail")).toHaveTextContent("System default");
    expect(screen.getByTestId("effective-assessment_profile-value")).toHaveTextContent("Not yet available — planned for U2");
    expect(screen.getByTestId("schedule-worker-state")).toHaveTextContent("never activates a worker");
    expect(screen.getByTestId("schedule-daily-state")).toHaveTextContent("Waiting for activation");
    expect(screen.getByTestId("override-save")).toBeDisabled();
  });
});
