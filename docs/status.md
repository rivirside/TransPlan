# TransPlan - Project Status

> **Read this file at the start of every session.**

## What TransPlan Is

A patient-facing clinical decision support tool that helps transplant patients identify the best US cities for their specific organ transplant needs. Currently a static site scoring 22 cities across 8 weighted categories using 40+ data points. On a path to become a probabilistic forecasting engine with Monte Carlo simulation, competing risks modeling, and policy impact analysis. See `docs/ideas.md` for the full SRS and `docs/roadmap.md` for phased development plan.

## Current State: Phase 3 M4 Complete — Equity Analysis

Phase 1 MVP complete (98 Jest tests, 56 limitations tracked). Phase 2 probabilistic engine: M1-M7 done. 193 pytest tests passing. Phase 3 M1: Home Center relocation comparison. Phase 3 M2: Organ-specific donor availability model. Phase 3 M3: City detail modal + side-by-side comparison + print-friendly view. Phase 3 M4: Demographic equity analysis with Gini coefficient metrics, 48-profile stratification matrix (8 blood types × 3 age brackets × 2 sexes), per-city equity rankings, 3 Chart.js disparity visualizations, and mandatory disclaimers. Three-tab results UI: Location Scores, Simulation Probabilities, Equity Analysis. Single-process architecture: FastAPI serves both API and static frontend on one port (no CORS needed). One-click launcher via `TransPlan.app` (macOS .app bundle, no Terminal window) or `start.command`. Graceful degradation when backend unavailable.

**UI/UX Redesign (March 2026):** Full professional redesign completed. Design token system in CSS custom properties. Header with gradient + curved bottom edge. Methodology section rebuilt as compact accordion (native `<details>/<summary>`) with inline SVG icons. Form grouped into fieldset sections. Two responsive breakpoints (768px tablet, 480px mobile). All JS functionality preserved — zero breaking changes.

**Docusaurus Docs Site (March 2026):** Full documentation site in `docs-site/`. Covers: Introduction, Getting Started (Quick Start + Local Setup), Theory (Scoring Methodology, Monte Carlo, Competing Risks, Wait Time Distributions), Architecture (Overview, Data Pipeline, Backend API, Frontend), API Reference (POST /simulate, GET /health, Schemas), Contributing (Dev Guide, Data Curation, Testing), About (FAQ, Limitations, Roadmap). TransPlan brand theme (Inter font, indigo color tokens). GitHub Actions deploy workflow. Builds cleanly (`npm run build` in `docs-site/`).

### What's Done

| Area | Status | Notes |
|------|--------|-------|
| Core algorithm | ✅ Done | 8 categories, organ-specific inputs (cPRA/MELD/LAS), deduped data |
| Data directory (data/) | ✅ Done | 10 JSON seed files, real SRTR volumes, corrected policy tiers |
| Data loader (data-loader.js) | ✅ Done | Runtime JSON loader, DEFAULTS as single source of truth |
| Clinical inputs | ✅ Done | cPRA slider (kidney), MELD (liver), LAS (lung) — conditional fields |
| Ethical/legal fixes | ✅ Done | Disclaimer expanded, "success probability" → "suitability score" |
| Chart.js visualizations | ✅ Done | Stacked weighted bar chart, radar per card, donut weights |
| Accessibility | ✅ Done | ARIA labels on map/charts/results, mobile collapse overlay controls |
| Methodology text | ✅ Done | Accurate data sources, correct volumes, real factors listed |
| Fetch scripts (scripts/) | ✅ Done | All scripts use mergeDataFile, skip-on-empty guards added |
| GitHub Actions | ✅ Done | Single sequential job, weekly cron + manual dispatch |
| Socioeconomic data | ✅ Done | Transplant-support rubric replacing wealth-correlated scores |
| Unit tests | ✅ Done | 98 tests (Jest): 75 algorithm + 23 utilities, 0 failures |
| CDN fallback | ✅ Done | Graceful degradation when Leaflet/Chart.js CDN unavailable |
| CMS API fix | ✅ Done | Multi-strategy query (SQL/filter/legacy); filter works for 22 cities |
| Browser testing | ✅ Done | All 6 organs, edge cases, map overlays — zero console errors |
| UI/UX redesign | ✅ Done | Design tokens, header curve, methodology accordion, SVG icons, responsive breakpoints |
| Docusaurus docs site | ✅ Done | 20 pages, 7 sections, TransPlan brand theme, GitHub Pages deploy workflow |

