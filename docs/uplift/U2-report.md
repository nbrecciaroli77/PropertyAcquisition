# U2 Report — Land profile and evidence-based qualification (uplift v2.0)

Date: 15–16 October 2026 (pod clock). Scope: **U2 only**. Baseline: U1 closeout `cf82f7dc1b6b6f311f9a4bb646e57562ee93c1dd`
(preserved; all U1 protections kept). U3 not started.

| Area | Implemented | Tested | Live |
|---|---|---|---|
| `LAND_FEASIBILITY_V1` engine (deterministic, versioned `land_feasibility_v1`) alongside `HOUSE_V1` | Yes | Yes (L01–L12 + API) | **No** |
| Explicit land brief config; missing config fails closed (`CONFIG_PROFILE_INVALID`) | Yes | Yes | **No** |
| Land evidence facts with provenance; intake API; synthetic seed | Yes | Yes | **No** |
| Brief, property detail, cards, pipeline/discover priority order (desktop + mobile) | Yes | Jest + screenshots | **No** |
| Exact money conversion (Decimal, integer minor units) | Yes | Yes | **No** |
| Migration `e7b2a9c4f1d6` | Yes | Throwaway DB: upgrade → downgrade → re-upgrade; fail-closed downgrade | **No — not executed** |
| House rules, weights, thresholds and stored scores | Unchanged | Yes | n/a |

## 1. Safety
- All commands ran against `127.0.0.1:5433/pa_u1_disposable` with `DATABASE_TARGET=disposable`. Each backend
  command printed `TARGET: 127.0.0.1:5433/pa_u1_disposable` first. Live Supabase was not contacted: no migration, seed,
  deploy, integration, email or worker.
- The private pack (`/app/reference/…`, git-ignored) was read once: work package U2, Build Specification R2–R3,
  `fixtures/acceptance-cases.json` L01–L12, and Transfer Register CT2-012/CT2-017. Nothing from it is committed apart
  from the requirement values the owner restated in the U2 instruction.
- Privacy: the owner's home suburb is **not** committed. The seed and tests use "Home suburb (synthetic, approximate)".
  The priority town names (public WA place names) are in the seed and tests because the instruction says to retain
  them. Owner decision: keep, or replace with invented names before Save to GitHub.
- The synthetic demo password already in `seed.py`/tests predates U2 and is unchanged.

