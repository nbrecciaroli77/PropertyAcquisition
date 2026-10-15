# U1 Report — Campaign configuration and isolation (uplift v2.0)

Date: 15 October 2026. Scope: **U1 only**. U2 (land assessment) not started.
Status at a glance:

| Area | Implemented | Tested | Deployed to live |
|---|---|---|---|
| Versioned user defaults + campaign overrides (7 settings) | Yes | Yes | **No** |
| Campaign-scoped report idempotency + legacy ID mapping (R1 fix) | Yes | Yes | **No** |
| Campaign/tenant isolation: receipts, cutoff, notifications, report history, export, duplicate review | Yes | Yes | **No** |
| Campaign selector + Campaign settings page (desktop + mobile) | Yes | Yes | **No** |
| `test_m5_2_privacy.py` cleanup defect (+ the same defect in `test_intake.py`) | Yes | Yes | n/a |
| Migration `d4e1f7a2b9c3` | Yes | Throwaway DB only: upgrade → downgrade → re-upgrade | **No — proposed, not executed (§10)** |
| Land assessment | Blocked by design (U2) | Shown as "Not yet available — planned for U2" | n/a |

## 1. Safety confirmations

- **Live Supabase unchanged.** No migration, downgrade, reset or seed touched it. At the end of U1 I ran
  SELECT-only queries against it: revision `c8d5e2f9a4b1`, 5 users, 5 workspaces, 4 journeys, 4 report runs,
  and the U1 table `campaign_config_versions` does not exist. (The pooler ignored the read-only session option,
  so the guarantee comes from only running SELECTs.)
- **ChatGPT prototype** was not opened or changed.
- **Throwaway database:** local PostgreSQL 17.11 at `127.0.0.1:5433/pa_u1_disposable` (self-signed TLS, because the
  app requires SSL). The preview backend points at it through the supervisor `DATABASE_URL`. `tests/conftest.py`
  refuses to run in-process tests against any non-local host. Every command in this report printed
  `TARGET: 127.0.0.1:5433/pa_u1_disposable` before running.
- The pod restarted once during U1 and wiped the throwaway cluster (it lives outside `/app`). It was rebuilt
  with `bash memory/u1_disposable_db.sh`, which refuses any host other than 127.0.0.1.
- No credentials or private data are in this report or the screenshots. All data is synthetic.

## 2. Requirement mapping

| Requirement | Where |
|---|---|
| Buyer campaign boundary | `journeys.campaign_kind` (`house`/`land`), `journeys.campaign_enabled`; API `POST /api/journeys {campaign_kind}`, `PATCH … {campaign_enabled}` (audited) |
| Versioned user defaults | `campaign_config_versions` (scope `user_default`); `GET/PUT /api/campaign-defaults`, `GET /api/campaign-defaults/versions` |
| Versioned campaign overrides | same table (scope `campaign`); `PUT /api/journeys/{id}/campaign/overrides`, `GET …/campaign/versions`; immutable rows, required reason, optimistic `expected_version` (409 `stale_configuration`) |
| Effective settings | `services/campaigns.resolve()`: campaign override → the campaign creator's default → system default. Requested and effective values are reported separately, along with their source |
| Assessment profile | `HOUSE_V1` (available), `LAND_FEASIBILITY_V1` (known but unavailable). Mismatched or unknown profiles are rejected with 422. If the profile is unavailable, matching is skipped (`reevaluation_state = skipped_profile_unavailable`); house rules and scores are never substituted |
| Activation time | Must carry a timezone offset. Blocks production runs until activation, and blocks periods ending before activation. Previews are unaffected |
| Timezone | IANA-validated. Drives report periods and cutoffs (`effective_timezone`) |
| Intake connection reference | Must be a connector instance in the same workspace. Stored as a reference only; connectors stay disabled |
| Recipient | Must be a workspace member. Falls back to the campaign creator |
| Delivery mode | `combined` can be requested but takes effect as `separate` until U6 |
| Cadence | Daily/weekly/monthly with validation. Scheduler sync is reported separately; `PRODUCTION_SCHEDULER_ENABLED = False`, so no worker is ever started |
| R1 report idempotency + lookup | `services/reports.generate_report`: key `c1:<journey>:<type>:<mode>:<period>:<version>`, unique `(workspace_id, journey_id, idempotency_key)`, `INSERT … ON CONFLICT DO NOTHING` plus a row lock so concurrent requests produce one row |
| Preserve historical report IDs | `report_run_legacy_mappings` maps each pre-U1 run to its recorded journey. A legacy run is reused only through that mapping. `GET /api/reports/runs/{id}/location` resolves old `?run=` links |
| Receipts (intake) | Duplicate checks are per campaign; same address in another campaign = independent record. The pasted-text receipt key is campaign-scoped (the legacy key is honoured only within its own campaign). A disabled campaign returns 409 for intake and CSV |
| Cutoff | Uses the effective campaign timezone; production coverage starts at activation |
| Notifications | `notification_events.journey_id` (backfilled only from rows in the same workspace); deep links carry `?campaign=` |
| Report history | Lists and reads are journey-scoped. Weekly/monthly duplicate, withdrawn and funnel counts are campaign-scoped |
| Export | Workspace export includes `campaign_config_versions.json` and `report_run_legacy_mappings.json` |
| Duplicate review | Scans never pair properties from different campaigns. `create_proposal`/`confirm_merge` refuse cross-campaign pairs. List filter `?journey_id=` |
| Tenant isolation | Every campaign route uses `scoped_journey`; another tenant's IDs return 404 (never 403) |
| Campaign selector UI | `app/layout/CampaignSwitcher.tsx` (top bar, desktop + mobile) |
| Effective-settings UI | `/app/campaign` (`features/campaign/*`): read-only "Settings in force" with Overridden/Inherited chips, separate Scheduler synchronisation card, "Edit overrides" and "My defaults" forms on the same page, version histories, Pause/Resume |
| Switching clears campaign data | Pages remount when the active campaign changes (`useCampaignEpoch`); the compare selection is cleared; property detail pages redirect to Pipeline; query state is dropped |
| Synthetic house + land campaigns | `scripts/seed.py` adds "Synthetic down-south land" (2 listings, one deliberately sharing a house-fixture address). Throwaway DB only |
| `test_m5_2_privacy.py` cleanup | Domain-wide deletes replaced by the shared exact-identity registry in `conftest.py`, applied per test (including failed tests) |

