# IDEA-010 Property Acquisition

## Product definition and initial prototype build specification

Prepared for Nick Brecciaroli and Emergent | 4 September 2026 | Build-pack version 1.0

### Decision status

Portfolio identity: IDEA-010.

Commercial verdict: RESEARCH FURTHER. Demand, differentiation, data rights and unit economics remain unvalidated.

Delivery gate: OWNER APPROVED — INITIAL PRIVATE PROTOTYPE. Build a production-shaped private responsive-web prototype for evaluation. This is not public launch approval.

Working name: Property Acquisition. It is descriptive and not an approved public brand.

## 1. Executive product definition

Property Acquisition is a buyer-owned workspace that brings property opportunities together, checks them against a configurable buying brief, separates facts from uncertainty, removes duplicate review, and helps a household decide what deserves attention next.

The first user hypothesis is an active Australian owner-occupier household using several listing sources. Renovators and buyers comparing multiple suburbs are useful early subsegments. Investors, buyer agencies and professional workspaces are later hypotheses.

The product promise is calm, traceable decision support — not exhaustive national listings, guaranteed off-market access, valuation, investment advice, negotiation or autonomous purchasing.

### Core user journey

1. Create an account and a buying journey.
2. Define hard requirements, preferences, geography, timing and notification choices.
3. Add or receive property opportunities from permitted sources.
4. Review deterministic hard-rule outcomes, fit, evidence coverage, conflicts and freshness.
5. Shortlist, compare, add notes/tasks and prepare inspection or enquiry actions.
6. Receive a concise daily digest and material-change notifications.
7. Decide and act personally. The application does not contact an agent, book an inspection or submit an offer without a later explicit controlled-action feature.

## 2. Rescan findings incorporated into this build

The 4 September preparation baseline has been superseded by later same-day prototype updates.

| Area | Current observed state | Product implication |
| --- | --- | --- |
| Hub | Twelve-tab Google Sheets record; 24 PA identifiers reached by the final digest, including retained exclusions | Preserve stable IDs, provenance and explicit excluded/unknown states; use synthetic fixtures for the build |
| Sources | REIWA, Domain, realestate.com.au, Quiet Listings and Listing Loop configured; actual delivery confirmed for REIWA and Quiet Listings; other first deliveries remain unverified | Connection status must distinguish Configured from Receiving, Degraded and Unsupported |
| Additional access | Property Whispers and Aussie access exist with gaps; Soho and Landgate accounts are owner-reported; no licensed PropTrack/Cotality integration | Account creation never equals verified coverage, entitlement or API rights |
| Monitoring | Hourly cloud mail-led intake is active; desktop duplicate paused | Build durable jobs and idempotency, but do not alter or duplicate the current ChatGPT tasks |
| Daily digest | Active for 07:00 Australia/Perth; approved final layout sent to the owner; first unattended scheduled run remains an acceptance check | Reproduce the approved presentation and scheduling semantics with synthetic data first |
| Agent workflow | Twenty-five contacts; eight approved general emails sent; seventeen drafts and property-specific enquiries remain unsent | Draft is a distinct state; initial app must not send agent mail |
| Scoring | Prototype v1 uses price 30, land 30, suburb 20 and condition 20; unknown scores zero | Preserve these default weights but improve the product by separating assessed fit from evidence coverage |
| Value research | Market-value and history methodology documented; optional Value Score remains uncalibrated and inactive | Do not implement or display a Value Score badge in this build |
| Presentation | White property cards, pale page background, navy/teal accents, prominent address and guide, validated image attribution, risk and freshness | Apply this to in-app digest preview and transactional self-email |
| Operating decision | Prototype enhancements were paused after the approved digest | The standalone build now resumes only under this new explicit owner decision; the live prototype remains independent |

## 3. Scope of the initial private prototype

### Included

