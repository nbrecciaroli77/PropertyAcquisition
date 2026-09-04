# Milestone 1 report — Foundation, repository and visual system

Status: **complete, awaiting owner review.** Checkpoint name: `checkpoint/m1-foundation`. Git commit is created by the platform "Save to GitHub" action (owner) — no credentials were requested or used.

## Boundaries honoured

- No Drive, Gmail, portal, Supabase or any other external service connected. Backend `/api/health` reports `database: not_configured`.
- Synthetic display data only, sourced from `fixtures/demo-data.json`; every authenticated screen carries a synthetic-data banner.
- No send, book, offer, billing, scraping or Value Score pathway — enforced by `backend/tests/test_system.py` and `frontend/src/__tests__/forbidden.test.ts`.
- Google/Apple provider buttons are present but disabled with the statement that Google identity never grants or implies Gmail access.

## Files created

- `backend/`: `server.py`, `app/main.py`, `app/core/config.py` (typed flag registry — `apple_sign_in`, `inbound_email`, `portal_connectors` locked off; `google_sign_in`, `ai_extraction`, `email_delivery` off; no `value_score` flag exists), `app/api/system.py`, `tests/test_system.py`, `pyproject.toml` (ruff, mypy strict, pytest), `requirements.txt`, `.env` (`APP_ENV`, `CORS_ORIGINS`).
- `frontend/`: react-scripts + TypeScript strict; `scripts/sync-design.mjs` generates `src/design/tokens.css` from the tokens fixture; `tailwind.config.js` maps only CSS variables; `src/app/` (router, `AppShell`, `PublicShell`, `DesktopRail`, `BottomNav`, `TopBar`, `nav.ts`); `src/components/` (`Brand`, `Button`, `StatusChip`, `EvidenceState`, `SourceFreshness`, `FitRing`, `PropertyCard`, `CompareRow`, `ConfirmDialog`, `States` = Empty/Error/Skeleton, `Page` = SyntheticBanner/PageHeader/MetricCard/MilestoneNote); `src/features/*` pages; `src/lib/` (types with tri-state `Tri<T>`, formatters, synthetic mapper, fixed display clock, API client); `public/manifest.json` + shell-only `sw.js`; Jest/RTL/jest-axe tests; Playwright responsive harness.
- `fixtures/` (copied pack fixtures), `docs/concept-image-map.md`, `readme.md`.

## Routes

Public: `/` Welcome/Sign in · `/about` · `/terms` · `/privacy` · `*` 404.
Authenticated shell (`/app`): `today` · `discover` · `pipeline` · `compare` · `saved` · `tasks` · `agents` · `sources` · `settings` · `more` (phone hub) · `properties/:id`.
Reserved for M2: `/app/journeys/new`, `/app/brief`, `/app/brief/locations`.

## Responsive behaviour

- ≥1024 px: full navy rail (collapsible, persisted) · 768–1023 px: icon rail with labels under icons · <768 px: bottom navigation Today / Properties / Saved / More (from `design-tokens.json`).
- Tables become stacked comparisons (`CompareRow`) or scroll inside a visibly labelled region (hard rules, pipeline). No horizontal page overflow at 320 px (asserted).

## Accessibility foundations

Skip link → `main` (focus moves to `main` on route change, not on first load), single `h1` per screen, landmarks with unique labels, `aria-current="page"`, labelled inputs, visible 3 px focus ring, `prefers-reduced-motion` zeroes durations and delays, status always text + icon (never colour alone), Unknown rendered as "Unknown"/"Unavailable" never 0 % or a dash. axe (jest-axe) clean on Welcome, About, Today, Discover.

## Test results

| Suite | Result |
| --- | --- |
| `yarn lint` (ESLint, zero warnings, incl. rule banning "Book inspection" copy) | pass |
| `yarn typecheck` (tsc strict, app + e2e) | pass |
| `yarn test` (Jest + RTL + jest-axe) | 30 / 30 |
| `yarn e2e` (Playwright, 5 viewports × 15 checks) | 75 / 75 |
| `ruff check`, `ruff format --check`, `mypy --strict` | pass |
| `pytest` (incl. 20-case regression suite added by QA, `tests/backend_test.py`) | 25 / 25 |

Screenshots: `frontend/e2e/screenshots/{desktop=1440,tablet=1024,iphone=390,android=412}/*.png` (12 screens each). The 320 px project asserts overflow only.

## Independent QA (testing agent, iteration 1)

Report: `test_reports/iteration_1.json`. Backend 100 %, frontend 95 % on first pass. Four findings, all fixed and re-verified in-browser: (1) `Button`/`ButtonLink` now `forwardRef` so Radix dialog triggers receive refs — console clean and focus returns to the trigger on close; (2) unknown-property state gained an `h1` and `data-testid="property-not-found"`; (3) pipeline cards gained `data-testid="pipeline-card-<id>"`; (4) phone top bar is opaque to stop scroll bleed-through.

## Known issues / limitations

1. Playwright's bundled Chromium could not be downloaded in this pod; the harness uses `PW_CHROMIUM_PATH` pointing at the pre-installed headless shell. CI should run `npx playwright install chromium` and omit the variable.
2. Fit/coverage/gate values on cards are display placeholders keyed by legacy ref; real `gates_v1`/`scoring_v1` arrive in M3. Property-detail hard-rule rows are computed from the fixture brief for display only.
3. Freshness bands use a fixed display clock (18 Jun 2026 08:00 AWST) so the synthetic screens are deterministic; M3 switches to server time.
4. No licensed imagery: an attributed "No image · synthetic" placeholder is used everywhere.
5. Service worker caches shell only and is registered in production builds only.
6. Manrope is loaded from Google Fonts; if blocked, the token fallback stack applies.
7. Backend has no persistence yet by design; Supabase PostgreSQL connection string is required before M2.
