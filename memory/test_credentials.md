# Test credentials — IDEA-010 Property Acquisition (Milestone 2)

Synthetic accounts only. Created by `cd /app/backend && python -m scripts.seed` (idempotent).
Reset everything with `cd /app/backend && python -m scripts.reset --confirm`.

## Owner account (primary test account)

- Email: `owner@propertyacquisition-demo.com`
- Password: `Prototype2026pass`
- Workspace: `Brecciaroli household` · role `owner`
- Journey: `Perth family home 2026` (active, brief version 1 published)
- Email is pre-verified by the seed.

## Second tenant (cross-tenant isolation checks)

- Email: `other@propertyacquisition-demo.com`
- Password: `Prototype2026pass`
- Workspace: `Second household` · role `owner`
- Journey: `Adelaide downsizer`

## Lockout drill account (use this for brute-force tests)

- Email: `lockout-drills@propertyacquisition-demo.com`
- Password: `Prototype2026pass`
- Workspace: `Lockout drill household` · journey `Drill journey`
- Exists so brute-force tests never lock the owner account. Clear a lockout with
  `cd /app/backend && python -m scripts.unlock lockout-drills@propertyacquisition-demo.com`
  (add an IP as a second argument, or `--all` to clear every recorded attempt).

## Auth endpoints

- `POST /api/auth/signup` → `{status: "verification_pending"}` (never signs you in)
- `POST /api/auth/verify-email` `{token}`
- `POST /api/auth/reissue-verification` `{email}`
- `POST /api/auth/login` → sets `pa_access` (15 min) + `pa_refresh` (7 days) httpOnly cookies
- `POST /api/auth/refresh`, `POST /api/auth/logout`, `POST /api/auth/logout-all`
- `GET /api/auth/me`, `PATCH /api/auth/me`, `GET /api/auth/sessions`, `DELETE /api/auth/sessions/{id}`
- `POST /api/auth/forgot-password`, `POST /api/auth/reset-password` `{token, password}`

## Email delivery

No provider is configured: every message lands in the durable outbox with
`delivery_state = suppressed_no_provider`. Read verification and reset links from:

- UI: `/dev/outbox` (development only; also `/dev/outbox?email=<address>`)
- API: `GET /api/dev/outbox?email=<address>`

## Notes for automated tests

- New signups are **not** signed in; login before verification returns `403 email_not_verified`.
- Five failed logins for one email address, or twenty for one client address (first `X-Forwarded-For`
  hop), locks it for 15 minutes and returns `429` with `Retry-After`.
- Password rules: at least 10 characters with a letter and a number.
- `workspace_id` is never accepted from the client — extra body fields are rejected with `422`.
- Cross-tenant reads and writes return `404`, never `403`.