- Responsive web application and installable PWA behaviour where supported.
- Desktop, iPhone-width, Android-width and tablet layouts using one cloud record set.
- Public Welcome and About / How it works screens.
- Email/password and Google authentication for the private prototype. Show Apple sign-in only behind a disabled feature flag until credentials and configuration are supplied.
- Workspace and buying-journey foundation, owner role and tenant-ready membership model.
- Versioned buying brief with hard rules, preferences, unknowns, weights and geography.
- Manual property intake by form, URL plus user-entered facts, pasted text and CSV fixture import.
- Source catalogue and honest connection-health states; no fake live integrations.
- Today, Discover, Pipeline, Property Detail, Match & Evidence, Compare, Shortlist, Inspections & Tasks, Agents & Drafts, Settings/Privacy/Household.
- Deterministic hard gates; configurable preference scoring; separate evidence coverage.
- Conservative duplicate proposals and reversible merge/split review.
- Notes, tasks, inspection preparation and calendar-file export after user action.
- In-app notifications and an approved-style daily-digest preview.
- Owner self-email digest through a transactional provider only after credentials are securely configured.
- Audit events, export/delete foundation, seed/reset tools, automated tests and private deployment.

### Explicitly excluded or deferred

- Direct access to Nick's Gmail, Google Drive Hub or portal accounts.
- Migration or cutover of the live Perth workflow.
- Web scraping or unlicensed reproduction of portal content.
- Licensed national listing feeds until commercial rights are documented.
- Gmail OAuth body ingestion; use a later inbound-email or approved connector phase.
- Agent email sending, bookings, offers, negotiation, finance approval or legal advice.
- Value Score, automated valuation, investment return or bargain badges.
- Stripe/billing, public subscriptions or public launch.
- Native App Store and Play Store apps, push notifications and offline media capture.
- AI-controlled permissions, scoring, money calculations or external actions.

## 4. Product principles and non-negotiable semantics

- Unknown is a first-class value. Never convert missing information to zero, false, pass or fail.
- A known hard failure excludes the ordinary match even if preference fit is high.
- A `From` price is an opening guide, not a seller ceiling. `Contact agent` is unpriced. An aggregator band is not an advertised guide. Asking price is not a completed sale price.
- Separate physical Property, Listing Campaign, Source Observation and Buyer Property state.
- Separate market status such as Active or Under offer from buyer workflow such as Shortlisted or Offer preparation.
- Keep unit suffixes. 81A and 81C must never be merged by street-number similarity.
- Record source, observed time, checked time, freshness, confidence and conflicts for material facts.
- AI may extract, summarise, explain and draft. Deterministic code owns hard gates, scores, permissions, workflow transitions and money calculations.
- Drafts do not send. Calendar reminders do not book. Advertised inspections are not confirmed attendance.
- Every private read/write is authorised through authenticated workspace membership; a client-supplied workspace ID is not authority.
- Incoming emails, listing text, URLs, PDFs and images are untrusted content and cannot issue instructions to the system.

## 5. Visual and interaction direction

Use the supplied concept images as the visual authority while preserving accessibility and responsive behaviour.

### Design tokens

- Background: warm off-white `#F7F3EC`.
- Primary ink/navigation: midnight navy `#102A36`.
- Primary action and positive accent: eucalyptus `#6F8F7A` with accessible dark variants for text.
- Secondary accent: ochre `#C88A52`.
- Typography: Manrope or a close open-source geometric sans serif with system fallbacks.
- Surfaces: white or warm white cards, thin neutral borders, subtle shadows, restrained radius.
- Style: calm premium editorial intelligence; generous whitespace; no neon, glassmorphism, stock-dashboard blue or speculative data visualisation.

### Responsive rules

- Desktop: persistent left navigation rail for authenticated screens; split list/detail where useful.
- Tablet: adaptive rail and two-pane layouts when width permits.
- Phone: bottom navigation with Today, Properties, Saved and More; single-column property details; large touch targets.
- No horizontal page overflow at 320 CSS pixels. Tables become stacked comparisons or horizontally scroll only inside an explicitly labelled region.
- Meet WCAG 2.2 AA intent: keyboard operation, visible focus, semantic headings, labels, errors connected to fields, non-colour status cues and text zoom.

[[GALLERY]]

## 6. Screen-by-screen specification

