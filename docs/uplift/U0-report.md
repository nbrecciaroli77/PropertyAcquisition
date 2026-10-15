# U0 Audit Report — Property Acquisition uplift v2.0

Date: 15 October 2026 (audit session). Scope: **U0 only** (audit/baseline). No application code, data,
feature flags, schedules, integrations, or credentials were changed. No live mutation occurred.

## 1. Baseline identity

| Item | Value |
|---|---|
| Local workspace HEAD | `19c8338cb3f44bad78994f09e830e5992f0ddfe9` ("Auto-generated changes", 2026‑10‑15 04:31 UTC) |
| GitHub `main` HEAD (verified via GitHub API, live) | `19c8338cb3f44bad78994f09e830e5992f0ddfe9` — **in sync with workspace** |
| Repository visibility (verified via GitHub API, live) | **Public** (`private: false`) — confirms spec's assumption; no pack content may be committed |
| Spec's "reviewed main" | `c0751038a2569339b02634c57122a040999a2333` (2026‑09‑14 13:50 UTC) |
| Diff between `19c8338` and reviewed `c075103` | 2 commits (`b3642ad`, `19c8338`), both touch **only** `.emergent/emergent.yml` / `.emergent/system_deps.txt` (platform metadata). **No application code, migration, or test file changed.** |
| Recorded hardening commit (spec) | `908bb6c2463dd33e7c18506e0a07d2608a928abc` — **confirmed present**, tagged `checkpoint/m6-2-private-mvp-live`, message "M6.2: Production hardening…" |
| Uncommitted/newer work | **None found.** `git status` is clean except the newly-added, now `.gitignore`-excluded `/app/reference/` (this uplift pack's extracted contents — see §6). |
| Other checkpoint tags present | `m3a-foundation-alignment`, `m4-2-intake-review`, `m4-2-verified`, `m5-1-notifications-reminders`, `m6-2-private-mvp-live`. `m5-2-reports-privacy` and `m6-1-product-alignment` exist as **branches**, not tags. |

**Conclusion:** the Emergent workspace, local git, and public GitHub `main` are all at the same reviewed,
hardened M6.2 state. Nothing needed to be preserved beyond what the spec already assumed.

## 2. Alembic migration head

- File-chain head computed from `backend/alembic/versions/*` (`down_revision` chain):
  `4bb12e1e9183 → 2fc5f4775fef → 2105faf7bef7 → f3c9b21a5d8e → a8d2e3f4b5c6 → e9f3b2c1d7a4 → f4a8c6d2e1b9 → b7c4d1e8f2a3 → c8d5e2f9a4b1`.
  **Sole file-chain head: `c8d5e2f9a4b1`** — matches the spec's recorded head.
- **Could not confirm this against the running database** (per instruction, this was not assumed). See
  blocker in §3 — the configured Supabase project is currently unreachable from this environment, so
  `alembic current` / `SELECT * FROM alembic_version` could not be executed.

## 3. Critical blocker — live database unreachable (confirmed, not hypothesis)

- `backend/.env` `DATABASE_URL` points at the project's Supabase session pooler
  (`aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres`; exact project ref/tenant redacted here since
  this report is committed to a public repository).
- `alembic current` fails: `asyncpg.exceptions.InternalServerError: (ENOTFOUND) tenant/user <project-ref> not found`.
- `GET /api/readiness` → `503 {"status":"not_ready"}`; `GET /api/health` → `503 {"status":"degraded","database":"unavailable"}` (both live, confirmed just now).
- `POST /api/auth/login` with the owner credentials → `500` with a correlation id (no stack trace leaked — the
  production error handler itself is working correctly). Backend log for that correlation id traces the 500
  to `app/api/auth.py::_failures_since` failing to open a DB connection — **same root cause, not a separate auth bug.**
- Network diagnosis performed (read-only, no mutation):
  - TCP to the pooler host (`aws-0-ap-southeast-2.pooler.supabase.com:5432`) **connects fine** — network egress/DNS for the pooler itself is not the problem.
  - DNS for the project's own `<project-ref>.supabase.co` domain **fails to resolve at all** (`curl: (6) Could not resolve host`).
  - This combination (pooler reachable, tenant not recognised + project domain NXDOMAIN) is consistent with the
    **Supabase project being paused or no longer existing** under that ref — not a pod/network defect on this side.
- **Effect on this audit:** every DB-backed check (login, journeys, reports, exports, pytest suites that touch
  the database) could not be run live. This is recorded as *unsafe/unavailable, not run*, not as a silent pass.
  `yarn tsc --noEmit` (frontend, no DB dependency) was run and passed clean (0 errors).
- **Action needed from the owner before any further package (U1+) or re-verification:** open the Supabase
  dashboard for the configured project and confirm/un-pause it, or issue a corrected `DATABASE_URL`.
  This is outside what an audit-only, no-live-mutation pass may attempt to fix.
- **Backup/restore claim not independently verifiable:** `memory/PRD.md` states "Supabase Free plan provides
  daily backups with 1‑day retention… PITR requires Pro." This could not be checked against the actual Supabase
  dashboard/management API in this session (no such access was available, and the project itself is
  unreachable). Treat as **unverified**, not confirmed, until checked directly in the Supabase dashboard.

## 4. Confirmed code-level findings (evidence-based, not hypotheses)

### 4a. R1 — report idempotency key omits `journey_id` (confirmed defect)

`backend/app/services/reports.py:598-600`:
```python
idem_key = f"{report_type}:{release_kind}:{period_start.isoformat()}:{period_end.isoformat()}:{generation_version}"
existing = await db.execute(select(ReportRun).where(
    ReportRun.workspace_id == journey.workspace_id, ReportRun.idempotency_key == idem_key))
```
The lookup filters by `workspace_id` + `idempotency_key` only — **not** `journey_id`. Today there is one
journey per workspace in practice, so this is latent. The moment a workspace has two journeys/campaigns
(e.g. the planned house + Down South Land campaigns) generating the same `report_type`/`release_kind` for
the same period, the second campaign's call returns the **first campaign's `ReportRun`** at line 604-605
(`if existing... return existing`) — a cross-campaign data leak, exactly as the spec's R1 describes. This is
U1's primary acceptance target; no fix was made in this audit.

### 4b. R6 — report validation is section-key + title only (confirmed gap, not a bug)

`backend/app/services/reports.py::_assert_contract` (lines 92-98) checks only `key not in snapshot` (presence)
and an exact `title` string match. It does **not** validate link/href correctness, image provenance/type,
stale-value detection, or nested nested coverage/footer content — the full structural/visual validation R6
and U5 require. Current behaviour matches the spec's description precisely ("section-key-only report
validation").

### 4c. R2/R3/R4/R5/R7/R8 — gap matrix by requirement

| Req | State found | Evidence |
|---|---|---|
| R1 Campaigns/config | **Confirmed defect** (above) + no versioned per-campaign override/activation model yet | `reports.py:598-600`; no `campaign_profile`/override tables in `app/db/models.py` |
| R2 Existing house campaign | **Built** (M2/M3), brief/gates/scoring unchanged, no Value Score | `app/services/matching.py`, PRD M2/M3 sections |
| R3 Land feasibility profile | **Not started** | `grep -rni "LAND_FEASIBILITY"` → no matches anywhere in `app/` |
| R4 Intake & source coverage | **Partial** — manual + CSV intake and duplicate review built; source rights defaults correct (`redistribution_allowed`/`attribution_text` seeded, only `email-inbound` is `true`); no mailbox/email adapter, triage, or per-source readiness milestones yet | `app/api/intake.py`, `app/api/csv_intake.py`, `scripts/seed.py:78-196`; `grep` for `imap\|gmail\|inbound_email` finds only an enum placeholder in `models.py:565` |
| R5 Evidence capture | **Not started** | No `Capture` route/component anywhere in `app/` or `frontend/src` |
| R6 Report releases/presentation | **Partial** (above) | `reports.py:51-98` |
| R7 Durable delivery/recovery | **Partial foundation only** — `ReportRun` has `ready`/`ready_to_send` states and `mark_ready_to_send` (immutable snapshot, 409 on repeat); **no** outbox/queue, `CLAIMED`/`SENT`/`DELIVERY_FAILED`/`DELIVERY_UNCERTAIN` states, claim/lease, or sender process exist | `reports.py:653-669`; `app/db/models.py` (`OutboxMessage` is the unrelated M2 email-verification outbox, not a report-sender queue) |
| R8 Scheduling/analytics/health | **Partial foundation only** — `ScheduledJob` rows seeded with `enabled=False` always, `JobRun` telemetry appended on generate/ready-to-send; **no** actual worker/scheduler process, no watchdog | `reports.py:101-141`; `grep` for `apscheduler\|celery\|watchdog` → no matches outside this placeholder logging |

### 4d. Other confirmed findings

- **Signup gate is reactive, not proactive (UI disclosure gap).** `frontend/src/features/auth/SignUpPage.tsx`
  renders the *full* working signup form by default; `signupDisabled` (line 16) is only set `true` **after** a
  form submission returns `403 signup_disabled` (lines 33‑34). A visitor landing on `/signup` sees a fully
  functional-looking form with no up-front indication it is closed — confirmed live via screenshot. The
  backend gate itself is correct and verified live (`POST /api/auth/signup` → `403 {"detail":"signup_disabled"}`).
  `GET /api/meta` already exposes `signup_enabled: false`, so a proactive fix (check on mount) is low-risk and
  small — recommended, not executed here.
- **Stale status tables inside `memory/PRD.md`** (not rewritten, per instruction — only reconciled here):
  - The "## Milestone status" table (lines 67‑79) is stale: it lists M5.2 as "Planned — Next" and "Hardening"
    as "Planned", while the correct "## Execution state" table at the top of the same file (lines 6‑18) shows
    all milestones through 06.2 as **Complete**. The Backlog section (P0/P1, lines 129‑148) is equally stale
    ("Milestone 6.2… Awaiting explicit user approval to start", even though 06.2 is finished per the same file).
  - The "### M6.1 Pre-deployment product alignment" heading is dated **17 September 2026** (line 250), but the
    file's own top banner says "Last updated: 14 September 2026" and the underlying commit (`703e585`/`908bb6c`
    chain) is dated **14 September 2026** — exactly the discrepancy flagged by the spec. No milestone history
    was rewritten; flagging only.