## 3. Migration

- **ID:** `d4e1f7a2b9c3_u1_campaign_configuration_isolation` (revises `c8d5e2f9a4b1`, the current live revision).
  It only adds columns, tables and constraints; existing report IDs and keys are never changed.
- **Fix made during U1:** after a downgrade, re-upgrading relabelled U1-created runs as `workspace_legacy`. The
  upgrade now marks `c1:<journey>:` keys as `campaign` and maps only genuine legacy rows.
- **Downgrade is fail-closed.** It refuses, without changing anything, if any address exists in two
  campaigns of one workspace or any report keys would collide.

Evidence (throwaway DB; pre-U1 code taken from commit `32bf41d`):

| Step | Result |
|---|---|
| Pre-U1 schema + seed, then pre-U1 code generates reports for two journeys in one workspace | **R1 reproduced** 3/3: the second journey got the first journey's run (`collided=True` for daily, weekly and monthly) |
| `alembic upgrade head` → `d4e1f7a2b9c3` | 3 legacy runs kept their IDs and keys, scope `workspace_legacy`, mapped with basis `recorded_journey_same_workspace`; notification attribution 5/5 |
| U1 code, same request | House replays return the 3 historical IDs; the second journey gets 3 **new, separate** runs (scope `campaign`) |
| `alembic downgrade c8d5e2f9a4b1` | OK. All 6 runs kept, 21 properties kept, U1 tables dropped, old unique constraints restored |
| `alembic upgrade head` (×2 cycles) | OK. After the fix: 3 legacy runs mapped, 3 U1 runs scope `campaign` |
| Downgrade attempted after the land seed (shared address) | **Blocked**: "1 address(es) exist in more than one campaign … No data was changed"; revision stays `d4e1f7a2b9c3` |
| Pre-U1 code against the U1 schema (`memory/u1_rollback_rehearsal.py`, rolled back) | Report generation, intake and journey insert all work, so the code can be rolled back alone (§10) |

## 4. Historical-data compatibility

- Existing journeys become `house` and enabled. Existing report runs keep their exact ID and key; their history,
  `ready_to_send` snapshots and links stay valid.
- Old links `/app/reports?type=…&run=<id>` (no campaign) resolve through the location endpoint and open in the
  owning campaign. A run that isn't mapped is never reused and never located.
- On the house campaign, legacy runs show the label "Historical run · ID preserved".
- Pasted-text receipts recorded before U1 still replay inside their own campaign.

