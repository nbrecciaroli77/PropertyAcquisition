# IDEA-010 Property Acquisition — Prompt 00 Master Initiation & Build Plan

Working name: **Property Acquisition** (IDEA-010 lineage retained, no new brand invented).
Gate: OWNER APPROVED — INITIAL PRIVATE PROTOTYPE. Not a public launch.

Status: **APPROVED with amendments (June 2026). Milestone 1 delivered — see `/app/docs/M1-report.md`. Stopped for review before Milestone 2.**

## Decisions recorded (owner, this session)

| # | Decision | Consequence |
| --- | --- | --- |
| 1 | **Owner's Supabase Free project (PostgreSQL)** via SQLAlchemy 2.0 + Alembic. **Never create or recommend a throwaway Neon database.** | Option A authorised. MongoDB fallback dropped. `DATABASE_URL` (Supabase) is an outstanding credential, required before milestone 2 |
| 2 | **Deterministic parser only** for pasted listing text | `ai_extraction` flag ships default OFF; provider-neutral adapter interface still built so it can be enabled later without domain change. No model cost in this prototype |
| 3 | **Email/password only**; Google sign-in deferred | `google_sign_in` flag OFF. Welcome screen still states that a Google identity would never imply Gmail permission. Apple remains locked OFF |
| 4 | **Digest delivery suppressed** | Milestone 5 ships in-app preview + durable outbox with status `suppressed_no_provider`. A transactional provider key (Resend/SendGrid) is a separate later gate |
| 5 | **GitHub via the platform "Save to GitHub" action** | Owner performs repo creation/push. Platform checkpoints serve as milestone history in the interim. I will never request pasted git credentials |
| 6 | **Milestone 1 may proceed without a database**; `DATABASE_URL` supplied before milestone 2 | Sequencing confirmed — but see status above, milestone 1 is NOT authorised to start yet |

## Amendments accepted (owner, June 2026)

1. Supabase Free project supplies PostgreSQL before M2; no Neon.
2. Python 3.11 + FastAPI substitution accepted.
3. Application-layer tenant scoping accepted **for the private prototype only**. Retain the build-failing cross-tenant suite; implement database-level constraints (NOT NULL `workspace_id` FKs, composite unique keys) and **Supabase RLS policies wherever technically compatible** with the SQLAlchemy service-role connection; record any remaining limitation explicitly in `docs/security-privacy-limitations.md`.
4. M1 uses no database credentials and synthetic display data only. ✅
5. All 25 concept images mapped to routes/components: `docs/concept-image-map.md`. ✅
6. M1 gate: lint, type checks, tests, responsive screenshots, named checkpoint `checkpoint/m1-foundation`, Save to GitHub (owner action), report, stop. ✅ report at `docs/M1-report.md`.
7. No live Drive, Gmail, portals, Supabase or other external services during M1. ✅
8. Welcome shows Google/Apple as disabled buttons with "not enabled in this prototype" + no-Gmail statement. Jest + RTL is the unit runner.

Resume condition for M2: owner review of M1 + Supabase `DATABASE_URL`.


---

## 1. File receipt confirmation

Received `IDEA-010 Emergent Starter Pack.zip` (50.8 MB), extracted to `/app/starter/emergent_pack/`.

| File | State |
| --- | --- |
| README-FIRST.md | Read |
| IDEA-010-Product-Definition-and-Build-Specification.md (333 lines) | Read — treated as accepted scope |
| IDEA-010 Product Definition and Build Specification.docx | Duplicate of the .md, not separately parsed |
| IDEA-010-Emergent-Prompt-Runbook.md (prompts 00–07 + parked migration prompt) | Read |
| IDEA-010 Emergent Prompt Runbook.docx | Duplicate of the .md |
| fixtures/design-tokens.json | Read |
| fixtures/demo-data.json (7 properties, duplicateReplay, draft) | Read |
| fixtures/acceptance-checklist.md | Read |
| fixtures/digest-reference.html | Read |
| concept-images/00–24 (25 PNGs) | All 25 decode cleanly (1536×1024 / 1672×941, RGB). Verified programmatically; `00-design-system.png` analysed in detail |

Unreadable or missing assets: **none.**

