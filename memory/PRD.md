# IDEA-010 Property Acquisition — Product requirements and status

Working name: "Property Acquisition" (working concept, not final). Gate: **initial private prototype**.
Last updated: 14 September 2026 (Prompt 05.1 complete — checkpoint/m5-1-notifications-reminders).

## Execution state

| Prompt | Scope | Status |
|--------|-------|--------|
| 00–03 | Foundation, design system, auth, tenancy, buying brief, property workspace | **Complete** |
| Security hotfix | `/api/dev/*` deny-by-default, outbox purge, token invalidation | **Complete** — `checkpoint/security-public-dev-surface` |
| **03A** | Post-M3 foundation alignment — connector catalog, source readiness, sender aliases, discovery/intake attribution, scheduler observability, enrichment records, report-run metadata | **Complete** — `checkpoint/m3a-foundation-alignment` |
| **04.1** | Manual property intake (structured form, URL + facts, pasted text), durable IntakeEvent, workspace-scoped idempotency, exact-address duplicate detection, deterministic text parser v1.0 | **Complete** — tested 12/12 scenarios |
| **04.2** | CSV intake (preview, server-authoritative re-parse, formula-injection protection), duplicate review (merge/split/undo, 81A/C warning, snapshot-based undo), sources & coverage screen (all required fields, read-only, synthetic), sender-alias review (demo workspace only) | **Verified** — `checkpoint/m4-2-verified` |
| **05.1** | Durable in-app notification domain, task CRUD/reminders, preferences, manual-only processing and local ICS export | **Complete** — `checkpoint/m5-1-notifications-reminders` |
| **05.2** | Digest/report previews plus essential privacy, export and deletion functions | **Next** |
| **Production Hardening** | Security, accessibility, configuration, backups, monitoring, recovery, final go/no-go | **Backlog** |

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
| 4.1 | Manual property intake (structured form, URL + facts, paste), IntakeEvent, idempotency, duplicate detection | **Done** — `checkpoint/m4-1-manual-intake` |
| 4.2 | CSV intake, duplicate review (merge/split/undo, unit-suffix warning), sources & coverage (all fields, read-only), sender-alias review (demo only) | **Verified** — `checkpoint/m4-2-verified` |
| 5.1 | In-app notification centre/settings, task management, deterministic reminders and ICS download | **Complete** — `checkpoint/m5-1-notifications-reminders` |
| 5.2 | Digest/report previews plus essential privacy, export and deletion functions | **Planned — Next** |
| Hardening | Security, accessibility, configuration, backups, monitoring, recovery, final go/no-go | **Planned** |

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

### M4.2 acceptance verification — 14 September 2026

- Live migration state confirmed at sole head `a8d2e3f4b5c6`; M4.2 revision is
  `a8d2e3f4b5c6` (parent `f3c9b21a5d8e`).
- Disposable database suite: `test_m4_2_verification.py` **8/8 passed** — CSV preview/revalidation,
  full-file and row idempotency, formula inertness/no fetch, duplicate actions and snapshot undo,
  merge-cycle prevention, 81A/81C separation, first discovery, tenancy, concurrency, aliases and
  dev-route protection.
- Disposable database rollback suite: `test_m4_2_migration_rollback.py` **1/1 passed** — upgrade to
  M4.2, downgrade to M4.1, then re-upgrade to the sole head. Live Supabase was queried read-only and
  was never downgraded, reset or seeded.
- Existing backend authentication/security regression: **16/16 passed**. Frontend Jest suite:
  **53/53 passed**; `yarn typecheck` and production `yarn build` both passed.
- Minimal verification-only correction: updated the stale shell navigation expectation to include the
  already-delivered Duplicate Review route. No application behavior changed.

### M5.1 notifications, tasks, reminders and ICS — 14 September 2026

- Added additive revisions `e9f3b2c1d7a4` (notification/task domain) and `f4a8c6d2e1b9`
  (manual reminder job constraint); current sole Alembic head is `f4a8c6d2e1b9`.
- Added durable workspace-scoped notification events, recipient inbox state, in-app delivery audit and
  requested/effective preferences. Every event uses an idempotent workspace fingerprint and deterministic
  delivery only; Email/Both remain visible but disabled/rejected with no provider connected.
- Added task create/view/edit/complete/reopen/delete with workspace checks, optional property links,
  assignee validation, optimistic concurrency and audit activity. The manual-only reminder processor
  records disabled scheduled-job/job-run observability and handles due-soon, overdue and explicit reminders.
- Added local individual-task ICS download with stable UID, IANA timezone, due time, description/property,
  internal application URL and generation stamp. It makes no calendar, booking, contact or network action.
- Seeded notification/task examples exclusively for the labelled demo workspace. Fresh workspaces retain
  empty notifications and task lists.
