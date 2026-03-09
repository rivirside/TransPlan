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
- [x] Run fetch scripts against live APIs (CDC works, FARS/CMS broken)
- [x] GitHub Actions weekly fetch operational (cron + workflow_dispatch)
- [ ] Fix FARS endpoint (L-045) — API may have moved to data.transportation.gov
- [ ] Fix CMS endpoint (L-046) — verify dataset ID and query format
- [ ] Add CDN fallback or error messaging (L-047)

### Open Limitations (L-045 through L-048)
- [ ] L-045: NHTSA FARS API endpoint returns 403
- [ ] L-046: CMS Provider Data API endpoint returns 400
- [ ] L-047: CDN fallback for Leaflet/Chart.js
- [ ] L-048: COL normalization hardcoded range

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
- [ ] Visual comparison panels (side-by-side probability curves)
- [ ] Exportable chart images

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

### M3: City Detail & Comparison UI
- [ ] City detail modal: full score breakdown (Phase 1 + Phase 2 + competing risks)
- [ ] Side-by-side comparison: pick 2-3 centers, see all metrics compared
- [ ] Print-friendly results view for sharing with care team

### M4: Policy Toggle Simulator (FR-9)
- [ ] Backend: parameterize donor rates, sharing policies, organ supply growth
- [ ] Frontend: toggle controls panel with side-by-side scenario comparison
- [ ] Scenarios: donor registration increase, regional sharing expansion

### M5: Equity Analysis (FR-10/FR-11)
- [ ] Backend: simulation matrix across demographic profiles (age/sex/blood type/insurance)
- [ ] Gini/Theil inequality indices for transplant access
- [ ] Frontend: disparity visualizations, equity alerts

### M6: UX Polish & Export (FR-19/FR-20)
- [ ] Dark mode (CSS custom properties)
- [ ] Save/share results via URL parameters
- [ ] PDF report generation with disclaimers
- [ ] CSV/JSON data export
- [ ] Exportable chart images

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

## Phase 4: Advanced Modeling & Clinical Validation (Months 25-36 per SRS)

> **Goal:** Publication-grade modeling, RCT, and FDA pathway preparation.

### Advanced Modeling
- [ ] Bayesian Belief Network layer (conditional probability graph for wait time)
- [ ] Agent-based simulation (patient agents, donor pool, regional allocation)
- [ ] Post-transplant survival estimator (1-year, 5-year graft survival)
- [ ] Living donor matching optimization (geographic clustering, demographic match probability)
- [ ] Historical trend analyzer (5-10 year changes in volumes, donor trends, waitlist mortality)
- [ ] Regression overlays for trend data

### FR-18: API Access
- [ ] REST API for programmatic queries (FastAPI + Swagger docs)
- [ ] Rate-limited research tier
- [ ] Versioned API endpoints
- [ ] API authentication and usage tracking

### FR-19/FR-20: Export & Reports
- [ ] CSV/JSON data export
- [ ] PDF reports with disclaimers, sources, watermarks
- [ ] Clinical export format for provider discussions

### Clinical Validation
- [x] Retrospective calibration (Brier score <0.001 for all 6 organs -- exceeded <0.2 target) — completed in Phase 2 M7
- [ ] External validation against held-out SRTR cohort data
- [ ] Bias audits across demographics
- [ ] RCT design (n=200-500): does TransPlan improve patient decision quality?
- [ ] Publication in transplant/health informatics journal

### Insurance Compatibility Layer
- [ ] Medicaid vs private transplant access differences by center
- [ ] Regional insurance acceptance patterns
- [ ] Payer-access analytics

---

## Phase 5: FDA Clearance & Scaling (Months 37+ per SRS)

> **Goal:** FDA clearance as SaMD, widespread adoption, sustainability.

### Regulatory
- [ ] FDA Q-submission for classification (Non-Device CDSS vs SaMD)
- [ ] If SaMD: 510(k) submission with clinical evidence
- [ ] QMS documentation (21 CFR 820)
- [ ] Risk management (ISO 14971)

### Deployment Modes
- [ ] **Local/Offline Mode** (default): runs entirely in-browser, no PHI transmitted
- [ ] **HIPAA-Compliant Cloud Mode** (clinical pilots): BAA-backed hosting, encryption, audit logging
- [ ] Feature flags to build both modes from same codebase

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
| NHTSA FARS | fetch-traffic.js | 403 Forbidden (L-045) | Weekly (CI) |
| EPA AQS | fetch-air-quality.js | Works (needs API key) | Weekly (CI) |
| CMS Provider | fetch-hospital-quality.js | 400 Bad Request (L-046) | Weekly (CI) |
| BLS | fetch-cost-of-living.js | Works (needs API key) | Weekly (CI) |
| CDC SODA | fetch-health-data.js | Works (public) | Weekly (CI) |
| SRTR | check-srtr-updates.js | Hash check only | Bimonthly (CI) |
| Donor Registration | (none) | Deferred (L-033) | Manual |

**Automation:** GitHub Actions runs weekly on Monday 6am UTC. Manual trigger available via `workflow_dispatch`. All scripts use `continue-on-error` so one failure doesn't block others. Single commit at end.

---

## Deferred Items (need API access or external data)

| ID | Issue | Blocker |
|----|-------|---------|
| L-009 | OPO boundary mapping | No API; 22 cities → 58 OPOs manual lookup |
| L-017 | SRTR program-specific outcomes | HTML/PDF reports only; 132 manual data points |
| L-033 | Donor registration fetch script | Donate Life America has no API |
| L-045 | FARS API endpoint | Endpoint deprecated or moved |
| L-046 | CMS API endpoint | Query format or dataset ID changed |
