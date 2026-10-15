# U0 Recovery Verification Report — Property Acquisition uplift v2.0

Date: 15 October 2026. Scope: **U0 recovery verification only** — re-check whether the database blocker
identified in `docs/uplift/U0-report.md` has cleared. **U1 was not started.** No application code, data,
feature flags, schedules, integrations, signup behaviour, or credentials were changed. No retries beyond a
single confirming pass were performed; the database, infrastructure, and connection architecture were left
untouched.

## 1. Prior report preserved and sanitised

`docs/uplift/U0-report.md` (written in the previous audit session) was reviewed before this pass. Two items
were redacted before this repo-committed copy:

- The Supabase project ref/tenant identifier that appeared inside `DATABASE_URL`/the pooler error text —
  replaced with `<project-ref>` throughout, since this report is committed to a confirmed-public GitHub
  repository and a project ref is infrastructure-identifying information.
- The owner's real personal email address that had been quoted once as an example of an unrecorded login —
  removed; no real credentials are written in either report.

No other secrets, tokens, passwords, or private-reference pack content (see U0-report.md §6) were present or
are present in either file.

## 2. Database connectivity re-check (single pass, existing configuration, no changes)

Using the **same, unmodified** `backend/.env` `DATABASE_URL` (Supabase session pooler,
`aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres`):

| Check | Result |
|---|---|
| `alembic current` | **Fails** — identical error to the prior session: `asyncpg.exceptions.InternalServerError: (ENOTFOUND) tenant/user postgres.<project-ref> not found` |
| `GET /api/readiness` (live) | `503 {"status":"not_ready"}` |
| `GET /api/health` (live) | `503 {"status":"degraded","database":"unavailable"}` |
| DNS for `<project-ref>.supabase.co` | **Changed since the prior session** — now resolves (previously NXDOMAIN) to Cloudflare-fronted IPs |
| `GET https://<project-ref>.supabase.co/rest/v1/` (no real key, diagnostic only) | `401 {"message":"Invalid API key",...}` — this is the **normal** response from an active, non-paused Supabase project queried without a valid key |

**Precise conclusion:** the database is **still unreachable from this environment via the configured pooler
connection string.** The failure signature is unchanged from the previous audit — Supavisor (the Supabase
pooler) does not recognise the tenant/project reference embedded in the `DATABASE_URL` username
(`postgres.<project-ref>`). However, one new fact narrows the cause: the project's own REST API now responds
normally (`401 Invalid API key`, not a "paused project" or DNS failure) — this is the behaviour of an
**active, running** Supabase project, not a paused one. This rules out "the whole project is paused" as the
explanation and points instead at something specific to the pooler/session-pooler tenant mapping for this
project ref — e.g. the pooler connection string, mode, or credentials on file may need to be regenerated from
the current Supabase project dashboard (Settings → Database → Connection pooling). This is an **infrastructure
configuration question for the owner to resolve directly in the Supabase dashboard**, not something correctable
by retrying, recreating the database, or changing this application's connection architecture — none of which
were attempted, per instruction.

No further connection retries were made after this single confirming pass.

## 3. Consequence — downstream checks not run

Because connectivity did not succeed, the following checks specified for the "if connectivity succeeds" branch
were **not run** (correctly, per instruction — not attempted, not silently skipped):

- Comparing the actual live Alembic revision against the repository's file-chain migration head
  (`c8d5e2f9a4b1`, computed from `backend/alembic/versions/*` in the prior audit — unchanged, still believed
  accurate for the repository, but **still not confirmed against the running database**).
- Focused baseline checks against disposable resources: authentication, tenant isolation, report generation.
- Any read or write against owner data (correctly never attempted).

## 4. Confirmation of unchanged constraints

- Signup behaviour: unchanged. `POST /api/auth/signup` still returns `403 signup_disabled` per the existing
  `SIGNUP_ENABLED=false` configuration (code path unmodified; not re-exercised live this pass to avoid an
  unnecessary extra DB-dependent call while the database is known to be down).
- No real login credentials were stored in this or the prior report.
- No integrations, workers, email delivery, or schedules were enabled, started, or configured. `DEV_ROUTES_ENABLED`
  and `APP_ENV=production` remain unchanged.
- No application code, migration, or architecture file was modified. The only repository changes across both
  sessions are: `.gitignore` (excludes the private-reference uplift pack from the public repo),
  `memory/PRD.md` (append-only audit note, no milestone history rewritten), `docs/uplift/U0-report.md`, and
  this file.

## 5. Credits

Actual credits consumed: **unavailable** — no credit/usage metering API is exposed to this environment to
query programmatically. Starting balance reported by the owner for the U0 audit: 462.12 (carried over from
the prior report; not re-verified here as no such verification method exists in this session).

## 6. Can U1 safely begin?

**No.** U1 depends on being able to run additive migrations and disposable-fixture regression tests against a
reachable database. The database is confirmed still unreachable via the existing, unmodified configuration.

**Recommended next step before any U1 work:** the owner should open the Supabase dashboard for this project,
confirm the project is not paused (the REST API response in §2 suggests it is not), and regenerate/re-copy the
exact session-pooler connection string from **Settings → Database → Connection pooling**, then update
`backend/.env` `DATABASE_URL` accordingly. Once that is done, request another U0 recovery verification pass
before U1 begins.

Stop. Awaiting the next instruction.
