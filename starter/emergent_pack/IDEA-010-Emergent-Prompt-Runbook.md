# IDEA-010 Property Acquisition

## Emergent prompt runbook

Run these prompts in order. Keep the same Emergent project and private GitHub repository. Do not paste secrets into chat. Each prompt requires a report before the next stage.

## Prompt 00 — Master initiation and build plan

```text
You are building IDEA-010 Property Acquisition as an initial private responsive-web prototype for Nick Brecciaroli.

Read every supplied file before acting, especially:
- README-FIRST.md
- IDEA-010 Product Definition and Build Specification
- the complete concept-images folder
- design-tokens.json
- demo-data.json
- acceptance-checklist.md
- digest-reference.html

Authority and boundaries:
- The Build Specification is the accepted scope for this prototype.
- The prototype-source Google Drive links are human reference only. Do not connect to, copy from, edit or synchronise with Nick's live Google Drive, Gmail, property portals or ChatGPT tasks.
- Use only the included synthetic fixtures.
- This is a private prototype, not a public commercial launch.
- Do not implement scraping, agent sending, offers, bookings, billing, native apps or Value Score.
- Keep IDEA-010 lineage and the working name Property Acquisition. Do not invent a final brand.

Before writing code:
1. Confirm the files you received and identify any unreadable or missing asset.
2. Produce a requirements map grouped Built now / Deferred / Blocked by credentials or decision.
3. Propose the concrete stack, repository structure, database, authentication, job and email approach supported by Emergent.
4. Identify every substitution from the preferred TypeScript + React + Node + PostgreSQL direction. Do not silently substitute a weaker persistence model.
5. Explain how tenant isolation, idempotent intake, migrations, seed/reset, feature flags and automated tests will work.
6. Give a milestone plan matching prompts 01–07, including a checkpoint and rollback point after each.
7. List only questions whose answers materially change architecture, scope, cost or permissions. Make reversible assumptions for cosmetic details.

Do not start implementation in this step. Wait for approval of the plan.
```

## Prompt 01 — Foundation, repository and visual system

```text
Proceed with milestone 1 using the approved plan.

Connect or initialise a new private GitHub repository through Emergent's secure integration. Never request that credentials be pasted into chat. Commit the clean initial scaffold and then commit each completed milestone separately.

Build the application shell and design system from the supplied concept images and tokens:
- public Welcome / Sign in screen;
- public About / How it works screen;
- authenticated responsive shell;
- desktop rail, tablet adaptive navigation and phone bottom navigation;
- routes/placeholders for Today, Discover, Pipeline, Compare, Saved/Shortlist, Tasks, Agents, Sources and Settings.

Use warm off-white, midnight navy, eucalyptus and restrained ochre; premium editorial spacing; Manrope-like typography; accessible contrast. Do not use generic blue dashboard styling, gradients or glassmorphism.

Implement shared components for property card, status chip, evidence state, source freshness, empty state, error state, loading skeleton, confirmation dialog and responsive comparison row.

Add accessibility foundations: semantic landmarks/headings, keyboard navigation, visible focus, labelled inputs, reduced-motion respect and no colour-only status.

Use synthetic display data only. Do not connect integrations.

Run lint/typecheck/tests and responsive screenshots at desktop, tablet, iPhone width and Android width. Report files changed, routes, screenshots, test results, known issues and the Git commit. Stop for review.
```

## Prompt 02 — Authentication, workspace and buying brief

