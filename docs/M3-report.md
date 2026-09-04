# Milestone 3 report — Property workspace, evidence, gates, fit and re-evaluation

Date: 4 September 2026 · Gate: initial private prototype · Working name: "Property Acquisition"
Preceding checkpoint: `checkpoint/m2-accounts-brief` (Milestone 2 as approved by the owner)
Migration identifier: **`2fc5f4775fef`** (`m3 property workspace evidence matching`, revises `4bb12e1e9183`)

## What Milestone 3 delivers

Milestone 2 made accounts and the buying brief real. Milestone 3 replaces the Milestone 1 display
fixtures on Today, Discover, Pipeline, Saved, Compare and the property page with persisted, tenant-scoped
records evaluated by a deterministic engine. Every number on screen can now be traced to a stored fact
with a source, an immutable brief version and a versioned rule set.

### Domain model (PostgreSQL via Supabase, Alembic-managed)

| Table | Purpose |
| --- | --- |
| `properties` | Physical address identity per workspace. `normalised_address` keeps the unit suffix so **81A and 81C never merge**. |
| `listing_campaigns` | Provider sale campaign: raw advertised guide, price kind (Exact, Range, From, Offers over, Auction, Contact agent, EOI, Conflicting), lower/upper minor units only when stated, **market state** (`active`, `under_offer`, `withdrawn`, `sold`, `unknown`). |
| `observations` | One look at one source at one time (`original_source`, `partial`, `manual`, `conflict`), with observed and checked timestamps. |
| `facts` | One material fact per property and key (beds, baths, cars, land, floor, type, detached, condition, location tier). `value_state` is `known`, `unknown`, `not_applicable` or `conflict`; each fact points at its observation for provenance. |
| `buyer_properties` | Household workflow state per journey (11 states), `saved` flag, who changed the stage and when, `row_version`. Deliberately separate from market state. |
| `match_evaluations` | Result of evaluating one property against one immutable `brief_versions` row: gates, verdict, fit, coverage, components, `evaluation_version`, `input_hash`. Unique per (property, brief version). |
| `gate_waivers` | Property-specific, reasoned, attributed acknowledgement of a Fail or Unknown gate. Revocable. |
| `property_notes`, `property_tasks` | Notes (edit with optimistic concurrency) and simple done/undone tasks. |
| `activity_events` | Auto-recorded history: fixture load, stage change, save, waiver recorded/revoked, note, task, re-evaluation. |

### The engine: `gates_v1 + scoring_v1` (`app/services/matching.py`)

Pure functions, no I/O, versioned, reproducible (`input_hash` over the brief version payload and the
property facts). Same inputs always produce the same stored result; a changed fact or a new brief
version changes the hash.

**Hard gates.** Every criterion in *Hard rule* mode yields Pass, Fail or Unknown with the brief value,
the observed value, the fact reference and source, a plain-language reason and "what would change it":

- Budget ceiling: only Exact, Range, From, Offers over and priced Auction guides carry a number.
  Contact agent, EOI, unpriced Auction and Conflicting are **Unknown** — no bound is ever inferred.
  A From/Offers-over guide above the ceiling is a known Fail; within the ceiling it passes with the
  caveat that an opening guide is not a seller ceiling. A Range that straddles the ceiling is Unknown.
- Property type, detached, bedrooms, bathrooms, parking, land area, floor area, renovation tolerance and
  location (states, included and excluded areas). Timing is a buyer-side criterion and is not a
  property gate.
- Verdict: any Fail → `fail` (excluded from ordinary matches); otherwise any Unknown → `unknown`
  (verification required); otherwise `pass`. **Unknown is never Pass, Fail, zero or false.**

**Preference fit and evidence coverage.** Four components (price, land, location, condition) each score
0–100 with a reason, weighted by the brief's enabled weights.
`fit = achieved points ÷ maximum achievable for assessed components`;
`coverage = assessed enabled weight ÷ total enabled weight`. They are stored, transported and displayed
side by side and never blended. When nothing can be assessed fit is `unavailable` (not 0%). There is
no Value Score and no valuation anywhere.

Worked fixture results (seeded brief: ceiling $1.3m, preferred max $1.2m, detached house, ≥3 beds,
≥1 bath, ≥400 m² land, moderate renovation tolerance, four included WA areas):