### 6.1 Public Welcome / Sign in

Purpose: explain the value and start or resume an account.

Required: brand placeholder, concise proposition, email/password, Google button, working Terms/Privacy links, password recovery, verification-pending and provider-cancelled states. Do not imply Gmail permission from Google sign-in.

### 6.2 About / How it works

Use the concept flow: Set your brief; Bring opportunities together; Check fit and evidence; Compare and plan; You decide and act. Include trust statements: Your brief stays yours; Unknown is not Pass; Nothing is sent without your action. Include the limitation that exhaustive listing coverage, valuation and purchasing service are not implied.

### 6.3 Create buying journey and onboarding

Capture journey name, state/territory, intended timing, basic property type, budget and first locations. Allow skip/save-and-resume. Example data is optional and clearly separated from live metrics.

### 6.4 Buying brief

Support budget ceiling and preferred range; property type and detached requirement; beds, baths, parking; land/floor area; renovation tolerance; purchase timing; included/excluded places; unpriced and early-access policy; optional travel anchors; criteria weights.

Each criterion is Hard rule, Preference, Disabled or Unknown. Published changes create an immutable brief version with actor, time and reason. Contradictory bounds block publication. Re-evaluation is queued after publish.

### 6.5 Locations and travel

Support all states and territories, suburb/postcode/state identity, included and excluded areas, radius and anchor preferences. Treat travel time as Unknown until provider data and assumptions exist. Display local timezone for deadlines and the user's timezone where different.

### 6.6 Source connections

Cards show source type, supported region, requested criteria, effective criteria, status, last receipt, last success, limitation and recovery action. Initial real states are Manual entry and CSV import. Portal cards are `Not connected / rights required`; do not fabricate a successful sync.

### 6.7 Today dashboard

Answer only: What changed? What needs a decision? What is waiting for evidence? Include meaningful-change cards, upcoming deadlines, source health and next actions. Empty state distinguishes no changes from a failed check.

### 6.8 Discover and Pipeline

Discover is an incoming review queue. Pipeline is the household's ongoing work. Provide list/card views, filters, search, sort, saved views and no-result explanations. Show source market state and buyer workflow state separately.

### 6.9 Property detail

Show address, image with attribution/fallback, guide semantics, beds/baths/cars/land, market state, buyer state, hard gates, fit, coverage, evidence freshness, conflicts, source observations, notes, tasks, inspections, contacts, documents and activity. Every critical fact must expose its source or user-entry label.

### 6.10 Match and evidence

Show Pass, Fail and Unknown per hard rule; preference components; assessed fit; evidence coverage; brief version; evaluation version; last recalculation. Explain what fact would change the result. Never use one blended score to hide unknowns.

### 6.11 Compare

Compare up to four properties. Align attributes, total-cost assumptions, risks and unknowns. Do not fill gaps with invented values. Unknown must differ visually and semantically from an unfavourable known value.

### 6.12 Shortlist board

Support Reviewing, Shortlisted, Inspection considered, Inspected, Due diligence, Offer preparation, Offer submitted, Under contract, Settled, Rejected and Archived. Use allowed transitions and record actor/time. A source status update cannot change these buyer-owned stages.

### 6.13 Inspections and tasks

Show advertised open times with source freshness. Users can create a task or download an ICS file. The UI must say `Add reminder`, not `Book inspection`, unless a later approved booking integration exists.

### 6.14 Agents and drafts

Maintain public contact evidence and private notes separately. Create editable enquiry drafts with an unmistakable UNSENT state. In this build there is no send button to an agent; offer copy/export to the user's mail client only after confirmation.

### 6.15 Settings, privacy and household

Profile, timezone, locale, notification cadence, quiet hours, membership foundation, sessions, export and deletion. Google sign-in and Gmail connection must remain separate. Privileged/admin access requires a separate role and audit event.

## 7. Matching specification

### Hard gates

Each enabled hard rule returns Pass, Fail or Unknown with fact reference and reason. Known Fail excludes ordinary matches. Unknown critical gates route to Verification required. A property-specific waiver is recorded and cannot alter the global brief.

