# Milestone 2 report — Authentication, workspace and the versioned buying brief

Date: 4 September 2026 · Gate: initial private prototype · Working name: "Property Acquisition" (working concept)

## What Milestone 2 delivers

Milestone 1 gave the shell its shape with synthetic fixtures. Milestone 2 makes the workspace real:
accounts, a tenant boundary, a resumable guided setup, and a buying brief that is versioned, validated
and immutable once published.

### Accounts (email and password only)

- `POST /api/auth/signup` creates the user, their workspace and an `owner` membership, then queues a
  verification message. It deliberately **does not** sign the person in — the response is
  `{"status": "verification_pending"}` and the UI lands on `/verify-pending`.
- Signing in before verification returns `403 email_not_verified` and reissues the link, so the person is
  routed back to the pending screen rather than into a half-built workspace.
- Verification and reset tokens are single use, hashed at rest (SHA-256), and expire (24 hours and 1 hour).
- Sessions are server-side and revocable. The access token (15 minutes) carries a session id that is
  checked against `auth_sessions` on every request, so "sign out of all devices" and a password reset take
  effect immediately rather than after the token expires. Refresh tokens (7 days) rotate on use.
- Cookies are `httpOnly`, `Secure`, `SameSite=None`, because the preview serves the client from a different
  host to the API. A readable `pa_signed_in` marker cookie (no payload) lets the client skip the session
  bootstrap when nobody is signed in.
- Failed logins are counted against the normalised email **and** the first hop of `X-Forwarded-For`:
  5 failures per email or 20 per address in 15 minutes returns `429` with `Retry-After`. The socket peer
  address alone is useless here because the ingress rotates proxy pods — the first QA pass caught exactly
  that and it is now covered by `tests/test_rate_limit.py`.
- Google and Apple sign-in remain visible and disabled, with the statement that Google identity would only
  ever identify you and never implies access to your Gmail.

### Email delivery is suppressed, not faked

No transactional provider is configured, so every message is written to `outbox_messages` with
`delivery_state = suppressed_no_provider` and never sent. The owner completes account flows from the
development-only `/dev/outbox` view (`GET /api/dev/outbox`), which returns `404` outside development.
This is the one deliberate prototype affordance in Milestone 2 and it is removed before any private preview.

### Workspace and tenancy

- Every workspace-owned row carries `workspace_id`; the value is resolved from the authenticated membership
  and is never accepted from the client (extra body fields are rejected with `422`).
- Cross-tenant reads and writes return `404`, never `403` — a foreign id is indistinguishable from a missing
  one. Negative tests cover deep links, draft writes, publication and renames.

### Guided setup

Six steps: journey name and state, purchase timing, property type, budget and price policy, first locations,
review. Every step persists, "Save and finish later" keeps your place, and the page resumes at the saved step
with a notice. Buttons stay disabled while the journey loads, and a version conflict refetches and retries once
instead of stranding you on an error.

### The versioned buying brief

- Every criterion is **Hard rule**, **Preference**, **Disabled** or **Unknown**, with plain-language help under
  each control. Unknown is never coerced to zero, false, pass or fail.
- Money is stored as integer minor units with a currency; areas are canonical square metres; travel time is
  explicitly Unknown until a provider and its assumptions exist.
- Publication validation is field-linked and blocking: contradictory bounds, a hard rule with no value, an
  area both included and excluded, or zero enabled preference weight all block publication and are listed
  against the exact field.
- Publishing writes an immutable `brief_versions` row (version number, payload, actor, reason, timestamp) and
  queues re-evaluation. Version history shows who published what, when and why. Drafts are saved separately
  and publishing never sends anything to anybody.
- Preference weights are editable per criterion with an enable toggle, a live enabled total, and a
  "Reset to 30 / 30 / 20 / 20" action. A weight can never promote a known hard failure.

## Data model (Alembic revision `4bb12e1e9183`)

`users`, `workspaces`, `memberships` (unique per workspace and user, role checked), `auth_sessions`,
`auth_tokens`, `outbox_messages`, `login_attempts`, `journeys` (holds the draft payload, onboarding step and
`row_version` for optimistic concurrency), `brief_versions` (unique per journey and version number),
`audit_events`.

Database: the owner's Supabase Free project, reached through the session pooler
(`aws-0-ap-southeast-2.pooler.supabase.com`) because this pod has no IPv6 route to the direct host.
Migrations run with `alembic upgrade head`; `python -m scripts.seed` is idempotent (owner, a second tenant
and a lockout-drill account), `python -m scripts.reset --confirm` clears prototype data, and
`python -m scripts.unlock <email> [ip] | --all` clears a brute-force lockout.

## Test coverage

| Suite | Scope | Result |
| --- | --- | --- |
| `backend/tests/test_auth.py` | signup, verification, single-use tokens, login, logout-all revocation, reset, lockout, anonymous rejection | pass |
| `backend/tests/test_rate_limit.py` | lockout with a rotating client IP, no collateral lockout, marker cookie, session cap | pass |
| `backend/tests/test_tenancy.py` | cross-tenant reads and writes, client-supplied `workspace_id`, anonymous deep links | pass |
| `backend/tests/test_brief.py` | validation blockers, Unknown never blocking, immutable versions, stale `row_version`, weight reset, resumable onboarding | pass |
| `backend/tests/test_system.py` | health with the database, flags, `/api` prefix, forbidden route fragments, correlation id, cross-origin writes | pass |
| `backend/tests/test_m2_public.py` | 41 cases over the public ingress with a cookie jar (added by the QA pass) | pass |
| `frontend` Jest | 47 tests: public pages, authenticated shell, account screens, brief editor and validation, axe checks | pass |
| `frontend` Playwright | 5 viewports (1440, 1024, 390, 412, 320) across public and authenticated screens: one `h1`, no horizontal overflow, navigation adaptation, skip link, brief editor | pass |

## Known limitations at the end of Milestone 2

- Property, gate and matching data on Today, Discover, Pipeline, Compare, Saved, Tasks, Agents, Sources and
  property detail is still the Milestone 1 synthetic fixture. Real evidence, gates and fit arrive in Milestone 3.
- API latency is roughly 0.5–1.5 seconds per call because the Supabase project is in `ap-southeast-2` and this
  pod is not. Every screen has an explicit loading state; nothing is cached across pages yet.
- Re-evaluation after publication is recorded as `queued` only. The job that consumes it arrives in Milestone 3.
- Household invitations, additional roles, export, deletion jobs and audit browsing are Milestone 6.
- "Add property" (Milestone 4) and "Add reminder" (Milestone 5) remain deliberate placeholders.
- The development outbox is unauthenticated by design so account flows can be completed before sign-in; it is
  disabled outside development and must not exist in a private preview.
