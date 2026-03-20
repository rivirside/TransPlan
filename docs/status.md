# TransPlan - Project Status

> **Read this file at the start of every session.**

## What TransPlan Is

A patient-facing clinical decision support tool that helps transplant patients identify the best US cities for their specific organ transplant needs. Currently a static site scoring 22 cities across 8 weighted categories using 40+ data points. On a path to become a probabilistic forecasting engine with Monte Carlo simulation, competing risks modeling, and policy impact analysis. See `docs/ideas.md` for the full SRS and `docs/roadmap.md` for phased development plan.

## Current State: Phase 6B In Progress (Spatial Geographic Modeling)

Phase 1 MVP complete (112 Jest tests, 62 limitations tracked). Phase 2 probabilistic engine: M1-M7 done. Phase 3 M1-M5 done. Phase 4 M1-M5 done. Phase 5 M1-M5 done. **Phase 6A complete, Phase 6B in progress.** Three-tab results UI: Location Scores, Simulation Probabilities, Equity Analysis. Single-process architecture: FastAPI serves both API and static frontend on one port (no CORS needed). One-click launcher via `TransPlan.app` or `start.command`. Graceful degradation when backend unavailable.

**Phase 4 complete (March 2026):** All 5 milestones done (ADR-021). M1 (Configurable Weights), M2 (Post-Transplant Outcomes), M3 (Historical Trends), M4 (Policy Scenario Engine), M5 (Validation & Reproducibility Pack). 112 Jest, 448 pytest.

**Phase 5 M1 complete (March 2026):** Bayesian Belief Network inference engine (ADR-024). 12-node DAG with pgmpy VariableElimination for exact inference (~30ms cached vs ~2s MC). Toggle via `POST /simulate?inference_mode=bayesian`. All 7 CPTs derived from existing JSON data (no duplication). Cross-validated: Spearman rank > 0.5 for city rankings, directional consistency on blood type/organ/urgency effects. Frontend inference method dropdown + method badge. 72 new BBN-specific pytest tests. Issues #36-#42 closed.

