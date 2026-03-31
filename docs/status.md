# TransPlan - Project Status

> **Read this file at the start of every session.**

## What TransPlan Is

A patient-facing clinical decision support tool that helps transplant patients identify the best US transplant centers for their specific organ needs. Deployed at transplant.today with a Python backend on Vercel. Covers all 248 SRTR centers with Monte Carlo simulation, Bayesian inference, competing risks modeling, equity analysis, and policy impact analysis. See `docs/ideas.md` for the full SRS and `docs/roadmap.md` for phased development plan.

## Current State: Rebuild Phase 3 (Page Merges) — Next Priority

**Full rebuild in progress** — Phases 0-2 complete, Phases 3-7 remaining. Plan: `.claude/plans/vectorized-honking-curry.md`

### Rebuild Progress

| Phase | Status | Commits | What Changed |
|-------|--------|---------|--------------|
| Phase 0: Seed & Reproducibility | ✅ Done | `a75dd72` | `seed` param on all simulation endpoints, `seed_used` in responses, `RunArtifact` export schema, frontend seed display + export |
| Phase 1: Nav Restructure | ✅ Done | `6749b10` | "For Patients" / "For Professionals" mega-dropdowns in `site-chrome.js`, old URLs redirect |
| Phase 2: Simulator Rebuild | ✅ Done | `6f99f07` `792e1da` `840e415` | Modular architecture: `simulator/{index,map,tier-panel,form-helpers,results,results-table}.js` + `shared/{api-client,export-handler,data-loader,continue-buttons,geo-utils,weight-config}.js`. `simulator.html` rewritten (two-panel sidebar+results). Verified: 233 centers scored, simulation runs, map renders, URL pre-fill works, continue buttons link to 4 tools |
| **Phase 3: Page Merges** | 🔲 **NEXT** | — | Merge find-centers + centers + wait-estimator → `centers.html` (tabs). Merge data.html + spatial.html → `explorer.html` (tabs) |
| Phase 4: Model Validation | 🔲 Pending | — | New `validation.html` with 7 sections, new backend router + services |
| Phase 5: Inter-tool Linking | 🔲 Pending | — | `shared/continue-buttons.js` already built in Phase 2; wire to all pages |
| Phase 6: Tier System | 🔲 Pending | — | Hide unavailable features (not greyed out) |
| Phase 7: Cleanup & Polish | 🔲 Pending | — | Delete `script.js` (4889 lines), old HTML pages, final QA |

### Bugs Fixed During Rebuild
- `scoring.py` NameError: `_donor_availability()` missing `lat`/`lon` params (caused 500 on POST /score)
- `index.js` DOMContentLoaded race: scripts at bottom of `<body>` run after event fires; fixed with `readyState` check
- `tier-panel.js` ID mismatches between old/new element IDs (now handles both)
- `form-helpers.js` inference mode select ID (`sim-inference-mode` → `inferenceMode`)

### Deferred Issues
- **#208 comprehensive audit** (33 issues) — deferred until rebuild complete
- **#206** BBN 248-center Region node, **#207** MCMC 248-center hierarchy
- **HIGH:** Equity analysis infeasible at scale (11.9M sims), BBN magic numbers uncited, CORS too permissive
- **CRITICAL:** Wait time sorting bug (script.js:2910) — will be fixed when script.js is deleted in Phase 7

**Phase 3 done:** Python backend deployed to Vercel as serverless function (api/index.py). Static files served by CDN, API paths routed via vercel.json rewrites. CORS configured for transplant.today and *.vercel.app. MCMC gracefully disabled on Vercel (missing pymc). **Phase 4 done:** Simulation engine expanded from 22 cities to all 248 SRTR centers. Center-level data (wait-time factors, competing risks, outcomes) wired into MC, BBN, and MCMC engines. All simulation parameters (iterations, copula_theta, elasticity) exposed as adjustable API query params. BBN/MCMC map 248 centers to 22 regions as interim; full expansion tracked in #206/#207. Frontend home-center dropdown dynamically loads all centers from API.

