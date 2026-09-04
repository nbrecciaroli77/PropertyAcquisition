# IDEA-010 Property Acquisition — PRD / working memory

Last updated: June 2026. Owner: Nick Brecciaroli. Working name **Property Acquisition** (IDEA-010 lineage, no invented brand).

## Original problem statement

Build IDEA-010 Property Acquisition as an initial private responsive-web prototype following the supplied runbook (prompts 00–07). Prompt 00 (plan) was approved with amendments; Prompt 01 (Milestone 1: foundation, repository and visual system) has been delivered. Each milestone ends with lint/typecheck/tests/responsive screenshots, a named checkpoint, Save to GitHub (owner action) and a hard stop for review.

## Hard boundaries (do not violate in any future session)

- No connection to, copy from, edit of or sync with Nick's live Google Drive, Gmail, property portals or ChatGPT tasks. The six README-FIRST links are human reference only.
- Synthetic fixtures only (`fixtures/demo-data.json`, `digest-reference.html`).
- Private prototype, not a public commercial launch. Never label it production-ready.
- Never implement: scraping, agent sending, offers, bookings, billing, native apps, or Value Score (no flag, no code path).
- Unknown is a first-class value — never coerced to zero, false, pass or fail.
- A known hard failure can never be promoted by high preference fit.
- Keep unit suffixes distinct: 81A and 81C must never merge.
- Drafts do not send. Calendar reminders do not book. Advertised inspections are not confirmed attendance.
- `workspace_id` is never accepted from the client; authority comes from authenticated membership.
- Secrets never in prompts, repo, fixtures or logs. Never request pasted git credentials.

## Authority

`IDEA-010-Product-Definition-and-Build-Specification.md` wins over concept images. Resolved conflicts: no Map or Comparables page; no Indicative Value / Value Score.

## Source pack location

`/app/starter/emergent_pack/` — README-FIRST.md, build specification, prompt runbook, `fixtures/` (copied to `/app/fixtures/`), `concept-images/` (25 PNGs; mapping in `/app/docs/concept-image-map.md`).

## Architecture (approved, with owner amendments)

- Client: React 18 + TypeScript (strict), react-scripts, Tailwind driven only by CSS variables generated from `fixtures/design-tokens.json` (`frontend/scripts/sync-design.mjs`), Radix primitives, lucide-react, CSS motion with reduced-motion respect. Jest + RTL + jest-axe; Playwright for e2e/responsive screenshots.
- API: Python 3.11 + FastAPI + Pydantic v2, all routes under `/api`. Substitution from Node accepted by owner.
- Database (from M2): **owner's Supabase Free PostgreSQL** + SQLAlchemy 2.0 + Alembic. Never Neon. `DATABASE_URL` outstanding. Tenant isolation: app-layer `ScopedRepository` + DB constraints + **Supabase RLS wherever compatible**, build-failing cross-tenant suite, limitations recorded explicitly.
- Jobs: DB-backed durable job table, in-process scheduler with locking claims.
- Email: null provider + durable outbox; delivery suppressed. Auth: email/password only (from an `integration_expert` playbook); Google deferred (OFF), Apple locked OFF; AI extraction OFF (deterministic parser).
- Feature flags live in `backend/app/core/config.py` and are exposed at `GET /api/meta`.

## What's been implemented

- **June 2026 — Milestone 1 complete** (`/app/docs/M1-report.md`). Backend scaffold (`/api/health`, `/api/meta`, flag registry, correlation IDs, safety tests). Frontend: token-driven design system, public Welcome/Sign in (providers disabled, no-Gmail statement) and About, Terms/Privacy, authenticated shell (desktop rail / tablet icon rail / phone bottom nav), routes Today, Discover, Pipeline, Compare, Saved, Tasks, Agents, Sources, Settings, More, Property detail, shared components (PropertyCard, StatusChip, EvidenceState, SourceFreshness, FitRing, Empty/Error/Skeleton, ConfirmDialog, CompareRow), a11y foundations, PWA manifest + shell SW. Lint/typecheck/30 unit tests/75 Playwright checks/5 pytest all green. Screenshots in `frontend/e2e/screenshots/`.

## Prioritised backlog

- **P0 / blocked on owner** — Review of M1; Save to GitHub with checkpoint `checkpoint/m1-foundation`; approval to start M2.
- **P0 / blocked on credential** — Supabase `DATABASE_URL` before M2.
- **P1 — M2** auth (email/password via `integration_expert` playbook), workspace/membership, journeys, onboarding (`/app/journeys/new`), versioned brief (`/app/brief`, `/app/brief/locations`), tenancy suite, Alembic migrations, seed/reset, RLS where compatible.
- **P1 — M3** property domain, gates_v1/scoring_v1 (replace display placeholders in `frontend/src/lib/synthetic.ts`), Discover master-detail, compare selection, shortlist transitions, real server clock (replace `lib/clock.ts`).
- **P1 — M4** intake events, idempotency, CSV/manual/pasted-text, dedupe with undo/split.
- **P2 — M5** tasks/ICS, UNSENT drafts, notification centre, digest preview + outbox.
- **P2 — M6** privacy, lifecycle, audit, export/delete, WCAG pass, hardening.
- **P2 — M7** acceptance gate; private preview only after explicit approval.

## Next task

Stop for owner review of Milestone 1. On approval and receipt of the Supabase `DATABASE_URL`, start Milestone 2 per Prompt 02 (call `integration_expert` for auth first).