### Fit and evidence coverage

Use versioned deterministic functions. Default prototype-derived weights are Price 30, Land 30, Location/Suburb 20 and Condition 20, but the configuration may change by brief.

`coverage = assessed enabled preference weight / total enabled preference weight`.

`fit = achieved points / maximum achievable assessed points`.

If no enabled preference can be assessed, fit is unavailable, not zero. Always show fit beside coverage. Display the component calculation and scoring version.

### Price semantics

Store raw label, price kind, lower bound, upper bound, currency and source. Supported kinds include Exact, Range, From, Offers over, Auction, Contact agent, Expressions of interest and Conflicting. Do not infer a numeric bound where none is stated.

### Notification promotion

Default `Strong match` requires no known hard failure, high fit, minimum coverage and recent availability evidence. `Potential match` may carry urgent or early-access incomplete information but must list unknowns. Users can configure thresholds later.

## 8. Intake, identity and deduplication

Persist an IntakeEvent before processing, with workspace, source, external ID, content hash, receipt time, source time, parser version and status. Use an idempotency key. Replaying the same event must not create another property, another match notification or another digest item.

Extraction output uses a validated schema with field-level provenance and confidence. Malformed or ambiguous output enters review and preserves the source event.

Identity resolution proposes a duplicate using normalised address, unit, locality and source evidence. Use conservative thresholds. Users can confirm merge, reject merge, undo merge and split. Preserve every observation and campaign.

## 9. Daily digest and notification behaviour

The app provides an in-app digest preview and, once a transactional email provider is configured, can send only to the authenticated owner's verified email during this prototype.

Daily cadence defaults to 07:00 in the user's IANA timezone. The digest is sent on quiet days and Monday includes a weekly recap. Select up to five candidates without padding. Exclude prior digest emails from intake.

Required digest hierarchy:

- Navy header with local date and honest release/snapshot label.
- Compact summary strip: new captured, material changes, relevant replies where supported.
- Freshness and coverage explanation.
- Up to five white property cards with optional validated image and attribution.
- Prominent address and raw guide; beds/baths/land; provisional fit and coverage.
- Why it fits, main gap/risk, source freshness and source link.
- New leads/material changes, verification opportunities and deadlines.
- Small service footer describing cadence, scoring semantics, evidence limits and no external action.

At phone width, image and details stack with no horizontal overflow. Missing or untrusted image produces a text-only card. A site plan must be labelled as a site plan, not a property photograph.

Use a unique report key per workspace, recipient and local date; durable outbox and send receipt; safe retry after uncertain provider status. Provider acceptance is not `read` or guaranteed delivery.

## 10. Data model

Minimum entities:

| Entity | Key responsibility |
| --- | --- |
| User, Identity, Session | Account lifecycle and immutable provider identity |
| Workspace, Membership | Tenant boundary and roles |
| BuyingJourney, BriefVersion, Criterion | Versioned configuration and reproducible evaluation |
| SourceConnection | Capability, consent, status and secret reference |
| IntakeEvent | Durable receipt, idempotency and processing checkpoint |
| Property | Physical address identity |
| ListingCampaign | Provider-specific sale campaign and state history |
| Observation, Fact, Evidence | Provenance, confidence, conflicts and freshness |
| BuyerProperty | Household workflow state separate from market state |
| MatchEvaluation | Brief/fact versions, gates, fit, coverage and components |
| Note, Task, Inspection | Collaboration and personal workflow |
| Agent, ContactEvidence, Draft | Contact facts and unsent communications |
| Notification, Digest, Outbox | Meaningful events, delivery and deduplication |
| AuditEvent, ExportJob, DeletionJob | Accountability and lifecycle controls |

Use UUIDs internally. Preserve optional legacy `PA-###` as an import reference, never as the database key. Use optimistic concurrency/version columns. Store money as currency plus integer minor units, area in canonical square metres, and time as UTC plus source timezone. Distinguish absent, zero and not applicable.

## 11. Architecture direction

