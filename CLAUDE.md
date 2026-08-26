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

npm test                                  # 44 Jest tests (from repo root)
```

## Landscape & Benchmarking

See `docs/landscape/` for 7 tool profiles (SRTR, KPSAM/LSAM/TSAM, COMET, LivSim, TransplantCenterSearch, statistical packages) and the comparison matrix. Benchmarking plan: COMET-Lung rank comparison is Priority 1.

## Clinical Assumptions Register

`docs/clinical-assumptions-register.md` — the living catalog of **every point where a clinical/medical judgment is encoded or clinically-derived data is used** (scoring weights, ABO/MELD/LAS multipliers, hazard model, copula θ, BBN CPTs, MCMC priors, equity/spatial/policy assumptions, the data files + generation clamps). Each entry has a stable ID, location, justification status, and risk. **225 assumptions tracked; 130 still need justification; 59 high-risk** (counts AND the priority shortlist are regenerated by `scripts/check-register.py`, pinned by `backend/tests/test_register_counts.py` — before #335 the header had drifted to 129/37/45 and the shortlist named 5 rows that no longer qualified while missing 11 that did, because nothing recomputed either) — see the "Priority to justify" shortlist at the bottom. **Keep it updated:** add/adjust a row whenever a clinical value or assumption is introduced, changed, or finally cited.

## Open Issues

Snapshot Aug 26, 2026. **Closed in #370** with evidence: #335 (pediatric mode), #328 (model card + docs-site routing), #350 (parameter audit), #336 (county trauma), #337 (waitlist-composition equity weights), #113 (coverage gaps).

**Opened by that work:**
- **#371:** BBN and MCMC have no pediatric wait model (L-079) — they restrict to pediatric centers but return adult numbers, currently disclosed via a `pediatric_wait_model` provenance family rather than fixed
- **#372:** PELD mapped onto MELD's thresholds without a published equivalence (SCORE-31 / L-078)
- **#373:** Remaining unexposed API parameters after the #350 audit

**Blocked on environment, not effort:** #323 (drive-time matrix) needs a self-hosted OSRM build — Docker daemon plus a ~10GB US OSM extract and hours of preprocessing. #267 (2SFCA) waits on it; its demand side is unblocked now that county population exists. `scripts/run-coverage-gaps.py` is written so swapping the distance function is the only change required.

**Still open from before:**
- **#285:** Epic — retire the 22-city list (inventory + phased plan; supersedes #205/#234 remainders; #207 is its first phase)
- **#270:** 2026-06 code-review epic — still-real remainder: #244 (BBN horizon), #249 (tier caps on /score), #251/#252/#254/#257/#258/#259 (statistical validity), #262/#264 (refactors), #260 (donation-banner, blocked on #179), #250 (exact dependency pins)
- **#207:** MCMC 248-center refit (BBN #206 done)
- **#236/#237/#238, #274/#275:** BBN latents / temporal validation / BBN hybrid / log_sigma ceiling / volume data
- **#107:** Face validity review with transplant faculty
- **Model limitations:** see `docs/limitations.md` — 79 entries (L-072 = BBN hybrid trade-off; L-076/L-077 pediatric derivation + small cohorts; L-078 PELD; L-079 BBN/MCMC pediatric wait model)

**Data-pipeline lesson (2026-08-05 incident):** the SRTR workflow once overwrote three model files with organ-less shells because `data/srtr-raw/` is absent in CI. Every generated data file must have a never-shrink guard (`_write_guarded` in parse-srtr-reports.py, dead-data guards in fetch-cost-of-living.js, organ-block checks in validate-data.js).

**Guard lesson (#370):** a guard that cannot fail is worse than none, because it reads as coverage. Two shipped in this state — `parse-waitlist-composition.py` checked that a vector summed to 1 *after normalizing over whatever survived*, so a renamed SRTR column would have produced "the kidney waitlist is 100% male" and passed; and `fetch-trauma-counties.py` silently dropped two centers because both fallback branches were conditional. **Negative-test every new guard** by breaking the data on purpose and confirming it fails with the remedy in the message.