Deliberately not opened (human reference only, per boundaries): all six Google Drive/Docs/Sheets links in README-FIRST, including the live Perth Hub spreadsheet and the approved digest PDF. No Drive, Gmail, portal or ChatGPT-task connection will be made. The `digest-reference.html` fixture is used as the digest authority instead of the Drive PDF.

Notes on gaps I will handle with reversible assumptions:
- The spec body contains a `[[GALLERY]]` placeholder (section 5) — the concept images themselves are the visual authority, so nothing is missing.
- `00-design-system.png` shows nav labels (Overview, Map, Comparables, Research) and card metrics (`Indicative Value`) that differ from the spec's route list and its explicit ban on Value Score. **The Build Specification wins**: routes will be Today / Discover / Pipeline / Compare / Saved / Tasks / Agents / Sources / Settings, no Map or Comparables page, and no Indicative Value or Value Score anywhere.
- design-tokens.json omits a spacing scale and `charcoal`; I will derive a documented 4px-based scale and use the tokens' `navy`/`mutedText` for text, recorded as cosmetic and reversible.

---

## 2. Requirements map

### Built now (in milestones 01–07)

**Foundation & design system (M1)**
- Token-driven visual system from design-tokens.json + concept images; Manrope with system fallback; warm off-white canvas, midnight navy ink, eucalyptus primary, restrained ochre. No blue dashboard styling, gradients or glassmorphism.
- Public Welcome/Sign in, public About/How it works.
- Authenticated responsive shell: desktop left rail, tablet adaptive rail, phone bottom nav (Today / Properties / Saved / More). No horizontal overflow at 320 CSS px.
- Shared components: property card, status chip, evidence state, source freshness, empty state, error state, loading skeleton, confirmation dialog, responsive comparison row.
- A11y foundations: landmarks, heading order, keyboard operation, visible focus, labelled inputs, `prefers-reduced-motion`, no colour-only status.
- Installable PWA manifest + basic service worker (shell caching only, no offline media capture).

**Auth, workspace, brief (M2)**
- Email/password signup, verification-pending state, login, logout, password reset; session expiry and logout-all-devices foundation.
- Workspace + Membership with owner role and tenant-ready roles; one or more BuyingJourneys per user.
- Resumable onboarding; full versioned Buying Brief (budget ceiling + preferred range, property type/detached, beds/baths/parking, land/floor area, renovation tolerance, purchase timing, states/suburbs/postcodes with included & excluded areas, optional anchors, unpriced/early-access policy).
- Per-criterion Hard rule / Preference / Disabled / Unknown; editable weights with validation and reset; publish creates immutable BriefVersion (actor, timestamp, reason, current pointer); contradictory bounds or zero enabled weight block publication with field-linked errors; AUD money as integer minor units, area in m², IANA timezones.

**Property workspace, evidence, matching (M3)**
- Property / ListingCampaign / Observation-Fact-Evidence / BuyerProperty as separate entities; market state separate from buyer workflow state.
- Screens: Today, Discover, Pipeline, Property Detail, Match & Evidence, Compare (up to 4), Shortlist board with the 11 defined stages and allowed transitions recording actor/time.
- Deterministic hard gates returning Pass / Fail / Unknown with fact reference and reason; known Fail cannot be promoted; Unknown critical gate routes to Verification required; property-specific waiver recorded without mutating the brief.
- Versioned scoring: default weights price 30 / land 30 / location 20 / condition 20; `coverage = assessed enabled weight / total enabled weight`; `fit = achieved / max achievable assessed`; fit unavailable (not zero) when nothing assessable; component explanations, brief version, evaluation version, last recalculation shown.
- Price semantics: raw label + kind (Exact, Range, From, Offers over, Auction, Contact agent, Expressions of interest, Conflicting) + lower/upper bound + currency + source; no inferred bounds; fit never described as value.
- Notes, tasks, activity history; optional image with source attribution and text-only fallback; optimistic concurrency (`version` column) on shared record edits.

**Intake, durable events, duplicate review (M4)**
- Structured manual form; URL + user-entered facts (no fetch of protected sites); pasted listing text handled as untrusted content; CSV import from synthetic fixtures.
- Source catalogue with honest states: Not connected / Configured / Receiving / Degraded / Reauthorisation required / Unsupported. Portal cards read "Not connected — rights required".
- IntakeEvent persisted before processing (workspace, source, external ID, content hash, source time, receipt time, parser version, idempotency key, processing state). Replay creates no duplicate property, notification, activity or digest item.
- Schema-validated extraction with field-level provenance and confidence; malformed output goes to review with the source event preserved.
- Conservative duplicate proposals on normalised address + unit + locality; confirm / reject / undo / split; all observations and campaigns preserved; 81A vs 81C provably never merged.