### Phase 2 Progress

| Milestone | Status | Notes |
|-----------|--------|-------|
| M1: Backend scaffold | ✅ Done | FastAPI app, Pydantic schemas, data loader, /health, 22 pytest tests |
| M2: Wait time distributions | ✅ Done | Log-normal models, 6 organs, 8 blood types, cPRA/MELD/LAS multipliers, 22 tests |
| M3: Monte Carlo engine | ✅ Done | 1000-iteration simulation, POST /simulate, 80ms perf, 25 tests |
| M4: Competing risks | ✅ Done | Mortality/delisting model, outcomes sum to 1.0, 17 tests |
| M5: SRTR data pipeline | ✅ Done | Excel downloader, parser, center mapping, 22 cities × 6 organs, 34 tests |
| M6: Frontend integration | ✅ Done | API client, CDF curves, competing risks chart, dual-mode tabs, graceful degradation |
| M7: Validation & docs | ✅ Done | Sensitivity analysis (tornado chart), Brier score calibration (BS<0.001 all organs), 41 new tests |

### Phase 3 Progress

| Milestone | Status | Notes |
|-----------|--------|-------|
| M1: Home Center Comparison | ✅ Done | Home Center dropdown, comparison badges (score + probability), green map marker, CDF reference line, 2 new tests |
| M2: Organ-Specific Donor Model | ✅ Done | COD multiplier (PMC10329409 × CDC WONDER), toggleable, frontend + backend, 7+2 new tests (ADR-017) |
| M3: City Detail & Comparison UI | ✅ Done | Detail modal (8-cat breakdown + radar + probs), 3-city comparison table, print view (ADR-018) |
| ~~M4: Policy Toggle Simulator~~ | Deferred | Partially redundant with M2 COD multiplier; sensitivity sliders → M5; causal model → Phase 4 |
| M4: Equity Analysis | ✅ Done | 48-profile demographic matrix, Gini coefficient, 3 charts, city equity table, disclaimers (ADR-019) |
| M5: UX Polish & Export | Pending | Dark mode, URL sharing, PDF reports, CSV/JSON export, sensitivity sliders |

### What's NOT Done (Next Steps)