```text
Proceed with milestone 2.

Implement production-shaped private-prototype account foundations:
- email/password signup, verification-pending, login, logout and reset;
- Google sign-in as a separate identity provider;
- Apple sign-in behind a disabled feature flag unless configuration is explicitly supplied;
- session expiry and logout-all-devices foundation;
- workspace owner membership and tenant-ready roles;
- one or more buying journeys per user.

Google sign-in must not request or imply Gmail permission.

Implement resumable onboarding and the full versioned Buying Brief:
- budget ceiling/preferred range;
- property type/detached requirement;
- beds, baths, parking, land/floor area;
- renovation tolerance and purchase timing;
- states, suburbs/postcodes, included/excluded areas and optional anchors;
- unpriced/early-access policy;
- hard rule, preference, disabled and unknown states;
- editable preference weights with validation and reset.

Publishing creates an immutable BriefVersion with actor, timestamp, reason and current pointer. Contradictory bounds or zero enabled weight block publication with field-linked errors. Keep Australian currency/units and IANA timezones.

Add tenant-isolation tests and negative deep-link tests now. Add synthetic seed/reset commands. Do not add live data or mailbox access.

Run migrations, tests and responsive UAT. Report requirement traceability, test evidence, known gaps and commit. Stop for review.
```

## Prompt 03 — Property workspace, evidence and matching

```text
Proceed with milestone 3.

Implement the core domain and screens using demo-data.json:
- Property, ListingCampaign, Observation/Fact/Evidence and BuyerProperty separation;
- Today, Discover, Pipeline, Property Detail, Match & Evidence, Compare and Shortlist;
- source market state separate from buyer workflow state;
- notes, tasks and activity history;
- optional image with source attribution and text-only fallback.

Implement deterministic hard gates as Pass / Fail / Unknown. A known hard failure cannot be promoted. Unknown critical facts route to verification.

Implement configurable preference scoring with the default 30 price / 30 land / 20 location / 20 condition weights. Calculate assessed fit separately from evidence coverage exactly as defined in the Build Specification. If nothing can be assessed, show fit unavailable. Preserve score and brief versions and component explanations.

Implement raw price semantics: Exact, Range, From, Offers over, Auction, Contact agent, Expressions of interest and Conflicting. Do not infer missing bounds or call the fit score value.

Implement compare for up to four properties and the defined buyer workflow states. Add optimistic concurrency where users edit shared records.

Tests must cover hard failure plus high fit, unknown values, unpriced property, conflicting guide, under-offer market status, separate unit suffixes, score reproducibility and no invented comparison values.

Run tests and visual regression checks. Report traceability, screenshots, calculation examples and commit. Stop for review.
```

## Prompt 04 — Manual intake, durable events and duplicate review

```text
Proceed with milestone 4.

Implement permitted first-build intake only:
- structured manual property form;
- URL plus user-entered facts without protected-site scraping;
- pasted listing text parsed as untrusted content;
- CSV import using synthetic fixtures;
- source catalogue with honest Not connected / Configured / Receiving / Degraded / Reauthorisation required / Unsupported states.

Persist IntakeEvent before processing with workspace, source, external ID, content hash, source time, receipt time, parser version, idempotency key and processing state. Replaying the same fixture must not create duplicate properties, notifications or activity side effects.

Implement schema-validated extraction with field provenance/confidence. AI may propose facts and duplicate candidates but cannot decide permissions, scoring or external actions. Malformed output goes to review.

Implement conservative duplicate proposals using address, unit and locality. Users can confirm, reject, undo and split. Preserve campaigns and observations. Demonstrate that 81A and 81C remain separate and that an actual duplicate replay is idempotent.

Do not create Gmail OAuth, portal login automation, web scraping or licensed feeds. Connector cards may explain future capability but must not claim connection.

Run replay, false-merge, untrusted-content and tenant-isolation tests. Report ingestion state machine, evidence, traceability and commit. Stop for review.
```

## Prompt 05 — Tasks, inspections, drafts, notifications and digest

