# IDEA-010 Property Acquisition — Product requirements and status

Working name: "Property Acquisition" (working concept, not final). Gate: **initial private prototype**.
Last updated: 14 September 2026 (Prompt 03A foundation alignment complete).

## Execution state

| Prompt | Scope | Status |
|--------|-------|--------|
| 00–03 | Foundation, design system, auth, tenancy, buying brief, property workspace | **Complete** |
| Security hotfix | `/api/dev/*` deny-by-default, outbox purge, token invalidation | **Complete** — `checkpoint/security-public-dev-surface` |
| **03A** | Post-M3 foundation alignment — connector catalog, source readiness, sender aliases, discovery/intake attribution, scheduler observability, enrichment records, report-run metadata; frontend `/dev/outbox` → genuine 404 | **Complete** — `checkpoint/m3a-foundation-alignment` |
| **04** | Property gates and pipelines, Add property intake UI | **Next** |

## Original problem statement (owner's brief)

Build IDEA-010 Property Acquisition as an initial private responsive-web prototype, following the supplied
Emergent Prompt Runbook and Product Definition and Build Specification, milestone by milestone, stopping for
review at each checkpoint.

Owner amendments that govern the whole build:

1. Database is the owner's **Supabase Free PostgreSQL** project (no local MongoDB).
2. Backend is **Python 3.11 + FastAPI** (not Node/Express).
3. Milestone 1 uses **synthetic fixtures only**; no live services.
4. All **25 supplied concept images** map to routes and components.
5. Strict testing and a checkpoint at the end of every milestone.
6. Authentication is **email and password only**; Google is deferred (visible, off) and Apple is locked off.
7. No public-launch features: no scraping, no agent sending, no billing, no live AI, no live Drive, Gmail or
   portal connectors.

## Non-negotiable product rules

- **Unknown is a first-class value.** It is never rendered or stored as 0, false, pass or fail.
- A **hard rule failure can never be promoted** by a high preference score. Rules, preferences and evidence
  coverage are scored and displayed separately.
- **Nothing is sent on the user's behalf.** Drafts stay drafts; there is no send, book, offer or billing path.
- **No Value Score and no indicative valuation** anywhere in the product or the code.
- Unpriced ("Contact agent") and aggregator bands are **never converted into numbers**.
- Travel time stays **Unknown** until a provider and its assumptions exist.
- Money is stored as **integer minor units plus a currency**; areas are canonical **square metres**.
- `workspace_id` is derived from the authenticated membership and **never accepted from the client**.
- Cross-tenant access returns **404**, never 403.

## Users

- **Primary:** a buyer (and their household) running one or more buying journeys in Australia.
- **Secondary:** a household partner with a role in the same workspace (invitations arrive in Milestone 6).
- Support access is a separate role with an audit event — never implicit.

## Architecture

- `/app/backend` — FastAPI app (`app/api`, `app/core`, `app/db`, `app/schemas`, `app/services`), Alembic
  migrations, `scripts/seed.py`, `scripts/reset.py`, `scripts/unlock.py`, pytest suites in `tests/`.
- `/app/frontend` — React 18 + TypeScript + Tailwind. `src/app` (router, shell), `src/components`,
  `src/features/*` (one folder per concept area), `src/lib` (api, auth, journey, formatting, synthetic
  fixtures), Jest tests in `src/__tests__`, Playwright specs in `e2e`.
- Database: Supabase PostgreSQL through the session pooler (`aws-0-ap-southeast-2.pooler.supabase.com`);
  the direct host is IPv6-only and unreachable from this pod.
- `/app/docs` — `concept-image-map.md`, `M1-report.md`, `M2-report.md`.

## Milestone status

| Milestone | Scope | Status |
| --- | --- | --- |
| 1 | Foundation, design system, shell, 25 concept routes, synthetic fixtures | **Done** — approved by the owner |
| 2 | Authentication, workspace and tenancy, guided setup, versioned buying brief | **Done** — approved; checkpoint `checkpoint/m2-accounts-brief` |
| 3 | Property workspace, evidence and matching (gates, fit, coverage), waivers, notes/tasks/activity | **Done** — approved |
| 3A | Post-M3 foundation alignment (connector, readiness, aliases, discovery, intake, scheduler, enrichment, reports) | **Done** — checkpoint `checkpoint/m3a-foundation-alignment` |
| 4 | Property gates and pipelines, "Add property" intake UI | Planned |
| 5 | Intake idempotency, reminders ("Add reminder") | Planned |
| 6 | Tasks and digest via a durable outbox, household invitations, export and deletion, audit browsing | Planned |
| 7 | Hardening, accessibility and performance passes, final checks | Planned |

### Milestone 1 — delivered (June 2026)

Responsive shell (desktop rail, mobile bottom bar, More hub), design tokens, component library, all 25
concept images mapped to routes with synthetic data, Jest + Playwright + pytest harnesses, `M1-report.md`.

### Milestone 2 — delivered (4 September 2026)

