# TransPlan - Roadmap

> **Grep-searchable.** Search for specific features, phases, or requirements to check their status.
> For the full SRS with governance, regulatory, and architectural details, see `docs/ideas.md`.

---

## Completed

### v0.1 - Original Codebase
- [x] 8-category scoring algorithm with 40+ factors
- [x] 22 cities across 6 organ types
- [x] Interactive Leaflet map with 10 overlay layers
- [x] Health profile form (organ, blood type, age, sex, urgency, weight, height, insurance)
- [x] Methodology section explaining the algorithm
- [x] Responsive design

### v0.2 - Bug Fixes + Data Pipeline + Charts
- [x] Fix multiplicative scoring bug in `calculateMedicalCompatibilityScore`
- [x] Fix `/100` normalization bug in `calculateDonorAvailabilityScore`
- [x] Remove non-deterministic random jitter from `calculateComprehensiveScore`
- [x] Extract hardcoded data into `data/` JSON files
- [x] Create `data-loader.js` with fallback defaults
- [x] Refactor algorithm.js to use `window.TransPlanData`
- [x] Refactor script.js to dynamically score all 22 cities
- [x] Add Chart.js: radar (per city), bar (comparison), donut (weights)
- [x] Data freshness banner
- [x] Create 6 fetch scripts (NHTSA, EPA, CMS, BLS, CDC, SRTR)
- [x] Create validation script
- [x] GitHub Actions: weekly fetch + bimonthly SRTR check
- [x] Documentation system (status, design, ADR, roadmap, brand bible)
- [x] README with architecture and usage docs

### v0.2.1 - Browser Testing & Derived Metrics
- [x] Browser tests: form submission, chart rendering, freshness banner, radar charts (22 canvases)
- [x] Fix N/A metrics: derive wait times, match rates, donor rates from algorithm data
- [x] Fix "1 months" pluralization bug
- [x] API keys configured as `EPA_BLS_KEYS` secret
- [x] Add `.gitignore` for node_modules, .DS_Store

### v0.3 - Limitation Audit & Quality Sweep (Batches 1-10)
- [x] 48 limitations tracked, 36 fixed, 3 deferred, 2 won't fix
- [x] Organ-specific clinical inputs: cPRA (kidney), MELD (liver), LAS (lung)
- [x] Ethical fixes: disclaimer expanded, "success probability" reframed as "suitability score"
- [x] Data pipeline safety: mergeDataFile prevents fetch scripts from destroying seed data
- [x] CI restructured: single sequential job eliminates push race condition
- [x] Socioeconomic scores rewritten to transplant-support rubric
- [x] Accessibility: ARIA labels, mobile-responsive map overlays
- [x] Real SRTR transplant volumes replace fabricated estimates
- [x] Unit test suite: 90 tests (Jest) covering algorithm + utilities
- [x] Add `data/metadata.json` to `.gitignore` (prevent cross-machine conflicts)

---

## Phase 1: MVP Deployment (current)

> **Goal:** Ship the static site MVP. Close out remaining housekeeping.

### Deployment
- [x] Local launcher: `start.command` / `stop.command` with dynamic port discovery (ADR-014)
- [x] Session management: `.transplan-session.json`, `session.js`, `POST /shutdown`
- [ ] Configure GitHub Pages deployment (Settings > Pages > Source: main)
- [ ] Verify site loads correctly on GitHub Pages (CDN paths, data loading)
- [ ] Set up custom domain (transplan.org) if available

### Data Pipeline Health
- [x] Run fetch scripts against live APIs (all 7 scripts working as of March 2026)
- [x] GitHub Actions weekly fetch operational (cron + workflow_dispatch)
- [x] Fix FARS endpoint (L-045) — rewritten to use CSV bulk download from static.nhtsa.gov
- [x] Fix CMS endpoint (L-046) — multi-strategy query (SQL/filter/legacy)
- [x] Add CDN fallback or error messaging (L-047)

