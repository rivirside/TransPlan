# TransPlan — Claude Session Guide

## What This Is

Transplant center analysis tool at transplant.today. Python/FastAPI backend + vanilla JS frontend on Vercel. 248 SRTR centers, Monte Carlo/BBN/MCMC inference, equity analysis, policy scenarios, spatial interpolation.

## Current State: Rebuild Complete ✅

All 8 rebuild phases (0-7) are done. The structural overhaul that started March 30, 2026 is finished.

**What's next:** See "Post-Rebuild Priorities" below.

### What the Rebuild Accomplished

| Phase | What |
|-------|------|
| 0: Seed & Reproducibility | `seed` param on all simulation endpoints, `seed_used` in responses |
| 1: Nav Restructure | "For Patients" / "For Professionals" mega-dropdowns |
| 2: Simulator Rebuild | 6 modules in `simulator/`, 5 in `shared/`, `simulator.html` rewritten |
| 3: Page Merges | 3 centers pages → 1 tabbed page, 2 explorer pages → 1 tabbed page |
| 4: Model Validation | `validation.html` with 7 analysis sections |
| 5: Inter-tool Linking | URL params + continue buttons across all tools |
| 6: Tier System | Hide unavailable features instead of greyed-out |
| 7: Cleanup & Polish | `script.js` (4889 lines) + `data-explorer.js` (1420 lines) deleted |

### Post-Rebuild Priorities

**Done in the June 2026 session** (see `docs/bbn-rebuild-plan.md`, `docs/limitations.md`):
- **#206 BBN 248-center rebuild — DONE.** CompetingOutcome now grounded in observed SRTR Table B7 rates (not magic numbers); hybrid p24 (WaitCategory timing × observed competing-loss drain) keeps blood-type sensitivity. Closed #209, #210, #211, #226; advanced #214. Full build 11.5s→0.39s (vectorized). Known trade-off tracked: L-072 / #238 (competing-risk split is center-average, not patient-specific).
- **Security/stats audit:** closed #215 (CORS), #218 (X-Forwarded-For), #225 (Gini validation), #229 (zero-rate fallback).
- **Validation:** SRTR per-center calibration (`scripts/run-center-calibration.py`) — Spearman ρ 0.70–0.89. COMET-Lung comparison found infeasible (COMET is population-level, doesn't rank centers) — SRTR calibration is the substitute. Historical SRTR data (2018–2025) retrieved + archived (`data/srtr-archive/`).
- **CI:** green again (was red since March — `netCDF4` missing + SHUTDOWN_TOKEN bug).

**Still open:**
1. **#207** MCMC 248-center refit (BBN done; MCMC not)
2. **#208 audit** — remaining sub-issues (BBN CPT empirical grounding #213/#214 deepening). Closed this session: #216 (equity now closed-form, full 248 centers), #217 (innerHTML XSS).
3. **#237** temporal validation — done as out-of-sample persistence + model concordance (`docs/temporal-validation-report.md`); full fit-on-N/predict-N+k forecast is the remaining follow-up. **#236** continuous BBN latents, **#238** revisit BBN hybrid.
4. **Papers** — owner-driven; do NOT work on `papers/` (rigor/usability/validation work is pre-approved instead)
5. **Old page cleanup** — `find-centers.html`, `wait-estimator.html`, `data.html`, `spatial.html` still on disk

## Architecture

```
backend/               Python FastAPI (uvicorn, port 8002)
  main.py              Entry point, CORS, static file serving
  routers/             simulate, score, sensitivity, equity, spatial, etc.
  services/            monte_carlo, scoring, bbn_inference, mcmc_inference, etc.
simulator/             Modular JS (IIFE pattern, no build step)
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
  weight-config.js     Scoring weight sliders
components/
  site-chrome.js       Nav + footer (injected into all pages)
centers-page.js        Centers tabbed page (Find/Browse/Estimate)
explorer/              Explorer tabbed page (Data Layers/Spatial Analysis)
  index.js             Entry point + tab switching
  data-layers.js       Choropleth/heatmap data visualization
  spatial-analysis.js  Spatial interpolation + environmental layers
```

### Pages

| Page | File | Purpose |
|------|------|---------|
| Landing | `index.html` | Hero + feature cards + CTA |
| Simulator | `simulator.html` | Main tool — score + simulate centers |
| Centers | `centers.html` | Find / Browse / Estimate (tabbed) |
| Explorer | `explorer.html` | Data Layers / Spatial Analysis (tabbed) |
| Validation | `validation.html` | 7-section model validation |
| Sensitivity | `sensitivity.html` | Parameter sensitivity analysis |
| Scenarios | `scenarios.html` | Policy scenario comparison |
| Equity | `equity.html` | Demographic equity auditing |
| Center Detail | `center.html` | Single-center deep dive |
| Patient Resources | `checklist.html`, `education.html`, `faq.html`, `organ-guides.html`, `support.html`, `advocacy.html` | Patient-facing content |

## Dev Server

```bash
# Backend (serves API + static files)
cd /Volumes/Lab/GitHub/TransPlan
source .venv/bin/activate          # local .venv is Python 3.12.11; .python-version is "3.12" (major.minor only — a patch pin like 3.12.11 breaks Vercel's uv runtime, which can't fetch exact patches)
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
# Python tests — must run from backend/ so services imports resolve
cd backend && python -m pytest -q         # all tests (requires .venv active)
cd backend && ../.venv/bin/python -m pytest -q  # without activating venv
# 838 pass on pymc 6.0.1, including the MCMC suites. (The MCMC tests need the
# netCDF4/h5netcdf backends in requirements.txt to serialize traces — without
# them they error out, which looks like a pymc-version problem but isn't.)

npm test                                  # 112 Jest tests (from repo root)
```

## Landscape & Benchmarking

See `docs/landscape/` for 7 tool profiles (SRTR, KPSAM/LSAM/TSAM, COMET, LivSim, TransplantCenterSearch, statistical packages) and the comparison matrix. Benchmarking plan: COMET-Lung rank comparison is Priority 1.

## Open Issues

- **#208:** Comprehensive audit — several sub-issues closed (#209, #210, #211, #215, #218, #225, #226, #229); remaining incl. #213, #214, #216, #217
- **#207:** MCMC 248-center refit (BBN #206 done)
- **#236/#237/#238:** continuous BBN latents / temporal validation / revisit BBN hybrid (filed June 2026)
- **#107:** Face validity review with transplant faculty
- **Model limitations:** see `docs/limitations.md` (L-072 = BBN hybrid trade-off)
