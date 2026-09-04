# Property Acquisition — IDEA-010 private prototype

Working concept, private prototype for the owner. **Synthetic fixture data only. Not production-ready. No live sources are connected.**

## Layout

```
backend/    FastAPI (Python 3.11), all routes under /api          — supervisor: uvicorn server:app :8001
frontend/   React 18 + TypeScript, react-scripts, Tailwind tokens  — supervisor: yarn start :3000
fixtures/   Copied synthetic pack fixtures (design tokens, demo data, digest reference, checklist)
docs/       concept-image-map.md, milestone reports
memory/     PRD.md, master build plan
starter/    Untouched supplied pack (spec, runbook, concept images)
```

## Commands

Frontend (`cd frontend`):

- `yarn start` — dev server (runs `sync-design` first: regenerates `src/design/tokens.css` from `fixtures/design-tokens.json` and copies `demo-data.json`)
- `yarn lint` · `yarn typecheck` · `yarn test` — ESLint (zero warnings), tsc strict, Jest + RTL + jest-axe
- `PW_CHROMIUM_PATH=<chromium binary> yarn e2e` — Playwright at 1440 / 1024 / 390 / 412 / 320 px, writes screenshots to `frontend/e2e/screenshots/<project>/`

Backend (`cd backend`, needs `APP_ENV` and `CORS_ORIGINS` in `.env`):

- `ruff check . && ruff format --check .` · `mypy` · `pytest`

## Boundaries enforced by tests

- No route or UI copy may offer send-to-agent, booking, offers, billing, scraping or a Value Score (`backend/tests/test_system.py`, `frontend/src/__tests__/forbidden.test.ts`).
- Unknown is rendered as Unknown — never 0 %, never a dash, never Fail (`components.test.tsx`).
- No horizontal overflow at 320 CSS px; one `h1` per screen; skip link reaches `main` (`e2e/responsive.spec.ts`).
