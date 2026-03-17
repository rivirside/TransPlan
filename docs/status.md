# TransPlan - Project Status

> **Read this file at the start of every session.**

## What TransPlan Is

A patient-facing clinical decision support tool that helps transplant patients identify the best US cities for their specific organ transplant needs. Currently a static site scoring 22 cities across 8 weighted categories using 40+ data points. On a path to become a probabilistic forecasting engine with Monte Carlo simulation, competing risks modeling, and policy impact analysis. See `docs/ideas.md` for the full SRS and `docs/roadmap.md` for phased development plan.

## Current State: Phase 4 In Progress (Advanced Modeling & Validation)

Phase 1 MVP complete (98 Jest tests, 56 limitations tracked). Phase 2 probabilistic engine: M1-M7 done. 237 pytest tests passing. Phase 3 M1-M5 done. Three-tab results UI: Location Scores, Simulation Probabilities, Equity Analysis. Single-process architecture: FastAPI serves both API and static frontend on one port (no CORS needed). One-click launcher via `TransPlan.app` or `start.command`. Graceful degradation when backend unavailable.

**Phase 4 in progress (March 2026):** 5 milestones scoped (ADR-021). Goal: deepen clinical accuracy and enable publication-grade validation. M1 (Configurable Weights) complete. M2 (Post-Transplant Outcomes) complete. M3 (Historical Trends) complete — multi-year SRTR time series, linear regression trend analysis, trending badges on cards, sparkline charts in modal, trend data in exports/comparison. Post-M3 bugfix: `organ` → `patient.organ` in monte_carlo.py (NameError silently caught, outcomes+trends always null in /simulate), duplicate `const CATEGORY_LABELS` in script.js (SyntaxError broke form submit handler). Both fixed and visually verified. 112 Jest, 333 pytest.

**Data Quality Sprint (March 2026):** 6 of 8 COD model issues resolved:
- L-055: Expanded state COD proportions from 17 to all 50 states + DC (CDC SODA API, donor-eligibility calibration)
- L-051: Automated `fetch-cod-data.js` script added to CI pipeline
- L-053: COD multiplier now stochastic (Beta-distributed recovery rates, kappa=50, ~3.5% CV)
- L-056: Sublinear supply-wait elasticity (0.65 exponent) replaces linear assumption
- L-054: Intestine recovery rates replaced pancreas proxy with OTPD-derived COD-specific rates
- L-052: Anoxia-NOS added as 5th COD category (9.2% of donors, estimated recovery rates, drowning-based state shares)
- Remaining: L-049 (cross-validate OPTN), L-050 (OPO boundaries) — documented as comprehensive GitHub issues

**Multi-Page Architecture (March 2026):** Split from single-page to landing + simulator. `index.html` = dense landing page (features table, how-it-works list, data sources). `simulator.html` = full simulation tool (form, results, modals, map, charts). No header/hero section — nav brand is the only title. Info buttons (ⓘ) on simulator form labels link to relevant docs pages. Docs URL resolution script detects local dev vs deployment.

**Infrastructure (March 2026):** CI pipeline (`.github/workflows/ci.yml`) with 3 parallel jobs: pytest, Jest, data validation. Docker single-container deployment (`Dockerfile` + `docker-compose.yml`): FastAPI serves API + static files, data/ volume-mounted. GitHub issue #1 (data validation failure) closed as stale.

**Design Overhaul (March 2026):** Early-2000s web-inspired redesign. Fonts: IBM Plex Sans (body) + Libre Baskerville (headings), replacing Inter/Lora. Spacing reduced ~40%, shadows eliminated (borders instead), border-radius flattened to 2-3px. Landing page: features table with colored headers, numbered steps list, HR dividers, inline anchor links. Navigation: pipe-separated links with more items (Features, Methodology, Disclaimer, Contact/Docs). Container max-width 960px. White background.

**Theme System (March 2026):** 6 themes — Default (dark nav, indigo accent, centered), Clinical (compact, uppercase, muted teal), Research (serif headings, editorial, warm tones), Government (USWDS-inspired, gov banner, bordered panels), **Windows XP Luna** (blue gradients, silver panels, 3D beveled borders, Tahoma), **2010s Flat** (Material blue, flat geometry, thin headings, Roboto). Windows XP Luna is the default theme. Theme switcher in page footer (both pages). Theme selection deferred to Phase 7. Design token system in CSS custom properties. Landing page has per-theme overrides.