**Tasks, drafts, notifications, digest (M5)**
- Inspection preparation with advertised-time freshness; tasks with due dates and ownership; ICS download only after explicit user action, labelled "Add reminder", never "Book inspection".
- Agent public contact evidence separate from private notes; editable drafts with unmistakable UNSENT state; **no send pathway server-side**; copy/export to the user's own mail client only after confirmation.
- In-app notification centre: event fingerprints, read state, expiry, quiet hours, timezone; Strong match vs Potential match promotion rules.
- Daily digest preview reproducing digest-reference.html hierarchy: navy header + local date + honest snapshot label, summary strip, freshness/coverage note, up to five cards without padding, prominent address + raw guide, beds/baths/land, separate provisional fit and coverage, why it fits, main gap/risk, freshness, source link, service footer. Site plans labelled as site plans. Stacks at phone width, readable with images disabled. Unique key per workspace + recipient + local date, durable outbox and receipt, safe retry on uncertain provider status. 07:00 local default, quiet-day variant, Monday recap.

**Hardening (M6)**
- Profile, notification preferences, session list, household-role foundation.
- Machine-readable private export; deletion request that revokes sessions, stops jobs and does not recreate data; audit events for security-sensitive and privileged actions (no hidden impersonation).
- Upload validation/sanitisation, bounded retention config, rate limits on account/intake/model endpoints, stable error codes, correlation IDs, secret-free logs.
- Backup/restore instructions, tested seed/reset, dependency + secret scanning.
- Full tenant-isolation suite across API, storage policy, deep links, background jobs, exports and caches; WCAG 2.2 AA-oriented pass on core flows; performance check on list/detail.

**Acceptance (M7)**
- Traceability report, test results, responsive screenshots at desktop/tablet/iPhone/Android widths, isolation + idempotency + reproducibility + no-send + digest-replay evidence, migration/seed/backup/rollback docs, ranked defects, deployment plan and cost drivers. Private preview only after explicit approval.

### Deferred (out of scope for this prototype, by specification)

Live Perth Hub migration or cutover; Gmail OAuth body ingestion; inbound-email connector; portal scraping or unlicensed reproduction; licensed national feeds (PropTrack/Cotality); agent email sending, bookings, offers, negotiation, finance, legal advice; Value Score / AVM / investment-return / bargain badges; Stripe, billing, public subscription, public launch; native iOS/Android apps, push notifications, offline media capture; AI-controlled permissions, scoring, money maths or external actions; travel-time computation (remains Unknown until a provider and assumptions exist); real-time collaboration; map view and comparables pages (present in a concept image but not in specified scope); configurable user-set notification thresholds (defaults only, per §7).

### Blocked by credentials or decision

| Item | Blocker |
| --- | --- |
| PostgreSQL persistence | No relational service exists in this environment; needs a managed Postgres connection string (see §4 Q1) |
| Apple sign-in | Behind a permanently disabled feature flag until Apple config is supplied (spec §3) |
| Google sign-in | Needs a decision on provider approach (Q3); will never request or imply Gmail scope |
| Owner self-email digest | Needs an approved transactional provider + API key; until then digest is preview + durable outbox with an explicit "delivery not configured" state |
| AI-assisted extraction of pasted text | Needs cost/permission approval (Q2); flag default OFF, deterministic parser is the fallback |
| Private GitHub repository | I cannot create or push repos; requires the platform "Save to GitHub" action by Nick (Q5) |
| Property images beyond fixture placeholders | No licensed imagery; text-only fallback plus attributed synthetic placeholders only |
| Read-only Hub export migration rehearsal | Parked prompt, explicitly not authorised |

---

## 3. Proposed stack, repository structure, database, auth, jobs, email

### Stack (constrained by this environment's read-only process supervisor)