### Open Limitations (L-045 through L-048) — ALL FIXED
- [x] L-045: NHTSA FARS — rewritten to CSV bulk download (#103)
- [x] L-046: CMS Provider Data — multi-strategy query fix
- [x] L-047: CDN fallback for Leaflet/Chart.js — onerror handlers + warning banners
- [x] L-048: COL normalization — dynamic min/max from loaded data

---

## Phase 2: Probabilistic Engine (Months 7-12 per SRS)

> **Goal:** Transform from deterministic scoring dashboard into probabilistic forecasting engine.
> **Key deliverable:** "P(transplant within X months given your profile)" — the single feature that makes TransPlan a forecasting tool.
> **Decision made:** Python FastAPI backend with NumPy/SciPy/Lifelines. Frontend stays vanilla JS, calls backend API.

### M1: Backend Scaffold ✅
- [x] FastAPI project structure (`backend/`)
- [x] Pydantic v2 schemas (PatientProfile, CityProbability, SimulationResult)
- [x] Data loader: loads all 10 JSON data files at startup
- [x] GET /health endpoint with data freshness metadata
- [x] POST /simulate stub (501 until M3)
- [x] Service stubs for distributions, monte_carlo, competing_risks
- [x] 22 pytest tests passing (data loader + schema validation)

### M2: Wait Time Distributions ✅
- [x] Create `data/wait-time-distributions.json` with literature-derived log-normal parameters
- [x] Implement `services/distributions.py`: log-normal models per organ/blood type/city
- [x] Move `cityWaitTimeFactors` from `algorithm.js` hardcoding to data file
- [x] Unit tests: known inputs → expected distribution parameters (22 tests)
- [x] Sanity checks: kidney O+ Cleveland ~55mo median; AB+ significantly shorter

### FR-5: Monte Carlo Wait-Time Simulator (M3) ✅
- [x] Build Monte Carlo simulation engine (1,000 iterations per scenario)
- [x] Implement POST /simulate endpoint (returns ranked cities with probabilities)
- [x] Probability output: P(transplant <= X months) at 6/12/24/36mo with 95% CI (bootstrap)
- [x] Performance: ~80ms for 22 cities × 1000 iterations (60x under 5s target)
- [x] Stability test: two runs with 2000 iterations agree within 15% relative / 0.03 absolute

### FR-6: Competing Risks Model (M4) ✅
- [x] Model: P(transplant) vs. P(mortality) vs. P(delisting) vs. P(still waiting)
- [x] Create `data/competing-risks.json` with national + city-adjusted rates (OPTN/SRTR 2023 ADR)
- [x] Integrate competing events into Monte Carlo (three independent exponential draws)
- [x] Verification: outcome probabilities sum to 1.0 at all time horizons (17 tests)

### M5: SRTR Data Pipeline ✅
- [x] Download SRTR PSR National Center-Level Excel files (6 organs) — `fetch-srtr-excel.py`
- [x] Create SRTR center-to-city mapping (22 cities, primary + alternates) — `srtr-center-mapping.json`
- [x] Parse Table B10: center-level wait time percentiles (P5/P10/P25/P50/P75) → log-normal fit
- [x] Parse Table B7: center-level waitlist outcomes (mortality, delisting) → annual rates
- [x] Handle censored data (">72" months) with multi-strategy sigma estimation
- [x] Output: updated `wait-time-distributions.json` + `competing-risks.json` with empirical SRTR data
- [x] 34 new tests (data validation, log-normal fitting, sanity checks) — 120 total pytest passing

### M6: Frontend Integration ✅
- [x] Single-process architecture: FastAPI serves API + static files on one port (ADR-015)
- [x] `api-client.js`: form normalization (camelCase→snake_case), POST /simulate, 15s timeout, graceful null return
- [x] `probability-charts.js`: CDF curves with 95% CI shading + competing risks stacked bar (Chart.js)
- [x] Dual-mode results: tab toggle between Location Scores and Simulation Probabilities
- [x] Probability city cards: P(transplant) at 6/12/24/36mo, median wait, CI, competing risks bar
- [x] Loading spinner during API call
- [x] Graceful degradation: if backend unreachable, Phase 1 scores shown, probability tab disabled
- [x] `TransPlan.app` macOS bundle: one-click launch with no Terminal window (LSUIElement)
- [x] `/shutdown` endpoint cleans up PID file before SIGTERM

### M7: Validation & Sensitivity ✅
- [x] Sensitivity analysis: POST /sensitivity endpoint, tornado chart UI
- [x] Tornado charts showing which clinical parameters most influence transplant probability
- [x] Brier score retrospective calibration (Monte Carlo vs analytical, BS<0.001 all 6 organs)
- [x] 22 sensitivity tests + 19 Brier score tests (161 total pytest)
- [x] Documentation updates (status.md, roadmap.md)

### FR-7: Probability Outputs & Visualization (Partial)
- [x] CDF curves with confidence intervals (M6)
- [ ] Ranked output: boost vs. current location
- [x] Visual comparison panels (side-by-side probability curves) — M3 comparison table
- [x] Exportable chart images — Phase 3 M5

### FR-4: Configurable Weights
- [ ] Research mode: allow users to adjust category weights
- [ ] Patient mode: locked weights (clinically validated defaults)
- [ ] Audit trail for weight changes

---

## Phase 3: Relocation, Equity & Usability (Months 13-24 per SRS)

> **Goal:** Full relocation modeling, equity analysis, and usability studies for clinical validation.

### M1: Home Center Relocation Comparison (FR-8 core) ✅
- [x] "Simulation Settings" fieldset with Home Center dropdown
- [x] Comparison badges on Phase 1 score cards (+/- pts vs. home)
- [x] Comparison indicators on Phase 2 probability cards (+/- % vs. home)
- [x] Map: green home center marker differentiation ("H" label, higher z-index)
- [x] CDF chart: dashed green reference line for home center
- [x] Backend: `home_center` field on PatientProfile (pass-through)
- [x] Graceful degradation: no visual changes when home center not selected
- [x] 2 new schema tests (163 total pytest)

### M2: Organ-Specific Donor Availability Model (toggleable) ✅
- [x] Data curation: `data/cause-of-death-by-region.json` — organ recovery rates (PMC10329409) + 17-state CDC WONDER proportions
- [x] Organ recovery conversion matrix from published literature (PMC10329409 Table 2)
- [x] `_computeCodMultiplier()` in algorithm.js + `_get_cod_multiplier()` in monte_carlo.py
- [x] Backend: COD multiplier divides Monte Carlo wait times (more donors → shorter waits)
- [x] Frontend: "Adjust for regional cause-of-death patterns" toggle in Simulation Settings
- [x] `data-loader.js` extended with causeOfDeath entry + full fallback defaults
- [x] 7 new frontend tests (toggle on/off, organ differentiation, bounds, backward compat)
- [x] 2 new backend schema tests (default False, accepted True) — 165 total pytest
- [x] ADR-017 documenting multiplier approach and rationale

### M2b: COD Model Data Quality Improvements (L-049 through L-056) — ✅ ALL CORE ITEMS DONE

> **Goal:** Upgrade the M2 cause-of-death multiplier from static single-paper seed data to a multi-source, automatable, stochastic model. Can be worked independently of M3–M6.
> **Status:** All 8 limitations (L-049 through L-056) resolved. Remaining items are optional enhancements.

#### Tier 1: OPO Geographic Mapping (L-050) — ✅ SUFFICIENTLY ADDRESSED
- [x] Authoritative county-to-OPO mapping from HRSA Data Warehouse (3,225 counties → 60 OPOs)
- [x] All 248 SRTR centers mapped to OPOs via `hrsa_county` method (40 corrections from proximity-based)
- [x] `data/opo-mapping.json` updated with `countyToOpo` section and multi-OPO overlap tracking
- [ ] *Optional future:* Aggregate county-level CDC data to OPO level using HRSA mapping (low priority — state-level COD proportions are well-mitigated by L-053 stochastic sampling and L-056 sublinear elasticity)

#### Tier 2: Automated CDC SODA Fetch (L-051, L-055) — ✅ FIXED
- [x] `scripts/fetch-cod-data.js` using data.cdc.gov SODA API (bi63-dtpu + xkb8-kh2a)
- [x] All 50 states + DC with donor-eligibility calibration weights (Nelder-Mead optimization)
- [x] Added to GitHub Actions weekly fetch job
- [x] L-055 resolved: expanded from 17 to 51 state COD proportions
- *Note:* CDC WONDER programmatic API blocks state filtering by policy — SODA approach bypasses this

#### Tier 3: Stochastic Multiplier (L-053) — ✅ FIXED
- [x] Recovery rates modeled as `Beta(rate×κ, (1-rate)×κ)` distributions with κ=50 (~3.5% CV)
- [x] Backend: `_get_cod_multiplier()` samples stochastic multiplier per Monte Carlo iteration
- [x] Applied across all simulation paths (MC, what-if, sensitivity, MCMC)
- [ ] *Optional future:* Frontend confidence range on score cards (e.g., "±2.3 pts")
- [ ] *Optional future:* COD uncertainty as a tornado parameter in sensitivity analysis

#### Tier 4: Expanded Categories & Cross-Validation (L-049, L-052) — ✅ L-049 VALIDATED
- [x] Add anoxia-NOS as 5th cause-of-death category (L-052 FIXED — see M2 above)
- [x] Cross-validate PMC10329409 recovery rates against OPTN 2023 national data (hrsa.unos.org)
- [x] 15/30 organ×COD cells updated where drift >10%: kidney↑ (DCD, perfusion), pancreas↓ (declining), heart/lung↓ (conservative selection)
- [x] All 6 organs within 7% of OPTN 2023 benchmarks (weighted average validation)
- [x] `scripts/validate-recovery-rates.py` updated with OPTN 2023 benchmarks and COD weights
- [x] L-056 FIXED: sub-linear elasticity (ε=0.65) implemented via `SUPPLY_WAIT_ELASTICITY` config
- [ ] *Optional future:* Calibrate ε against SRTR historical wait times (validate 0.65 assumption)

#### API Landscape (as of March 2026)

| Source | Type | Granularity | Automatable | Notes |
|--------|------|-------------|-------------|-------|
| CDC WONDER API | XML POST | National only | Yes | State filtering blocked by policy |
| data.cdc.gov SODA | REST/JSON | State | Yes | Broad categories; drug OD available separately |
| NVSS Public Files | CSV download | National only | Partial | State codes stripped since 2005 |
| OPTN Build Advanced | Web form → CSV | State/OPO | No (manual) | Best donor-specific data |
| SRTR OPO Reports | Excel download | OPO | Parseable | Already proven in M5 pipeline |
| HRSA OPTN Modernization | TBD | TBD | TBD | New system targeted fall 2026 |

### M3: City Detail & Comparison UI ✅
- [x] City detail modal: full score breakdown (Phase 1 + Phase 2 + competing risks)
- [x] Side-by-side comparison: pick 2-3 centers, see all metrics compared
- [x] Print-friendly results view for sharing with care team

### ~~M4: Policy Toggle Simulator~~ → Deferred (see note)

> **Decision (2026-03-09):** M4 as originally spec'd is partially redundant with M2's
> cause-of-death multiplier, which already adjusts organ-specific donor availability
> based on regional injury/death prevalence patterns (trauma, cardiovascular, drug,
> stroke). The remaining useful piece — sensitivity sliders letting users see how
> results change when assumptions shift — is folded into M5 (formerly M6). A proper
> causal policy model (researching real elasticities from transplant literature,
> modeling how supply changes propagate to wait times) is added to Phase 4 as a
> future milestone.

### M4: Equity Analysis (FR-10/FR-11) ← was M5 ✅
- [x] Backend: simulation matrix across 48 demographic profiles (8 blood types × 3 age brackets × 2 sexes) — `services/equity.py`
- [x] Gini coefficient inequality index per city and overall — sorted city rankings, green/yellow/red thresholds
- [x] Frontend: 3 Chart.js disparity charts (blood type, age bracket, Gini by city), city equity table, summary card, disclaimer banner
- [x] Mandatory disclaimers (no race, no insurance, model-vs-reality distinction)
- [x] 28 new pytest tests (193 total), 98 Jest tests unchanged
- [x] ADR-019 documenting demographic simulation matrix design

### M5: UX Polish & Export (FR-19/FR-20) ← was M6 ✅
- [x] Dark mode (CSS custom properties, auto-detect prefers-color-scheme, localStorage persist)
- [x] Save/share results via URL parameters (url-sharing.js, auto-submit on load)
- [x] PDF report generation with disclaimers (browser print to PDF, DOM-built)
- [x] CSV/JSON data export (scores + probabilities, metadata headers)
- [x] Exportable chart images (Chart.js toBase64Image, bulk PNG zip)
- [x] What-if scenario sliders — real Monte Carlo re-simulation, not interpolation (POST /what-if, 25 new pytest tests, 218 total)

### Documentation
- [x] User-facing "How It Works" page — Docusaurus docs site (completed Phase 2)
- [x] Technical implementation guide — architecture docs in docs-site/
- [x] FAQ page with transplant disclaimers — docs-site/docs/about/faq.md
- [ ] Jupyter notebooks for model documentation

### Usability Studies
- [ ] Beta testing with transplant patients/families (n=50)
- [ ] Observational study (n=100)
- [ ] Feedback integration and iteration

---

## Phase 4: Advanced Modeling & Validation (ADR-021)

> **Goal:** Deepen clinical accuracy and enable publication-grade validation. Transform TransPlan from "where to get a transplant fastest" to "where to get AND keep a transplant, with validated evidence."
>
> **Scoping decision (2026-03-16):** Original Phase 4 listed ~15 features (~1500+ hours). Scoped down to 5 milestones that build on existing infrastructure and directly support the publication goal. API access, SDKs, bulk analysis, and embeddable widgets deferred to Phase 5. See ADR-021 for full rationale.

### M1: Configurable Scoring Weights (FR-4) — #22

> **Why:** Enables ablation studies ("what if we remove category X?") essential for any publication. Highest-demand researcher feature.

- [ ] **Research mode**: weight sliders in Advanced Settings panel (8 categories, sum to 100%)
- [ ] **Patient mode**: locked defaults with explanation tooltip
- [ ] **Presets**: "Balanced" (current defaults), "Clinical Focus" (medical 35% + hospital 25%), "Speed" (wait time 30% + donor 25%), "Quality of Life" (geographic 20% + socio 15%)
- [ ] Frontend: instant re-scoring for Phase 1 scores (no backend needed)
- [ ] Backend: `custom_weights` field on `PatientProfile`, `POST /simulate` re-weights Monte Carlo city scoring
- [ ] Validation: weights must sum to 100%, each clamped [0, 100%], error message if invalid
- [ ] Weight change audit trail (session-level, logged to console/export)
- [ ] Tests: weight edge cases (all on one category, zero weight, preset switching)

**Key files:** `algorithm.js` (weights), `script.js` (form UI), `backend/models/schemas.py`, `backend/services/monte_carlo.py`
**Depends on:** Nothing — fully independent, start immediately.

### M2: Post-Transplant Outcomes Model ✅ DONE

> **Why:** "Getting a transplant" is half the story. Center-level graft survival data transforms TransPlan into a tool clinicians take seriously. Compound success metric (P(transplant) × P(1yr graft survival)) is a novel contribution.

- [x] **SRTR PSR Tables C5-C12 / C11-C20 parsing**: extract graft/patient survival, hazard ratios, 95% CI, performance ratings (6 organs × 22 cities)
- [x] New data file: `data/post-transplant-outcomes.json` — center graft/patient survival, HR, CI, performance ratings, national baselines
- [x] Extend `scripts/parse-srtr-reports.py` to extract C-series tables (alongside existing B7/B10)
- [x] New backend service: `services/outcomes.py` — survival lookup with center→national fallback, compound success computation
- [x] **Compound success metric**: `P(transplant within 24mo) × P(1yr graft survival)` = overall success probability
- [x] Extended `POST /simulate` response: outcomes dict attached to each CityProbability
- [x] Frontend: "Post-Transplant Outlook" section in city detail modal (5-cell outcome grid, performance badge)
- [x] Frontend: graft survival + compound success on probability cards, outcomes in comparison table
- [x] Disclaimers: risk-adjusted Bayesian hierarchical estimates, not individual predictions
- [x] Export: outcomes in CSV (4 columns), JSON (pass-through), PDF (2 columns)
- [x] Tests: 35 new pytest (282 total) — baselines, city outcomes, survival helpers, compound metric, build_outcomes_dict
- [x] Pancreas handling: no adult graft survival in SRTR; falls back to patient survival with annotation

**Key files:** `scripts/parse-srtr-reports.py`, `backend/services/outcomes.py`, `script.js`, `export-handler.js`
**Completed:** March 2026. GitHub issue #31.

### M3: Historical Trends & Center Trajectories ✅ DONE

> **Why:** Centers change over time. "Is Cleveland getting better or worse for kidney transplants?" is critical context no existing tool provides. Adds temporal validity to the model.

- [x] **Multi-year SRTR PSR downloads**: `fetch-srtr-historical.py` scrapes srtr.org dropdown, downloads archived zip bundles (2019–2025, 14 biannual releases)
- [x] Extended `scripts/parse-srtr-reports.py` with `parse_historical_trends()` extracting Table B10/B9, B7/B6, C-series across releases (handles old/new sheet naming)
- [x] Auto-discovery: parser scans `data/srtr-raw/historical/` directories — no hardcoded release list needed for future releases
- [x] New data file: `data/srtr-historical.json` — 15-release time-series (2019–2025) of wait times, volumes, outcomes per center per organ (real SRTR data, not synthetic)
- [x] GitHub Actions workflow: `.github/workflows/fetch-srtr-historical.yml` — scheduled checks after SRTR Jan/Jul releases
- [x] New backend service: `services/trends.py` — `scipy.stats.linregress`, p < 0.10 significance, direction classification
- [x] **Trending badge** on city probability cards: ↑ improving / → stable / ↓ declining (weighted vote across metrics)
- [x] **Sparkline charts** in city detail modal: wait time, volume, graft survival (Chart.js, national reference dashed line)
- [x] Trends included in `POST /simulate` response + dedicated `GET /trends/{city}/{organ}` endpoint
- [x] Missing years handled gracefully (null filtering, MIN_POINTS=3 guard, try/except per release)
- [x] Trend data in CSV/JSON/PDF exports and side-by-side comparison table
- [x] 51 new pytest tests (333 total), 112 Jest unchanged

**Key files:** `scripts/fetch-srtr-excel.py`, `scripts/parse-srtr-reports.py`, `backend/services/trends.py`, `backend/routers/trends.py`, `script.js`, `styles.css`
**Completed:** March 2026. ADR-022.

### M4: Policy Scenario Engine (FR-9 upgrade) — #23

> **Why:** The hardest but most novel feature. Upgrades Phase 3 what-if sliders from raw multipliers to real UNOS policy scenarios with literature-backed elasticities. This is what makes TransPlan a research-grade tool.

**Phase 1: Literature Review (before coding)**
- [ ] Research SRTR historical wait times before/after 2021 kidney allocation policy change
- [ ] Estimate empirical supply-to-wait elasticity from real data (validate/update 0.65 assumption — L-056 core implementation already done)
- [ ] Review transplant policy papers: OPTN continuous distribution, regional sharing rules, DCD expansion
- [ ] Document causal model assumptions as a formal DAG (directed acyclic graph)

**Phase 2: Predefined Scenarios**
- [ ] **2021 Kidney 250nm circles**: donor pool +15-25% for small centers, -5% for large (geography-dependent)
- [ ] **Continuous distribution**: points-based allocation, reduces geographic advantage (distance matters less)
- [ ] **Increased DCD utilization**: organ supply +10-20% (expanded donation after circulatory death)
- [ ] **Broader HCV+ acceptance**: donor pool +5-8% (hepatitis C positive donors with DAA treatment)
- [ ] Each scenario maps to concrete per-city parameter adjustments (not just global multipliers)

**Phase 3: Implementation**
- [ ] Upgrade `POST /what-if` to accept structured `PolicyScenario` objects (not just raw multipliers)
- [ ] New schema: `PolicyScenario` with name, description, per-city adjustments, literature references
- [ ] Paired-seed comparison (baseline vs. scenario) — reuse Phase 3 M5 infrastructure
- [ ] Frontend: scenario selector dropdown (predefined) + custom parameter builder
- [ ] Side-by-side results: baseline vs scenario, delta highlighting, ranking changes
- [ ] Tests: scenario application correctness, per-city vs global adjustments, edge cases

**Key files:** `backend/services/what_if.py`, `backend/models/schemas.py`, `api-client.js`, `script.js`
**Depends on:** Literature review (Weeks 2-4). Can research while M1-M2 are being coded.

### M5: Validation & Reproducibility Pack — NEW

> **Why:** This is what makes the model publishable. Retrospective validation against real outcomes, demographic bias audits, and reproducible Jupyter notebooks are standard requirements for medical informatics publications.

- [ ] **Retrospective validation**: run model against historical SRTR cohorts, compare predicted vs actual wait times and outcomes
- [ ] **Bias audit**: run equity analysis with expanded demographic profiles, document disparity patterns and magnitudes
- [ ] **Calibration curves**: predicted P(transplant by X months) vs observed rates (extending Phase 2 M7 Brier scores)
- [ ] **Jupyter notebooks** (3-5): one per major model component (wait times, competing risks, COD multiplier, outcomes, trends)
- [ ] **Validation report**: auto-generated document with Brier scores, calibration plots, fairness metrics, sensitivity results
- [ ] **Ablation study**: use M1 configurable weights to systematically test category importance
- [ ] Export validation artifacts for paper supplementary materials (tables, figures, data)
- [ ] **Reproducibility**: document exact software versions, data file hashes, RNG seeds for all validation runs

**Key files:** New `notebooks/` directory, `backend/services/brier_score.py` (extend), `backend/services/equity.py` (extend)
**Depends on:** M1-M4 stabilized. This is the capstone milestone.

### Documentation
- [x] User-facing "How It Works" page — Docusaurus docs site (completed Phase 2)
- [x] Technical implementation guide — architecture docs in docs-site/
- [x] FAQ page with transplant disclaimers — docs-site/docs/about/faq.md
- [ ] Jupyter notebooks for model documentation — Phase 4 M5
- [x] CSV/JSON data export — Phase 3 M5
- [x] PDF reports with disclaimers — Phase 3 M5 (browser print-to-PDF)
- [ ] Clinical export format for provider discussions

### Phase 4 Dependency Graph
```
M1 (Weights) ──────────── independent ─────────────────┐
                                                        │
M2 (Outcomes) ── SRTR C-series ── ✅ DONE ──────────────┼──→ M5 (Validation)
                                                        │
M3 (Trends) ──── multi-year SRTR ── ✅ DONE ───────────┤
                                                        │
M4 (Policy) ──── literature review (weeks 2-4) ────────┘
```

---

## Phase 5: Platform, Regulatory & Scaling

> **Goal:** Public API, FDA clearance as SaMD, widespread adoption, sustainability.
> **Includes items deferred from Phase 4 scope-down (ADR-021).**

### M1: Bayesian Belief Network ✅ DONE

> **Why:** Alternative inference engine providing exact probabilistic inference (~30ms cached vs ~2s Monte Carlo). Enables instant results and cross-validation of Monte Carlo outputs.

- [x] **pgmpy dependency + CPT parameterizer**: 7 CPTs built from existing JSON data (no duplication) — `bbn_parameterizer.py`
- [x] **12-node DAG + inference engine**: 5 evidence, 3 latent, 2 outcome, 2 post-tx nodes, 21 edges — `bayesian_network.py`
- [x] **API integration**: `POST /simulate?inference_mode=bayesian` dispatches to BBN; default remains Monte Carlo
- [x] **Frontend toggle + results badge**: inference method dropdown, blue MC / green BBN badge
- [x] **Cross-validation**: Spearman rank correlation > 0.5, directional consistency on blood type/organ/urgency
- [x] **ADR-024 + documentation**: architecture decision record, status.md, file map updates
- [x] **Age mortality multipliers**: added to competing-risks.json for BBN age-group modeling
- [x] **URL sharing**: inference mode persisted in URL params
- [x] 72 new pytest tests (30 parameterizer + 32 inference + 10 cross-validation)

**Key files:** `backend/services/bbn_parameterizer.py`, `backend/services/bayesian_network.py`, `api-client.js`, `simulator.html`
**Completed:** March 2026. ADR-024. Issues #36-#42.

### M2: Clayton Copula for Correlated Competing Risks ✅ DONE

> **Why:** The independence assumption between mortality and delisting in the Monte Carlo engine (three separate exponential draws) underestimates clustered adverse events. A Clayton copula introduces positive lower-tail dependence — when health deteriorates, both mortality and delisting accelerate together.

- [x] **Clayton copula sampler**: `services/copula.py` with conditional method (Nelsen, 2006 §4.2)
- [x] **Marginal preservation**: maps copula-coupled uniforms through exponential inverse CDF
- [x] **Opt-in toggle**: `use_copula: bool` on PatientProfile (default False for backward compat)
- [x] **All 3 simulation paths**: monte_carlo.py, what_if.py, sensitivity.py support copula draws
- [x] **Config**: `COPULA_THETA = 1.0` (Kendall's τ ≈ 0.33, moderate positive dependence)
- [x] **22 copula unit tests**: marginal uniformity (KS test), Kendall's τ matches theoretical, edge cases
- [x] **4 integration tests**: copula + all organs, copula + COD combined, probability monotonicity
- [x] **ADR-025**: documents copula choice, alternatives rejected, validation approach

**Key files:** `backend/services/copula.py`, `backend/config.py`, `backend/models/schemas.py`, `backend/services/monte_carlo.py`, `backend/services/what_if.py`, `backend/services/sensitivity.py`
**Completed:** March 2026. ADR-025. Issues #94.

### M3: MCMC Hierarchical Survival Model ✅ DONE

> **Why:** Replace point-estimate parameters (fixed mortality rates, fixed delisting rates) with full posterior distributions. A ~550-parameter PyMC model with organ→city→patient hierarchy produces credible intervals on every prediction, honest uncertainty quantification, and adaptive shrinkage for data-sparse centers.

**Architecture:**
- **Offline training**: PyMC NUTS sampler fits organ-specific hierarchical models from SRTR data
- **Trace-as-cache**: Posterior traces saved as ArviZ InferenceData (~10-50MB per organ)
- **Online query**: Draw from cached trace at inference time (~200-500ms, no re-fitting)
- **Schema**: `inference_mode: "mcmc"` on SimulationResult

**Completed:**
- [x] PyMC + ArviZ dependencies added to requirements.txt
- [x] Hierarchical model specification: national hyperpriors → city random effects → patient covariates (92 free params per organ)
- [x] SRTR data adapter: existing JSON → PyMC observed data (5 likelihood terms)
- [x] Trace caching + loading infrastructure (ArviZ NetCDF)
- [x] Offline fitting script: `scripts/fit-mcmc-model.py` (per-organ or --all, --quick mode)
- [x] `POST /simulate?inference_mode=mcmc` endpoint with 503 if trace missing
- [x] Frontend: dropdown option + orange MCMC badge
- [x] ADR-026: MCMC hierarchical survival model
- [x] 53 new pytest tests (38 survival + 15 inference)

**Key files:** `backend/services/mcmc_survival.py`, `backend/services/mcmc_inference.py`, `scripts/fit-mcmc-model.py`, `backend/routers/simulate.py`
**Completed:** March 2026. ADR-026. Issue #95.

### M4: Shared Frailty + Bayesian HDI ✅ DONE

> **Why:** The MCMC model fitted mortality and delisting city offsets independently, then relied on the external Clayton copula (fixed θ=1.0) to couple them at query time. A shared frailty model learns the correlation from data, making MCMC genuinely richer than MC+copula. Bayesian HDI replaces bootstrap CIs with proper posterior-predictive credible intervals.

**Completed:**
- [x] LKJ-Cholesky correlation prior (`pm.LKJCholeskyCov`, η=2) for bivariate (mortality, delisting) city offsets
- [x] `mort_delist_corr` deterministic: learned organ-specific correlation exposed in trace
- [x] Auto-detect shared frailty in MCMC inference — external copula becomes redundant when trace has learned correlation
- [x] Posterior-predictive 95% credible intervals: per-draw p24 → percentiles (replaces bootstrap)
- [x] L-053 and L-056 marked FIXED (stochastic COD + sub-linear elasticity already implemented)
- [x] 11 new tests (7 survival model + 4 inference), total MCMC tests: 64
- [x] ADR-027: Shared frailty decision record

**Key files:** `backend/services/mcmc_survival.py` (model restructured), `backend/services/mcmc_inference.py` (Bayesian HDI + frailty detection)
**Completed:** March 2026. ADR-027. Issues #96, #99.

### M5: Cross-Engine Validation & Model Quality ✅ DONE

> **Why:** Paper-grade validation that all three inference engines (MC, BBN, MCMC) agree on key predictions, and that MCMC posterior predictions match observed SRTR data. Also fixes known statistical issues.

**Completed:**
- [x] Cross-engine validation service (`services/cross_validation.py`): runs MC, BBN, MCMC on same patient; Spearman rank correlation, mean/max p24 diff, top-5 overlap
- [x] Posterior predictive checks (`services/posterior_checks.py`): MCMC posterior vs observed SRTR statistics (8 checks: national median, log-sigma, city factors, blood type ranks, mortality, delisting, urgency monotonicity, calibration)
- [x] L-059 fix: per-organ copula θ (kidney=0.8, liver=1.2, heart=1.8, lung=1.5, pancreas=0.9, intestine=1.5) — all 4 simulation paths
- [x] L-062 fix: `--strict` convergence gate (R-hat < 1.01, ESS > 400) on `fit-mcmc-model.py`
- [x] 24 new tests (14 cross-validation + 10 posterior checks)

**Bug/Quality Sprint (March 2026):** 15 issues closed across 3 tiers:
- [x] Tier 1: Thread-safe lazy-load globals (#55), bare except handling (#56), centerReputation differentiation (#44), XSS audit — no user input reaches innerHTML (#57, closed as won't-fix)
- [x] Tier 2: Nullish coalescing for zero-preserving defaults (#67), LAS float parsing (#68), dead variable removal (#71), concurrent submission guard (#66), frozen dist introspection helper (#61), honest BBN uncertainty band (#54), per-organ BBN CPT terciles (#59)
- [x] Tier 3: BLS cost-of-living verified (#101), EPA air quality verified (#100), CDC PLACES expanded to 5 county-level indicators (#102), FARS CSV bulk download (#103)
- [x] #104: Real SRTR historical data — 14 biannual releases (2019–2025) with automated GH Actions refresh (resolved by user)

**Remaining:**
- [ ] API endpoint for cross-engine validation (`POST /cross-validate`)
- [ ] API endpoint for posterior checks (`GET /posterior-checks/{organ}`)

**Key files:** `backend/services/cross_validation.py`, `backend/services/posterior_checks.py`, `backend/config.py`
**Started:** March 2026.

### Platform API & Integrations (deferred from Phase 4)
- [ ] **Public REST API with tiered access (FR-18)** — #24: API key auth, rate limiting, versioned endpoints, Swagger docs
- [ ] **Python & JavaScript SDKs** — #25: client libraries wrapping TransPlan API (PyPI + npm)
- [ ] **Policy scenario builder UI** — #26: interactive scenario creation extending M4 engine
- [ ] **Institutional bulk analysis & cohort tools** — #27: CSV upload, batch simulation, cohort equity reports
- [ ] **Embeddable widget / white-label integration** — #28: iframe/Web Component mini-calculator
- [ ] Clinical export format for provider discussions

### Regulatory
- [ ] FDA Q-submission for classification (Non-Device CDSS vs SaMD)
- [ ] If SaMD: 510(k) submission with clinical evidence
- [ ] QMS documentation (21 CFR 820)
- [ ] Risk management (ISO 14971)

### Clinical Validation (continued from Phase 4 M5)
- [ ] RCT design (n=200-500): does TransPlan improve patient decision quality?
- [ ] Publication in transplant/health informatics journal
- [ ] External validation with transplant center partners

### Deployment Modes
- [ ] **Local/Offline Mode** (default): runs entirely in-browser, no PHI transmitted
- [ ] **HIPAA-Compliant Cloud Mode** (clinical pilots): BAA-backed hosting, encryption, audit logging
- [ ] Feature flags to build both modes from same codebase

### Advanced Modeling (deferred from Phase 4)
- [x] Bayesian Belief Network layer — ✅ Phase 5 M1 (see above)
- [ ] Agent-based simulation (patient agents, donor pool, regional allocation)
- [ ] Living donor matching optimization (geographic clustering, demographic match probability)
- [ ] Insurance compatibility layer (Medicaid vs private access patterns)

### Scaling
- [ ] EHR integration (post-FDA)
- [ ] International expansion (non-US transplant systems)
- [ ] ML-enhanced risk models
- [ ] Mobile PWA
- [ ] Multilingual support (WCAG 2.1 AA)

### Sustainability
- [ ] GitHub Sponsors / Patreon
- [ ] Grant applications (NIH SBIR, HRSA)
- [ ] Annual transparency reports
- [ ] No paywalls on core functionality

---

## Phase 6: Spatial Geographic Modeling

> **Goal:** Transform TransPlan from discrete city-level scoring to continuous spatial modeling. Expand from 22 hand-picked cities to all ~250 SRTR transplant centers. Build interpolated geographic surfaces. Model UNOS allocation geography.
>
> **Why three sub-phases?** The ROI curve flattens sharply. Phase 6A captures ~80% of accuracy gain for ~20% of effort by using data we already download but discard. Phase 6B adds ~10% more via new data acquisition and interpolation infrastructure. Phase 6C adds the final ~10% with research-grade geostatistics. Each phase builds on the prior — 6B needs the coordinates and dynamic loading from 6A; 6C needs the interpolation engine from 6B.

### Phase 6A: Center Expansion & Geographic Foundation (Epic #114)

> **Why a separate phase?** This is the highest-ROI work. SRTR PSR Excel files already contain center-level statistics for ALL ~250 US transplant programs, but our parse script filters to 22 cities. Removing this filter and adding coordinates enables everything that follows.

- [x] **Extract SRTR center list** (#115): 248 centers cataloged from SRTR PSR Excel files → `data/srtr-all-centers.json`
- [x] **Add geographic coordinates** (#116): Nominatim + manual geocoding. All 248 centers verified March 2026 — hospital-specific coordinates, no city-center approximations remain (#136)
- [x] **Update parse script** (#117): center-level data files for all ~248 centers (wait times, competing risks, outcomes)
- [x] **Replace hardcoded CITIES** (#118): dynamic `_get_cities()` in all backend services with fallback
- [x] **Dynamic center dropdown** (#119): API-first with hardcoded fallback in frontend
- [x] **Leaflet marker clustering** (#120): L.markerClusterGroup for 248+ center markers, fetches from backend API with hardcoded fallback
- [x] **Results pagination** (#121): top-10/20/50/all page size, state filter, prev/next navigation
- [ ] **OPO-to-center mapping** (#122): 57 OPOs → constituent centers, boundary data (extends #19)
- [x] **Patient home location** (#123): Nominatim geocoding, haversine distance display on city cards

**Status:** All items complete except OPO mapping (#122, deferred — requires OPO boundary data).

### Phase 6B: Spatial Interpolation (Epic #124)

> **Why a separate phase?** Requires new data acquisition (full county datasets, monitor-level data) and new infrastructure (interpolation engine, surface caching). Phase 6A is a prerequisite — we need coordinates and dynamic loading before spatial surfaces make sense.

**Current data waste:** TransPlan discards ~99% of available spatial data. EPA AQS has ~4,000 monitors → averaged to 22 values. CDC PLACES has ~3,000 counties → only 20-22 queried. Building continuous surfaces from this data enables accurate scores at ANY location, not just 22 predefined cities.

- [x] **EPA monitor data** (#125): `scripts/fetch-air-quality-monitors.js` — per-monitor lat/lon + AQI scores across all 50 states, ~2000-4000 points
- [x] **CDC county data** (#126): `scripts/fetch-health-data-counties.js` — 2,956 US counties with lat/lon + 4 health indicators from CDC PLACES
- [x] **Interpolation service** (#127): `backend/services/spatial_interpolation.py` — RBF/IDW surface builder + point queries, 24 layers, 19 pytest
- [x] **Interpolation API** (#128): `GET /spatial-layers`, `/interpolated-value`, `/interpolated-profile`, `/spatial-grid` endpoints
- [x] **Heatmap overlay** (#129): Leaflet heatmap via `/spatial-grid` endpoint, layer selector dropdown (6 layers)
- [x] **Allocation circle modeling** (#130): 250nm/500nm UNOS circles, competition scoring, composite distance score, 13 pytest
- [x] **Patient-relative scoring** (#131): `GET /location-delta` endpoint — per-layer delta comparison between patient home and any center

**Status:** All items complete. Phase 6B done. Interpolation now uses 2,956 health data points (was 22) and ~4,000 EPA monitor points (when fetched).

### Phase 6C: Full Spatial Model & Geostatistical Inference (Epic #132)

> **Why a separate phase?** This is research-grade work — highest effort, lowest marginal gain. Adds ~10% accuracy for ~40% of total effort. Pursue when 6A+6B are stable and if targeting publication in health geography / medical informatics journals.

- [ ] **Pre-computed raster grid** (#133): 10km resolution, CONUS-wide, ~80,000 cells × N layers
- [ ] **Kriging uncertainty** (#134): variance estimates at every prediction point, confidence intervals on interpolated values
- [ ] **Spatial econometric models** (#135): spatial lag model for center competition effects (wait times influenced by demand at nearby centers)

**Estimated effort:** 3-5 weeks after 6B. **Depends on:** Phase 6B interpolation engine.

### Phase 6 Dependency Graph
```
Phase 6A: Center Expansion ──────────────────────────────┐
  ├── Extract center list (#115)                          │
  ├── Add coordinates (#116)                              │
  ├── Update parse script (#117)                          │
  ├── Replace hardcoded CITIES (#118)                     │
  ├── Dynamic dropdown (#119)                             │
  ├── Marker clustering (#120)                            │
  ├── Results pagination (#121)                           │
  ├── OPO mapping (#122)                                  │
  └── Patient home location (#123)                        │
                                                          ▼
Phase 6B: Spatial Interpolation ─────────────────────────┐
  ├── EPA monitor data (#125)                             │
  ├── CDC county data (#126)                              │
  ├── Interpolation service (#127)                        │
  ├── Interpolation API (#128)                            │
  ├── Heatmap overlay (#129)                              │
  ├── Allocation circles (#130)                           │
  └── Patient-relative scoring (#131)                     │
                                                          ▼
Phase 6C: Full Spatial Model
  ├── Pre-computed raster grid (#133)
  ├── Kriging uncertainty (#134)
  └── Spatial econometric models (#135)
```

---

## Architecture Decision: Stack Migration

The SRS (docs/ideas.md) specifies a target architecture of:
- **Backend:** Python (FastAPI), NumPy/SciPy/PyMC/Lifelines
- **Frontend:** Next.js/React, D3.js, TypeScript
- **Data:** PostgreSQL, Git LFS for SRTR datasets
- **Infra:** Docker, Celery workers for Monte Carlo, Terraform/Pulumi

**Current stack:** Static vanilla HTML/CSS/JS (no backend, no build step)

**Migration path (incremental, not big-bang):**
1. Phase 1 (current): ship static MVP as-is on GitHub Pages
2. Phase 2: add Python `backend/` for Monte Carlo engine; static frontend calls API
3. Phase 3: migrate frontend to Next.js/React if needed (or keep static if API-first works)
4. Phase 4+: full stack per SRS

This avoids a premature rewrite while keeping the path open.

---

## Data Pipeline Status

| Source | Script | API Status | Frequency |
|--------|--------|------------|-----------|
| NHTSA FARS | fetch-traffic.js | ✅ Works (CSV bulk download) | Weekly (CI) |
| EPA AQS | fetch-air-quality.js | ✅ Works (needs API key) | Weekly (CI) |
| CMS Provider | fetch-hospital-quality.js | ✅ Works (multi-strategy query) | Weekly (CI) |
| BLS | fetch-cost-of-living.js | ✅ Works (needs API key) | Weekly (CI) |
| CDC PLACES | fetch-health-data.js | ✅ Works (5 county-level indicators, public) | Weekly (CI) |
| CDC COD | fetch-cod-data.js | ✅ Works (50 states + DC, public) | Weekly (CI) |
| SRTR | check-srtr-updates.js | Hash check only | Bimonthly (CI) |
| SRTR Historical | fetch-srtr-historical.yml | ✅ Works (GH Actions automated) | After SRTR Jan/Jul releases |
| Donor Registration | Manual (DLA 2019 Annual Report PDF) | `stateRegistrationRates` from DLA DDR (2018 data) | Report-based |

**Automation:** GitHub Actions runs weekly on Monday 6am UTC. Manual trigger available via `workflow_dispatch`. All scripts use `continue-on-error` so one failure doesn't block others. Single commit at end.

---

## Deferred Items (need API access or external data)

| ID | Issue | Blocker |
|----|-------|---------|
| L-009 | ~~OPO boundary mapping~~ | **RESOLVED** — HRSA Data Warehouse Excel (3,225 counties → 60 OPOs) |
| L-017 | SRTR program-specific outcomes | HTML/PDF reports only; 132 manual data points |
| L-033 | ~~Donor registration fetch script~~ | **PARTIALLY RESOLVED** — `stateRegistrationRates` from DLA report; `livingDonorProgramStrength` and `populationFactors` remain manual by design |