**Docusaurus Docs Site (March 2026):** Full documentation site in `docs-site/`. 20 pages, 7 sections. baseUrl configured for local dev (`/docs-site/build/`). Builds cleanly (`npm run build` in `docs-site/`). Comprehensive docs audit completed March 2026: all 20 pages updated to reflect Phase 3 M4, multi-page architecture, new API endpoints, current test counts, and deployment changes. Navbar has Home (→ `/`) and Open App (→ `/simulator.html`) links using `type: 'html'` to bypass Docusaurus baseUrl prepending. Pre-release info admonitions on intro, roadmap, and contributing pages.

**Deployment (March 2026):** Primary deployment is **Vercel** (`vercel.json` at repo root, `outputDirectory: "."`). Vercel Analytics added to both `index.html` and `simulator.html`. GitHub Pages **disabled** — the `deploy-docs.yml` workflow was removed because it deployed only the docs with a mismatched baseUrl, causing a broken error page. When the project is open-sourced, GitHub Pages can be re-enabled with corrected config.

**Pre-Release Status:** Project under active development. Repository is private, being developed in the open. Will be open-sourced at a future stable release milestone. Contact: tomer@arizona.edu.

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
| Unit tests | ✅ Done | 112 tests (Jest), 333 tests (pytest), 0 failures |
| CDN fallback | ✅ Done | Graceful degradation when Leaflet/Chart.js CDN unavailable |
| CMS API fix | ✅ Done | Multi-strategy query (SQL/filter/legacy); filter works for 22 cities |
| Browser testing | ✅ Done | All 6 organs, edge cases, map overlays — zero console errors |
| UI/UX redesign | ✅ Done | Design tokens, methodology accordion, SVG icons, responsive breakpoints |
| Theme system | ✅ Done | 6 themes (Default/Clinical/Research/Government/WinXP/2010s Flat), XP Luna default |
| Multi-page split | ✅ Done | Landing page (index.html) + simulator (simulator.html), info buttons, nav active state |
| Docusaurus docs site | ✅ Done | 20 pages, 7 sections, TransPlan brand theme, baseUrl fixed for local dev |

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
| M5: UX Polish & Export | ✅ Done | Dark mode, URL sharing, PDF reports, CSV/JSON export, chart image export, what-if scenario sliders (ADR-020), 25 new pytest tests (218 total) |

### Data Quality Sprint (M2b: COD Model)