- **Client:** React 18 + **TypeScript**, react-scripts (`yarn start` is the fixed supervisor command), react-router-dom, TanStack Query, Tailwind CSS driven entirely by CSS variables generated from design-tokens.json, Radix primitives for dialog/menu/tabs, lucide-react icons (no emoji icons), Motion for restrained micro-interaction respecting reduced motion. Vitest + Testing Library; Playwright for end-to-end and responsive screenshots.
- **API/domain:** **Python 3.11 + FastAPI** (fixed supervisor command `uvicorn server:app` on 0.0.0.0:8001, all routes under `/api`), Pydantic v2 for request/response and extraction schemas, modular monolith with an in-process durable worker. Pytest + httpx for unit/integration.
- **Persistence:** decision pending — see §4. Primary recommendation is managed PostgreSQL (SQLAlchemy 2.0 + Alembic).
- **Object storage:** deferred; document uploads in M6 use validated local storage behind a storage adapter interface so an object-storage integration can be dropped in without domain changes.
- **AI:** provider-neutral `ExtractionProvider` interface with a deterministic rule-based implementation as default and an LLM implementation behind a flag. AI never touches gates, scores, permissions, money or external actions.

### Repository structure

```
/app
  backend/
    server.py                 # FastAPI app factory + /api router mount + lifespan (worker)
    app/
      core/                   # config, secrets loading, errors, correlation IDs, rate limit
      auth/                   # password hashing, tokens, sessions, providers, dependencies
      tenancy/                # workspace context, membership guard, scoped repository base
      domain/
        brief/                # criteria, weights, publication validation, BriefVersion
        property/             # Property, ListingCampaign, Observation/Fact/Evidence, BuyerProperty
        matching/             # gates_v1.py, scoring_v1.py (pure, versioned, no I/O)
        intake/               # IntakeEvent, parsers, provenance, idempotency
        identity/             # address normalisation, duplicate proposal, merge/split
        workflow/             # notes, tasks, inspections, ICS, stage transitions
        agents/               # contacts, contact evidence, UNSENT drafts (no send path)
        notify/               # notifications, digest builder, outbox
        lifecycle/            # audit, export, deletion, retention
      api/                    # thin routers per screen area
      jobs/                   # scheduler, durable job table, handlers
      migrations/             # Alembic versions
      seed/                   # seed_demo.py, reset.py from fixtures/demo-data.json
    tests/                    # unit / integration / tenancy / idempotency / acceptance
  frontend/
    src/
      app/                    # router, providers, layout shell (rail / tablet / bottom nav)
      design/                 # tokens.css generated from design-tokens.json, primitives
      components/             # PropertyCard, StatusChip, EvidenceState, SourceFreshness,
                              # EmptyState, ErrorState, Skeleton, ConfirmDialog, CompareRow
      features/              # today, discover, pipeline, property, match, compare, shortlist,
                              # tasks, agents, sources, settings, digest-preview, onboarding, brief
      lib/                    # api client (REACT_APP_BACKEND_URL), types, formatters (AUD, m², tz)
    e2e/                      # Playwright specs + responsive screenshot runs
  fixtures/                   # copied synthetic pack fixtures (no secrets)
  docs/                       # traceability.md, architecture.md, security-privacy-limitations.md,
                              # runbook-seed-reset.md, backup-restore.md, rollback.md
  memory/                     # PRD.md, plan, test_credentials.md
```

### Database

Design is relational-first regardless of engine, matching spec §10: UUID primary keys; `PA-###` legacy refs stored as non-key references only; `version` integer column for optimistic concurrency; money as `currency` + integer minor units; area in canonical m²; timestamps as UTC plus a separate source timezone string; tri-state modelling that keeps *absent*, *zero*, *not applicable* and *unknown* distinct (nullable value column + explicit `value_state` enum, never a magic zero); `workspace_id` on every tenant-scoped table with a NOT NULL FK and a composite index leading on `workspace_id`.

Entities: User, Identity, Session; Workspace, Membership; BuyingJourney, BriefVersion, Criterion; SourceConnection; IntakeEvent; Property; ListingCampaign; Observation, Fact, Evidence; BuyerProperty; MatchEvaluation; Note, Task, Inspection; Agent, ContactEvidence, Draft; Notification, Digest, Outbox; AuditEvent, ExportJob, DeletionJob; plus JobRun for the durable worker.

### Authentication