- Verification: M5.1 focused backend **6/6 passed** after one forward-only check-constraint correction;
  affected backend regression evidence **29/29 passed**; focused frontend M5.1 rerun **2/2 passed**;
  production TypeScript build and typecheck passed. Targeted desktop and iPhone inbox smoke flows passed.
- No email, calendar provider, push, external API or production scheduler was added or invoked. Existing
  Supabase data was only migrated additively; no reset, downgrade or destructive operation occurred.

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

### M5.2 report previews, exports and account/workspace deletion — 14 September 2026

- Added additive revision `b7c4d1e8f2a3` (report_type/period/cutoff/timezone/snapshot columns on
  `report_runs`, plus new `report_preferences`, `data_exports`, `deletion_requests` tables); sole
  Alembic head is now `b7c4d1e8f2a3` (parent `f4a8c6d2e1b9`).
- Report generation: `app/services/reports.py` builds deterministic daily/weekly/monthly snapshots from
  live evidence only (Unknown stays Unknown; no invented travel/price/coverage). Idempotency key covers
  report type + release kind + exact period + generation version, so repeat "Generate preview" requests
  return the same run and never create a duplicate `digest_ready`/`weekly_report_ready`/
  `monthly_report_ready` notification. Daily uses a rolling calendar-day window with cutoff=now; weekly
  is an exact trailing 7-day Australia/Perth window; monthly is the previous calendar month, labelled
  `is_partial_period` when the workspace has less history than the month requires.
- Reports UI at `/app/reports` (also linked from the rail nav and the Today page): Daily/Weekly/Monthly
  tabs, "Generate preview" button, latest preview with preview/state badges, previous-runs history list,
  print/PDF button. Fixed a testing-agent-found cold-navigation flash (empty state showed before
  `useJourneys()` finished loading) by gating on the `loading` flag.
- Report generation *schedule* preferences (`report_preferences` table, distinct from the M5.1
  notification-category preferences) are exposed in Settings → Notifications via `ReportPreferences.tsx`:
  daily time+weekdays, weekly day/time, monthly day/time, timezone, requested vs. effective channel
  (email/both always rejected 422 `email_provider_not_connected` and rendered inert). No scheduler reads
  these yet — generation stays manual/on-demand only.
- Data export (`app/services/exports.py`, `app/api/exports.py`): personal export (profile, memberships,
  notifications, tasks, audit) and owner-only workspace export (brief versions, properties, buyer
  workflow, campaigns, observations/facts, evaluations/waivers, notes/tasks, intake/discovery history,
  duplicate decisions, notification/report history, source config/readiness, audit) are built on demand
  as an in-memory ZIP and stored as `bytea` directly in Postgres (no object storage / external service),
  expiring after 24h. Excludes password hashes, session/refresh/reset tokens and credential references by
  construction. UI at Settings → "Open data & privacy" (`/app/settings/privacy`).
- Account/workspace deletion (`app/services/deletion.py`, `app/api/account.py`): request needs a fresh
  password check + typed `"DELETE"` confirmation, enters a 72-hour cooling-off (`pending_cooloff`) and can
  be cancelled any time before execution. Distinguishes `leave_workspace` / `delete_account` /
  `delete_workspace`, blocking any path that would orphan a shared workspace
  (`ownership_transfer_required` / `sole_owner_cannot_leave`). Execution (`process_due_deletions`) revokes
  all sessions, anonymises the user row, cascades deletion of any solely-owned workspace, purges the
  user's exports, and never touches another workspace — only reachable via the dev-gated
  `/api/dev/process-deletions` route (404 unless `DEV_ROUTES_ENABLED=true`) or the manual
  `scripts/process_deletions.py`; no production scheduler was added.
- Verification: new `tests/test_m5_2_privacy.py` — **14/14 passed** against the live Supabase DB using
  disposable synthetic accounts under `m52tests.pa-prototype.com` (idempotency + notification dedup,
  Perth timezone period boundaries, quiet-day + Unknown preservation, partial-period monthly, cross-tenant
  report isolation, requested-vs-effective channel rejection, export contents/secret exclusion,
  export owner-only + isolation, export expiry, deletion reauth/typed-confirmation errors, ownership
  transfer blocking, cancel flow, isolated execution with session revocation + workspace cascade delete,
  no email queued for any of the above). All disposable test users/workspaces cleaned up after the run;
  confirmed `owner@`/`other@propertyacquisition-demo.com` untouched (`deleted_at` still `None`).
  `yarn tsc --noEmit` clean. Frontend testing agent run: 11/11 scoped features passed; one LOW-priority
  cold-navigation UX bug found and fixed (see above).
- No email, Gmail, Google Drive, external API or production scheduler was added or invoked. Live
  Supabase data was only migrated additively; demo owner/other accounts were never mutated destructively.
- Checkpoint: `checkpoint/m5-2-reports-privacy`.