**Phase 7 (March 2026):** UI overhaul — removed all 6 themes (themes.css, theme-switcher.js deleted), replaced with single polished light-mode design. System fonts (no Google Fonts dependency), 15px base font, soft radii, restored shadows. Simulator restructured: sidebar layout with form on left, results/map on right, methodology collapsed below results. Landing page redesigned: hero + feature card grid + 4-step flow + data trust badges + CTA. Nav simplified to Home | Simulator | Docs + dark mode toggle. Mobile hamburger menu added. Center expansion: `POST /score` endpoint scores all 248 SRTR centers using center-level data + spatial RBF interpolation. Frontend calls backend scoring API with 22-city local fallback. 19 new pytest tests. 224 Jest + 613+ pytest.

**Phase 4 complete (March 2026):** All 5 milestones done (ADR-021). M1 (Configurable Weights), M2 (Post-Transplant Outcomes), M3 (Historical Trends), M4 (Policy Scenario Engine), M5 (Validation & Reproducibility Pack). 112 Jest, 448 pytest.

**Phase 5 M1 complete (March 2026):** Bayesian Belief Network inference engine (ADR-024). 12-node DAG with pgmpy VariableElimination for exact inference (~30ms cached vs ~2s MC). Toggle via `POST /simulate?inference_mode=bayesian`. All 7 CPTs derived from existing JSON data (no duplication). Cross-validated: Spearman rank > 0.5 for city rankings, directional consistency on blood type/organ/urgency effects. Frontend inference method dropdown + method badge. 72 new BBN-specific pytest tests. Issues #36-#42 closed.