Email/password with Argon2id (or bcrypt if the vetted integration playbook specifies it), server-side opaque session records plus short-lived access tokens, `session_version` per user to power logout-all-devices, verification-pending as a real account state that gates workspace writes, single-use expiring reset tokens, rate limiting and lockout on credential endpoints, immutable `Identity` rows per provider. Google is a *separate identity provider* with identity scope only — the UI states explicitly that signing in with Google grants no Gmail access, and no Gmail scope is ever requested. Apple sits behind a disabled flag. **All auth code will be written from an `integration_expert` playbook, not improvised.**

### Jobs

Durable DB-backed queue: enqueue a `JobRun` row inside the same transaction as the triggering write, then a scheduler running in the FastAPI lifespan claims rows with a locking update, honours `attempt`/`max_attempts`/`next_run_at` with exponential backoff, and records terminal state. Jobs: brief re-evaluation after publish, intake processing, duplicate proposal, notification fan-out, digest build at 07:00 local per workspace timezone, retention pruning, export build, deletion execution. Every job carries `workspace_id` and re-checks membership; every handler is idempotent on a natural key. Single worker replica is a documented constraint (locking update makes it safe if that changes).

### Email

Three honest layers: (1) in-app digest preview rendering the same template as the email; (2) durable Outbox rows with status `queued / suppressed_no_provider / sent / uncertain / failed` and a unique key of workspace + recipient + local date, so a re-run never double-sends; (3) a pluggable `EmailProvider` with a default `NullProvider` that writes the rendered MIME to `/app/backend/.mail_dev/` and marks `suppressed_no_provider`. A real transactional provider (Resend or SendGrid, via `integration_expert`) is wired only when Nick supplies a key, and then only to the authenticated owner's verified address. Nick's Gmail credentials will never be used.

---

## 4. Substitutions from the preferred TypeScript + React + Node + PostgreSQL direction

Declared openly, none silent.

| Preferred | Substitution | Reason | Impact / mitigation |
| --- | --- | --- | --- |
| Node API/domain layer | **Python 3.11 + FastAPI** | `/etc/supervisor/conf.d/supervisord.conf` is marked READONLY and hard-codes `uvicorn server:app` in `/app/backend`. A Node API cannot be process-managed here or in the preview deployment | Not end-to-end TypeScript. Mitigated with Pydantic v2 schemas as the single contract and generated TypeScript types for the client, so the type boundary is still enforced |
| TypeScript client | **Retained** — React + TypeScript | — | None |
| Vite | react-scripts | `yarn start` is the fixed frontend command | Slower dev build only |
| PostgreSQL via Supabase | **Decision required (Q1)** | No relational engine is provisioned in this pod or in Emergent's preview deployment; only MongoDB is supervisor-managed. `apt` could install Postgres locally but it would not exist after deployment, so that is not an honest option | Option A: external managed Postgres (Neon/Supabase, ideally ap-southeast-2) with SQLAlchemy 2.0 + Alembic — keeps FK integrity, transactions, real migrations. Option B: pod MongoDB with compensating controls (see below). **I will not silently substitute an unstructured demo database.** |
| Supabase RLS for tenant isolation | Application-layer enforcement in a scoped repository base class, plus a test suite that fails the build if any query omits `workspace_id` | No Supabase in scope until Q1 | Documented as a weaker control than database-enforced RLS in the security limitations note |
| Redis/queue service for background jobs | DB-backed durable job table + in-process scheduler with locking claims | No broker service available | Single-replica constraint documented; durability preserved because jobs are rows, not memory |
| Managed email | Null provider + durable outbox until a key is supplied | No provider configured | Digest is truthful about non-delivery; nothing is labelled "sent" that was not sent |
| Private object storage | Storage adapter with validated local backend | Uploads are a small M6 item | Swappable to an object-storage integration with no domain change |
| Native apps / push | Responsive web + installable PWA only | Out of scope by spec | — |

**If Option B (MongoDB) is chosen**, the compensating controls I would build and test — and would still record as a real downgrade in the limitations note — are: a single-writer repository layer where every tenant collection access goes through a scoped base that injects `workspace_id`; explicit reference-integrity checks in domain services plus `$jsonSchema` validators on every collection; unique indexes for the invariants that matter (idempotency key, digest report key, outbox natural key, `(workspace_id, normalised_address, unit)`); multi-document transactions on a replica set (requires converting the pod mongod to a single-node replica set — verified as available); Alembic replaced by a numbered, forward-and-rollback migration runner with a `schema_migrations` collection; and optimistic concurrency via `version` field guards on update.

