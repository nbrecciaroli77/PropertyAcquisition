# IDEA-010 Property Acquisition — PRD / working memory

Last updated: June 2026. Owner: Nick Brecciaroli. Working name **Property Acquisition** (IDEA-010 lineage, no invented brand).

## Original problem statement

Build IDEA-010 Property Acquisition as an initial private responsive-web prototype. Prompt 00 of the supplied runbook required a plan only — file receipt confirmation, requirements map (Built now / Deferred / Blocked), concrete stack proposal, explicit disclosure of every substitution from the preferred TypeScript + React + Node + PostgreSQL direction, an explanation of tenant isolation / idempotent intake / migrations / seed-reset / feature flags / tests, a milestone plan matching prompts 01–07 with checkpoints and rollback, and only architecture-material questions. Implementation was explicitly forbidden in this step.

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
- Secrets never in prompts, repo, fixtures or logs.

## Authority

`IDEA-010-Product-Definition-and-Build-Specification.md` is the accepted scope and wins over the concept images where they conflict. Two known conflicts already resolved: no Map or Comparables page, and no Indicative Value / Value Score (both appear only in `00-design-system.png`).

## Source pack location

`/app/starter/emergent_pack/` — README-FIRST.md, build specification (.md + .docx), prompt runbook (.md + .docx), `fixtures/` (4 files), `concept-images/` (25 PNGs, all verified readable).

## Architecture (approved direction)

- Client: React 18 + TypeScript, react-scripts, Tailwind driven by CSS variables generated from `design-tokens.json`, Radix primitives, lucide-react, Motion with reduced-motion respect.
- API: Python 3.11 + FastAPI + Pydantic v2, modular monolith, all routes under `/api`. **Substitution from Node** — forced by the read-only supervisor config that hard-codes `uvicorn server:app`.
- Database: managed PostgreSQL (Neon/Supabase) + SQLAlchemy 2.0 + Alembic. Authorised by owner. `DATABASE_URL` outstanding.
- Jobs: DB-backed durable job table, in-process scheduler with locking claims (no broker available; single-replica constraint documented).
- Email: pluggable provider, default null provider + durable outbox, delivery suppressed.
- Tenant isolation: `ScopedRepository` injecting `workspace_id`, 404-not-403 on non-membership, build-failing tenancy suite. Weaker than DB-enforced RLS — recorded in the limitations note.
- Full plan, including the substitution table and compensating controls: `/app/memory/PLAN-00-master-build-plan.md`.

## What's been implemented

- **June 2026** — Nothing. Prompt 00 planning deliverable only (`/app/memory/PLAN-00-master-build-plan.md`). `/app` has no backend or frontend scaffold. Owner placed the build ON HOLD after reviewing the plan.

## Prioritised backlog

- **P0 / blocked on owner** — Approval to start milestone 1 (foundation, repo scaffold, visual system). No database needed for this milestone.
- **P0 / blocked on credential** — `DATABASE_URL` for managed PostgreSQL, required before milestone 2.
- **P1** — M2 auth + workspace + versioned brief (auth code must come from an `integration_expert` playbook, never improvised).
- **P1** — M3 property domain, hard gates, fit vs evidence coverage, compare, shortlist.
- **P1** — M4 intake events, idempotency, CSV/manual/pasted-text intake, conservative dedupe with undo/split.
- **P2** — M5 tasks, ICS, UNSENT drafts, notification centre, digest preview + outbox.
- **P2** — M6 privacy, lifecycle, audit, export/delete, WCAG 2.2 AA pass, security hardening.
- **P2** — M7 final acceptance gate, then private preview only after explicit approval.
- **Later gates (not authorised)** — transactional email provider, Google/Apple sign-in, AI extraction enablement, inbound email, licensed feeds, read-only Hub migration rehearsal.

## Next task

Wait for owner approval. On approval, start milestone 1 per prompt 01 and stop for review at the checkpoint.
