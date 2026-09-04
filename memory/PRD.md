# IDEA-010 Property Acquisition — Product requirements and status

Working name: "Property Acquisition" (working concept, not final). Gate: **initial private prototype**.
Last updated: 4 September 2026 (end of Milestone 2).

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
| 2 | Authentication, workspace and tenancy, guided setup, versioned buying brief | **Done** — awaiting owner review |
| 3 | Property workspace, evidence and matching (gates, fit, coverage) | Next |
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

## Backlog

### P0 — next milestone (3)

- Property workspace: property record, evidence items and their sources, coverage and freshness.
- Matching: evaluate a published brief against a property to produce a gate (Pass, Fail, Unknown) with the
  reason for every criterion, plus a separate preference score and coverage indicator.
- Consume the `reevaluation_state = queued` marker written at publication.

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
  plus QA-authored `backend_test.py`, `test_m2_public.py`, `test_m2_retest.py` — all passing.
- Frontend: 47 Jest tests (including axe checks) and a five-viewport Playwright sweep (1440, 1024, 412, 390,
  320) — all passing.
- Independent QA: `/app/test_reports/iteration_1.json` (M1), `iteration_2.json` (M2 first pass, 4 findings),
  `iteration_3.json` (M2 retest, all fixes verified, no new defects).
- Credentials for testing: `/app/memory/test_credentials.md`.