---

## 5. How the cross-cutting guarantees work

**Tenant isolation.** `workspace_id` is never read from the client. A request dependency resolves the authenticated user, loads their memberships, and produces a `TenantContext`; any workspace in the URL is validated against that membership and returns 404 (not 403) when absent, so deep links leak nothing. All tenant data access goes through `ScopedRepository`, which injects the workspace filter — direct model access from routers is prevented by an import-boundary test. Jobs, exports, digest builds, notification fan-out, search and caches all carry and re-check the workspace; every cache key is prefixed with the workspace id. Negative tests cover cross-tenant read, write, media/document fetch, deep link, export, job payload tampering and cache bleed.

**Idempotent intake.** The idempotency key is `sha256(workspace_id | source_id | external_id | content_hash)`, stored with a unique constraint. Persist the IntakeEvent first, then process in a transaction that also enqueues downstream jobs; a replay hits the unique constraint, returns the original event, and short-circuits with `processing_state = duplicate_replay`. Downstream side effects each have their own natural key (notification event fingerprint, digest report key, activity dedupe key), so even a partial replay cannot double-fire. The fixture `duplicateReplay` block asserts `expectedCreatedSideEffects = 1`.

**Migrations.** Alembic under Postgres (Option A): autogenerate reviewed by hand, every revision has a working `downgrade`, and CI applies `upgrade head` from an empty database then `downgrade base`. Under Option B, an equivalent numbered migration runner with explicit up/down and a `schema_migrations` collection. Migrations never run implicitly on boot; they are an explicit documented command.

**Seed / reset.** `python -m app.seed.reset` truncates tenant data only; `python -m app.seed.seed_demo` loads `fixtures/demo-data.json` idempotently and asserts the expected outcomes it encodes (DEMO-001 eligible-high-fit, DEMO-002 verification-required, DEMO-003 hard-fail-land, DEMO-004 conflicting price, DEMO-005/006 kept separate, DEMO-007 market under offer with buyer Archived, plus the UNSENT draft with zero external messages). Seeded rows are tagged `synthetic = true` and every screen shows an unmissable synthetic-data banner.

**Feature flags.** A typed flag registry in config with DB overrides per workspace, defaults: `apple_sign_in = off (locked)`, `google_sign_in` per Q3, `ai_extraction = off`, `email_delivery = off`, `inbound_email = off (locked)`, `portal_connectors = off (locked, unsupported)`, `value_score = permanently absent — no flag, no code path`. A test asserts that no route, template or serialiser can emit a Value Score or a send-to-agent action.

**Automated tests.** Layered: pure unit tests on `gates_v1` and `scoring_v1` (property-based cases for unknown handling, hard-fail-plus-high-fit, unavailable fit, coverage vs fit separation, reproducibility of the same brief version + fact set producing a byte-identical evaluation); integration tests on FastAPI with a real database per run for auth lifecycle, brief publication validation, intake replay, merge/undo/split, 81A vs 81C, stage-transition legality, optimistic-concurrency conflict, rate limits and error codes; a dedicated tenancy suite; a safety suite asserting no send endpoint exists, drafts stay UNSENT, ICS creation contacts nobody, and digest replay produces one outbox row; Playwright end-to-end for signup → journey → brief → import → score → compare → draft → digest preview → export → deletion, run at 1440, 1024, 390 and 412 CSS px plus a 320 px overflow assertion and an images-disabled digest render; axe-core accessibility assertions on every primary screen.

---

## 6. Milestone plan (prompts 01–07) with checkpoints and rollback

Each milestone ends with a milestone commit, a written report (files changed, routes, tests, screenshots, traceability delta, known issues) and a hard stop for review. Rollback for every milestone is the platform rollback to the previous checkpoint plus, where the schema moved, the named migration downgrade and a seed reset — no milestone requires manual data repair to undo.

