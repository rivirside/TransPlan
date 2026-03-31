# TransPlan — Claude Session Guide

> Read `docs/status.md` for full project history. Read `.claude/plans/vectorized-honking-curry.md` for implementation details.

## What This Is

Transplant center analysis tool at transplant.today. Python/FastAPI backend + vanilla JS frontend on Vercel. 248 SRTR centers, Monte Carlo/BBN/MCMC inference, equity analysis, policy scenarios, spatial interpolation.

## Current State: Rebuild Phase 3

Full 8-phase rebuild in progress. **Phases 0-2 complete. Phase 3 (page merges) is next.**

### What's Done

| Phase | What | Key Files |
|-------|------|-----------|
| 0 | Seed support on all simulation endpoints | `backend/routers/*.py`, `shared/export-handler.js` |
| 1 | Nav → "For Patients" / "For Professionals" | `components/site-chrome.js` |
| 2 | Simulator rebuilt as modular architecture | `simulator/*.js` (6 files), `shared/*.js` (5 files), `simulator.html` |

### What's Next

**Phase 3:** Merge redundant pages
- `find-centers.html` + `centers.html` + `wait-estimator.html` → single `centers.html` with tabs
- `data.html` + `spatial.html` → single `explorer.html` with tabs

**Phase 4:** New Model Validation tool (`validation.html`, backend router + services)
**Phase 5:** Inter-tool linking (continue buttons already built in Phase 2)
**Phase 6:** Tier system (hide, not disable)
**Phase 7:** Delete `script.js`, old pages, final QA

## Architecture

```
backend/               Python FastAPI (uvicorn, port 8002)
  main.py              Entry point, CORS, static file serving
  routers/             simulate, score, sensitivity, equity, spatial, etc.
  services/            monte_carlo, scoring, bbn_inference, mcmc_inference, etc.
simulator/             NEW modular JS (IIFE pattern, no build step)
  index.js             Entry point — form → API → table/map
  map.js               Leaflet map with center markers
  tier-panel.js        Fetches GET /tier, applies caps
  form-helpers.js      Home center dropdown, slider wiring
  results.js           Orchestrator (runScoring, runSimulation)
  results-table.js     Sortable table renderer
shared/                Cross-page utilities
  api-client.js        All API calls (TransPlanAPI namespace)
  export-handler.js    PDF/CSV/JSON/RunArtifact export
  data-loader.js       Runtime JSON loader
  continue-buttons.js  Inter-tool linking buttons
  geo-utils.js         Haversine, geocoding
components/
  site-chrome.js       Nav + footer (injected into all pages)
  weight-config.js     Scoring weight sliders
script.js              LEGACY monolith (4889 lines) — DO NOT MODIFY, will be deleted in Phase 7
```

## Dev Server

```bash
# Backend (serves API + static files)
cd /Users/rivir/Documents/GitHub/TransPlan
source .venv/bin/activate
uvicorn backend.main:app --port 8002 --reload

# Or use .claude/launch.json preset:
# preview_start with name "backend"
```

## Key Patterns

- **IIFE modules:** All JS uses `(function() { 'use strict'; ... window.ModuleName = { ... }; })()` pattern
- **No build step:** Vanilla JS, loaded via `<script>` tags at bottom of `<body>`
- **DOMContentLoaded fix:** Use `if (document.readyState === 'loading') { addEventListener... } else { init(); }` because scripts at bottom of body run after DOMContentLoaded fires
- **Tier system:** `GET /tier` returns caps; `tier-panel.js` hides/caps UI controls server-side
- **URL params:** Tools pass patient profile via `?organ=kidney&bt=O%2B&age=45&sex=male&urg=2`
- **Two buttons:** "Score Centers" (POST /score, instant) + "Run Simulation" (POST /simulate, Monte Carlo)

## Tests

```bash
pytest                    # 594+ tests
npm test                  # 112 Jest tests
```

## Open Issues

- **#208:** Comprehensive audit (33 sub-issues) — deferred until rebuild complete
- **#206/#207:** BBN/MCMC model expansion to 248 centers
- **#107:** Face validity review with transplant faculty