**Phase 5 M2 complete (March 2026):** Clayton copula for correlated competing risks (ADR-025). Mortality and delisting times now optionally drawn with positive lower-tail dependence via `use_copula: true` on PatientProfile. Default θ=1.0 (Kendall's τ ≈ 0.33). Conditional sampling method preserves marginal exponential distributions. All 3 simulation paths (monte_carlo, what_if, sensitivity) support copula. 22 copula unit tests + 4 integration tests. Issue #94.

**Phase 5 M3 complete (March 2026):** PyMC MCMC hierarchical survival model (ADR-026). Third inference engine (`inference_mode=mcmc`) with honest Bayesian uncertainty quantification. Three-level hierarchy: national hyperpriors → 22 city random effects → patient covariates (blood type, urgency). 92 free parameters per organ, 6 independent models. Offline NUTS fitting via `scripts/fit-mcmc-model.py`, cached traces in ArviZ NetCDF (~10-50 MB per organ). Query-time: 50 posterior draws × forward simulation (~200-500ms). Frontend dropdown + orange MCMC badge. Issue #95.

**Phase 5 M4 complete (March 2026):** Shared frailty via LKJ-Cholesky correlated city offsets (ADR-027). MCMC model now learns mortality ↔ delisting correlation from data via bivariate MvNormal with LKJ prior (η=2), replacing the fixed external copula for MCMC mode. Bayesian HDI replaces bootstrap CIs — posterior-predictive credible intervals computed from per-draw p24 values. 11 new tests. 538 pytest + 112 Jest = 650 total. Issues #96, #99.

**Phase 5 M5 near-complete (March 2026):** Cross-engine validation, model quality checks, and comprehensive bug/quality sprint. (1) Cross-engine validation service (`services/cross_validation.py`): runs MC, BBN, and MCMC on the same patient and computes Spearman rank correlation, mean/max absolute probability differences, top-5 city overlap. (2) Per-organ copula θ (L-059 fix): organ-specific Clayton copula parameters (kidney=0.8 through heart=1.8) replace the single fixed θ=1.0 across all 4 simulation paths. (3) Strict convergence gate (L-062 fix): `--strict` flag on `fit-mcmc-model.py` requires R-hat < 1.01 and ESS > 400 before saving traces. (4) Posterior predictive checks (`services/posterior_checks.py`): compares MCMC posterior predictions against observed SRTR statistics (national medians, city factors, blood type multipliers, mortality/delisting rates, urgency monotonicity). 24 new tests (14 cross-validation + 10 posterior checks). (5) Bug/quality sprint: 15 issues closed across 3 tiers — thread safety (#55), exception handling (#56), centerReputation differentiation (#44), XSS audit (#57), nullish coalescing (#67), LAS float parsing (#68), dead code removal (#71), concurrent submission guard (#66), frozen dist introspection (#61), honest BBN uncertainty band (#54), per-organ BBN terciles (#59), BLS cost-of-living verified (#101), EPA air quality verified (#100), CDC PLACES expanded to 5 county-level indicators (#102), FARS CSV bulk download (#103). (6) #104: Real SRTR historical data (14 biannual releases 2019–2025) with automated GitHub Actions refresh — resolved by user.

**Phase 6A complete (March 2026):** Center expansion from 22 cities to ~250 SRTR centers. (1) Extracted all center codes, names, coordinates, and organ programs from SRTR PSR Excel files → `data/srtr-all-centers.json` (248 centers). (2) Three-tier geocoding: Nominatim automated (200+), city_mapping fallback, manual coordinates. (3) Center-level data files: `wait-time-distributions-centers.json` (248), `competing-risks-centers.json` (248), `post-transplant-outcomes-centers.json` (243). (4) Dynamic CITIES loading: all backend services (`monte_carlo`, `equity`, `sensitivity`, `what_if`, `mcmc_inference`) now use `_get_cities()` with fallback, replacing hardcoded lists. (5) `GET /centers` endpoint with organ and focus_only filters. (6) Frontend dropdown tries API first, falls back to hardcoded cityStateMap. Issues #115-#119 closed.

**Phase 6B in progress (March 2026):** Spatial interpolation and UNOS allocation geography. (1) RBF/IDW interpolation engine (`services/spatial_interpolation.py`): continuous geographic surfaces from center-level data (24 layers: air quality, cost of living, 5 health metrics, per-organ wait_time_factor/mortality_factor/graft_survival). (2) Spatial API endpoints: `GET /spatial-layers`, `GET /interpolated-value`, `GET /interpolated-profile`, `GET /allocation-circles`, `GET /distance-score`. (3) UNOS allocation circle modeling (`services/allocation_geography.py`): 250nm/500nm radius analysis, competition scoring, composite distance score (proximity 40% + competition 35% + donor pool 25%). (4) `haversine_distance_nm()` for UNOS-policy-aligned nautical mile calculations. 32 new pytest tests (19 spatial + 13 allocation). Issues #127, #128, #130 closed. Remaining: EPA monitor data (#125), CDC county data (#126), frontend heatmap overlay (#129).

**M4 (Policy Scenario Engine):** 4 predefined UNOS policy scenarios with literature-backed parameters and per-city adjustments: (1) 2021 Kidney 250nm Circles — per-center-size donor/wait adjustments, (2) Continuous Distribution — stronger geography de-emphasis, (3) Increased DCD Utilization — +15% organ supply, (4) Broader HCV+ Acceptance — +6% donor pool for kidney/liver. Frontend policy scenario selector in probability tab. `POST /policy-scenario` endpoint, `GET /policy-scenarios` listing. 24 new pytest tests.

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

**Docusaurus Docs Site (March 2026):** Full documentation site in `docs-site/`. 22 pages (20 original + 2 validation), 8 sections. baseUrl configured for local dev (`/docs-site/build/`). Builds cleanly (`npm run build` in `docs-site/`). Comprehensive docs audit completed March 2026: all 20 pages updated to reflect Phase 3 M4, multi-page architecture, new API endpoints, current test counts, and deployment changes. Navbar has Home (→ `/`) and Open App (→ `/simulator.html`) links using `type: 'html'` to bypass Docusaurus baseUrl prepending. Pre-release info admonitions on intro, roadmap, and contributing pages. **MDX + Interactive Charts (March 2026):** 4 theory pages migrated from .md to .mdx with Recharts interactive visualizations — DistributionCurve (wait times by blood type + all organs), HeatmapTable (competing risks rates, scoring categories), TornadoChart (sensitivity parameter impact). 2 new validation pages: sensitivity analysis (tornado charts per organ) and SRTR ground-truth comparison (color-coded accuracy table). 4 custom React components in `docs-site/src/components/`.

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
| Unit tests | ✅ Done | 112 tests (Jest), 594 tests (pytest) |
| CDN fallback | ✅ Done | Graceful degradation when Leaflet/Chart.js CDN unavailable |
| CMS API fix | ✅ Done | Multi-strategy query (SQL/filter/legacy); filter works for 22 cities |
| Browser testing | ✅ Done | All 6 organs, edge cases, map overlays — zero console errors |
| UI/UX redesign | ✅ Done | Design tokens, methodology accordion, SVG icons, responsive breakpoints |
| Theme system | ✅ Done | 6 themes (Default/Clinical/Research/Government/WinXP/2010s Flat), XP Luna default |
| Multi-page split | ✅ Done | Landing page (index.html) + simulator (simulator.html), info buttons, nav active state |
| Docusaurus docs site | ✅ Done | 22 pages, 8 sections (+ Validation), MDX + Recharts interactive charts, TransPlan brand theme |

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
| M4: Policy Scenario Engine | ✅ Done | 4 predefined UNOS scenarios (250nm circles, continuous distribution, DCD expansion, HCV+ donors), per-city multipliers, literature refs, 24 pytest (#23) |
| M5: Validation & Reproducibility Pack | ✅ Done | 6 Jupyter notebooks (wait-time, competing-risks, COD-multiplier, outcomes, trends, equity), bias audit service (19 pytest), 39 figures |

### Phase 5 Progress

| Milestone | Status | Notes |
|-----------|--------|-------|
| M1: Bayesian Belief Network | ✅ Done | 12-node DAG, pgmpy VariableElimination, 7 CPTs from existing data, API toggle, frontend dropdown, cross-validated, 72 pytest (ADR-024, #36-#42 closed) |
| M2: Clayton Copula | ✅ Done | Correlated mortality/delisting draws, θ=1.0 (τ≈0.33), opt-in via `use_copula`, all 3 sim paths, 22+4 tests (ADR-025, #94) |
| M3: MCMC Hierarchical Model | ✅ Done | PyMC NUTS, 92 params/organ, trace-as-cache, offline fitting, posterior uncertainty, 53 pytest (ADR-026, #95) |
| M4: Shared Frailty + Bayesian HDI | ✅ Done | LKJ-Cholesky correlated mort/delist offsets, learned correlation, posterior-predictive CIs, 11 new tests (ADR-027, #96, #99) |
| M5: Cross-Engine Validation & Quality | ✅ Done | Cross-engine validation, posterior checks, per-organ copula, strict convergence, 15-issue bug sprint, real SRTR historical data (#104). Sensitivity analysis report (#109) and SRTR ground-truth comparison (#110) complete with interactive docs. |

### Phase 6 Progress

| Milestone | Status | Notes |
|-----------|--------|-------|
| 6A: Extract SRTR center list (#115) | ✅ Done | 248 centers cataloged from Excel files |
| 6A: Add geographic coordinates (#116) | ✅ Done | Three-tier geocoding (Nominatim + city_mapping + manual) |
| 6A: Update parse script (#117) | ✅ Done | Center-level data files for wait times, competing risks, outcomes |
| 6A: Replace hardcoded CITIES (#118) | ✅ Done | Dynamic `_get_cities()` in all backend services |
| 6A: Dynamic center dropdown (#119) | ✅ Done | API-first with hardcoded fallback |
| 6A: Marker clustering (#120) | Deferred | Frontend enhancement — not blocking spatial work |
| 6A: Results pagination (#121) | Deferred | Frontend enhancement — not blocking spatial work |
| 6A: OPO mapping (#122) | Deferred | Extends existing #19, requires manual lookup |
| 6A: Patient home location (#123) | Deferred | Extends existing #111, needs geocoding UI |
| 6B: Interpolation service (#127) | ✅ Done | RBF/IDW engine, 24 layers, SpatialSurface cache, 19 pytest |
| 6B: Interpolation API (#128) | ✅ Done | 4 new endpoints on spatial router |
| 6B: Heatmap overlay (#129) | Open | Frontend Leaflet heatmap/choropleth |
| 6B: Allocation circles (#130) | ✅ Done | 250nm/500nm UNOS circles, competition score, distance score, 13 pytest |
| 6B: EPA monitor data (#125) | Open | Per-monitor lat/lon for finer spatial resolution |
| 6B: CDC county data (#126) | Open | All ~3,000 US counties from CDC PLACES |

### What's NOT Done (Next Steps)

- **Phase 6B remaining:** EPA monitor data (#125), CDC county data (#126), frontend heatmap overlay (#129)
- **Phase 6A deferred:** Marker clustering (#120), results pagination (#121), OPO mapping (#122), patient home location (#123)
- **Phase 6C (future):** Pre-computed raster grid (#133), kriging uncertainty (#134), spatial econometric models (#135)
- **Phase 5 platform features:** API access (#24), SDKs (#25), scenario builder UI (#26), bulk analysis (#27), widget (#28)
- **Deferred (no API):** OPO boundaries (#19), SRTR outcomes (#20), donor reg fetch (#21), theme selection (Phase 7, #3)
- **Infrastructure:** CI pipeline (#29) ✅, Docker Compose (#30) ✅ — both shipped
- See `docs/roadmap.md` for full phased plan
- See `docs/ideas.md` for full SRS with architecture, governance, and regulatory details

## Issue Tracking

**GitHub Issues** is the primary tracker for actionable work items (bugs, features, limitations). ~10 open, ~105+ closed:

| Category | Status | Description |
|----------|--------|-------------|
| Phase 6A: Center Expansion | ✅ 5 closed | #115-#119 — center list, geocoding, parse script, dynamic CITIES, dropdown |
| Phase 6B: Spatial Interpolation | ✅ 3 closed / 3 open | #127, #128, #130 closed — interpolation engine, API, allocation circles. #125, #126, #129 open |
| Phase 6A deferred | 4 open | #120 (marker clustering), #121 (pagination), #122 (OPO mapping), #123 (patient home) |
| Bug/Quality Sprint (March 2026) | ✅ 30+ closed | Thread safety, error handling, data quality, code fixes — comprehensive sprint across 3 tiers |
| Phase 5 M1-M5 | ✅ 8+ closed | #36-#42, #94, #95, #96, #99 — BBN, copula, MCMC, shared frailty, cross-validation |
| M2b: COD Model Data Quality | 2 open / 6 closed | L-049–L-056 — 6 resolved, 2 remain (OPTN validation #11, OPO mapping #12) |
| Pre-publication | 1 open | #107 (face validity review with transplant faculty) |
| Phase 5+ platform features | 5 open | API access (#24), SDKs (#25), scenario builder (#26), bulk analysis (#27), widget (#28) |
| Deferred | 4 open | OPO mapping (#19), SRTR outcomes (#20), donor reg (#21), theme selection (#3) |

**Labels:** `phase:*`, `priority:*`, `limitation`, `cod-model`, `blocked`, `deferred`, `ui/ux`, `backend`, `frontend`, `data-quality`, `data-pipeline`, `milestone:m5`

**Doc files stay as reference:** `status.md` (session start), `design.md` (UI guidelines), `brand-bible.md` (colors/fonts), `limitations.md` (full issue descriptions with file paths and fix complexity).

## File Map

```
TransPlan/
  docs-site/              <- Docusaurus documentation site
    docs/                 <- 22 pages: intro, getting-started/, theory/ (4 MDX), architecture/, api-reference/, contributing/, about/, validation/ (2 MDX)
    src/css/custom.css    <- TransPlan brand theme
    src/components/       <- React components: TornadoChart, ComparisonTable, DistributionCurve, HeatmapTable (Recharts)
    static/data/          <- Generated JSON: sensitivity-results.json, srtr-comparison-results.json
    docusaurus.config.ts  <- Site config (baseUrl /docs-site/build/, blog disabled)
    sidebars.ts           <- 8-section sidebar navigation (+ Validation)
  TransPlan.app/          <- macOS .app bundle (double-click to launch, no Terminal)
    Contents/Info.plist   <- App metadata, LSUIElement=true (background app)
    Contents/MacOS/launch <- Shell script: start uvicorn, open browser
  start.command           <- Double-click to launch (macOS); auto-finds free ports
  stop.command            <- Double-click to stop a running session
  session.js              <- Local session UI (End Session button, same-origin health check)
  api-client.js           <- Backend API client (POST /simulate + /sensitivity + /equity-analysis + /what-if + GET /centers, graceful fallback)
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
    wait-time-distributions.json  <- Log-normal params from SRTR Table B10 (22 cities)
    competing-risks.json          <- Mortality/delisting from SRTR Table B7 (22 cities)
    post-transplant-outcomes.json <- Graft/patient survival from SRTR Tables C5-C20 (22 cities, Phase 4 M2)
    srtr-all-centers.json         <- All ~248 SRTR centers with lat/lon, organs, state (Phase 6A)
    wait-time-distributions-centers.json <- Center-level wait times (248 centers, Phase 6A)
    competing-risks-centers.json  <- Center-level competing risks (248 centers, Phase 6A)
    post-transplant-outcomes-centers.json <- Center-level outcomes (243 centers, Phase 6A)
    srtr-historical.json      <- Real SRTR 15-release time-series 2019–2025 (Phase 4 M3, #104 resolved)
    cause-of-death-by-region.json <- Organ recovery rates × state COD proportions (M2)
    srtr-center-mapping.json      <- SRTR center codes → 22 TransPlan cities
    srtr-raw/                     <- Downloaded SRTR Excel files (gitignored)
      historical/               <- 14 extracted SRTR archive releases (gitignored, auto-fetched)
    manual/               <- Hand-curated data (no API available)
      srtr-reports.json
      climate-scores.json
      policy-tiers.json
      socioeconomic.json
  docs/
    sensitivity-report.md       <- Sensitivity analysis report (parameter dominance by organ)
    srtr-ground-truth-comparison.md <- SRTR ground-truth comparison report (6 spot checks)
  scripts/                <- Node fetch scripts for GitHub Actions
    utils.js              <- Shared retry, write, city list
    fetch-traffic.js      <- NHTSA FARS CSV bulk download (state fatalities)
    fetch-air-quality.js  <- EPA AQS (needs API key)
    fetch-hospital-quality.js <- CMS Provider Data
    fetch-cost-of-living.js   <- BLS API (needs API key)
    fetch-health-data.js      <- CDC PLACES county-level (5 indicators)
    fetch-cod-data.js         <- CDC SODA (cause-of-death by state, donor-eligibility calibration)
    check-srtr-updates.js     <- SRTR website hash check
    validate-data.js          <- Post-fetch validation
    run-sensitivity-report.py <- Sensitivity sweep: 6 organs × 3 profiles × 10 cities → JSON + markdown report
    run-srtr-comparison.py    <- SRTR spot-check: 6 city/organ pairs → JSON + markdown report
    fetch-srtr-excel.py       <- Download SRTR PSR Excel files (6 organs)
    parse-srtr-reports.py     <- Parse Excel → wait-time-distributions.json + competing-risks.json + post-transplant-outcomes.json
  .github/workflows/
    ci.yml                <- CI: 3 parallel jobs (pytest, Jest, data validation) on push/PR to main
    fetch-data.yml        <- Weekly data fetch (Mon 6am UTC)
    check-srtr-updates.yml <- Bimonthly SRTR check
    fetch-srtr-historical.yml <- Auto-fetch SRTR historical archives after Jan/Jul releases
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
      simulate.py         <- POST /simulate (Monte Carlo or Bayesian inference, dispatch via ?inference_mode=)
      sensitivity.py      <- POST /sensitivity (tornado chart parameter analysis)
      equity.py           <- POST /equity-analysis (demographic equity analysis)
      what_if.py          <- POST /what-if (what-if scenario analysis with multipliers)
      centers.py          <- GET /centers (all 248 centers or 22 focus cities, Phase 6A)
      spatial.py          <- GET /spatial-layers, /interpolated-value, /interpolated-profile, /allocation-circles, /distance-score (Phase 6B)
    services/
      data_loader.py      <- Loads data/*.json at startup (20 files including Phase 6A center data)
      distributions.py    <- Log-normal wait time distributions (6 organs)
      monte_carlo.py      <- Monte Carlo simulation engine (22 cities × 1000 iter, dynamic CITIES loading)
      spatial_interpolation.py <- RBF/IDW interpolation engine, 24 layers, SpatialSurface cache (Phase 6B)
      allocation_geography.py  <- UNOS 250nm/500nm allocation circles, distance scoring (Phase 6B)
      competing_risks.py  <- Competing risks: mortality/delisting rates (6 organs)
      sensitivity.py      <- Sensitivity analysis: parameter impact on p_transplant_24mo
      equity.py           <- Demographic equity analysis (48 profiles × 22 cities, Gini coefficient)
      what_if.py          <- What-if scenario analysis (Monte Carlo with donor/wait multipliers)
      brier_score.py      <- Brier score calibration: Monte Carlo vs analytical validation
      outcomes.py         <- Post-transplant outcomes: graft/patient survival, compound success (Phase 4 M2)
      trends.py           <- Historical trends: linear regression, direction classification (Phase 4 M3)
      policy_scenarios.py <- Policy scenario engine: 4 UNOS scenarios, per-city multipliers (Phase 4 M4)
      bias_audit.py       <- Demographic bias audit: Cohen's d, Gini, disparity metrics (Phase 4 M5)
      bbn_parameterizer.py <- BBN CPT builder: 7 CPTs from existing JSON data, no duplication (Phase 5 M1)
      bayesian_network.py  <- BBN inference engine: 12-node DAG, pgmpy VariableElimination (Phase 5 M1)
      copula.py            <- Clayton copula: correlated mortality/delisting draws, conditional method (Phase 5 M2)
      mcmc_survival.py     <- MCMC hierarchical model: PyMC specification, fitting, trace I/O (Phase 5 M3)
      mcmc_inference.py    <- MCMC query-time inference: posterior sampling, forward simulation (Phase 5 M3)
    routers/
      ...
      trends.py           <- GET /trends/{city}/{organ}, GET /trends/{organ} (Phase 4 M3)
    tests/                <- pytest suite (594 tests)
      ...
      test_policy_scenarios.py <- 24 tests: scenario registry, filtering, per-city multipliers
      test_bias_audit.py       <- 19 tests: Cohen's d, Gini, dimension disparity, full audit
      test_bbn_parameterizer.py <- 30 tests: CPT shapes, normalization, semantic checks (Phase 5 M1)
      test_bayesian_network.py  <- 32 tests: DAG structure, inference validity, organ-specific (Phase 5 M1)
      test_bbn_cross_validation.py <- 10 tests: rank correlation, directional consistency, speed (Phase 5 M1)
      test_copula.py             <- 22 tests: marginal uniformity, Kendall's τ, edge cases, integration (Phase 5 M2)
      test_spatial_interpolation.py <- 19 tests: RBF/IDW surfaces, layer extraction, edge cases (Phase 6B)
      test_allocation_geography.py  <- 13 tests: centers within radius, allocation circles, distance score (Phase 6B)
      test_mcmc_survival.py      <- 38 tests: data loading, model building, posterior sampling, sanity (Phase 5 M3)
      test_mcmc_inference.py     <- 15 tests: result structure, clinical params, copula compat, error handling (Phase 5 M3)
  docs/
    status.md             <- THIS FILE (read every session)
    ideas.md              <- Full SRS: requirements, architecture, FDA pathway
    design.md             <- Read when touching UI/UX/CSS
    adr-log.md            <- Grep-searchable decision log
    roadmap.md            <- Phased development plan (5 phases)
    limitations.md        <- Issue tracker (65 items, L-001 through L-065)
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

**65 tracked issues** in `docs/limitations.md`. Read when auditing data quality or planning future work.

| Status | Count | Details |
|--------|-------|---------|
| FIXED | 48 | L-001–L-048 (all critical/high/medium from original audit), L-051–L-056 (COD model), L-058–L-059, L-062 |
| OPEN | 7 | L-049 (OPTN cross-validation), L-050 (OPO boundaries), L-060 (patient-level MCMC), L-061 (informative priors), L-063–L-065 (Phase 6 spatial) |
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