| M | Prompt | Scope | Checkpoint gate | Rollback point |
| --- | --- | --- | --- | --- |
| 1 | 01 | Repo scaffold, tokens, design system, public Welcome + About, responsive shell and nav, shared components, a11y foundations, route placeholders, lint/typecheck/test/screenshot harness | Screenshots at 4 widths, no 320 px overflow, axe clean on public screens, no integrations connected | `checkpoint/m1-foundation` — scaffold only, no schema |
| 2 | 02 | Auth (from integration playbook), workspace/membership, journeys, onboarding, versioned brief, weights, publication validation, tenancy + deep-link tests, seed/reset | Migrations apply from empty, publish blocks contradictions, tenancy suite green, no Gmail scope | `checkpoint/m2-auth-brief` — `downgrade` to m1 revision + reset |
| 3 | 03 | Property/campaign/observation/buyer-property model, Today/Discover/Pipeline/Detail/Match/Compare/Shortlist, gates, scoring v1, price semantics, notes/tasks/activity, optimistic concurrency | Hard-fail-plus-high-fit cannot promote, fit unavailable ≠ 0, coverage separate, score reproducible, no invented compare values | `checkpoint/m3-domain-matching` |
| 4 | 04 | Manual/URL+facts/pasted-text/CSV intake, source catalogue states, IntakeEvent + idempotency, schema-validated extraction with provenance, duplicate propose/confirm/reject/undo/split | Replay side effects = 1, 81A ≠ 81C, untrusted content cannot instruct, no connector claims connection | `checkpoint/m4-intake-dedupe` |
| 5 | 05 | Inspections, tasks, ICS, agents + UNSENT drafts, notification centre with quiet hours, digest builder + preview + outbox, 07:00 scheduling, quiet-day and Monday recap | Zero send pathways, one outbox row per workspace/recipient/local date, phone-width and images-off digest pass, DST and date-only correctness | `checkpoint/m5-digest-tasks` |
| 6 | 06 | Profile/preferences/sessions/household role, export, deletion, audit, upload validation, retention, rate limits, correlation IDs, backup/restore, dependency + secret scan, full tenancy suite, WCAG 2.2 AA pass, perf check | Zero critical/high a11y or security findings, deletion does not recreate data, no unaudited privileged access, secrets absent from repo/logs/fixtures | `checkpoint/m6-hardening` |
| 7 | 07 | Final acceptance gate against acceptance-checklist.md and definition-of-done; full evidence pack; deployment plan and cost drivers; **deploy only after explicit approval** | Every checklist box evidenced; stop on any critical defect, cross-tenant exposure, data-loss defect, send pathway, broken migration or missing rollback | `checkpoint/m7-acceptance` — preview deploy is separately revertable |

Realistic sequencing note: M1–M3 are the largest blocks. I will report at each stop rather than combining milestones, per the runbook.

---

## 7. Questions that materially change architecture, scope, cost or permissions

1. **Persistence (architecture-critical).** Option A: supply a managed PostgreSQL connection string (Neon or Supabase, ap-southeast-2 preferred) — I keep SQLAlchemy + Alembic, real foreign keys and transactions, closest to the specified direction; cost is a small external service and a secret Nick controls. Option B: use this pod's MongoDB with the compensating controls in §4 — zero extra cost and no external dependency, but a genuine downgrade in relational integrity and no database-enforced row-level security, which I would record permanently in the limitations note. Which do you authorise?
2. **AI-assisted extraction.** Enable a schema-validated LLM proposal step for pasted listing text (proposals only — never gates, scores or actions), which incurs model cost, or ship milestone 4 with a deterministic parser only and leave the AI adapter behind an off flag?
3. **Google sign-in.** Use Emergent's managed Google sign-in for the prototype (identity only, no Gmail scope), or defer Google entirely and ship email/password for the private prototype?
4. **Digest self-email.** Confirm that milestone 5 delivers preview plus durable outbox with delivery suppressed, and that a transactional provider key (Resend or SendGrid) comes later as a separate gate?
5. **Private GitHub repository.** I cannot create or push to a repository myself. Confirm you will use the platform's "Save to GitHub" action to create the private repo, and that a milestone-commit history in the platform checkpoints satisfies the handover requirement in the interim?

Reversible assumptions I am making without asking: the derived 4px spacing scale, the exact Manrope fallback stack, icon set (lucide-react), microcopy wording, the choice to omit Map/Comparables pages that appear only in the design-system image, and placeholder synthetic imagery treatment.

**No implementation will begin until this plan is approved.**
