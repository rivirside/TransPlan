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

### FR-5: Monte Carlo Wait-Time Simulator
- [ ] Download SRTR program-specific report datasets (quarterly, srtr.org)
- [ ] Parse SRTR data: center-level wait times, volumes, survival rates by organ/blood type
- [ ] Build Monte Carlo simulation engine (1,000+ iterations per scenario)
  - **Decision:** JS in-browser for static deployment, or Python/FastAPI backend
  - If Python: FastAPI server, NumPy/SciPy for distributions
  - If JS: Web Worker for non-blocking simulation, same math
- [ ] Probability output: P(transplant <= X months) with confidence intervals
- [ ] Show probability curves (CDF) — D3.js or Chart.js line charts
- [ ] Allow comparison across regions on the same curve
- [ ] Performance target: <5 seconds per simulation run
- [ ] Validate: retrospective testing against SRTR benchmark waitlists

### FR-6: Competing Risks Model
- [ ] Model: P(transplant) vs. P(mortality) vs. P(delisting)
- [ ] Kaplan-Meier survival curves per center/organ
- [ ] Library decision: Lifelines (Python) or custom JS implementation
- [ ] Relocation variants: show how competing risks shift by geography

### FR-7: Probability Outputs & Visualization
- [ ] CDF curves with confidence intervals
- [ ] Ranked output: boost vs. current location
- [ ] Visual comparison panels (side-by-side probability curves)
- [ ] Exportable chart images

### FR-4: Configurable Weights
- [ ] Research mode: allow users to adjust category weights
- [ ] Patient mode: locked weights (clinically validated defaults)
- [ ] Audit trail for weight changes

### Sensitivity Analysis
- [ ] Tornado charts showing which variables most influence a patient's ranking
- [ ] Weight sensitivity: how much does each category shift the result?
- [ ] Adds transparency and academic credibility

---

## Phase 3: Relocation, Equity & Usability (Months 13-24 per SRS)

> **Goal:** Full relocation modeling, equity analysis, and usability studies for clinical validation.

### FR-8: Relocation Modeling
- [ ] Rank states/DSAs/centers by probability improvement
- [ ] Integrate relocation costs: housing, travel, temporary living
- [ ] Show barriers: insurance portability, Medicaid reciprocity
- [ ] Relocation cost model (housing APIs, travel frequency projections)

### FR-9: Policy Toggle Simulator
- [ ] Toggle: opt-in vs opt-out donation models
- [ ] Toggle: increased donor registration rates
- [ ] Toggle: expanded living donor programs
- [ ] Toggle: regional sharing policy changes
- [ ] Side-by-side comparison of policy scenarios
- [ ] Targets: policy students, think tanks, research groups

### FR-10/FR-11: Equity Analysis
- [ ] Stratification by demographics/SES
- [ ] Gini/Theil inequality indices for transplant access
- [ ] Flag high-inequity scenarios in relocations
- [ ] Equity alerts integrated into reports
- [ ] Racial/ethnic disparity visualizations

### Support Infrastructure Index
- [ ] Caregiver availability scoring
- [ ] Social services density per city
- [ ] Rehabilitation access metrics
- [ ] Patient housing programs (extends L-022 rubric)

### UI/UX Improvements
- [ ] City detail modal with full score breakdown
- [ ] Side-by-side city comparison mode
- [ ] Print-friendly results view for sharing with care team
- [ ] Dark mode
- [ ] Save/share results via URL parameters
- [ ] Form validation with inline error messages
- [ ] Loading spinner during simulation
- [ ] Wizard UI flow for guided input

### Documentation
- [ ] User-facing "How It Works" page
- [ ] Technical implementation guide
- [ ] FAQ page with transplant disclaimers
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
- [ ] Retrospective validation (Brier score <0.2)
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