**Phase 5 M2 complete (March 2026):** Clayton copula for correlated competing risks (ADR-025). Mortality and delisting times now optionally drawn with positive lower-tail dependence via `use_copula: true` on PatientProfile. Default θ=1.0 (Kendall's τ ≈ 0.33). Conditional sampling method preserves marginal exponential distributions. All 3 simulation paths (monte_carlo, what_if, sensitivity) support copula. 22 copula unit tests + 4 integration tests. Issue #94.

**Phase 5 M3 complete (March 2026):** PyMC MCMC hierarchical survival model (ADR-026). Third inference engine (`inference_mode=mcmc`) with honest Bayesian uncertainty quantification. Three-level hierarchy: national hyperpriors → 22 city random effects → patient covariates (blood type, urgency). 92 free parameters per organ, 6 independent models. Offline NUTS fitting via `scripts/fit-mcmc-model.py`, cached traces in ArviZ NetCDF (~10-50 MB per organ). Query-time: 50 posterior draws × forward simulation (~200-500ms). Frontend dropdown + orange MCMC badge. Issue #95.

**Phase 5 M4 complete (March 2026):** Shared frailty via LKJ-Cholesky correlated city offsets (ADR-027). MCMC model now learns mortality ↔ delisting correlation from data via bivariate MvNormal with LKJ prior (η=2), replacing the fixed external copula for MCMC mode. Bayesian HDI replaces bootstrap CIs — posterior-predictive credible intervals computed from per-draw p24 values. 11 new tests. 538 pytest + 112 Jest = 650 total. Issues #96, #99.

**Phase 5 M5 near-complete (March 2026):** Cross-engine validation, model quality checks, and comprehensive bug/quality sprint. (1) Cross-engine validation service (`services/cross_validation.py`): runs MC, BBN, and MCMC on the same patient and computes Spearman rank correlation, mean/max absolute probability differences, top-5 city overlap. (2) Per-organ copula θ (L-059 fix): organ-specific Clayton copula parameters (kidney=0.8 through heart=1.8) replace the single fixed θ=1.0 across all 4 simulation paths. (3) Strict convergence gate (L-062 fix): `--strict` flag on `fit-mcmc-model.py` requires R-hat < 1.01 and ESS > 400 before saving traces. (4) Posterior predictive checks (`services/posterior_checks.py`): compares MCMC posterior predictions against observed SRTR statistics (national medians, city factors, blood type multipliers, mortality/delisting rates, urgency monotonicity). 24 new tests (14 cross-validation + 10 posterior checks). (5) Bug/quality sprint: 15 issues closed across 3 tiers — thread safety (#55), exception handling (#56), centerReputation differentiation (#44), XSS audit (#57), nullish coalescing (#67), LAS float parsing (#68), dead code removal (#71), concurrent submission guard (#66), frozen dist introspection (#61), honest BBN uncertainty band (#54), per-organ BBN terciles (#59), BLS cost-of-living verified (#101), EPA air quality verified (#100), CDC PLACES expanded to 5 county-level indicators (#102), FARS CSV bulk download (#103). (6) #104: Real SRTR historical data (14 biannual releases 2019–2025) with automated GitHub Actions refresh — resolved by user.

**Phase 6A complete (March 2026):** Center expansion from 22 cities to ~250 SRTR centers. (1) Extracted all center codes, names, coordinates, and organ programs from SRTR PSR Excel files → `data/srtr-all-centers.json` (248 centers). (2) Three-tier geocoding: Nominatim automated (200+), city_mapping fallback, manual coordinates. (3) Center-level data files: `wait-time-distributions-centers.json` (248), `competing-risks-centers.json` (248), `post-transplant-outcomes-centers.json` (243). (4) Dynamic CITIES loading: all backend services (`monte_carlo`, `equity`, `sensitivity`, `what_if`, `mcmc_inference`) now use `_get_cities()` with fallback, replacing hardcoded lists. (5) `GET /centers` endpoint with organ and focus_only filters. (6) Frontend dropdown tries API first, falls back to hardcoded cityStateMap. Issues #115-#119 closed.

**Phase 6B complete (March 2026):** Spatial interpolation and UNOS allocation geography. (1) RBF/IDW interpolation engine (`services/spatial_interpolation.py`): continuous geographic surfaces from center-level data (24 layers: air quality, cost of living, 5 health metrics, per-organ wait_time_factor/mortality_factor/graft_survival). (2) Spatial API endpoints: `GET /spatial-layers`, `GET /interpolated-value`, `GET /interpolated-profile`, `GET /allocation-circles`, `GET /distance-score`, `GET /spatial-grid`, `GET /location-delta`. (3) UNOS allocation circle modeling (`services/allocation_geography.py`): 250nm/500nm radius analysis, competition scoring, composite distance score (proximity 40% + competition 35% + donor pool 25%). (4) Dense spatial data: `fetch-health-data-counties.js` (2,956 US counties from CDC PLACES) and `fetch-air-quality-monitors.js` (per-monitor EPA AQS data) — interpolation engine auto-prefers dense sources over city-level aggregates. (5) Frontend: Leaflet heatmap overlay with layer selector, marker clustering (L.markerClusterGroup), results pagination with state filter, patient home location input with Nominatim geocoding and haversine distance display, patient-relative delta scoring (`GET /location-delta`). 32 new pytest tests (19 spatial + 13 allocation). Issues #125, #126, #127, #128, #129, #130, #131 closed. Phase 6B done.

**M4 (Policy Scenario Engine):** 4 predefined UNOS policy scenarios with literature-backed parameters and per-city adjustments: (1) 2021 Kidney 250nm Circles — per-center-size donor/wait adjustments, (2) Continuous Distribution — stronger geography de-emphasis, (3) Increased DCD Utilization — +15% organ supply, (4) Broader HCV+ Acceptance — +6% donor pool for kidney/liver. Frontend policy scenario selector in probability tab. `POST /policy-scenario` endpoint, `GET /policy-scenarios` listing. 24 new pytest tests.

**Data Quality Sprint (March 2026):** 6 of 8 COD model issues resolved:
- L-055: Expanded state COD proportions from 17 to all 50 states + DC (CDC SODA API, donor-eligibility calibration)
- L-051: Automated `fetch-cod-data.js` script added to CI pipeline
- L-053: COD multiplier now stochastic (Beta-distributed recovery rates, kappa=50, ~3.5% CV)
- L-056: Sublinear supply-wait elasticity (0.65 exponent) replaces linear assumption
- L-054: Intestine recovery rates replaced pancreas proxy with OTPD-derived COD-specific rates
- L-052: Anoxia-NOS added as 5th COD category (9.2% of donors, estimated recovery rates, drowning-based state shares)
- L-049 mitigated (validated vs OPTN 2023), L-050 partially addressed (55 OPOs cataloged, 22 cities mapped)

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
| UI/UX redesign | ✅ Done | Phase 7: sidebar layout, system fonts, 15px base, soft radii, restored shadows. Landing page: hero + feature cards + steps + CTA |
| Theme system | ✅ Removed | All 6 themes deleted (Phase 7). Single polished light-mode design. Dark mode toggle preserved |
| Multi-page split | ✅ Done | Landing page (index.html) + simulator (simulator.html), sidebar layout on simulator |
| Center expansion scoring | ✅ Done | `POST /score` endpoint: 8-category scoring for 248 SRTR centers via backend API, 22-city local fallback |
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
| L-049: Cross-validate OPTN rates (#11) | ✅ Mitigated | Validated against OPTN 2023; kidney/liver OK, heart/lung conservative (post-2019 tech) |
| L-050: OPO boundary mapping (#12) | Partial | 55 OPOs cataloged, all 248 centers mapped to OPOs via geographic proximity |
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
| 6A: Add geographic coordinates (#116) | ✅ Done | All 248 hospital-specific coords verified (#136). No city-center approximations remain. |
| 6A: Update parse script (#117) | ✅ Done | Center-level data files for wait times, competing risks, outcomes |
| 6A: Replace hardcoded CITIES (#118) | ✅ Done | Dynamic `_get_cities()` in all backend services |
| 6A: Dynamic center dropdown (#119) | ✅ Done | API-first with hardcoded fallback |
| 6A: Marker clustering (#120) | ✅ Done | L.markerClusterGroup for 248+ center markers |
| 6A: Results pagination (#121) | ✅ Done | Top-10/20/50/all, state filter, prev/next |
| 6A: OPO mapping (#122) | ✅ Done | 60 OPOs, 3,225 counties, 248 centers — authoritative HRSA county-to-OPO mapping. Replaces proximity heuristic. #138 resolved |
| 6A: Patient home location (#123) | ✅ Done | Nominatim geocoding, haversine distance on cards |
| 6B: EPA monitor data (#125) | ✅ Done | `fetch-air-quality-monitors.js`, ~4000 per-monitor points |
| 6B: CDC county data (#126) | ✅ Done | `fetch-health-data-counties.js`, 3,144 counties (multi-release fallback) |
| 6B: Interpolation service (#127) | ✅ Done | RBF/IDW engine, 24 layers, SpatialSurface cache, 19 pytest |
| 6B: Interpolation API (#128) | ✅ Done | 6 endpoints on spatial router |
| 6B: Heatmap overlay (#129) | ✅ Done | Leaflet heatmap via /spatial-grid, layer selector |
| 6B: Allocation circles (#130) | ✅ Done | 250nm/500nm UNOS circles, competition score, distance score, 13 pytest |
| 6B: Patient-relative scoring (#131) | ✅ Done | GET /location-delta, per-layer delta comparison |

### Phase 7 Patient Resources & Tools (March 2026)

| Feature | Status | Issue |
|---------|--------|-------|
| Center detail page overhaul | ✅ Done | #161 — collapsible sections, patient survival, hazard ratios, waitlist mortality, contact+map merged card |
| Landing page interactive map | ✅ Done | #154 — Leaflet + MarkerCluster showing all 248 centers |
| Zip code nearest-center search | ✅ Done | #143 — Nominatim geocoding + haversine, "X mi away" badges |
| Find My Centers wizard | ✅ Done | #170 — location + organ + blood type → composite-scored ranked list |
| Wait Time Estimator | ✅ Done | #171 — organ + blood type → log-normal IQR estimate |
| Center Comparison tool | ✅ Done | #165 — side-by-side up to 3 centers, URL-shareable |
| FAQ page | ✅ Done | #169 — 10 collapsible Q&A with native details/summary |
| Transplant Journey Checklist | ✅ Done | #164 — 34 items, 5 phases, localStorage persistence, progress bar |
| Organ-Specific Guides | ✅ Done | #166 — kidney, liver, heart, lung, pancreas with allocation scoring |
| Post-Transplant Medication Guide | ✅ Done | #167 — added to education.html (immunosuppressants, adherence, rejection) |
| Caregiver & Family Resources | ✅ Done | #168 — added to support.html (travel, work, burnout) |
| Insurance & Coverage Navigator | ✅ Done | #163 — added to support.html (Medicare, Medicaid, private, Rx costs) |
| Advocacy & Give Back page | ✅ Done | #172-178 — 6 articles: organ donor, bone marrow, blood, living donor, volunteer, fundraise |
| Scoring data gaps fixed | ✅ Done | #140 — policy/socioeconomic extended to all 50 states, climate+traffic use spatial interpolation |
| Dark mode polish | ✅ Done | #139 — verified all landing page components have proper contrast |
| Nav standardization | ✅ Done | 10-item Resources dropdown consistent across all 13 pages |
| Cross-page links | ✅ Done | Education, support, FAQ, organ guides, tools all interlinked |
| Donation banner | ✅ Done | Dismissible bottom banner (GitHub Sponsors, Buy Me a Coffee, Ko-fi) on all pages |
| SEO files | ✅ Done | robots.txt, sitemap.xml, llms.txt, llms-full.txt |

### What's NOT Done (Next Steps)

- **Phase 6C (future):** Pre-computed raster grid (#133), kriging uncertainty (#134), spatial econometric models (#135)
- **Validation:** Face validity review with transplant faculty (#107), cross-iteration model comparison (#137)
- **Platform features:** SDKs (#25), scenario builder UI (#26), bulk analysis (#27), widget (#28)
- **Data:** Physician/staff directory (#162 — requires per-hospital scraping)
- **Deferred:** SRTR outcomes API (#20), geographic accessibility model (#142), coverage gap analysis (#113)
- See `docs/roadmap.md` for full phased plan
- See `docs/ideas.md` for full SRS with architecture, governance, and regulatory details

## Issue Tracking

**GitHub Issues** is the primary tracker for actionable work items (bugs, features, limitations). ~14 open, ~165+ closed:

| Category | Status | Description |
|----------|--------|-------------|
| Phase 7: Patient Resources | ✅ 19 closed | #139, #143, #154, #161, #163-178 — tools (find-centers, wait-estimator, compare), content pages (FAQ, checklist, organ guides, advocacy), scoring data gaps, nav/SEO |
| Phase 6A: Center Expansion | ✅ 8 closed / 1 deferred | #115-#121, #123 closed. #122 (OPO mapping) deferred |
| Phase 6B: Spatial Interpolation | ✅ 7 closed | #125-#131 — all items complete |
| Bug/Quality Sprint (March 2026) | ✅ 30+ closed | Thread safety, error handling, data quality, code fixes |
| Phase 5 M1-M5 | ✅ 8+ closed | #36-#42, #94, #95, #96, #99 — BBN, copula, MCMC, shared frailty, cross-validation |
| M2b: COD Model Data Quality | 0 open / 8 closed | L-049–L-056 — all addressed |
| Pre-publication | 1 open | #107 (face validity review with transplant faculty) |
| Phase 5+ platform features | 4 open / 1 closed | API access (#24 ✅), SDKs (#25), scenario builder (#26), bulk analysis (#27), widget (#28) |
| Research/Deferred | 7 open | SRTR outcomes (#20), spatial models (#132-135), model validation (#137), accessibility model (#142), physician directory (#162) |

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
  simulator/              <- NEW (Phase 2 rebuild) — modular simulator
    index.js              <- Entry point: form → score/simulate → table/map wiring, URL pre-fill
    map.js                <- Leaflet map with center markers, highlighting, popups
    tier-panel.js         <- Fetches /tier, applies caps, shows badge (WEB/LOCAL)
    form-helpers.js       <- Home center dropdown, slider wiring, advanced params collection
    results.js            <- Orchestrator: runScoring(), runSimulation(), geocodeHome(), state management
    results-table.js      <- Renders sortable table with rank, score bars, simulation probability columns
  shared/                 <- NEW (Phase 2 rebuild) — cross-page utilities
    api-client.js         <- Backend API client (POST /simulate + /score + /sensitivity + /equity-analysis + /what-if + GET /centers)
    export-handler.js     <- PDF report, CSV, JSON, RunArtifact export with seed
    data-loader.js        <- Runtime JSON loader with fallbacks
    continue-buttons.js   <- Inter-tool "Continue to..." buttons encoding patient profile as URL params
    geo-utils.js          <- Haversine distance, geocoding helpers
  components/
    site-chrome.js        <- Shared nav/footer (For Patients / For Professionals dropdowns)
    weight-config.js      <- Scoring weight sliders, presets, normalization, re-score trigger
  index.html              <- Landing page (hero, feature cards, 248-center map, steps flow, data trust badges, CTA)
  simulator.html          <- Simulation tool — REBUILT: two-panel sidebar form + results/map/table
  find-centers.html       <- Find My Centers wizard (→ merge into centers.html in Phase 3)
  wait-estimator.html     <- Wait Time Estimator (→ merge into centers.html in Phase 3)
  compare.html            <- Side-by-side center comparison (up to 3, URL-shareable)
  organ-guides.html       <- Organ-specific transplant guides (kidney, liver, heart, lung, pancreas)
  faq.html                <- Frequently asked questions (10 collapsible Q&A)
  checklist.html          <- Transplant journey checklist (34 items, 5 phases, localStorage)
  advocacy.html           <- Advocacy & Give Back (6 articles: donor, marrow, blood, living, volunteer, fundraise)
  algorithm.js            <- Frontend scoring engine (8 categories, 22 cities — fallback when backend unavailable)
  script.js               <- LEGACY monolith (4889 lines) — TO BE DELETED in Phase 7
  styles.css              <- All CSS + Phase 2 additions (sim-action-row, btn-secondary, sim-error, continue-buttons, dark mode overrides)
  (themes.css deleted)    <- 6 themes removed in Phase 7 UI overhaul
  (theme-switcher.js deleted) <- Theme picker removed in Phase 7
  package.json            <- Node deps (xml2js, jest)
  README.md               <- User-facing docs
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
    health-demographics-counties.json <- 2,956 US counties with health indicators (Phase 6B)
    air-quality-monitors.json     <- Per-monitor EPA AQS data with lat/lon (Phase 6B)
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
    fetch-health-data-counties.js <- CDC PLACES county-level health data (2,956 counties, Phase 6B)
    fetch-air-quality-monitors.js <- EPA AQS per-monitor air quality with lat/lon (Phase 6B)
    build-opo-mapping.py       <- Build OPO catalog (55 OPOs, 22 focus city mappings)
    fetch-opo-service-areas.py <- Map all 248 centers to OPOs (geographic proximity + manual overrides)
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
      schemas.py          <- Pydantic: PatientProfile, SimulationResult, CenterScore, ScoringResult, etc.
    routers/
      health.py           <- GET /health (data freshness)
      shutdown.py         <- POST /shutdown (graceful local session end)
      simulate.py         <- POST /simulate (Monte Carlo or Bayesian inference, dispatch via ?inference_mode=)
      score.py            <- POST /score (8-category comprehensive scoring for 248 centers, Phase 7)
      sensitivity.py      <- POST /sensitivity (tornado chart parameter analysis)
      equity.py           <- POST /equity-analysis (demographic equity analysis)
      what_if.py          <- POST /what-if (what-if scenario analysis with multipliers)
      centers.py          <- GET /centers (all 248 centers or 22 focus cities, Phase 6A)
      spatial.py          <- GET /spatial-layers, /interpolated-value, /interpolated-profile, /allocation-circles, /distance-score, /spatial-grid, /location-delta (Phase 6B)
    services/
      data_loader.py      <- Loads data/*.json at startup (22 files including Phase 6A center data + Phase 6B dense spatial data)
      scoring.py          <- 8-category comprehensive scoring for 248 centers using center-level + spatial data (Phase 7)
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
| FIXED | 49 | L-001–L-048 (all critical/high/medium from original audit), L-051–L-056 (COD model), L-058–L-059, L-062, L-012 (county health) |
| OPEN | 4 | L-060 (patient-level MCMC), L-061 (informative priors), L-064–L-065 (Phase 6 spatial) |
| PARTIALLY FIXED | 3 | L-009 (OPO — now HRSA-authoritative, #138 resolved), L-050 (OPO boundaries — center-to-OPO mapped), L-063 (sparse spatial data) |
| MITIGATED | 2 | L-049 (OPTN cross-validation — kidney/liver OK, heart/lung conservative), L-057 (pancreas graft survival) |
| DEFERRED | 1 | L-017 (SRTR outcomes) |
| PARTIALLY RESOLVED | 1 | L-033 (donor reg — `stateRegistrationRates` from DLA report; `livingDonorProgramStrength`/`populationFactors` manual by design) |
| WONT FIX | 1 | L-039 (false positive) |

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