- **Pick winning UI theme** (#3) — 3 professional themes (Clinical/Research/Government) live for comparison
- **Phase 3 M5:** UX Polish & Export (#4–#9) — dark mode, URL sharing, PDF/CSV/JSON export, sensitivity sliders
- **Deploy:** Configure GitHub Pages (#2)
- **FARS API (L-045):** MITIGATED (#10) — entire NHTSA FARS API appears retired; seed data preserved
- **Deferred:** OPO boundaries (#19), SRTR outcomes (#20), donor reg fetch (#21)
- See `docs/roadmap.md` for full phased plan (5 phases through FDA clearance)
- See `docs/ideas.md` for full SRS with architecture, governance, and regulatory details

## Issue Tracking

**GitHub Issues** is the primary tracker for actionable work items (bugs, features, limitations). 23 issues across 5 milestones:

| Milestone | Issues | Description |
|-----------|--------|-------------|
| Phase 1: Deployment | 2 | GitHub Pages, FARS API |
| Phase 3: UI Overhaul | 1 | Pick winning theme, merge, cleanup |
| Phase 3 M5: UX Polish & Export | 6 | Dark mode, URL sharing, PDF/CSV/JSON, charts, sensitivity sliders |
| M2b: COD Model Data Quality | 8 | L-049 through L-056 — upgrade COD multiplier |
| Phase 4: Advanced Modeling | 2 | Configurable weights, causal policy simulator |

**Labels:** `phase:*`, `priority:*`, `limitation`, `cod-model`, `blocked`, `deferred`, `ui/ux`, `backend`, `frontend`, `data-quality`, `data-pipeline`, `milestone:m5`

**Doc files stay as reference:** `status.md` (session start), `design.md` (UI guidelines), `brand-bible.md` (colors/fonts), `limitations.md` (full issue descriptions with file paths and fix complexity).

## File Map

```
TransPlan/
  docs-site/              <- Docusaurus documentation site
    docs/                 <- 20 markdown pages (intro, getting-started/, theory/, architecture/, api-reference/, contributing/, about/)
    src/css/custom.css    <- TransPlan brand theme
    docusaurus.config.ts  <- Site config (baseUrl /TransPlan/docs/, blog disabled)
    sidebars.ts           <- 7-section sidebar navigation
  TransPlan.app/          <- macOS .app bundle (double-click to launch, no Terminal)
    Contents/Info.plist   <- App metadata, LSUIElement=true (background app)
    Contents/MacOS/launch <- Shell script: start uvicorn, open browser
  start.command           <- Double-click to launch (macOS); auto-finds free ports
  stop.command            <- Double-click to stop a running session
  session.js              <- Local session UI (End Session button, same-origin health check)
  api-client.js           <- Backend API client (POST /simulate + /sensitivity + /equity-analysis, graceful fallback)
  probability-charts.js   <- CDF curves, competing risks bar, tornado sensitivity chart (Chart.js)
  equity-charts.js        <- Blood type disparity, age bracket disparity, Gini by city charts (Chart.js)
  index.html              <- Main page (3-tab results: scores, probabilities, equity)
  algorithm.js            <- Scoring engine (8 categories, 22 cities)
  script.js               <- UI, map, form, results display, probability card rendering
  data-loader.js          <- Runtime JSON loader with fallbacks
  charts.js               <- Chart.js radar/bar/donut charts
  styles.css              <- All CSS: design tokens, nav bar, accordion, responsive (768px + 480px)
  themes.css              <- TEMPORARY: 3 professional theme overrides (clinical/research/government)
  theme-switcher.js       <- TEMPORARY: floating theme picker (remove after winner selected)
  package.json            <- Node deps (xml2js, jest)
  README.md               <- User-facing docs
  tests/                  <- Unit tests (Jest)
    algorithm.test.js     <- 75 tests: all 8 scoring categories + comprehensive + COD multiplier
    utils.test.js         <- 23 tests: deepMerge, writeDataFile, mergeDataFile, CITIES
  data/                   <- JSON data files (seed + auto-updated)
    air-quality.json
    cost-of-living.json
    donor-registration.json
    health-demographics.json
    hospital-quality.json
    traffic-fatalities.json
    wait-time-distributions.json  <- Log-normal params from SRTR Table B10
    competing-risks.json          <- Mortality/delisting from SRTR Table B7
    cause-of-death-by-region.json <- Organ recovery rates × state COD proportions (M2)
    srtr-center-mapping.json      <- SRTR center codes → 22 TransPlan cities
    srtr-raw/                     <- Downloaded SRTR Excel files (gitignored)
    manual/               <- Hand-curated data (no API available)
      srtr-reports.json
      climate-scores.json
      policy-tiers.json
      socioeconomic.json
  scripts/                <- Node fetch scripts for GitHub Actions
    utils.js              <- Shared retry, write, city list
    fetch-traffic.js      <- NHTSA FARS
    fetch-air-quality.js  <- EPA AQS (needs API key)
    fetch-hospital-quality.js <- CMS Provider Data
    fetch-cost-of-living.js   <- BLS API (needs API key)
    fetch-health-data.js      <- CDC SODA
    check-srtr-updates.js     <- SRTR website hash check
    validate-data.js          <- Post-fetch validation
    fetch-srtr-excel.py       <- Download SRTR PSR Excel files (6 organs)
    parse-srtr-reports.py     <- Parse Excel → wait-time-distributions.json + competing-risks.json
  .github/workflows/
    fetch-data.yml        <- Weekly data fetch (Mon 6am UTC)
    check-srtr-updates.yml <- Bimonthly SRTR check
  backend/                <- Phase 2 Python FastAPI backend
    main.py               <- FastAPI app, CORS, static file serving, startup data load
    config.py             <- DATA_DIR, SIMULATION_ITERATIONS, ALLOWED_ORIGINS
    requirements.txt      <- Python dependencies
    models/
      schemas.py          <- Pydantic: PatientProfile, SimulationResult, etc.
    routers/
      health.py           <- GET /health (data freshness)
      shutdown.py         <- POST /shutdown (graceful local session end)
      simulate.py         <- POST /simulate (Monte Carlo simulation)
      sensitivity.py      <- POST /sensitivity (tornado chart parameter analysis)
      equity.py           <- POST /equity-analysis (demographic equity analysis)
    services/
      data_loader.py      <- Loads data/*.json at startup
      distributions.py    <- Log-normal wait time distributions (6 organs)
      monte_carlo.py      <- Monte Carlo simulation engine (22 cities × 1000 iter)
      competing_risks.py  <- Competing risks: mortality/delisting rates (6 organs)
      sensitivity.py      <- Sensitivity analysis: parameter impact on p_transplant_24mo
      equity.py           <- Demographic equity analysis (48 profiles × 22 cities, Gini coefficient)
      brier_score.py      <- Brier score calibration: Monte Carlo vs analytical validation
    tests/                <- pytest suite (193 tests)
  docs/
    status.md             <- THIS FILE (read every session)
    ideas.md              <- Full SRS: requirements, architecture, FDA pathway
    design.md             <- Read when touching UI/UX/CSS
    adr-log.md            <- Grep-searchable decision log
    roadmap.md            <- Phased development plan (5 phases)
    limitations.md        <- Issue tracker (56 items, L-001 through L-056)
    brand-bible.md        <- Grep-searchable visual identity
```

## Scoring Algorithm Summary

8 categories, weights sum to 100%:

| # | Category | Weight | Key Data |
|---|----------|--------|----------|
| 1 | Medical Compatibility | 25% | Blood type, age, sex, BMI |
| 2 | Wait Time | 20% | City wait factors, urgency |
| 3 | Donor Availability | 18% | Registration rates, population, living donors |
| 4 | Hospital Quality | 15% | Volume, reputation, specialization |
| 5 | Geographic | 10% | Cost of living, climate, air quality |
| 6 | Health Demographics | 7% | Diabetes, obesity, CKD, hypertension, smoking |
| 7 | Policy | 3% | State donation laws |
| 8 | Socioeconomic | 2% | Support systems |

## Known Limitations

**56 tracked issues** in `docs/limitations.md`. Read when auditing data quality or planning future work.

| Status | Count | Details |
|--------|-------|---------|
| FIXED | 36 | All critical + most high/medium issues (L-001–L-044) |
| OPEN | 12 | L-045 (FARS), L-046–L-048 (fixed), L-049–L-056 (M2 COD model data quality) |
| DEFERRED | 3 | L-009 (OPO), L-017 (SRTR outcomes), L-033 (donor reg fetch) |
| WONT FIX | 2 | L-012 (county health, <0.5pt impact), L-039 (false positive) |

## Documentation Tiers

| Tier | When to Read | Files |
|------|-------------|-------|
| Always | Start of every session | `docs/status.md` |
| Context | When touching that area | `docs/design.md`, `docs/limitations.md` |
| Grep | Only search when needed | `docs/adr-log.md`, `docs/roadmap.md`, `docs/brand-bible.md` |

## Commit & Documentation Habits

- Commit after each logical unit of work with a descriptive message
- Update `docs/status.md` when project state changes meaningfully
- Update `docs/limitations.md` when discovering or resolving issues
- Add an ADR entry when making a non-obvious architectural choice
- Update roadmap when completing items or discovering new work
