# Concept image → route / component map (Milestone 1)

Authority order: Build Specification > concept images. Two known conflicts resolved in the spec's favour: no Map or Comparables page, and no Indicative Value / Value Score anywhere.

Status legend — **Built (M1)**: implemented with synthetic display data · **Shell (M1)**: route and layout exist, real behaviour arrives in the milestone shown · **Later**: route reserved, not yet rendered.

| # | Concept image | Route(s) | Components realised in M1 | Status |
| --- | --- | --- | --- | --- |
| 00 | `00-design-system.png` | — (global) | `design/tokens.css` (generated), `tailwind.config.js`, `Button`, `StatusChip`, `FitRing`, `PropertyCard`, `CompareRow`, `SourceFreshness`, text-field styles, top bar, desktop sidebar, mobile bottom nav. **Omitted by spec:** Map marker, Comparables nav, Indicative value | Built (M1) |
| 01 | `01-web-welcome-sign-in.png` | `/` | `WelcomePage`, `PublicShell`, `BrandMark`, `ConceptBadge`, disabled provider buttons with no-Gmail statement, Terms/Privacy links | Built (M1); auth wiring M2 |
| 02 | `02-web-create-buying-journey.png` | `/app/journeys/new` | — (reserved) | Later (M2) |
| 03 | `03-web-buying-brief.png` | `/app/brief` | — (reserved) | Later (M2) |
| 04 | `04-web-locations-travel.png` | `/app/brief/locations` | — (reserved). Travel time already rendered as **Unknown** in Compare | Later (M2) |
| 05 | `05-web-source-connections.png` | `/app/sources` | `SourcesPage` — five cards with honest states (Configured / Not connected / Unsupported), `StatusChip` | Shell (M1) → M4 |
| 06 | `06-web-today-dashboard.png` | `/app/today` | `TodayPage`, `MetricCard`, change timeline with "Why it matters", Journey health `FitRing`s, Next actions, quiet `EmptyState` | Shell (M1) → M3 |
| 07 | `07-web-discover-pipeline.png` | `/app/discover`, `/app/pipeline` | `DiscoverPage` (gate filters, cards/list toggle, result count, no-result `EmptyState`), `PipelinePage` (11 buyer stages, horizontally scrolling labelled region), `PropertyCard` | Shell (M1) → M3 |
| 08 | `08-web-property-detail.png` | `/app/properties/:id` | `PropertyDetailPage` header (raw guide + kind, facts, separate market/buyer chips), image placeholder with attribution fallback, context panel | Shell (M1) → M3 |
| 09 | `09-web-match-evidence.png` | `/app/properties/:id` (Hard rules section) | Hard-rules table with Pass/Fail/Unknown `EvidenceState`, "Unknown is not Pass" note, fit + coverage rings, source evidence panel | Shell (M1) → M3 |
| 10 | `10-web-property-comparison.png` | `/app/compare` | `ComparePage`, `CompareRow` (Unknown cell distinct from a value), column headers, add-property slot. **Comparable sales strip omitted by spec** | Shell (M1) → M3 |
| 11 | `11-web-shortlist-board.png` | `/app/saved`, `/app/pipeline` | `SavedPage` (saved cards), `PipelinePage` (stage columns) | Shell (M1) → M3 |
| 12 | `12-web-inspections-tasks.png` | `/app/tasks` | `TasksPage` — advertised open homes with `SourceFreshness`, "Add reminder" `ConfirmDialog` (never "Book"), task list | Shell (M1) → M5 |
| 13 | `13-web-agents-drafts.png` | `/app/agents` | `AgentsPage` — public contact evidence vs private notes, UNSENT draft, copy-to-mail-client confirm; no send control | Shell (M1) → M5 |
| 14 | `14-web-settings-privacy-household.png` | `/app/settings` | `SettingsPage` — profile, notifications, household, privacy/deletion `ConfirmDialog` | Shell (M1) → M2/M6 |
| 15 | `15-iphone-today-discover.png` | `/app/today`, `/app/discover` @ 390px | `BottomNav` (Today / Properties / Saved / More), stacked metrics, phone filter chips | Built (M1) |
| 16 | `16-iphone-property-evidence.png` | `/app/properties/:id` @ 390px | single-column detail, scrollable labelled rules table | Shell (M1) |
| 17 | `17-iphone-compare-tasks.png` | `/app/compare`, `/app/tasks` @ 390px | `CompareRow` stacked mode (attribute heading + per-column labels) | Built (M1) |
| 18 | `18-iphone-sources-notifications.png` | `/app/sources`, notifications (bell → `/app/tasks` placeholder) @ 390px | source cards stacked; notification centre itself is M5 | Shell (M1) → M5 |
| 19 | `19-android-today-discover.png` | `/app/today`, `/app/discover` @ 412px | as 15 | Built (M1) |
| 20 | `20-android-property-compare.png` | `/app/properties/:id`, `/app/compare` @ 412px | as 16/17 | Built (M1) |
| 21 | `21-android-tasks-drafts-settings.png` | `/app/tasks`, `/app/agents`, `/app/settings` @ 412px | as 12/13/14 | Shell (M1) |
| 22 | `22-tablet-today-discover.png` | `/app/today`, `/app/discover` @ 768–1023px | `DesktopRail` icon-rail mode (labels under icons), two-column Today; Discover master-detail pane is M3 | Built (M1) / Shell |
| 23 | `23-tablet-property-compare.png` | `/app/properties/:id`, `/app/compare` @ 1024px | grid comparison, detail two-pane | Shell (M1) |
| 24 | `24-web-about-how-it-works.png` | `/about` | `AboutPage` — hero, example brief + fit + evidence checklist, five steps, three trust statements, CTA, limitation line | Built (M1) |

## Derived tokens (documented, reversible)

`design-tokens.json` supplies canvas, navy, eucalyptus, ochre, surface, border, mutedText, risk, radius and the phone bottom-nav labels. Milestone 1 derives, for accessible contrast only: `eucalyptus-deep #3D6B51` (text/button on white ≥ 4.5:1), `ochre-deep #8A5A2B` (text), soft tints (`eucalyptus-soft`, `eucalyptus-tint`, `ochre-soft`, `risk-soft`, `navy-soft`), `charcoal #2A2E33`, `stone #D9DDD7`, `canvas-deep #EFEAE1`, and a 4-px spacing scale. Raw `eucalyptus #6F8F7A` and `ochre #C88A52` are used only as fills/rings, never as small text on white.