- **`memory/test_credentials.md` is out of date post‑bootstrap.** It still documents the original seed
  password (`Prototype2026pass`) for `owner@propertyacquisition-demo.com` / `other@…` / lockout-drill accounts.
  `memory/PRD.md` (§M6.2, lines 302‑304) states `bootstrap_owner.py` "resets demo account passwords to random
  opaque values" during the M6.2 run. This means the documented demo passwords are very likely stale/non-working,
  and the real owner login used in this session is **not recorded** in `test_credentials.md` at all
  (that real email/password is intentionally omitted from this report). Could not be verified live
  (database unreachable — §3). Flagged as a
  documentation gap for the owner/next session to correct; **not edited here**, since U0 is audit-only and the
  instruction explicitly excludes changing credentials/files.
- **`/api/system/health` (as named in a prior hand-off note) does not exist** — the actual mounted path is
  `/api/health` (router included with prefix `/api`, no `/system` segment, `app/main.py:107`). Minor
  documentation-naming drift, not a functional defect.

## 5. Checks actually run (live, read-only, non-mutating)

- `git log` / `git status` / `git tag` / `git branch -a` — baseline identity (§1).
- GitHub REST API `GET /repos/nbrecciaroli77/PropertyAcquisition` and `/commits/main` — live, read-only,
  confirmed public visibility and HEAD sync (§1).
