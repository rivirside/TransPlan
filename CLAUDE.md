# TransPlan — Claude Session Guide

## What This Is

Transplant center analysis tool at transplant.today. Python/FastAPI backend + vanilla JS frontend on Vercel. 248 SRTR centers, Monte Carlo/BBN/MCMC inference, equity analysis, policy scenarios, spatial interpolation.

## ⚠️ TWO PHASE SYSTEMS — DO NOT CONFUSE

The project has TWO separate numbering systems in `docs/status.md`:

1. **Original development phases (1-7)** — ALL COMPLETE. These built the core product over many months (Monte Carlo engine, BBN, MCMC, copula, center expansion, spatial interpolation, patient resources, UI overhaul). These are documented in `docs/status.md` under sections like "Phase 5 M1-M5", "Phase 6A/6B", "Phase 7 Patient Resources".

2. **Rebuild phases (0-7)** — IN PROGRESS. A structural overhaul started March 30, 2026 to fix architecture problems left over from rapid development. Plan file: `docs/rebuild-plan.md` (also exists at `~/docs/rebuild-plan.md`).

**The rebuild phases are what matter for current work.** Ignore the original phase numbers.

## Current State: Rebuild Phase 3 Is Next

| Rebuild Phase | Status | What |
|---------------|--------|------|
| 0: Seed & Reproducibility | ✅ Done | `seed` param on all simulation endpoints, `seed_used` in responses |
| 1: Nav Restructure | ✅ Done | "For Patients" / "For Professionals" mega-dropdowns |
| 2: Simulator Rebuild | ✅ Done | 6 modules in `simulator/`, 5 in `shared/`, `simulator.html` rewritten |
| **3: Page Merges** | 🔲 **NEXT** | Merge 3 centers pages → 1, merge 2 explorer pages → 1 |
| 4: Model Validation | 🔲 Pending | New `validation.html` with 7 sections, backend router + services |
| 5: Inter-tool Linking | 🔲 Pending | URL params + continue buttons (buttons already built in Phase 2) |
| 6: Tier System | 🔲 Pending | Hide unavailable features instead of greyed-out |
| 7: Cleanup & Polish | 🔲 Pending | Delete `script.js` (4889 lines), delete old HTML pages, final QA |

### Phase 3 Details (Next Session)

Read `docs/rebuild-plan.md` for full implementation specs. Summary:

**3.1 Centers page merge:**
- Combine `find-centers.html` + `centers.html` + `wait-estimator.html` → single `centers.html` with tabs (Find / Browse / Estimate)
- New `centers-page.js` (~500 lines)

**3.2 Explorer page merge:**
- Combine `data.html` + `spatial.html` → single `explorer.html` with tabs (Data Layers / Spatial Analysis)
- New `explorer/index.js`, `explorer/data-layers.js`, `explorer/spatial-analysis.js`

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
script.js              LEGACY monolith (4889 lines) — DO NOT MODIFY, will be deleted in Rebuild Phase 7
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
