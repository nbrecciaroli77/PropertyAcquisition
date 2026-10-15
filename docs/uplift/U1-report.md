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
| Closeout: preview database guard (fails closed, never migrates) | Yes | Yes: isolated tests + a real pod restart (§12) | **No** |
| Closeout: meaningful house duplicate-count assertion | Yes | Yes | n/a |
| Closeout: failure register | Yes (§13) | Baseline re-run at `32bf41d` | n/a |

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
| `yarn test` (Jest) | **56 passed, 2 failed** in the final run (that run's log was not kept). The saved `test_reports/pytest/u1_jest.log` (12:09) is an earlier mid-development run with 16 failures, so it does not match this row; see §13 F7 |
| `yarn build` | Pass (2 eslint warnings, also present at baseline) |
| Testing agent (`test_reports/iteration_11.json`) | Frontend 17/17 items pass; cross-tenant 404s pass; no issues raised |

The full-suite failures are classified with evidence in §13. Closeout commands and results are in §12.4.

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
- Closeout pass: new `backend/app/core/db_guard.py`, `backend/tests/test_u1_db_guard.py`; changed `backend/app/main.py`,
  `backend/app/db/base.py`, `backend/app/api/system.py` (readiness), `backend/alembic/env.py`, `backend/tests/conftest.py`,
  `backend/tests/test_u1_campaigns.py`, `memory/u1_disposable_db.sh`, this report. Local only (not in the repository):
  `backend/.env` (+`DATABASE_TARGET=disposable`) and `/etc/supervisor/conf.d/u1_disposable_pg.conf`. Logs:
  `test_reports/pytest/u1_closeout_*.log`

## 8. Known limitations

- Land assessment is unavailable until U2: land properties are recorded with "Not evaluated" and Unknown fit.
- Scheduled report jobs are still per workspace. Per-campaign cadence is stored, and differences are shown as
  "drift", but jobs are only reconciled when production scheduling is activated (U7). No worker runs.
- Combined delivery takes effect as separate until U6. The intake connection is a reference only.
- Recipient choices are limited to existing members (only the owner; invitations are not built).
- After any campaign-specific data exists (for example, the same address in two campaigns), a schema downgrade is
  intentionally blocked. Use the code-only rollback instead (§10).
- The preview backend runs on the throwaway DB. A pod restart wipes that DB and its PostgreSQL install. After the
  closeout pass, the preview fails closed in that case (503) and never falls back to live Supabase (§12).
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
4. From a trusted operator shell, not the preview pod's configuration, with both values passed to that one process only:
   `cd backend && DATABASE_TARGET=live DATABASE_URL=<live> alembic upgrade d4e1f7a2b9c3`. Since the U1 closeout guard,
   Alembic refuses to run unless `DATABASE_TARGET` matches the URL. Never put `DATABASE_TARGET=live` in the preview's
   `backend/.env` or supervisor config. It is one revision with transactional DDL; it only adds columns, tables and
   constraints. (Corrected during U2; if U2 is also approved, see `U2-report.md` §8 for its follow-on revision.)
5. Verify: `alembic current` = `d4e1f7a2b9c3`; the same report IDs and keys, all `workspace_legacy` and mapped; every journey `house` and enabled.
6. Set the production configuration on its own, in the Emergent deployment secrets, never in the preview's
   `backend/.env`: `DATABASE_TARGET=live` plus the live `DATABASE_URL`. Without `DATABASE_TARGET=live` the U1 build
   refuses to start (§12), which is intended. Then deploy the U1 code through Emergent.
   Do **not** run `scripts/seed.py` on live: the land campaign is demo-only. The owner can create one in the UI.
7. Live smoke: `/api/readiness` returns 200 `{"status":"ready"}`. A 503 with `reason` `schema_incompatible` means step 4
   didn't apply; stop and use Tier 1. `/api/health` returns 200; owner signs in; selector shows the existing campaign;
   `/app/campaign` loads; the historical report IDs open; signup still 403; dev outbox still 404; no scheduler or integration enabled.
8. Keep the preview on the throwaway DB (`DATABASE_TARGET=disposable`). Pointing the preview at live is a separate decision.

Recovery plan
- **Tier 1 (preferred, no data loss):** redeploy the previous production build and leave the schema at `d4e1f7a2b9c3`.
  The pre-U1 code was rehearsed on the U1 schema. Side effect: the R1 collision returns for new report runs only.
- **Tier 2:** `alembic downgrade c8d5e2f9a4b1`. Use this only before any U1-specific data exists. It refuses if
  addresses are shared across campaigns or keys would collide. It removes campaign settings, legacy mappings and
  campaign attribution on notifications.
- **Tier 3:** restore from the pre-flight dump or the Supabase backup.

## 11. Actions for the owner (see §14 for the closeout status)

1. Review this report and the screenshots.
2. Use **Save to GitHub** to publish the U1 code and report; that step gives you the commit ID.
3. Decide whether to approve the live step in §10, and confirm the Supabase backup first.
4. Credits used for U1: not available to me.


## 12. Closeout: preview database guard

### 12.1 What it does
`backend/app/core/db_guard.py` checks the database target before any connection is opened. It never runs a migration.

| Condition | Result |
|---|---|
| `DATABASE_TARGET` missing or not `disposable`/`live` | Backend refuses to start (`DatabaseTargetError`) |
| `DATABASE_URL` missing | Refuses to start |
| `DATABASE_TARGET=disposable` and the host is not 127.0.0.1/localhost/::1 (for example, the supervisor override was reset and only the live URL in `.env` is left) | Refuses to start. Alembic (`alembic/env.py`), `scripts/seed.py` and every `get_engine()` caller refuse in the same way |
| `DATABASE_TARGET=live` and a loopback host | Refuses to start |
| Database unreachable, `alembic_version` missing, or revision ≠ code head (`d4e1f7a2b9c3`) | Every `/api/*` route returns 503 `{"reason": "database_unavailable" \| "schema_missing" \| "schema_incompatible"}`. Only `/api/health` and `/api/readiness` answer, and readiness gives the reason. Rechecked every 5 s while blocked and every 30 s once healthy, so a rebuilt database is picked up without a restart |
| In-process pytest | `conftest.py` also requires `DATABASE_TARGET=disposable` (in addition to the existing loopback-host check) |

Error messages never include the URL or credentials.

### 12.2 Restart and rebuild behaviour (observed during this pass)
- The pod restarted at 21:52 UTC. PostgreSQL 17, the `postgres` OS user and `/var/lib/u1pg` were wiped. Supervisor
  configs survived.
- **U1 regression found and fixed:** the earlier `u1_disposable_pg` supervisor entry had `user=postgres`. With that user
  gone, `supervisord` itself would not start ("Invalid user name postgres"), so the **whole preview was down** (502).
  The entry now runs a shell check as root and exits cleanly when PostgreSQL is absent, so it can't block supervisord.
  The rebuild script rewrites this entry.
- With the guard in place and the database gone, the preview failed closed: `/api/readiness` 503
  `{"status":"not_ready","reason":"database_unavailable"}`, `/api/health` 503, and `/api/meta` and `/api/journeys` 503 with
  the guard message. Nothing contacted Supabase.
- Rebuild: `bash memory/u1_disposable_db.sh` (exit 0). It reinstalled PostgreSQL, rebuilt the pre-U1 history, ran
  `alembic upgrade head` to `d4e1f7a2b9c3` and seeded. Readiness then returned 200 without a backend restart.
- If supervisord is not running after a pod restart: `sudo supervisord -c /etc/supervisor/supervisord.conf`, then
  run the rebuild script.
- `.emergent/system_deps.txt` lost and regained its `postgresql-17` line through platform commits, so it is not a
  reliable way to keep PostgreSQL installed. The guard is the protection.

### 12.3 Keeping production separate
- The preview's `backend/.env` (git-ignored, never committed) has `DATABASE_TARGET=disposable`. The live
  `DATABASE_URL` line in that file is unchanged and unused while the supervisor override is in place. If the override
  is lost, that URL is refused rather than used.
- The approved production configuration is set only in the Emergent deployment secrets: `DATABASE_TARGET=live` plus
  the live URL (§10 step 6). It is not applied in this pass.

### 12.4 Closeout commands and results (throwaway DB only)
Each backend command printed `TARGET: 127.0.0.1:5433/pa_u1_disposable` first.

| Command | Result |
|---|---|
| `DATABASE_URL=<throwaway> APP_ENV=development pytest -q -p no:cacheprovider tests/test_u1_db_guard.py tests/test_u1_campaigns.py tests/test_u1_report_collision.py` | **29 passed** (14 guard + 15 U1 campaign/report-collision). Users/workspaces/journeys/properties/report runs `3/3/4/23/3` before and after. Log: `test_reports/pytest/u1_closeout_focused.log` |
| Same file before the test fix (meaningful assertion only) | 1 failed: house weekly `{'detected': 0, 'resolved': 0}` ≠ `{'detected': 1, 'resolved': 0}` (see F6) |
| `ruff check` on the new guard module and its tests | All checks passed |
| `CI=true yarn test --watchAll=false auth shell m4_2 m5_1` (current) | 29 passed, 2 failed (F7, F8). Log: `u1_closeout_jest_current.log` |
| Same 4 suites at `32bf41d` (temporary worktree, deleted) | 29 passed, the **same 2** failed. Log: `u1_closeout_jest_baseline_32bf41d.log` |
| `pytest` at `32bf41d` on a temporary local DB `pa_u1_baseline` (`c8d5e2f9a4b1`, seeded; dropped afterwards): `test_system::test_no_forbidden_pathways_exist`, `test_m3a_foundation::test_migration_head_is_m3a`, `test_m4_2_migration_rollback.py` | 3 failed, same as the U1 run (F3–F5). Log: `u1_closeout_pytest_baseline_32bf41d.log` |
| Baseline OpenAPI generated in-process at `32bf41d` | Contains "never fetched or scraped" once (F2) |

Not rerun: the full pytest suite, the full Jest suite, `yarn build`, the testing agent and screenshots. No frontend code
changed. The screenshots and `iteration_11.json` still apply.

## 13. Failure register

Sources: `u1_full_suite.log` (16 failed, 11 errors), the saved `u1_jest.log`, the closeout runs in §12.4.

| # | Failure | Class | Evidence | Action |
|---|---|---|---|---|
| F1 | `test_m2_public` 12 failed + 10 errors; `test_m3_public::TestReevaluation` 1 error (reported at setup and teardown) | Test/configuration mismatch | Every error is `403 {"detail":"signup_disabled"}` from public signup. These suites call the preview URL, where signup is off. The gate came in M6.2 (`908bb6c`), which is an ancestor of `32bf41d`. **Not re-run at baseline**: that would need the baseline code serving the preview URL | Not changed (not U1) |
| F2 | `test_m2_public::test_openapi_has_no_unsafe_or_value_score_paths` | Demonstrated pre-existing (test vs existing schema text) | The baseline OpenAPI at `32bf41d` already contains "never fetched or scraped" (intake schema docstring) | Not changed |
| F3 | `test_system::test_no_forbidden_pathways_exist` | Demonstrated pre-existing (test vs M6.1 route) | Fails the same way at `32bf41d`: `'send'` in `/ready-to-send` (route added in `703e585`, before U1) | Not changed |
| F4 | `test_m3a_foundation::test_migration_head_is_m3a` | Demonstrated pre-existing (test pins an old head) | At `32bf41d`: `'c8d5e2f9a4b1' == '2105faf7bef7'` fails | Not changed |
| F5 | `test_m4_2_migration_rollback` | Demonstrated pre-existing (test pins an old head) | At `32bf41d`: `'a8d2e3f4b5c6' in 'c8d5e2f9a4b1'` fails at the first assertion, before any downgrade. The test hard-codes `cwd=/app/backend`, so the baseline run used the current Alembic scripts. The assertion only reads the database revision, so the result holds | Not changed |
| F6 | `test_u1_campaigns`: `house_weekly["duplicates"] == house_weekly["duplicates"]` | U1 test defect (fixed) | The self-comparison hid that the default weekly period ends at today's local midnight. The fixture's duplicate pair was outside the period, so both house and land counted 0 and the land check proved nothing | The test now requests the week starting today (Perth). It asserts house `{"detected": 1, "resolved": 0}` and keeps land `detected == 0`. Passes. No product code changed |
| F7 | Jest `auth.test` › verification pending … delivery suppressed | Demonstrated pre-existing | Same failure at `32bf41d` (expects `/no email is delivered/`) | Not changed |
| F8 | Jest `shell.test` › desktop rail order | Demonstrated pre-existing | Same failure at `32bf41d` (extra `"Reports"` rail item) | Not changed |
| F9 | Saved `u1_jest.log`: 16 failed (13 `shell.test`, 1 each in `auth`, `m4_2`, `m5_1`) | Unverified cause | Not reproduced now: `m4_2`/`m5_1` pass, and only F7/F8 fail in the current and baseline runs. It was an earlier mid-development run, and its cause wasn't determined | §5 row corrected; nothing to fix |
| F10 | `supervisord` would not start after a pod restart (preview down) | **U1 regression (fixed)** | §12.2 | Supervisor entry and rebuild script fixed |

Also not fixed (lint only, outside this pass): `tests/test_u1_campaigns.py` already had about 70 ruff findings (line
length, `UP017`) before this change.

## 14. Closeout status
- Changed files: §7 (closeout bullet).
- Remaining blockers: owner review and **Save to GitHub** (commit SHA); a Supabase backup confirmation; the production
  secret `DATABASE_TARGET=live` must be set at deploy time (§10 step 6); a pod restart still needs
  `bash memory/u1_disposable_db.sh` before the preview works again (it now stays fail-closed until then).
  Decisions on F1–F5 and F7–F8 are separate, non-U1 work.
- No live changes, no deploy, no U2, no integrations, email or workers.