| Issue | Status | Notes |
|-------|--------|-------|
| L-055: 50-state COD proportions (#17) | ✅ Done | CDC SODA API, donor-eligibility calibration weights |
| L-051: Automated CDC fetch script (#13) | ✅ Done | `fetch-cod-data.js` added to CI pipeline |
| L-053: Stochastic COD multiplier (#15) | ✅ Done | Beta-distributed recovery rates, kappa=50, ~3.5% CV |
| L-056: Supply-wait elasticity (#18) | ✅ Done | 0.65 exponent, sublinear donor→wait relationship |
| L-049: Cross-validate OPTN rates (#11) | Open | Comprehensive issue with validation approach documented |
| L-050: OPO boundary mapping (#12) | Open | City→OPO mapping documented, highest complexity |
| L-052: Add anoxia COD category (#14) | ✅ Done | 5th COD category added (9.2% of donors), estimated recovery rates, state shares from drowning patterns |
| L-054: Intestine-specific rates (#16) | ✅ Done | OTPD ratio × COD-specific clinical adjustments (trauma=0.030, cardio=0.003, drug=0.010, stroke=0.004) |

### Phase 4 Progress

| Milestone | Status | Notes |
|-----------|--------|-------|
| M1: Configurable Scoring Weights | ✅ Done | Weight sliders, 4 presets, auto-normalization, lock, URL/export round-trip, 14 Jest + 10 pytest (#22) |
| M2: Post-Transplant Outcomes Model | ✅ Done | SRTR PSR C-series graft/patient survival, compound success metric, performance ratings, 35 pytest (#31) |
| M3: Historical Trends & Trajectories | ✅ Done | Multi-year SRTR (2019-2025), linregress trends, sparkline charts, trending badges, 51 pytest (ADR-022) |
| M4: Policy Scenario Engine | 🔲 Not started | Literature review → predefined UNOS scenarios (#23) |
| M5: Validation & Reproducibility Pack | ✅ Done | 6 Jupyter notebooks (wait-time, competing-risks, COD-multiplier, outcomes, trends, equity), bias audit service (19 pytest), 39 figures |

### What's NOT Done (Next Steps)

- **Phase 4 IN PROGRESS** — 5 milestones scoped (ADR-021), M1-M3 + M5 done, M4 remaining
- **Data Quality Sprint** — 6/8 COD model issues resolved, 2 documented as comprehensive feature requests
- **FARS API (L-045):** MITIGATED (#10) — entire NHTSA FARS API appears retired; seed data preserved
- **Deferred to Phase 5:** API access (#24), SDKs (#25), scenario builder UI (#26), bulk analysis (#27), widget (#28)
- **Deferred (no API):** OPO boundaries (#19), SRTR outcomes (#20), donor reg fetch (#21), theme selection (Phase 7, #3)
- **Infrastructure:** CI pipeline (#29) ✅, Docker Compose (#30) ✅ — both shipped
- See `docs/roadmap.md` for full phased plan (Phase 4 detailed, Phase 5 expanded)
- See `docs/ideas.md` for full SRS with architecture, governance, and regulatory details

## Issue Tracking

**GitHub Issues** is the primary tracker for actionable work items (bugs, features, limitations). 23 issues across 5 milestones:

| Milestone | Issues | Description |
|-----------|--------|-------------|
| Phase 1: Deployment | 1 | FARS API (GitHub Pages disabled, Vercel is primary) |
| Phase 3: UI Overhaul | 1 | Pick winning theme, merge, cleanup |
| Phase 3 M5: UX Polish & Export | 6 | ✅ DONE — Dark mode, URL sharing, PDF/CSV/JSON, charts, what-if sliders |
| M2b: COD Model Data Quality | 2 open / 6 closed | L-049–L-056 — 6 resolved (50-state, fetch script, stochastic, elasticity, intestine rates, anoxia COD), 2 remain (OPTN validation, OPO mapping) |
| Phase 4: Advanced Modeling | 2 | Configurable weights, causal policy simulator |

**Labels:** `phase:*`, `priority:*`, `limitation`, `cod-model`, `blocked`, `deferred`, `ui/ux`, `backend`, `frontend`, `data-quality`, `data-pipeline`, `milestone:m5`

**Doc files stay as reference:** `status.md` (session start), `design.md` (UI guidelines), `brand-bible.md` (colors/fonts), `limitations.md` (full issue descriptions with file paths and fix complexity).

## File Map

```
TransPlan/
  docs-site/              <- Docusaurus documentation site
    docs/                 <- 20 markdown pages (intro, getting-started/, theory/, architecture/, api-reference/, contributing/, about/)
    src/css/custom.css    <- TransPlan brand theme
    docusaurus.config.ts  <- Site config (baseUrl /docs-site/build/, blog disabled)
    sidebars.ts           <- 7-section sidebar navigation
  TransPlan.app/          <- macOS .app bundle (double-click to launch, no Terminal)
    Contents/Info.plist   <- App metadata, LSUIElement=true (background app)
    Contents/MacOS/launch <- Shell script: start uvicorn, open browser
  start.command           <- Double-click to launch (macOS); auto-finds free ports
  stop.command            <- Double-click to stop a running session
  session.js              <- Local session UI (End Session button, same-origin health check)
  api-client.js           <- Backend API client (POST /simulate + /sensitivity + /equity-analysis + /what-if, graceful fallback)
  probability-charts.js   <- CDF curves, competing risks bar, tornado sensitivity chart (Chart.js)
  equity-charts.js        <- Blood type disparity, age bracket disparity, Gini by city charts (Chart.js)
  dark-mode.js            <- Dark mode toggle (auto-detect, localStorage persist, sun/moon button)
  url-sharing.js          <- URL query param encode/decode for shareable form state
  export-handler.js       <- PDF report, CSV, JSON, chart PNG export
  index.html              <- Landing page (features table, how-it-works list, data sources)
  simulator.html          <- Simulation tool (form, 3-tab results, modals, map, methodology)
  algorithm.js            <- Scoring engine (8 categories, 22 cities)
  script.js               <- UI, map, form, results display, probability card rendering
  data-loader.js          <- Runtime JSON loader with fallbacks
  charts.js               <- Chart.js radar/bar/donut charts
  styles.css              <- All CSS: design tokens (tight spacing, no shadows), nav, landing, accordion, responsive
  themes.css              <- Theme overrides: clinical, research, government (+ landing page per-theme)
  theme-switcher.js       <- Footer-mounted theme picker (6 themes: Default/Clinical/Research/Government/WinXP/2010s Flat)
  package.json            <- Node deps (xml2js, jest)
  README.md               <- User-facing docs
  weight-config.js          <- Scoring weight sliders, presets, normalization, re-score trigger (Phase 4 M1)
  tests/                  <- Unit tests (Jest)
    algorithm.test.js     <- 89 tests: all 8 scoring categories + comprehensive + COD multiplier + configurable weights
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
    post-transplant-outcomes.json <- Graft/patient survival from SRTR Tables C5-C20 (Phase 4 M2)
    srtr-historical.json      <- Multi-year SRTR center metrics for trend analysis (Phase 4 M3)
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
    fetch-cod-data.js         <- CDC SODA (cause-of-death by state, donor-eligibility calibration)
    check-srtr-updates.js     <- SRTR website hash check
    validate-data.js          <- Post-fetch validation
    fetch-srtr-excel.py       <- Download SRTR PSR Excel files (6 organs)
    parse-srtr-reports.py     <- Parse Excel → wait-time-distributions.json + competing-risks.json + post-transplant-outcomes.json
  .github/workflows/
    ci.yml                <- CI: 3 parallel jobs (pytest, Jest, data validation) on push/PR to main
    fetch-data.yml        <- Weekly data fetch (Mon 6am UTC)
    check-srtr-updates.yml <- Bimonthly SRTR check
    (deploy-docs.yml removed — GitHub Pages disabled, Vercel is primary deployment)
  Dockerfile              <- Single container: Python 3.13, uvicorn, static files
  docker-compose.yml      <- Docker Compose: port 8002, data/ volume mount, healthcheck
  .dockerignore           <- Excludes node_modules, .venv, tests, docs, .git
  notebooks/              <- Validation Jupyter notebooks (Phase 4 M5)
    01-wait-time-distributions.ipynb  <- Log-normal model: parameters, PDFs, CDFs, sensitivity
    02-competing-risks.ipynb          <- Mortality/delisting: stacked outcomes, multi-horizon Brier
    figures/              <- Generated PNG figures (gitignored, regenerate by running notebooks)
    README.md             <- Setup instructions, notebook index
  backend/                <- Phase 2 Python FastAPI backend
    main.py               <- FastAPI app, CORS, static file serving, startup data load
    config.py             <- DATA_DIR, SIMULATION_ITERATIONS, SUPPLY_WAIT_ELASTICITY, ALLOWED_ORIGINS
    requirements.txt      <- Python dependencies
    models/
      schemas.py          <- Pydantic: PatientProfile, SimulationResult, etc.
    routers/
      health.py           <- GET /health (data freshness)
      shutdown.py         <- POST /shutdown (graceful local session end)
      simulate.py         <- POST /simulate (Monte Carlo simulation)
      sensitivity.py      <- POST /sensitivity (tornado chart parameter analysis)
      equity.py           <- POST /equity-analysis (demographic equity analysis)
      what_if.py          <- POST /what-if (what-if scenario analysis with multipliers)
    services/
      data_loader.py      <- Loads data/*.json at startup
      distributions.py    <- Log-normal wait time distributions (6 organs)
      monte_carlo.py      <- Monte Carlo simulation engine (22 cities × 1000 iter)
      competing_risks.py  <- Competing risks: mortality/delisting rates (6 organs)
      sensitivity.py      <- Sensitivity analysis: parameter impact on p_transplant_24mo
      equity.py           <- Demographic equity analysis (48 profiles × 22 cities, Gini coefficient)
      what_if.py          <- What-if scenario analysis (Monte Carlo with donor/wait multipliers)
      brier_score.py      <- Brier score calibration: Monte Carlo vs analytical validation
      outcomes.py         <- Post-transplant outcomes: graft/patient survival, compound success (Phase 4 M2)
      trends.py           <- Historical trends: linear regression, direction classification (Phase 4 M3)
    routers/
      ...
      trends.py           <- GET /trends/{city}/{organ}, GET /trends/{organ} (Phase 4 M3)
    tests/                <- pytest suite (333 tests)
  docs/
    status.md             <- THIS FILE (read every session)
    ideas.md              <- Full SRS: requirements, architecture, FDA pathway
    design.md             <- Read when touching UI/UX/CSS
    adr-log.md            <- Grep-searchable decision log
    roadmap.md            <- Phased development plan (5 phases)
    limitations.md        <- Issue tracker (57 items, L-001 through L-057)
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

**57 tracked issues** in `docs/limitations.md`. Read when auditing data quality or planning future work.

| Status | Count | Details |
|--------|-------|---------|
| FIXED | 36 | All critical + most high/medium issues (L-001–L-044) |
| OPEN | 6 | L-045 (FARS), L-049–L-050 (M2 COD model), L-046–L-048 fixed |
| FIXED (M2b) | 6 | L-051 (fetch script), L-052 (anoxia), L-053 (stochastic), L-054 (intestine), L-055 (50 states), L-056 (elasticity) |
| MITIGATED | 1 | L-057 (pancreas graft survival — falls back to patient survival) |
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