- `alembic current` (failed — DB unreachable, evidence captured, §3).
- DNS/TCP diagnosis of the Supabase pooler and project domain (read-only `getent`/`curl`/`/dev/tcp`, §3).
- Live HTTP probes against the deployed preview backend (`https://property-find-1.preview.emergentagent.com`):
  `/api/readiness`, `/api/health`, `/api/meta`, `/api/dev/outbox` (404, confirms dev routes locked),
  `POST /api/auth/signup` (403 `signup_disabled`, confirmed), `POST /api/auth/login` (500, traced to DB
  outage, not an auth defect), security response headers on `/api/meta` (CSP, X‑Frame‑Options,
  X‑Content‑Type‑Options, Referrer‑Policy, Permissions‑Policy, `Cache-Control: no-store` all present and
  correct).
- `backend/tests/test_system.py` (the only suite attempted, as a disposable/low-risk probe): **4 passed,
  2 failed, 1 error** — all three failures/errors trace to the same DB outage or one pre-existing stale
  assertion (`test_no_forbidden_pathways_exist` fails because the legitimate `…/ready-to-send` route contains
  the substring `"send"`; this is a test-quality issue against intentionally safe functionality, not a security
  defect — `reports.py` confirms `ready-to-send` never contacts an email provider). **No other pytest suite was
  run** — every other suite (M4.2/M5.1/M5.2/M6.1 verification suites) requires live DB writes against
  disposable synthetic accounts, which is unsafe/unavailable while the database itself cannot be reached; this
  is recorded as **not run**, not as a pass.