Preferred initial stack: TypeScript end to end; React-based responsive web client; Node API/domain layer; PostgreSQL through Supabase or another managed relational service; private object storage; background jobs; managed email; provider-neutral AI adapter. Use a modular monolith with independent workers, not premature microservices.

Emergent may use an equivalent supported stack only after it explains the substitution and confirms tenant isolation, migrations, transactions, background-job durability, tests, export and code ownership. Do not silently replace relational integrity with an unstructured demo database.

Connect a new private GitHub repository before substantial implementation. Use development and private-preview environments. Secrets live only in managed secret settings; never in prompts, fixtures, commits or logs.

## 12. Security, privacy and AI controls

- Enforce tenant membership in server-side queries, storage policies, jobs, search, exports and caches.
- Add negative cross-tenant tests for reads, writes, media and deep links.
- Rate limit account, intake and model endpoints.
- Validate uploads, file size/type and sanitise HTML. Never execute source content.
- Minimise raw intake retention; expose configurable policy and deletion jobs.
- Keep raw finance notes and source bodies out of analytics and model prompts unless necessary.
- Audit privileged support/admin access; no hidden impersonation.
- AI output must pass JSON/schema validation and cannot trigger communications or account changes.
- Do not train shared models on household content by default.
- Add dependency, secret and basic OWASP checks before private deployment.

## 13. Synthetic seed and import rules

Use `fixtures/demo-data.json`. It deliberately covers pass, fail, unknown, conflicting guide, unpriced, duplicate proposal, separate unit suffixes, under-offer market state and unsent draft safety.

Do not copy the live Hub into development. A later migration rehearsal requires a dated read-only export, mapping report, duplicate report, rollback/reset, preservation of unknowns/provenance, and proof that unsent drafts cannot enter an outbox.

## 14. Definition of done for the initial prototype

- A new user can sign up, create a journey and publish a valid brief on desktop and phone.
- Synthetic properties can be imported idempotently and reviewed without false unit merges.
- Known hard failures cannot be promoted by a high preference score.
- Fit and evidence coverage are separate, reproducible and explained.
- Today, Discover, Pipeline, detail, evidence, compare, shortlist, tasks, drafts, sources and settings function with meaningful empty/error states.
- Draft creation sends nothing. Reminder creation contacts nobody.
- Digest preview matches the approved hierarchy and passes narrow-width rendering with images disabled and enabled.
- Tenant isolation tests pass for API, storage and deep links.
- Export/delete flows have private prototype behaviour and documented limitations.
- Automated unit/integration/end-to-end tests pass and are committed.
- Emergent supplies a traceability report, known issues, setup guide and rollback instructions.
- Private preview is deployed only after Nick approves the pre-deployment report.

## 15. Delivery sequence

- **Phase 1 — Plan and architecture check:** no code until gaps and substitutions are reported.
- **Phase 2 — Foundation and visual system.**
- **Phase 3 — Authentication, workspace and buying brief.**
- **Phase 4 — Property workspace, gates, scoring and comparison.**
- **Phase 5 — Intake events, manual/CSV import and duplicate review.**
- **Phase 6 — Digest preview, self-email and notification centre.**
- **Phase 7 — Security, accessibility, automated QA and private preview.**
- **Phase 8 — Later decisions:** Gmail/inbound email, Hub migration rehearsal, licensed feeds, pilot, billing and native apps.

## 16. Open decisions that do not block scaffolding

- Final public brand and domain.
- Exact managed providers and Australian-region availability.
- Whether Apple sign-in is enabled before private beta.
- Inbound-email provider and approved retention window.
- First external pilot participants and commercial success gate.
- Licensed source strategy and cost.

Emergent must use feature flags or neutral placeholders, not invent decisions.

## 17. Source authority

The current Prototype Specification and User Guide describe observed personal workflow. The Nationwide Requirements document is the broad proposal. This build specification is the accepted scope for the initial private prototype where conflicts exist. The Hub remains authoritative only for live personal operations and is not a build database.

Source links are listed in README-FIRST. No source link implies automatic synchronisation, credentials or permission to edit.