```text
Proceed with milestone 5.

Implement:
- inspection preparation with advertised-time freshness;
- user tasks, due dates and ownership;
- ICS calendar-file export after explicit user action;
- agent/contact evidence and editable UNSENT drafts;
- in-app notification centre with event fingerprints, read state, expiry, quiet hours and timezone;
- daily digest preview using digest-reference.html and the Build Specification.

Safety controls:
- There is no server-side agent send action in this milestone.
- Saving/generating a draft sends nothing.
- Creating a task or ICS reminder does not contact an agent or claim a booking.
- Offers and negotiations remain out of scope.

Digest behaviour:
- daily at 07:00 local timezone, quiet-day message, Monday recap;
- up to five candidates without padding;
- fit and evidence coverage separate and provisional where appropriate;
- address, raw guide, why it fits, main risk/gap, freshness and source link;
- validated image attribution or text-only fallback;
- site plan correctly labelled;
- stacked cards at phone width and usable with images disabled;
- unique workspace/recipient/local-date key and durable outbox/receipt.

First implement preview and local/test delivery. Add owner self-email only when Nick configures an approved transactional provider securely. Do not use Nick's Gmail password or current ChatGPT task.

Test duplicate digest generation, uncertain provider state, images off, phone width, date-only deadlines, DST timezone conversion and draft safety. Report results and commit. Stop for review.
```

## Prompt 06 — Privacy, lifecycle, accessibility and operational hardening

```text
Proceed with milestone 6.

Complete private-prototype hardening:
- profile, notification preferences, sessions and household-role foundation;
- private machine-readable export;
- deletion request that revokes sessions, stops jobs and does not recreate data;
- audit events for security-sensitive and privileged actions;
- upload validation/sanitisation and bounded retention configuration;
- rate limits, error codes, correlation IDs and safe logs;
- backup/restore instructions and a tested seed reset;
- dependency and secret scanning.

Run a focused tenant-isolation suite across API, database/storage policy, deep links, background jobs, exports and caches. No support or admin role may browse private content without an explicit audited pathway.

Complete WCAG 2.2 AA-oriented testing for core flows: keyboard, focus, labels, contrast, text zoom, status without colour, reduced motion and representative screen-reader checks. Fix critical/high findings.

Performance-check common list/detail flows at prototype load. Document external-provider and AI cost controls even if disabled.

Produce a security/privacy limitations note. Do not label the result production-ready. Report tests, unresolved risks, traceability and commit. Stop for review.
```

## Prompt 07 — Final acceptance and private preview deployment

```text
Do not deploy yet. First run the final acceptance gate against acceptance-checklist.md and every Build Specification definition-of-done item.

Provide:
1. Built / Deferred / Blocked requirements traceability.
2. Full automated test results and failures.
3. Responsive screenshots for every primary screen at desktop, tablet, iPhone width and Android width.
4. Tenant-isolation, idempotency, score reproducibility, draft-no-send and digest replay evidence.
5. Database migration, seed/reset, backup/restore and rollback instructions.
6. Secrets and external services required, with no secret values.
7. Known defects ranked Critical / High / Medium / Low.
8. GitHub repository and commit reference.
9. A recommended private-preview deployment plan and expected cost drivers.

Stop if any critical defect, cross-tenant exposure, data-loss defect, accidental-send pathway, broken migration or missing rollback exists. Do not hide incomplete integrations behind success labels.

Wait for Nick's approval. Only after explicit approval, deploy a private preview with no public indexing, no live Perth data, no Gmail/portal connection and no agent-send capability. Then smoke-test signup, onboarding, import, scoring, compare, draft safety, digest preview, export and deletion. Return the private URL and a concise handover report.
```

## Later prompt — Read-only migration rehearsal, not yet authorised

```text
This prompt is intentionally parked. Do not run it until Nick explicitly supplies and approves a dated export.

Create a staging-only import rehearsal from the approved snapshot. Preserve legacy PA identifiers as references, source observations, raw price wording, unknowns, conflicts and unsent states. Produce a mapping report, duplicate/exception report and rollback proof. Do not write back to Google Drive, stop the ChatGPT prototype, connect Gmail, send notifications or change the live coverage cutoff.
```