| Property | Verdict | Fit | Coverage | Why |
| --- | --- | --- | --- | --- |
| DEMO-001 12 Banksia Crescent | Pass | 94% | 100% | From $1.1m within ceiling; 690 m²; strong-alternative tier |
| DEMO-002 7/22 Marri Lane | **Unknown** | 60% | 70% | Contact agent → budget Unknown; condition unknown |
| DEMO-003 5 Jarrah Court | **Fail** | 87% | 100% | 318 m² < 400 m². High fit reported, never promotes |
| DEMO-004 40 Tuart Road | **Unknown** | 60% | 70% | Two sources disagree on the guide |
| DEMO-005 81A Sample Street | Pass | 100% | 100% | Shortlisted, saved |
| DEMO-006 81C Sample Street | **Unknown** | 100% | 20% | EOI; land and condition unknown — coverage shows how little is assessed |
| DEMO-007 3 Peppermint Way | Pass | 88% | 100% | Market *under offer*, buyer state *Archived* — shown separately |

### Brief-driven re-evaluation

Publishing a brief version now evaluates every property in the journey against that version inside the
publish request, stores one `match_evaluations` row per (property, version) and moves
`reevaluation_state` from `queued` to `completed`. Earlier versions and their scores are preserved, so
the history reads "brief v1 → v2 → v3" with each property's result at each version. The seed also
evaluates any legacy `queued` version.

### Buyer workflow, waivers, notes, tasks, activity

- Eleven buyer states with an explicit allowed-transition map; the UI offers only allowed moves.
  Illegal moves return `409 transition_not_allowed`; stale edits return `409 stale_write` and the client
  reloads.
- **A known hard-rule failure cannot be promoted** past Reviewing (`409 hard_failure_cannot_be_promoted`,
  listing the failing rules). A property-specific **waiver** — reason, actor, time, revocable — is required
  for each failing rule before a manual promotion is accepted. The waiver **never changes the published
  brief and never converts the gate**: the row still reads Fail with "Waived by you · gate unchanged", and
  the property remains excluded from ordinary matches. Waivers on a passing gate are rejected (`422`).
- Notes (create, edit with `expected_row_version`), simple tasks (title, done/undone), and an automatic
  activity history. No reminders, due dates, ICS or drafts — those remain Milestone 5.

### Screens replaced with persisted behaviour

- **Today** — counts from real evaluations (eligible awaiting decision, verification required, known
  failures), "Waiting for evidence" with the exact unknown rule, journey health, "What changed" from
  activity. Honest empty states; a development-only fixture loader when a journey has no properties.
- **Discover** — Reviewing queue with gate filter (all / pass / unknown / fail), search, sort (last
  checked, fit, address), cards or list, add-to-compare (max four). Each card shows market state and
  buyer state as separate chips, the raw guide exactly as advertised, Unknown facts as "Unknown", and fit
  beside coverage.
- **Pipeline** — eleven buyer-stage columns; source updates never move cards.
- **Saved** — the `saved` flag, owned by the household.
- **Compare** — up to four properties; every gap stays Unknown; no invented totals or travel times.
- **Property page** — Overview (facts with source and freshness, notes, tasks) and **Match & evidence**
  (`?view=match`: per-rule gate table, waiver form, components table, fit and coverage, evaluation
  version, hash and recalculation time). Workflow panel, source observations and activity in the sidebar.
  Foreign or unknown ids show "Property not found" — never data.

### Fixture loading (internal, development-only)

`POST /api/dev/load-demo-properties {journey_id}` loads `fixtures/demo-data.json` into the caller's
journey (idempotent by normalised address, `404` outside development). The seed calls the same routine.
This is **not** the Add-property intake, which stays in Milestone 4; addresses are fictional and every
row is flagged `synthetic`.

## API surface added

`GET /api/journeys/{j}/properties` (filters: `buyer_state`, `verdict`, `saved`, `q`, `sort`) ·
`GET …/properties/compare?ids=` · `GET …/properties/{id}` · `POST …/stage` · `POST …/saved` ·
`POST/DELETE …/waivers` · `POST/PATCH …/notes` · `POST/PATCH …/tasks` · `GET /api/journeys/{j}/today` ·
`GET /api/journeys/{j}/activity` · `POST /api/dev/load-demo-properties`.
All routes require a session, resolve the workspace from the membership, and return `404` for any
foreign journey or property (negative tests included).

## Tests

| Suite | Count | Result |
| --- | --- | --- |
| Backend pytest — engine (`tests/test_matching.py`) | 12 | pass |
| Backend pytest — API, workflow, waivers, concurrency, re-evaluation, tenancy (`tests/test_properties.py`) | 5 | pass |
| Backend pytest — Milestone 2 suites (`test_auth`, `test_rate_limit`, `test_tenancy`, `test_brief`, `test_system`, QA suites) | 118 | pass (one expectation updated: `reevaluation_state` is now `completed` on publish) |
| QA-authored public-ingress suite (`tests/test_m3_public.py`, from the consolidated QA cycle) | 41 | pass |
| Frontend Jest (components, shell, auth, brief, forbidden-words, axe) | 47 | pass |
| Playwright — five-viewport responsive sweep incl. property detail and match tab | 131 runs | pass after one fix (17 px overflow on the match tab at 320 px) |
| Playwright — workspace flows (`e2e/workspace.spec.ts`, desktop) | 5 | pass |
| Independent QA (`/app/test_reports/iteration_4.json`) | backend 41/41, frontend all flows | no critical or blocking defects; one minor (seed left brief v1 `queued`) — fixed |