- Email and password accounts: signup that never signs you in, verification-pending state, single-use hashed
  verification and reset tokens, revocable server-side sessions (15-minute access token bound to a session
  row, 7-day rotating refresh), sign out of one device or all devices, profile and timezone editing.
- Brute-force protection keyed on the normalised email (5 per 15 minutes) and the first `X-Forwarded-For`
  hop (20 per 15 minutes), returning 429 with `Retry-After` — the socket peer address rotates behind the
  ingress and cannot be trusted.
- Durable outbox: no provider is configured, every message is stored with
  `delivery_state = suppressed_no_provider`, and the owner completes flows from the development-only
  `/dev/outbox`.
- Workspace, owner membership and application-layer tenant scoping with negative cross-tenant tests.
- Six-step resumable guided setup with save-and-finish-later and conflict recovery.
- Versioned buying brief: four modes per criterion (Hard rule, Preference, Disabled, Unknown), field-linked
  publication validation, immutable `brief_versions` with actor, timestamp and reason, version history,
  editable preference weights with an enabled total and a reset action, locations with all states and
  territories, included and excluded areas, an optional radius and travel anchors that stay Unknown.
- Full detail and known limitations: `/app/docs/M2-report.md`.

### Milestone 3 — delivered (4 September 2026)

- Persisted property workspace: `properties` (unit-aware identity), `listing_campaigns` (raw guide, price
  kind, market state), `observations` + `facts` (provenance, `known/unknown/not_applicable/conflict`),
  `buyer_properties` (11 buyer states, saved flag, row_version), `match_evaluations`, `gate_waivers`,
  `property_notes`, `property_tasks`, `activity_events`. Migration `2fc5f4775fef`.
- Engine `gates_v1 + scoring_v1` (`app/services/matching.py`): pure, versioned, reproducible (`input_hash`).
  Unknown never becomes Pass/Fail/0/false; fit and coverage separate; no Value Score.
- Publish re-evaluates every property synchronously; `reevaluation_state` → `completed`; old versions kept.
- Workflow transitions with `409 transition_not_allowed` / `stale_write` / `hard_failure_cannot_be_promoted`;
  property-specific waivers (reasoned, attributed, revocable) that never alter the brief or the gate.
- Screens on persisted data: Today, Discover, Pipeline, Saved, Compare (client-side selection, max 4),
  Property page with Overview and Match & evidence (`?view=match`).
- Dev-only fixture loader `POST /api/dev/load-demo-properties` (+ button on empty Discover/Today). Not intake.
- Full detail, limitations and manual review steps: `/app/docs/M3-report.md`.

### Post-M3 fix — 6 September 2026

- Bug: after the 15-minute access token expired, any API call showed a raw "Not authenticated" while the
  shell still looked signed in (owner hit it on step 1 of the guided setup). Fix: `apiFetch` refreshes the
  session once on 401 (deduplicated) and replays the request; if refresh fails it emits `pa.session-expired`,
  the shell returns to sign-in with `?next=` and a notice, and sign-in lands back on the same page.
  Verified by QA (`/app/test_reports/iteration_5.json`) and 3 new Jest tests.

## Backlog

### P0 — next milestone (4)

- Property gates and pipelines as defined in the runbook Prompt 04; the deferred **Add property** intake UI
  with the durable re-evaluation job worker.
- Push list filters/sorts into SQL; consider a regional cache for the ~190 ms pooler round-trip.

### P1

- Milestone 4: property gates and pipelines, the deferred **Add property** intake UI.
- Milestone 5: intake idempotency and the deferred **Add reminder** interaction.
- Milestone 6: tasks and daily digest through the durable outbox (still no delivery), household invitations
  and roles, data export, deletion job, audit browsing, retention controls.

### P2

- Milestone 7: hardening — accessibility sweep, performance budget, error-path review, final gate checks.
- Deferred by the owner until asked for: **Concept Walkthrough** and the **Rail Density Toggle**.
- Optional later: cache journeys and the brief across screens to hide the cross-region latency; a
  "restore my edits" affordance after a brief version conflict; clear the IP lockout bucket from the UI.

## Test and verification status

- Backend: `tests/test_auth.py`, `test_rate_limit.py`, `test_tenancy.py`, `test_brief.py`, `test_system.py`,
  `test_matching.py`, `test_properties.py`, `test_security_dev_surface.py`, `test_m3a_foundation.py`,
  plus QA-authored `backend_test.py`, `test_m2_public.py`, `test_m2_retest.py`, `test_m3_public.py`.
  **17 targeted M3A tests all pass.** 16 security+auth regression tests all pass.
- Security hotfix in effect: `/api/dev/*` returns 404 when `DEV_ROUTES_ENABLED=false` (default).
  Frontend `/dev/outbox` route removed; catch-all renders genuine `NotFoundPage`. Auth pages no longer
  disclose dev-route paths.
- Frontend: 7 `auth.test.tsx` Jest tests pass (updated for outbox link removal). `yarn build` clean.
- Seed accounts preserved: `owner@`, `other@`, `lockout-drills@propertyacquisition-demo.com`.
- Credentials for testing: `/app/memory/test_credentials.md`.