## 2. Rules implemented (approved by the owner before the build)
| Rule | Implementation (`backend/app/services/land.py`) |
|---|---|
| Hard gates (only documented evidence excludes) | Supported land price ≤ cap (inclusive), usable area ≥ minimum (optional max; default none), availability, title/covenants, legal access, zoning/dwelling permission, dwelling pathway |
| Verification items | Building envelope, bushfire, flood/wetlands, power, water, wastewater, prefab/modular/habitable-shed feasibility. Unknown = named gap (doesn't block Priority 1); documented `unsuitable` = field-specific exclusion |
| Status | Any documented failure → `EXCLUDED` (not ranked as a candidate); all hard gates supported → `SUPPORTED` / Priority 1; otherwise `PROVISIONAL` / Priority 2 with named gaps |
| Price | Kept separately: advertised/package amount, price kind, subtype, supported land component, supported land price (used for the cap), seller-ceiling confidence. A supported price is either an explicit land component or a vacant-land exact advertised amount ≥ AUD10,000. A package without a component, any opening guide (`from`/`offers_over`, even above the cap) and amounts below AUD10,000 stay provisional with a named price-verification reason, never a pass, failure or "rent" |
| Area | Total lot (`land_sqm`) ≠ usable (`usable_sqm`). Unknown usable area stays unknown, whatever the lot size |
| Travel/location | Soft preference only (`hard_exclusion: false`): met / missed / unknown. Mount Barker is listed as an explicit longer-drive option; the origin is labelled approximate. Priority towns + surrounds + "Mandurah and south" are labels, never exclusions |
| Shed | `shed_present` never sets the dwelling pathway. A note says it is not permission to live there |
| No score | `fit.pct = null`, `coverage.pct = null`, `components = []`; `MatchEvaluation.fit_pct` stored as NULL |
| Tie-breaks (`rank_key`) | Priority → supported price (known, lower first) → travel (met, missed, unknown) → drive minutes → freshness (most recent first) → stable property ID |
| Inactive | `completed_project_budget` and `airbnb` are typed `Literal["inactive"]` and cannot be activated |
| Config | `LandFeasibilityBrief` has **no defaults** for cap, minimum usable area, preferred drive or origin. Publication of a land brief validates only the land profile; the profile is "available" only when the published brief passes `validate_land_config`. Otherwise `config_state = CONFIG_PROFILE_INVALID`, nothing is evaluated, and the stale 250k/180 values are never used |

Synthetic Down South Land settings (seed): cap AUD200,000 inclusive (`20000000` minor units), minimum usable 250 m², no
maximum, preferred drive 240 min (soft), priority towns retained with surrounds, Mount Barker longer-drive option.

## 3. Requirement mapping
| Requirement | Where |
|---|---|
| R3 separate land campaign/profile, versioned + deterministic | `services/land.py` (`LAND_ENGINE_VERSION`, `input_hash`), `services/campaigns.py` profile table, `services/properties.py:evaluate_property` dispatch by campaign kind |
| R3 explicit current brief values; fail closed | `schemas/brief.py:LandFeasibilityBrief`, `validate_land_config`, `validate_for_publish(brief, kind)`; `campaigns.profile_config_errors`; `api/journeys.py:_initial_draft` (empty land config for new land campaigns) |
| R3 vacant + house-and-land; distinct price/area/pathway facts | `db/models.py:LAND_FACT_KEYS`, `schemas/intake.py:FactsIn`, `services/intake.py` (rows written only when supplied) |
| R3 title/covenants, envelope, access, zoning, bushfire, flood/wetlands, power, water, wastewater, modular/shed evidence | Same facts. Each gate/check shows requirement, observed value and source label (provenance) |
| R3 ordinal priorities, explained gaps, tie-breaks | `evaluate_land` → `land.status/priority/explanation/gaps/failures`; `rank_key`; `GET …/properties?sort=priority` |
| R3 completed budget/Airbnb inactive | Brief schema literals; result `land.inactive`; brief and detail UI notices |
| R2 house unchanged; history preserved; no silent recalculation | `matching.input_hash` excludes `land_feasibility`; house engine code unchanged; seed compares normalised payloads so no new house brief version is created; §6 evidence |
| R2 explain app-vs-prototype unknown-aware scoring | §5 |
| CT2-012 acceptance | §4 |
| CT2-017 configuration rule (explicit profile config, no silent defaults) | `CONFIG_PROFILE_INVALID` path, tests L10 + `test_api_missing_land_configuration_fails_closed` |
| UI: brief/property/detail + provenance; availability shown only when valid | `features/brief/LandBriefEditor.tsx`, `features/property/LandAssessment.tsx`, `lib/land.ts`, `PropertyCard`, `PipelinePage` / `DiscoverPage` (priority order), campaign notices now say "configuration required" |
| Money in integer minor units | `core/money.py:aud_to_minor` (Decimal, rejects sub-cent); `services/parser.py` uses it |
| Campaign/tenant isolation | Existing `scoped_journey` routes; `test_api_land_evidence_is_tenant_isolated`; U1 suites rerun |

## 4. Acceptance cases (`backend/tests/test_u2_land.py`, real engine + intake service + API)
| Case | Test | Result |
|---|---|---|
| L01 AUD200,000 supported, usable 250, gates evidenced | `test_l01_…` | `SUPPORTED`, Priority 1 |
| L02 AUD200,001 supported land-only | `test_l02_…` (component and vacant-land exact) | `EXCLUDED`, `PRICE_ABOVE_CAP` |
| L03 249 vs 250 m² usable | `test_l03_…` | 249 → `USABLE_AREA_TOO_SMALL`; 250 → `SUPPORTED` |
| L04 lot 1000 m², usable unknown | `test_l04_…` | `PROVISIONAL`; the gap says the total lot is not usable area |
| L05 package AUD230,000, component unknown | `test_l05_…` | `PROVISIONAL`, `LAND_COMPONENT_UNKNOWN`, no failure |
| L06 anomalous AUD950 | `test_l06_…` | `PROVISIONAL`, `PRICE_ANOMALOUS_VERIFY`; not a land price, not rent (also for vacant land) |
| L07 opening guide From AUD160,000 (and 210,000) | `test_l07_…` | Seller ceiling `opening_guide_unverified`; provisional |
| L08 241 min | `test_l08_…` | `SUPPORTED`, travel `missed`, `hard_exclusion: false`; Mount Barker 320 min flagged as the explicit exception |
| L09 shed, dwelling approval unknown | `test_l09_…` | `PROVISIONAL` + shed note |
| Documented unsuitable title/pathway | `test_documented_unsuitable_title_or_pathway_excludes` | `TITLE_UNSUITABLE` / `DWELLING_PATHWAY_UNSUITABLE` |
| L10 missing config | `test_l10_…`, `test_api_missing_land_configuration_fails_closed` | Field errors; empty config has no defaults; the engine raises `CONFIG_PROFILE_INVALID`; the API reports `config_state`, stores 0 evaluations |
| L11 known failure with strong preferences | `test_l11_…` | Excluded and ranked after a provisional candidate |
| L12 house AUD1,300,000 / 400 m² | `test_l12_house_rules_and_hash_are_unchanged` | Budget and land pass (inclusive); `gates_v1+scoring_v1`; fit and coverage separate; hash equals the pre-U2 formula |
| Money | `test_money_…` (11 cases) | `$200,000`→`20000000`, `$200,001`→`20000100`, `1.15m`→`115000000`, `$950`→`95000`, `1.005k`→`100500`; sub-cent/NaN rejected |
| Through the API | `test_api_land_campaign_assesses_ranks_and_isolates` | 5 intakes → statuses as above; priority order Echo ($150k) → Alpha ($200k) → provisional → Beta (excluded) last; provenance on `usable_sqm` |

## 5. Calculation examples and the house app-versus-prototype comparison
Land, from the engine (cap 20,000,000 minor units):
- `land_price_minor = 20000000` → 20000000 ≤ 20000000 → pass. `20000100` → fail `PRICE_ABOVE_CAP`.
- Package `$230,000` (`23000000`) with no component → supported land price `null` → unknown `LAND_COMPONENT_UNKNOWN`.
- `$950` (`95000` < `1000000` anomaly floor) → unknown `PRICE_ANOMALOUS_VERIFY`.
- Usable `249` < `250` → fail; `250` → pass; usable unknown with total `1000` → unknown.

House, the unknown-aware treatment (engine run, not a recalculation of stored scores). Brief weights price 30 / land 30
/ location 20 / condition 20. Property AUD1,150,000 exact in a primary included suburb; land area and condition unknown:

| | App (HOUSE_V1, unchanged) | Prototype zero-for-unknown |
|---|---|---|
| Points | price 30/30, location 20/20, land and condition not assessed | same 50 points; unknown = 0 |
| Fit | 50 / 50 achievable = **100%** of what's evidenced | 50 / 100 = **50%** |
| Coverage | **50%** (50 of 100 enabled weight evidenced), shown separately | not reported |
| Gate verdict | `unknown` → verification required (unknown is not a pass) | n/a |

The app keeps fit and evidence coverage separate, so "100% fit at 50% coverage" is never read as a strong
match. The prototype's 50% merges missing evidence into the score. Neither is recalculated: stored house evaluations
keep their hash, scores and timestamps (§6).

## 6. House regression and history
- `memory/u2_house_unchanged_check.py` (rolled back; throwaway DB). It re-ran `reevaluate_journey` with U2 code over the
  21 house evaluations created by U1 code: `house journeys=3 evaluations=21 changed=0 new=0`
  (`test_reports/pytest/u2_house_unchanged.log`). Hash, verdict, fit, coverage, version, `computed_at` and the full
  result are byte-identical.
- House suites rerun: `test_matching`, `test_brief`, `test_properties`, `test_intake` (included in §7).
- Reseeding no longer creates a spurious house brief version (the seed log still shows brief v1).

## 7. Commands and results (throwaway DB; logs in `test_reports/pytest/`)
| Command | Result |
|---|---|
| Migration rehearsal (`u2_migration_rehearsal.log`) | `d4e1f7a2b9c3` → `upgrade head` → `e7b2a9c4f1d6` → `downgrade d4e1f7a2b9c3` → `upgrade head`. Facts/evaluations/properties `207/21/23` unchanged throughout. After the U2 seed: downgrade **refused** ("33 land evidence fact(s) exist. No data was changed"), revision stays `e7b2a9c4f1d6` |
| `bash memory/u1_disposable_db.sh` (clean rebuild, then all tests) | exit 0; pre-U1 history → `e7b2a9c4f1d6`; land seed: 2 × Priority 1, 3 × Priority 2, 1 × Excluded |
| `pytest test_u2_land test_u1_db_guard test_u1_campaigns test_u1_report_collision test_matching test_brief test_properties test_intake test_m4_2_verification test_m6_1_alignment test_m5_2_privacy test_tenancy` (`u2_backend_focused.log`) | **133 passed**, 0 failed |
| `yarn typecheck` | Pass |
| `CI=true yarn test u2_land u1_campaigns brief` (`u2_jest.log`) | **11 passed** |
| `yarn build` (`u2_frontend_build.log`) | Pass. 2 eslint warnings (`NotificationCenterPage`, `TasksPage`), the same as the U1 build |
| Rerun of `test_m4_2_verification` on the same DB (`u2_m4_2_rerun.log`) | 3 failed, 5 passed. See F-U2-1 |

Not run: full pytest/Jest suites and the testing agent (no unrelated code changed; U1 failure register §13 applies unchanged).

Updated U1 tests (intent preserved): `test_u1_db_guard` expects the new head `e7b2a9c4f1d6`. `test_u1_campaigns` now
asserts that a land campaign stays unavailable with `CONFIG_PROFILE_INVALID`, and that a house-shaped brief is
rejected at publication (previously it asserted U1's "planned for U2" state). The Jest U1 test was updated for the new
notice text.

**F-U2-1 (not a U2 regression; not fixed):** `test_m4_2_verification` writes into the seeded owner workspace and
isn't re-runnable. It passes on a freshly built DB and fails on a rerun with leftovers ("17 == 3", "already merged").
The file is unchanged since `b320cea` (M4.2). It isn't verified at baseline, so this is classed as a test-isolation
defect, not as pre-existing on evidence.

## 8. Migration
- `e7b2a9c4f1d6_u2_land_feasibility_fact_keys` (revises `d4e1f7a2b9c3`). It only widens the `ck_fact_key` check
  constraint to the 18 land keys; there are no new tables and no row changes. The downgrade fails closed while any land
  fact exists.
- The U1 database guard now expects this head; a database at `d4e1f7a2b9c3` gets 503 `schema_incompatible` until it is
  upgraded.

## 9. Screenshots (`docs/uplift/U2-screenshots/`, synthetic data)
Desktop 1920×800: `U2-desktop-1-discover-priority` (priority order, chips, "no score out of 100"),
`-2-shed-provisional-detail`, `-3-priority1-evidence` (price/area evidence + hard gates with sources), `-4-land-brief`,
`-5-campaign-available`. Mobile 390×844: `U2-mobile-1-opening-guide-summary`, `-2-opening-guide-price`,
`-3-documented-title-exclusion`, `-4-pipeline`. No horizontal overflow (checked).

## 10. Changed files
- Backend new: `app/services/land.py`, `app/core/money.py`, `alembic/versions/e7b2a9c4f1d6_u2_land_feasibility_fact_keys.py`, `tests/test_u2_land.py`
- Backend changed: `app/schemas/{brief,intake,properties,campaigns}.py`, `app/db/models.py`, `app/services/{campaigns,properties,intake,matching,parser}.py`, `app/api/{journeys,properties}.py`, `scripts/seed.py`, `tests/test_u1_campaigns.py`, `tests/test_u1_db_guard.py`
- Frontend new: `lib/land.ts`, `features/brief/LandBriefEditor.tsx`, `features/property/LandAssessment.tsx`, `__tests__/u2_land.test.tsx`
- Frontend changed: `lib/{api,properties}.ts`, `features/brief/BriefPage.tsx`, `features/property/PropertyDetailPage.tsx`, `components/PropertyCard.tsx`, `features/{pipeline/PipelinePage,discover/DiscoverPage}.tsx`, `app/layout/{CampaignShell,CampaignSwitcher}.tsx`, `features/settings/CampaignsSection.tsx`, `features/campaign/{CampaignSettingsPage.tsx,settingFormat.ts}`, `__tests__/u1_campaigns.test.tsx`
- Docs/ops: this report, its screenshots, `memory/u2_house_unchanged_check.py`, U1-report §10 step 4 (checklist correction)

## 11. Limitations
- Land evidence can be entered only through the intake API (structured `facts`) and the synthetic seed. The manual
  intake form has no land fields yet (owner choice). Existing properties are updated only by new observations.
- The AUD10,000 anomaly floor is a code constant in `land_feasibility_v1`, not a brief setting.
- Driving minutes are recorded evidence. No routing provider is connected, so the origin stays approximate.
- Gate waivers (house) aren't applied to land gates. Land cards still show the house bed/bath/car icons as Unknown.
- `MatchEvaluation.fit_pct` is NULL for land; the coverage column stores 0 because the column is NOT NULL. The API
  reports `coverage.pct = null`.
- Integer minor units use the existing 32-bit `Integer` columns, which hold up to about AUD21.4m per amount.

## 12. Proposed live deployment step (NOT executed)
Follows U1-report §10, with these changes:
1. Approve U1 and U2; Save to GitHub; record the SHA. Confirm a Supabase backup and take a `pg_dump`.
2. From a trusted operator shell, **separately from the preview configuration**:
   `cd backend && DATABASE_TARGET=live DATABASE_URL=<live> alembic upgrade e7b2a9c4f1d6`. This applies `d4e1f7a2b9c3`
   then `e7b2a9c4f1d6`. Without `DATABASE_TARGET=live`, Alembic refuses.
3. Verify `alembic current = e7b2a9c4f1d6`, the existing report IDs/keys unchanged, house evaluation count and hashes
   unchanged (SELECT only).
4. Deployment secrets only: `DATABASE_TARGET=live` + the live `DATABASE_URL`; then deploy. Do not run `scripts/seed.py` on
   live. The owner creates the land campaign and publishes its brief explicitly; until then it shows "configuration
   required".
5. Smoke: readiness 200; house properties show the same verdict, fit and coverage; a land campaign with no published
   brief shows `CONFIG_PROFILE_INVALID`.
Recovery: Tier 1 code-only rollback (the U2 schema change is a constraint widening). Tier 2 downgrade only while no land
facts exist (it refuses otherwise). Tier 3 restore.

## 13. Remaining blockers and owner actions
- Review U2; decide on the town names in the seed/tests (§1); Save to GitHub (commit SHA).
- Supabase backup confirmation before any live step; the live step needs explicit approval.
- F-U2-1 test isolation, and U1-register items F1–F5/F7–F8, remain separate non-U2 work.
- Credits used: not available to me.