- `yarn tsc --noEmit` (frontend) — **passed**, 0 errors (no DB dependency).
- One frontend screenshot each of `/` (sign-in) and `/signup` — confirmed app renders; confirmed the signup
  UI gap in §4d.
- Code `grep`/read review of `reports.py`, `system.py`, `seed.py`, `SignUpPage.tsx`, `main.py`, `PRD.md`,
  `test_credentials.md`, Alembic version files — no code was modified.

**Explicitly not run (unsafe/unavailable, by design):** any pytest suite requiring live Supabase writes;
`scripts/seed.py` / `scripts/reset.py` / `scripts/bootstrap_owner.py` (would mutate data); any fixture load
against the production database; a disposable backup/restore rehearsal (requires Supabase dashboard access
not available in this session).

## 6. Pack handling

The uploaded `IDEA-010_Emergent_Uplift_v2.0.zip` was extracted to `/app/reference/IDEA-010_v2.0/` for this
session's reference. `reference-assets/source-index.json` self-declares `"private_reference_only": true` and
contains private Google Drive asset IDs; `manifest-land.json`/`manifest-padbury.json` contain approver names
and internal release metadata. Since the GitHub repository is confirmed **public** (§1), `/app/.gitignore`
was updated to add a `reference/` entry so the platform's automatic commit process cannot publish this pack.
No pack content (masters, manifests, source index) was copied into any committed/tracked file.

## 7. Proposed additive sequence (unchanged from the spec's own ordering — no new sequence invented)

U1 (campaign scoping + idempotency-key fix) → U2 (land profile) → U3 (intake/source identity) → U4 (capture)
→ U5 (report release/validation) → U6 (durable outbox/sender) → U7 (scheduler/watchdog) → U8 (migration/cutover
rehearsal). U1 should fix the confirmed `journey_id` idempotency defect (§4a) as its first acceptance item,
since it is a real, demonstrated code defect rather than a hypothetical.

## 8. Blockers carried into any next package

1. **Live database unreachable from this environment** (§3) — must be resolved (Supabase project
   unpaused/`DATABASE_URL` corrected) before any U1+ work that needs to run against a real/disposable DB, or
   before re-verifying this report's DB-dependent items.
2. Backup/restore capability is unverified (§3) — needs direct Supabase dashboard confirmation.
3. `test_credentials.md` likely stale after the M6.2 bootstrap rotation (§4d) — recommend the owner refresh it
   out-of-band before the next testing pass; not edited in this audit.

## 9. Credits

- Starting balance reported by the owner: **462.12 credits**.
- Actual usage for this U0 session: **unavailable** (no credit/usage metering API was exposed to this
  environment to query programmatically, per the spec's own instruction to mark this unavailable rather than
  guess).

## 10. Acceptance check

- Actual current baseline and gaps documented: **yes** (§1‑4).
- No live mutation performed: **yes** — only `/app/.gitignore` (repo hygiene, not app code/data/flags/schedule/
  integration/credentials) and this report file were added.
- Unsafe/unavailable tests explicitly not run, and listed as such: **yes** (§5).
- No claim of production health from historical test counts: confirmed — current live health/readiness checks
  (§3) show the database is presently unreachable, independent of any historical pass counts recorded in
  `memory/PRD.md`.

**Recommended next step:** resolve blocker #1 (Supabase reachability) first; then proceed to **U1** on
owner approval.

Stop. Awaiting the next instruction.