Static checks: `ruff`, `ruff format`, `mypy --strict` (backend); `tsc`, ESLint/oxlint with zero warnings,
Prettier (frontend).

## Known limitations and remaining placeholders

- **Latency.** The Supabase session pooler adds ~190 ms per round trip from this region; warm list and
  detail calls take 1.5–3 s and the first call after idle can take ~8 s. List queries are batched (four
  round trips for any number of properties) but Milestone 7 should add a regional cache or move the
  database closer.
- **List filtering in Python.** Filters and sorts run in the API layer; fine for fixture volumes, to be
  pushed into SQL with Milestone 4 intake.
- **Lazy evaluation on read.** If an evaluation is missing for the current version (it should not be,
  publish evaluates everything) a GET computes and stores it. Bounded by the journey's property count.
- **Location score** uses the fixture's location tier when present and otherwise falls back to area
  membership; travel time and total-cost rows remain explicitly Unknown until a provider exists.
- **Images.** No licensed listing imagery; the text-only placeholder is used everywhere.
- Still deferred by design: Add property intake (M4), Add reminder / due dates / ICS (M5), household
  invitations, brief compare, Concept Walkthrough, Rail Density Toggle, digest delivery.
- Agents, Tasks hub and other Milestone 5–6 routes still show Milestone 1 display data.

## Files

- Engine: `backend/app/services/matching.py`; services: `backend/app/services/properties.py`
- API: `backend/app/api/properties.py`, `backend/app/api/dev.py` (loader), `backend/app/api/journeys.py`
  (publish hook)
- Models and schemas: `backend/app/db/models.py`, `backend/app/schemas/properties.py`
- Migration: `backend/alembic/versions/2fc5f4775fef_m3_property_workspace_evidence_matching.py`
- Seed/reset: `backend/scripts/seed.py`, `backend/scripts/reset.py`
- Frontend: `frontend/src/lib/properties.ts`, `frontend/src/features/properties/*`,
  `frontend/src/features/property/*`, `discover`, `pipeline`, `saved`, `compare`, `today`,
  `frontend/src/components/PropertyCard.tsx`
- Tests: `backend/tests/test_matching.py`, `backend/tests/test_properties.py`,
  `backend/tests/test_m3_public.py`, `frontend/e2e/workspace.spec.ts`, `frontend/e2e/responsive.spec.ts`
- QA report: `/app/test_reports/iteration_4.json`

## Manual review steps (owner)

1. Sign in as `owner@propertyacquisition-demo.com` → **Today**: counts read 3 eligible awaiting decision,
   3 need verification, 1 known failure; "Waiting for evidence" lists 7/22 Marri Lane, 40 Tuart Road and
   81C Sample Street with the exact unknown rule.
2. **Discover** → filter *Known failure* → honest empty state (nothing failing is in Reviewing) → *Clear
   filter*. Note "Market: Active" and "You: Reviewing" as separate chips and "Unknown" land on 81C.
3. **Pipeline** → open **5 Jarrah Court** (Rejected column) → red note "Known hard-rule failure" → tab
   **Match & evidence**: land row reads Fail (318 m² < 400 m²) while fit is 87% and coverage 100%.
4. Workflow panel → move to *Reviewing* → try *Shortlisted* → refused with the waiver explanation. Record
   a waiver on land with a reason → gate still reads Fail with "Waived by you · gate unchanged" → the move
   is now accepted. Revoke the waiver. Move it back to *Rejected*.
5. Open **81C Sample Street** → coverage 20 %, budget and land rows Unknown, yellow "Unknown is not
   Pass" note. Add a note and a task; watch the Activity panel update.
6. **Compare**: add four properties from Discover; the fifth button reads "Compare full (4)". Land for 81C
   is Unknown, total-cost and travel rows are Unknown.
7. **Brief** → change land minimum to 700 m² → publish → Discover: 12 Banksia Crescent now reads *Known
   failure*; the version history shows every version "re-evaluation completed". Publish 400 m² again to
   restore.
8. Open `/app/properties/00000000-0000-4000-8000-000000000000` → "Property not found".

Suggested checkpoint after review: **`checkpoint/m3-property-workspace`** (Save to GitHub).