## 5. Tests (all on the throwaway DB)

Environment: `DATABASE_URL=<throwaway> APP_ENV=development M4_2_VERIFY_ISOLATED_DB=1 M5_1_VERIFY_ISOLATED_DB=1 REACT_APP_BACKEND_URL=<preview>`

| Command | Result |
|---|---|
| `pytest tests/test_u1_report_collision.py tests/test_u1_campaigns.py` | **15 passed**. One U1 test-fixture defect was fixed (the land brief draft lacked the required `land_sqm.min`); no assertion was weakened |
| `pytest tests/test_m5_2_privacy.py tests/test_u1_*.py tests/test_intake.py tests/test_rate_limit.py` | **45 passed**. Users/workspaces/journeys/properties/report runs: `3/3/4/23/3` before and after, so cleanup is verified |
| `pytest tests` (full) | **227 passed, 16 failed, 11 errors.** Every failure is pre-existing or environmental (below) |
| `yarn typecheck` | Pass |
| `yarn test` (Jest) | **56 passed, 2 failed.** The 2 failures are identical to the pre-U1 baseline, which I re-ran at `32bf41d` (53 passed, the same 2 failed) |
| `yarn build` | Pass (2 pre-existing eslint warnings, same as baseline) |
| Testing agent (`test_reports/iteration_11.json`) | Frontend 17/17 items pass; cross-tenant 404s pass; no issues raised |

Pre-existing failures, reported separately and not changed:
- `test_m2_public` (12 failed + 10 errors) and `test_m3_public::TestReevaluation` (1 error): these need public signup,
  which the preview disables (`SIGNUP_ENABLED=false`, 403 `signup_disabled`).
- `test_m2_public::test_openapi_has_no_unsafe_or_value_score_paths`: the word "scraped" comes from the existing
  intake schema docstring ("Never fetched or scraped"). Present at `32bf41d`.
- `test_system::test_no_forbidden_pathways_exist`: the word "send" in the M6.1 route `/ready-to-send`. Present at `32bf41d`.
- `test_m3a_foundation::test_migration_head_is_m3a` and `test_m4_2_migration_rollback`: both expect an old fixed
  migration revision (`2105faf7bef7` / `a8d2e3f4b5c6`). The rollback test fails before running any downgrade.
- Jest `auth.test` (copy text changed in M6.2) and `shell.test` (rail order).

Test-cleanup defects fixed: `test_m5_2_privacy.py` (per the handoff) and `test_intake.py`. The latter wrote into the
seeded owner/other accounts and could not be re-run; it now uses tracked synthetic tenants.

## 6. Screenshots (`docs/uplift/U1-screenshots/`)

Desktop 1920×800: `U1-desktop-1-campaign-selector`, `-2-land-pipeline-isolated`, `-3-land-campaign-settings`,
`-4-edit-defaults-saved`, `-5-inherited-from-defaults`, `-6-house-reports-historical`.
Mobile 390×844: `U1-mobile-1-campaign-selector`, `-2-land-campaign-settings`, `-3-scheduler-sync` (no horizontal overflow).
The defaults change shown in screenshots 4 and 5 was a demo; the throwaway DB was rebuilt afterwards.

## 7. Changed files

- Migration: `backend/alembic/versions/d4e1f7a2b9c3_u1_campaign_configuration_isolation.py`
- Backend new: `app/api/campaigns.py`, `app/schemas/campaigns.py`, `app/services/campaigns.py`
- Backend changed: `app/db/models.py`, `app/main.py`; `app/api/{csv_intake,duplicates,intake,journeys,notifications,properties,reports,tasks}.py`;
  `app/schemas/{journeys,notifications,reports}.py`; `app/services/{duplicates,exports,intake,notifications,properties,reminders,reports}.py`; `scripts/seed.py`
- Backend tests: new `tests/test_u1_campaigns.py`, `tests/test_u1_report_collision.py`; changed `tests/conftest.py`,
  `tests/test_intake.py`, `tests/test_m5_2_privacy.py`, `tests/test_rate_limit.py`
- Frontend new: `app/layout/CampaignSwitcher.tsx`, `app/layout/CampaignShell.tsx`, `lib/campaigns.ts`,
  `features/campaign/*` (11 files), `features/settings/CampaignsSection.tsx`, `__tests__/u1_campaigns.test.tsx`
- Frontend changed: `app/layout/{AppShell,TopBar}.tsx`, `app/router.tsx`, `lib/{api,duplicates,journey,notifications,reports}.ts(x)`,
  `features/{duplicates/DuplicatesPage,journeys/NewJourneyPage,more/MorePage,notifications/NotificationCenterPage,reports/ReportsPage,settings/SettingsPage}.tsx`,
  `test/helpers.tsx`, `__tests__/m4_2.test.tsx`
- Ops/docs: `memory/u1_disposable_db.sh`, `memory/u1_rollback_rehearsal.py`, `memory/test_credentials.md`,
  `.emergent/system_deps.txt` (postgresql-17), this report and its screenshots

## 8. Known limitations

- Land assessment is unavailable until U2: land properties are recorded with "Not evaluated" and Unknown fit.
- Scheduled report jobs are still per workspace. Per-campaign cadence is stored, and differences are shown as
  "drift", but jobs are only reconciled when production scheduling is activated (U7). No worker runs.
- Combined delivery takes effect as separate until U6. The intake connection is a reference only.
- Recipient choices are limited to existing members (only the owner; invitations are not built).
- After any campaign-specific data exists (for example, the same address in two campaigns), a schema downgrade is
  intentionally blocked. Use the code-only rollback instead (§10).
- The preview backend currently runs on the throwaway DB. A pod restart wipes that DB (rebuild with the script). If the
  platform resets the supervisor config, the preview would point at live Supabase with U1 code and U1 endpoints would
  fail on the missing schema. Nothing applies a migration automatically.
- In Jest, Radix menus take about 18 s to mount (the account menu does the same); one U1 test uses a 60 s timeout.

## 9. Checks not run

- Live `alembic upgrade`, live deploy, and any live smoke test after deployment (awaiting approval).
- A Supabase backup/restore rehearsal (this needs dashboard access; still unverified since U0).
- Concurrency under real network load beyond the in-process concurrent-generation test.

## 10. Proposed live deployment step (NOT executed — for owner review)

Pre-flight
1. Owner approves U1 and uses **Save to GitHub**; record the commit SHA.
2. Confirm in the Supabase dashboard (Database → Backups) that there is a backup less than 24 h old. Also take a logical
   dump from a trusted machine: `pg_dump --format=custom --no-owner -f pa-pre-u1.dump "$LIVE_DATABASE_URL"` (keep it out of the repo).
3. SELECT-only pre-checks on live: `alembic_version = c8d5e2f9a4b1`; zero rows from
   `select workspace_id, normalised_address from properties group by 1,2 having count(*)>1`; record
   `select id, journey_id, idempotency_key from report_runs` (4 rows today) and `count(*)` of `notification_events`.

Deploy, in this order (rehearsed: the current production code runs unchanged on the U1 schema)
4. `cd backend && DATABASE_URL=<live> alembic upgrade d4e1f7a2b9c3`. It is one revision with transactional DDL; it only adds columns, tables and constraints.
5. Verify: `alembic current` = `d4e1f7a2b9c3`; the same report IDs and keys, all `workspace_legacy` and mapped; every journey `house` and enabled.
6. Point the preview backend back at live (remove the supervisor `DATABASE_URL` override) and redeploy the U1 code through Emergent.
   Do **not** run `scripts/seed.py` on live: the land campaign is demo-only. The owner can create one in the UI.
7. Live smoke: `/api/health` and `/api/readiness` return 200; owner signs in; selector shows the existing campaign;
   `/app/campaign` loads; the historical report IDs open; signup still 403; dev outbox still 404; no scheduler or integration enabled.

Recovery plan
- **Tier 1 (preferred, no data loss):** redeploy the previous production build and leave the schema at `d4e1f7a2b9c3`.
  The pre-U1 code was rehearsed on the U1 schema. Side effect: the R1 collision returns for new report runs only.
- **Tier 2:** `alembic downgrade c8d5e2f9a4b1`. Use this only before any U1-specific data exists. It refuses if
  addresses are shared across campaigns or keys would collide. It removes campaign settings, legacy mappings and
  campaign attribution on notifications.
- **Tier 3:** restore from the pre-flight dump or the Supabase backup.

## 11. Actions for the owner

1. Review this report and the screenshots.
2. Use **Save to GitHub** to publish the U1 code and report; that step gives you the commit ID.
3. Decide whether to approve the live step in §10, and confirm the Supabase backup first.
4. Credits used for U1: not available to me.
