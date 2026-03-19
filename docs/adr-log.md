# TransPlan - Architecture Decision Records

> **Grep-searchable.** Only search this file when you need context on why a specific decision was made.

---

## ADR-001: Static Site with JSON Data Files

**Date:** 2026-02-28
**Status:** Accepted

**Context:** TransPlan needs real data but has no backend. Options: (a) build a server, (b) use a BaaS, (c) pre-fetch data via CI and serve as static JSON.

**Decision:** Option (c). GitHub Actions fetches data weekly, writes to `data/` as JSON, commits to repo. GitHub Pages serves the static site. Frontend loads JSON at runtime.

**Rationale:** Zero infrastructure cost, zero ops burden, data is version-controlled, site works offline with hardcoded fallbacks. No API keys exposed to the client.

**Consequences:** Data is at most 1 week old. Adding a new data source requires a new fetch script + workflow job. Cannot do real-time queries.

---

## ADR-002: Hardcoded Fallbacks in data-loader.js

**Date:** 2026-02-28
**Status:** Accepted

**Context:** JSON files might fail to load (network error, CORS on local file://, deleted files). Should the app crash or degrade?

**Decision:** `data-loader.js` contains complete hardcoded copies of all data as fallback defaults. If any JSON fetch fails, the app uses the hardcoded value for that source and continues.

**Rationale:** The app must always work. Medical tool users need reliability. Fallback data is better than no data.

**Consequences:** `data-loader.js` is large (~300 lines of defaults). Defaults can drift from fetched data over time. Need to periodically update defaults from the latest fetched data.

---

## ADR-003: Algorithm Bug Fixes - Additive Scoring

**Date:** 2026-02-28
**Status:** Accepted

**Context:** `calculateMedicalCompatibilityScore` started at `score = 100` and multiplied the first component (`score *= bloodType * 0.40`), then added the rest. This mixed multiplicative and additive math, producing wildly wrong results.

**Decision:** Changed to `score = 0` with all components purely additive: `score += component * weight`. Each component contributes its weighted share independently.

**Rationale:** Additive is mathematically correct for weighted averaging. All other scoring functions already used additive. The multiplicative approach was a bug, not a design choice.

---

## ADR-004: Remove Random Jitter from Scoring

**Date:** 2026-02-28
**Status:** Accepted

**Context:** `calculateComprehensiveScore` applied `totalScore *= (0.98 + Math.random() * 0.04)` to simulate "real-world uncertainty."

**Decision:** Removed entirely. Scores are now deterministic.

**Rationale:** This is a medical decision-support tool. Users comparing results need consistency. Non-determinism makes debugging impossible and erodes trust. If uncertainty communication is needed later, it should be shown as a confidence interval, not baked into the score.

---

## ADR-005: Score All 21 Cities Dynamically

**Date:** 2026-02-28
**Status:** Accepted

**Context:** Original `script.js` had hardcoded `cityData` with only 5 pre-selected cities per organ type. The algorithm existed but its results were ignored in favor of the mock data.

**Decision:** `calculateResults()` now iterates all 22 cities in `cityStateMap`, calls `calculateComprehensiveScore` for each, and ranks them dynamically. Mock `cityData` is only used as fallback if the algorithm is unavailable.

**Rationale:** The whole point of the algorithm is to personalize results. Showing the same 5 cities regardless of patient profile defeats the purpose.

**Consequences:** Results now change based on patient inputs (blood type, age, urgency, etc.). Some cities that were never shown before may now appear in top results.

---

## ADR-006: Chart.js via CDN

**Date:** 2026-02-28
**Status:** Accepted

**Context:** Need charts for score visualization. Options: (a) build custom SVG charts, (b) D3.js, (c) Chart.js via CDN.

**Decision:** Chart.js via `cdn.jsdelivr.net`. No build step, no bundler.

**Rationale:** Chart.js is lightweight (~60KB gzipped), has radar/bar/donut out of the box, and works well without a build system. D3 is overkill for 3 chart types. Custom SVG is too much effort.

**Consequences:** External CDN dependency. If CDN is down, charts don't render but the rest of the app works fine.

---

## ADR-007: Separate Fetch Jobs in GitHub Actions

**Date:** 2026-02-28
**Status:** Accepted

**Context:** The data pipeline fetches from 5+ APIs. Should they run as one job or separate jobs?

**Decision:** Each API source gets its own job in `fetch-data.yml`. A final `validate` job runs after all fetch jobs (`if: always()`).

**Rationale:** Isolated failures. If EPA is down, NHTSA data still gets updated. Each job commits independently. Easier to debug which source failed.

**Consequences:** More workflow YAML. Potential git conflicts if two jobs try to push simultaneously (mitigated by each writing different files).

---

## ADR-008: Documentation Tiers

**Date:** 2026-02-28
**Status:** Accepted

**Context:** Need project documentation that's useful for AI-assisted development across sessions.

**Decision:** Three tiers:
1. **Always-read**: `docs/status.md` - loaded every session
2. **Context-read**: `docs/design.md` - read in full when touching UI/CSS
3. **Grep-searchable**: `docs/adr-log.md`, `docs/roadmap.md`, `docs/brand-bible.md` - only searched

**Rationale:** Avoids context bloat. Status is short and always relevant. Design details only matter when doing design work. ADRs and roadmap are reference material, not active reading.

---

## ADR-009: Socioeconomic Scoring Rubric (L-022)

**Date:** 2026-03-01
**Status:** Accepted

**Context:** Original socioeconomic scores correlated with general city wealth (SF: 95, Palo Alto: 94, Cleveland: 81). A transplant patient relocating to Cleveland has access to the Transplant House of Cleveland, dedicated financial advocates, and peer support — objectively better transplant support than many wealthier cities.

**Decision:** Replace wealth-correlated scores with a transplant-support rubric: patient housing (30%), financial assistance (25%), support groups (20%), caregiver resources (15%), health literacy (10%). Researched each center's specific programs.

**Rationale:** The socioeconomic category should measure what helps transplant patients, not general wealth. Centers with dedicated transplant hospitality houses (Rochester's Gift of Life, Cleveland's Transplant House, Pittsburgh's Family House, Houston's Nora's Home) now score highest. SF dropped from 95 to 85, Cleveland rose from 81 to 92.

**Consequences:** Scores now reflect transplant-specific support. Cities with strong general economies but no transplant-specific programs (Minneapolis: 91→81) are appropriately scored lower. Category is only 2% weight so overall rankings shift modestly.

---

## ADR-010: OPO Boundaries Not Incorporated (L-009)

**Date:** 2026-03-01
**Status:** Deferred

**Context:** Pittsburgh and Philadelphia are both in Pennsylvania but served by different OPOs (CORE and Gift of Life) with meaningfully different operations. The algorithm uses state-level donor registration rates, treating all cities in a state as equivalent.

**Decision:** Defer. OPO-level data requires mapping 22 cities to 58 OPOs and sourcing performance metrics that aren't available via API. The effort is disproportionate to the impact on a 2% or 18% category.

**Rationale:** The Donor Availability category (18%) already has 4 sub-factors. Adding OPO data would require manual research for each of the 22 cities and ongoing maintenance. State-level registration rates are a reasonable proxy. If HRSA makes OPO data API-accessible in the future, revisit.

---

## ADR-011: State-Level Health Data Retained (L-012)

**Date:** 2026-03-01
**Status:** Won't Fix

**Context:** Health demographics uses state-level averages applied to cities. Dallas and Houston show different rates despite both being Texas cities — but these were manually adjusted, not from real county data. CDC PLACES dataset has county-level data.

**Decision:** Won't fix. Health demographics is 7% of the total score. County-vs-state granularity would change individual city scores by <0.5 points. The current state-level data with manual city adjustments is adequate.

**Rationale:** Cost-benefit is unfavorable. Fetching county-level CDC PLACES data for 22 cities would require FIPS mapping and a new API integration for marginal scoring improvement. If the Health Demographics weight increases in future versions, revisit.

---

## ADR-012: SRTR Outcomes Not Incorporated (L-017)

**Date:** 2026-03-01
**Status:** Deferred

**Context:** The Hospital Quality category uses transplant volume and center reputation but not program-specific outcomes (1-year survival, graft survival). SRTR publishes these in program-specific reports, but they're HTML/PDF — not API-accessible.

**Decision:** Defer. Extracting outcomes data requires scraping 132 data points (22 centers × 6 organs) from SRTR program-specific reports. These reports change format periodically and have no stable API.

**Rationale:** Volume-outcome correlation is well-established in transplant literature. Centers with high volume (which we do track) tend to have good outcomes. Adding outcomes data would be valuable but requires significant manual effort and ongoing maintenance. If SRTR releases an outcomes API, revisit.

---

## ADR-013: Donor Registration Fetch Script Not Created (L-033)

**Date:** 2026-03-01
**Status:** Deferred

**Context:** donor-registration.json is the only data file with no automated fetch script. It contains state registration rates, living donor program strength, and population factors.

**Decision:** Defer. No machine-readable API for state donor registration rates exists. Donate Life America publishes annual reports (PDF), not an API. Living donor program strength and population factors require manual curation.

**Rationale:** The seed data is reasonable and won't change dramatically year-to-year. When Donate Life America or HRSA makes registration data API-accessible, create a fetch script. For now, the bimonthly SRTR check workflow serves as a reminder to review all manual data files.

---

## ADR-012: Phase 2 Backend — Python FastAPI

**Date:** 2026-03-06
**Status:** Accepted

**Context:** Phase 2 requires Monte Carlo simulation (1,000+ iterations × 22 cities), log-normal wait-time distributions, and competing risks modeling (Kaplan-Meier). Need to choose between in-browser JS (Web Workers) and a Python backend.

**Decision:** Python FastAPI backend (`backend/` directory) with NumPy, SciPy, and Lifelines. Frontend stays vanilla JS and calls the backend API. Dual-mode results: Phase 1 deterministic scores + Phase 2 probabilistic forecasts side by side. Frontend degrades gracefully if backend is unreachable — Phase 1 scores still work standalone on GitHub Pages.

**Rationale:**
- NumPy/SciPy provide production-grade statistical distributions (log-normal, exponential) and vectorized sampling — no need to reimplement in JS.
- Lifelines provides Kaplan-Meier and competing risks out of the box.
- Performance: NumPy `rvs(size=1000)` per city is ~1ms, total simulation <1s.
- Keeping the frontend vanilla avoids a premature React/Next.js migration while Phase 1 is still pre-deploy.
- Local-only deployment for now (uvicorn or Docker Compose); cloud deploy deferred.

**Alternatives Rejected:**
- In-browser JS simulation: would work but requires reimplementing statistical distributions, harder to test, and can't use Lifelines.
- Full stack migration (React + FastAPI): over-engineering for current needs; incremental approach keeps Phase 1 shippable.

## ADR-014: Local Launcher with Dynamic Port Discovery

**Date:** 2026-03-07
**Status:** Accepted

**Context:** TransPlan has a static frontend and a Python backend that must both run for full functionality. Users need a one-click way to start everything locally, and a clean way to stop it. Ports 8002/8080 may not always be available.

**Decision:** `start.command` (macOS double-clickable) auto-discovers free ports by scanning from preferred ports (8002, 8080) upward. Writes `.transplan-session.json` with active ports and PIDs. Frontend reads this file to discover the backend URL. `POST /shutdown` endpoint lets the frontend trigger graceful shutdown. `stop.command` reads the session file for external shutdown. CORS uses `allow_origin_regex` to accept any localhost origin (safe for local-only use).

**Rationale:**
- Dynamic ports prevent "port in use" errors that frustrate users.
- Session file bridges frontend↔backend port discovery without hardcoding.
- `/shutdown` endpoint enables the "End Session" UI button, which is cleaner than asking users to find a terminal.
- `session.js` only activates on localhost — no UI pollution when deployed to GitHub Pages.
- Cleanup trap in start.command ensures both servers stop together.

**Alternatives Rejected:**
- Fixed ports with "kill existing" approach: destructive if the user has other services on those ports.
- Electron wrapper: massive overhead for a simple launcher.
- Docker Compose: adds a Docker dependency most users don't have.

**Update (ADR-015):** Superseded by single-process architecture — see ADR-015.

---

## ADR-015: Single-Process Architecture (FastAPI serves static files)

**Date:** 2026-03-07
**Status:** Accepted (supersedes dual-process parts of ADR-014)

**Context:** The dual-process architecture (separate backend + frontend servers) required CORS configuration, port discovery for two servers, a session file to bridge them, and cross-origin API calls. This added complexity for the user and codebase.

**Decision:** FastAPI serves both the API endpoints AND the static frontend files on a single port using `StaticFiles(directory=REPO_ROOT, html=True)`. API routes are mounted first so they take priority over static files. The frontend uses relative URLs (`/simulate` instead of `http://localhost:8002/simulate`), eliminating CORS entirely. Added `TransPlan.app` macOS .app bundle with `LSUIElement=true` for no-Terminal-window launch.

**Rationale:**
- Same-origin eliminates all CORS issues — no preflight requests, no headers, no regex.
- One port instead of two — simpler port discovery, simpler PID management.
- `session.js` can use same-origin `/health` check instead of reading a session file.
- `api-client.js` defaults to relative URLs, falls back to explicit `window.TransPlanBackend` for dev setups.
- macOS `.app` bundle provides true one-click launch without a Terminal window.
- `sys.path` fix in `main.py` ensures bare imports (`from config import ...`) work whether running as `backend.main:app` from repo root or `main:app` from `backend/`.

**Trade-offs:**
- Static files now routed through Python/uvicorn instead of a dedicated HTTP server — negligible perf impact for local use.
- Larger serving surface (entire repo root), but only localhost access so no security concern.
- CORS middleware kept as fallback for developers running separate frontend/backend servers.

---

## ADR-016: Frontend-Only Home Center Comparison

**Date:** 2026-03-08
**Status:** Accepted

**Context:** Phase 3 M1 adds "Home Center" relocation comparison (FR-8). Patients select their current transplant listing center and see how other cities compare. The backend already simulates all 22 cities in every request, returning ranked probabilities for all of them.

**Decision:** All comparison logic (delta computation, badge rendering, map differentiation, CDF reference line) is computed entirely in the frontend JavaScript. The backend only receives `home_center` as an optional pass-through field on `PatientProfile` — it does not alter simulation behavior.

**Rationale:**
- Zero backend changes needed beyond the schema field — the simulation already returns all 22 cities.
- Delta math is trivial: `otherCity.score - homeCenter.score` or `otherCity.p_transplant_24mo - homeCenter.p_transplant_24mo`.
- Graceful degradation: when no home center is selected, all comparison UI is guarded by `if (homeCenter)` checks — zero visual changes.
- Keeps backend focused on simulation; presentation logic stays in the frontend.

**Trade-offs:**
- If the backend ever needs to optimize (e.g., only simulate a subset of cities), the comparison logic would need to ensure the home center city is always included.
- "Home Center" terminology chosen over "Current City" because patients often live hours from their listing center.

---

## ADR-017: Organ-Specific Donor Availability via Cause-of-Death Multiplier

**Date:** 2026-03-08
**Status:** Accepted

**Context:** `calculateDonorAvailabilityScore()` in `algorithm.js` ignores the `organType` parameter — a kidney patient and a heart patient get identical donor availability scores for the same city. In reality, organ recovery rates vary 3–5× by cause of death (PMC10329409 Table 2). States with many trauma deaths are better for hearts (48.8% recovery) than ones dominated by cardiovascular deaths (15.1%), while kidneys are relatively insensitive (89.6% vs 68.6%).

**Decision:** Implement a **normalized multiplier** centered at 1.0 that adjusts the existing 0–100 donor availability score based on regional cause-of-death patterns × organ-specific recovery rates.

```
organScore(state, organ) = Σ stateProportions[cause] × recoveryRates[organ][cause]
nationalAvg(organ) = mean(organScore(s, organ)) for all states
multiplier = organScore(state, organ) / nationalAvg(organ)
adjustedScore = baseScore × multiplier   (clamped 0–100)
```

The multiplier is **toggleable** (default OFF) via a checkbox in the Simulation Settings fieldset. Both frontend (Phase 1 scoring) and backend (Monte Carlo wait times) apply the same multiplier when enabled.

**Rationale:**
- **Normalized to national average** → multiplier centered at 1.0, preserving existing scores as baseline rather than systematically inflating/deflating.
- **Default OFF** → preserves backward compatibility; existing test results unchanged unless user opts in.
- **Same math frontend and backend** → consistent behavior whether patient uses Phase 1 scores or Phase 2 probabilities.
- **Four cause-of-death categories** (trauma, cardiovascular, drug intoxication, stroke) map well to CDC WONDER ICD-10 codes and PMC10329409 recovery rate data.

**Expected multiplier ranges:**
- Kidney: ~0.97–1.03 (tight — kidneys recovered at high rates from all causes)
- Liver: ~0.98–1.02 (also tight)
- Heart: ~0.92–1.08 (moderate — trauma vs cardiovascular gap is wide)
- Pancreas: ~0.85–1.20 (widest — 0.246 trauma vs 0.048 cardiovascular)

**Trade-offs:**
- State-level granularity misses intra-state variation (e.g., rural vs urban within Texas).
- Intestine uses pancreas rates as proxy — PMC10329409 has no intestine-specific data.
- Seed data is manually curated from CDC WONDER; FIXME for automated fetch script.
- Backend divides Monte Carlo wait times by multiplier (more donors → shorter waits), which is a simplification of the true supply-demand dynamics.

## ADR-018: City Detail Modal & Side-by-Side Comparison UI

**Date:** 2026-03-08
**Status:** Accepted

**Context:** City cards in the results list show summary data (overall score, wait time, donor availability, compatibility index, quality tier). Users need to see the full 8-category score breakdown, Phase 2 simulation probabilities, competing risks, and key factors — all in one view. Users also need to compare 2–3 cities side by side across all metrics.

**Decision:** Implement three features using the existing modal overlay pattern:
1. **City Detail Modal** — click any card to see full score breakdown table (8 categories with raw scores, weights, weighted contributions, and inline bar charts), key factors, radar chart, Phase 2 probabilities grid, and competing risks bar.
2. **Side-by-Side Comparison** — checkboxes on cards (max 3) with a floating compare bar; comparison opens a wider modal with all metrics aligned in a table, best values highlighted green per row.
3. **Print-Friendly View** — `@media print` rules hide form/map/modals and show both score and probability panels; disclaimer footer auto-appended.

**Architecture:**
- **Modal overlay** (same z-index 9000 / backdrop pattern as simulation spinner) — no router needed in vanilla JS, preserves scroll position.
- **Module-scope result storage** (`_currentResults`, `_currentSimResult`, `_currentFormData`) — modals read from stored results, no new data fetching.
- **Compare checkboxes** use `stopPropagation` on the label to prevent card click (modal) from triggering on checkbox click.
- **3-city comparison limit** keeps the table readable; unchecked boxes disabled when 3 already selected.
- **ESC key + backdrop click** to close both modals; body overflow locked while modal is open.

**Rationale:**
- **Modal over accordion** — accordion would clutter the 22-card list; modal shows full detail without losing scroll context.
- **Modal over routing** — no router in the stack; adding one for a detail view would be over-engineering.
- **Reuse existing chart functions** — `createRadarChart()` renders inside modal canvas; `buildRiskBar()` pattern reused for competing risks display.
- **No new dependencies** — pure vanilla JS/CSS, consistent with project stack.
- **Print view shows both panels** — physicians may want to see both Phase 1 scores and Phase 2 probabilities in one printout.

**Trade-offs:**
- Modal approach means only one city detail visible at a time (comparison table mitigates this).
- Radar chart inside modal requires creating and destroying Chart.js instances on open/close to avoid memory leaks.
- Compare checkboxes duplicate across score and probability panels (synced via `data-city` attribute matching).
- Print layout is basic — no custom page breaks or headers/footers beyond the disclaimer.

---

## ADR-019: Equity Analysis — Demographic Simulation Matrix

**Date:** 2026-03-09
**Status:** Accepted

**Context:** Users need to understand how transplant outcomes differ across demographic profiles. The Monte Carlo engine runs a single simulation for one patient's profile, but transplant disparities are well-documented across blood types, age groups, and sex. We need a structured way to surface these model-predicted disparities without overstepping what the model can actually claim.

**Decision:** Implement a demographic stratification matrix that varies blood type (8), age bracket (3), and sex (2) = 48 profiles across all 22 cities, computing Gini coefficient as an inequality metric. Key design choices:

1. **No race/ethnicity simulation** — Race is a social construct; transplant disparities attributed to race are driven by structural factors (insurance, referral patterns, geographic access, implicit bias) that our model cannot capture. We simulate the clinical drivers (blood type, age, sex) that correlate with documented disparities without conflating correlation with causation.

2. **No insurance stratification** — The `insurance` field exists on `PatientProfile` but is unused by the Monte Carlo engine. Including it would produce zero variation and mislead users into thinking insurance impact was being modeled.

3. **Gini coefficient over Theil index** — Gini is simpler, more widely understood, and sufficient for MVP. The [0,1] range maps naturally to green/yellow/red UI feedback. Theil decomposition added to future work.

4. **Fixed seed RNG** (`np.random.default_rng(42)`) — Reproducibility across the 48×22×300 = 316,800 simulation runs.

5. **Mandatory disclaimers** — Every equity response includes 4 hardcoded limitation statements covering: race/ethnicity exclusion, mortality stratification gap, insurance modeling gap, and model-vs-reality distinction.

**Architecture:**
- `backend/services/equity.py` — Generates 48 profile variants via `model_copy(update={...})`, reuses `_p24_single_city()` from sensitivity.py for efficiency.
- `backend/routers/equity.py` — `POST /equity-analysis` with configurable iterations (100-1000, default 300).
- Frontend: Third tab "Equity Analysis" with disclaimer banner, summary card (overall Gini badge), city equity rankings table (sorted by Gini ascending), and 3 Chart.js charts (blood type disparity, age bracket disparity, Gini by city).
- `equity-charts.js` — IIFE module following `probability-charts.js` pattern.
- Tab switching extended from 2 to 3 tabs via `initResultsTabs(simAvail, equityAvail)`.

**Rationale:**
- **48-profile matrix** balances computational cost (~1-5s) with meaningful stratification depth.
- **Per-city Gini** allows users to see which regions show more equitable model outcomes.
- **Dimension disparity charts** (blood type, age) show which factors drive the most variation.
- **Reuse of `_p24_single_city()`** avoids code duplication and ensures consistency with sensitivity analysis.

**Trade-offs:**
- Equity analysis is sequential (not parallelized) — acceptable for MVP but could be optimized with multiprocessing.
- Age brackets use representative ages (26, 45, 62) which are approximations of continuous age effects.
- Gini is computed from p24 values only; could also weight by median wait time for a more holistic metric.
- Charts show averages across all cities; per-city drill-down charts deferred to future work.

---

## ADR-020: What-If Scenario Analysis with Paired Seeds

**Date:** 2026-03-10
**Status:** Accepted

**Context:** Phase 3 M5 added what-if scenario sliders (donor rate ±20%, wait time ±30%). The naive approach — run two independent simulations and compare — produces noisy deltas because Monte Carlo variance swamps the signal from small multiplier changes.

**Decision:** Use paired seeds: baseline and adjusted scenarios share the same RNG seed per iteration. The same "patient" draws the same random events in both runs; only the multiplier-adjusted parameters differ. This isolates the effect of the scenario change from Monte Carlo noise.

**Rationale:** Paired seeds reduce delta noise by ~10× compared to independent runs. A 5% donor increase that changes p24 by 1.2 percentage points would be lost in ±3% Monte Carlo noise without pairing.

---

## ADR-021: Phase 4 Scope — Advanced Modeling & Validation

**Date:** 2026-03-16
**Status:** Accepted

**Context:** The roadmap's Phase 4 ("Advanced Modeling & Clinical Validation") originally listed ~15 features spanning software engineering, academic research, regulatory consulting, and clinical partnerships. This is ~1500+ hours of work — unrealistic as a single development phase. We need to scope Phase 4 to what's buildable on the existing infrastructure while directly supporting the publication goal.

**Decision:** Phase 4 is scoped to 5 milestones focused on **deepening clinical accuracy** and **enabling publication-grade validation**:

| # | Milestone | Scope |
|---|-----------|-------|
| M1 | Configurable Scoring Weights | Weight sliders (research mode), presets, backend re-simulation with custom weights |
| M2 | Post-Transplant Outcomes Model | SRTR Table B11 graft survival data, compound success metric (P(transplant) × P(graft survival)) |
| M3 | Historical Trends & Center Trajectories | Multi-year SRTR data, trajectory analysis, sparkline charts, trending badges |
| M4 | Policy Scenario Engine | Predefined UNOS policy scenarios with literature-backed parameters, upgraded what-if |
| M5 | Validation & Reproducibility Pack | Retrospective validation, bias audit, Jupyter notebooks, publication-ready artifacts |

**Deferred to Phase 5+:**
- Public REST API with tiered access (FR-18) — no public deployment yet
- Python & JavaScript SDKs — premature without public API
- Policy scenario builder (interactive UI) — builds on M4 but requires M4 to stabilize first
- Institutional bulk analysis & cohort tools — requires deployed API
- Embeddable widget / white-label integration — premature
- Bayesian belief networks / agent-based simulation — academic research features
- Insurance compatibility layer — no data source available
- RCT design, FDA pathway — require external partnerships and funding

**Rationale:**
- **M1 (Weights)** enables ablation studies — essential for any publication. "What happens if we remove category X?" is a standard validation question. Also the highest-demand user feature (researchers want to explore weight sensitivity).
- **M2 (Outcomes)** transforms the tool from "where to get a transplant fastest" to "where to get AND keep a transplant" — a genuine clinical contribution. SRTR PSR Table B11 data is parseable using the proven M5 pipeline pattern.
- **M3 (Trends)** adds temporal validity — "is this center improving or declining?" is critical context that no existing tool provides. Multi-year SRTR PSR downloads are feasible with the existing fetch infrastructure.
- **M4 (Policy)** is the hardest but most novel feature. Upgrades the Phase 3 what-if sliders from raw multipliers to real UNOS policy scenarios with literature-backed elasticities. Requires research before coding.
- **M5 (Validation)** is the capstone — retrospective validation against SRTR cohorts, demographic bias audits, and reproducible Jupyter notebooks. This is what makes the model publishable.

**Dependencies:**
```
M1 (Weights) ─── independent, start immediately
M2 (Outcomes) ── extends SRTR pipeline (fetch-srtr-excel.py)
M3 (Trends) ──── extends SRTR pipeline (multi-year downloads)
M4 (Policy) ──── requires literature review before coding
M5 (Validation) ─ runs after M1-M4 stabilize
```

M1 is fully independent. M2 and M3 share SRTR pipeline work and can be parallelized. M4 needs upfront research. M5 is the final integration milestone.

**Ordering rationale:**
- M1 first because it's the simplest, unblocks ablation studies, and demonstrates immediate user value.
- M2 before M3 because outcomes data is clinically more important than trends.
- M4 after M2/M3 because it needs literature review time (can happen while M2/M3 are coded).
- M5 last because it validates everything built in M1-M4.

**What this means for existing GitHub issues:**
- #22 (Configurable weights) → updated as M1
- #23 (Causal policy simulator) → updated as M4
- #24 (Public REST API) → deferred to Phase 5
- #25 (SDKs) → deferred to Phase 5
- #26 (Policy scenario builder) → deferred to Phase 5
- #27 (Bulk analysis) → deferred to Phase 5
- #28 (Embeddable widget) → deferred to Phase 5

---

## ADR-022: Historical Trends via Multi-Year SRTR PSR Releases

**Date:** 2026-03-17
**Status:** Accepted

**Context:** Phase 4 M3 adds "Historical Trends & Center Trajectories" — answering "Is Cleveland getting better or worse for kidney transplants?" Centers change over time, and temporal context is critical for patient decision-making. No existing patient-facing tool provides this.

**Decision:** Use archived SRTR PSR releases (one per year, 2019–2025) to build center-level time series. One release per year (January releases preferred) for 7 data points. Each release parsed for Table B10 (wait times), Table B7 (volumes/outcomes), and C-series (survival).

**Technical approach:**
- `fetch-srtr-excel.py --historical` downloads archived zip bundles from SRTR's archive URL pattern (`csrs_tables_all/csrs_final_tables_{YYMM}.zip`)
- `parse-srtr-reports.py` extended with `parse_historical_trends()` producing `data/srtr-historical.json`
- New `services/trends.py`: `scipy.stats.linregress` on each metric, p < 0.10 significance threshold, direction classification (improving/stable/declining)
- Trends attached to `/simulate` response (same pattern as M2 outcomes), plus dedicated `GET /trends/{city}/{organ}` endpoint
- Frontend: trend badges on probability cards, sparkline charts in city detail modal (Chart.js), trend column in comparison table and exports

**Trend classification logic:**
- Wait time: negative slope = improving (shorter waits)
- Volume: positive slope = improving (more transplants)
- Survival: positive slope = improving (better outcomes)
- Mortality/delisting: negative slope = improving (fewer adverse events)
- "Stable" if p > 0.10 or |slope| below minimum annual change threshold
- Overall direction: weighted vote (wait time ×3, volume ×2, survival ×2, mortality ×1)
- Minimum 3 data points for any regression; fewer → "insufficient_data"

**Seed data strategy:** Deterministic generator script produces realistic 7-year time series from SRTR-calibrated baselines with city profiles (improving/stable/declining), COVID dip modeling, and null values for smaller programs. Replaced when actual historical downloads are run.

**Rationale:**
- Leverages existing SRTR pipeline (proven in M2/M5) — low marginal effort
- One release per year avoids redundant overlapping cohorts
- Linear regression is simple, interpretable, and appropriate for 5-7 data points
- p-value threshold of 0.10 (rather than 0.05) is appropriate for the small sample size and exploratory nature

**Consequences:**
- Historical data requires ~2 GB of Excel files (gitignored in `data/srtr-raw/historical/`)
- Seed data is placeholder until actual downloads complete
- Older releases (pre-2019) may have different Excel formats; the parser handles this gracefully with try/except
- Trend direction can change when new SRTR releases become available (by design)
- New: M2 (Post-Transplant Outcomes), M3 (Historical Trends), M5 (Validation Pack)

---

## ADR-023: Policy Scenario Engine with Literature-Backed Parameters

**Date:** 2026-03-17
**Status:** Accepted

**Context:** Phase 3 M5 introduced what-if sliders with raw multipliers (donor availability, wait time). While useful for exploration, raw multipliers lack clinical grounding — users don't know what "1.2× donor rate" means in real-world terms. Phase 4 M4 upgrades this to predefined UNOS policy scenarios with literature-backed parameters.

**Decision:** Implement a `PolicyScenario` system that maps real transplant policy changes to concrete per-city model parameter adjustments:

1. **2021 Kidney 250nm Circles** — OPTN's shift from DSA-based to 250nm circle allocation. Small centers get +20% donor access, large centers get -4%. Based on King et al., AJT 2023.
2. **Continuous Distribution** — OPTN's points-based allocation that de-emphasizes geography. Stronger effect than 250nm: +30% for small, -8% for large. Based on OPTN framework documents.
3. **Increased DCD Utilization** — +15% organ supply from expanded DCD protocols. Uniform geographically. Based on Croome et al., Transplantation 2020.
4. **Broader HCV+ Acceptance** — +6% donor pool for kidney/liver via DAA treatment. Based on Reese et al., NEJM 2023.

**Key design choices:**
- **Per-city overrides**: Scenarios 1-2 have different multipliers per city based on center size classification (large/medium/small). This is the key upgrade over raw multipliers.
- **Organ applicability**: Each scenario specifies which organs it applies to. The endpoint returns 400 for mismatched organs.
- **Backward compatible**: Existing `POST /what-if` is unchanged. New `POST /policy-scenario` and `GET /policy-scenarios` endpoints added.
- **Literature references and caveats**: Every scenario includes published references and explicit caveats (limitations of the model, assumptions, etc.).

**Files:** `backend/services/policy_scenarios.py`, `backend/routers/what_if.py` (extended), `api-client.js`, `script.js`, `simulator.html`, `styles.css`

**Consequences:**
- 4 predefined scenarios with 24 tests
- Frontend shows scenario selector with description, references, and caveats — full transparency
- Per-city multipliers make the results more meaningful than raw slider adjustments
- Adding new scenarios is simple: call `_register(PolicyScenario(...))` in policy_scenarios.py
- Phase 5 can build a custom scenario builder UI on top of this foundation

---

## ADR-024: Bayesian Belief Network as Alternative Inference Engine

**Date:** 2026-03-17
**Status:** Accepted

**Context:** The existing Monte Carlo engine treats all factors as multiplicatively independent: blood type multiplier × city factor × urgency multiplier × COD multiplier. This misses important interactions: the effect of blood type on wait time depends on regional donor supply (O- in a low-O-donor region is superlinearly disadvantaged), age-organ mortality interactions vary (heart mortality is far more age-sensitive than kidney), and high-wait cities tend to have correlated high delisting rates. A Bayesian Belief Network can model these causal dependencies as a directed acyclic graph with conditional probability tables.

**Decision:** Add a BBN as a **toggle mode** alongside Monte Carlo, not a replacement.

1. **12-node DAG**: 5 evidence nodes (Organ, BloodType, AgeGroup, Urgency, Region), 3 latent nodes (DonorSupply, WaitCategory, MortalityRisk), 2 outcome nodes (DelistingRisk, CompetingOutcome), 2 post-transplant nodes (GraftSurvival1yr, CompoundSuccess).
2. **CPTs derived from existing data**: The parameterizer reads the same JSON files (wait-time-distributions, competing-risks, cause-of-death-by-region, post-transplant-outcomes) through the same `data_loader.py`. No data duplication. One new parameter added: age-mortality multipliers from SRTR literature.
3. **Exact inference via Variable Elimination**: The small DAG (12 nodes, max 8 states) allows exact inference in microseconds. Full 22-city inference in < 100ms (vs ~1s for MC).
4. **Same output schema**: `simulate_bbn()` returns `SimulationResult` — identical to Monte Carlo. Frontend rendering code works unchanged.
5. **Single endpoint dispatch**: `POST /simulate?inference_mode=bayesian` routes to BBN; default remains Monte Carlo. Feature flag `BBN_ENABLED` for graceful degradation.

**Key interactions captured:**
- `DonorSupply` as mediator between (Organ, BloodType, Region) and WaitCategory — blood type effect varies by regional supply
- `MortalityRisk` conditional on (AgeGroup × Organ) — age-dependent mortality per organ type
- `DelistingRisk` conditional on WaitCategory — correlated with wait duration, not independent
- `CompetingOutcome` jointly conditioned on WaitCategory + MortalityRisk + DelistingRisk — captures correlations

**Validation approach:** Cross-validate BBN vs Monte Carlo. Acceptance: Spearman rank correlation > 0.7 for city rankings, all directional effects preserved. Exact numerical match not required — divergence from interaction effects is expected and correct.

**Files:** `backend/services/bayesian_network.py`, `backend/services/bbn_parameterizer.py`, `backend/routers/simulate.py` (modified), `backend/models/schemas.py` (modified), `simulator.html`, `api-client.js`

**Consequences:**
- Users can compare two inference approaches for the same patient profile
- BBN surfaces interaction effects invisible to the Monte Carlo
- Performance: BBN is 10-50× faster than MC, enabling real-time exploration
- Maintenance: both engines read from the same data layer, but CPT logic must be updated when new variables are added
- Future: BBN can be extended with learned parameters if patient-level data becomes available

---

## ADR-025: Clayton Copula for Correlated Competing Risks

**Date:** 2026-03-18
**Status:** Accepted

**Context:** The Monte Carlo engine draws mortality and delisting times as independent exponentials (lines 220-232 of `monte_carlo.py`). In reality, a patient whose health deteriorates faces both higher mortality AND higher delisting risk simultaneously — these events exhibit positive lower-tail dependence. The independence assumption underestimates the probability that both bad outcomes cluster together, leading to overly optimistic transplant probability estimates for high-risk patients.

**Decision:** Introduce a Clayton copula to model correlated mortality-delisting draws, available as an opt-in toggle (`use_copula: true` on PatientProfile).

1. **Clayton copula**: Chosen specifically for its asymmetric dependence structure — strong positive dependence in the lower tail (both events happen sooner when health deteriorates), weaker upper tail. This matches the clinical reality: declining health simultaneously accelerates mortality and delisting, but being very healthy doesn't equally decouple the events.
2. **Conditional sampling method** (Nelsen, 2006 §4.2): Draw `u1, t ~ Uniform(0,1)`, compute `u2 = (u1^(-θ) · (t^(-θ/(θ+1)) - 1) + 1)^(-1/θ)`. Map through exponential inverse CDF to get correlated event times. Preserves marginal exponential distributions exactly.
3. **Default θ = 1.0**: Kendall's τ ≈ 0.33 (moderate positive dependence). Conservative choice supported by SRTR registry analyses. Configurable via `config.py::COPULA_THETA`.
4. **Opt-in via `use_copula` flag**: Default `False` preserves backward compatibility. All three simulation paths (monte_carlo, what_if, sensitivity) support the toggle.

**Alternatives considered:**
- **Gaussian copula**: Symmetric tail dependence — doesn't match clinical asymmetry. Rejected.
- **Frank copula**: No tail dependence at all — events become independent in extremes. Rejected.
- **Gumbel copula**: Upper-tail dependence (opposite of what we need). Rejected.
- **Full joint survival model**: Requires patient-level data we don't have. Deferred to Phase 5 M3 (MCMC).

**Files:** `backend/services/copula.py` (new), `backend/config.py`, `backend/models/schemas.py`, `backend/services/monte_carlo.py`, `backend/services/what_if.py`, `backend/services/sensitivity.py`, `backend/tests/test_copula.py` (new, 22 tests)

**Consequences:**
- With copula enabled, mortality and delisting times are positively correlated: patients in decline face clustered adverse events
- Transplant probabilities for high-acuity patients decrease slightly (more realistic)
- Marginal distributions unchanged — mean mortality/delisting rates are preserved
- Statistical validation: empirical Kendall's τ matches θ/(θ+2) within 0.03 tolerance across θ ∈ {0.5, 1, 2, 5}
- Future: θ can be calibrated from patient-level competing risks data when available

---

## ADR-026: PyMC MCMC Hierarchical Survival Model

**Date:** 2026-03-18
**Status:** Accepted

**Context:** The Monte Carlo engine and Bayesian Belief Network both treat model parameters as known constants — `national_median_months = 27.4` for kidney, `city_wait_time_factor["Portland"] = 0.73`, etc. In reality, these are noisy estimates from SRTR data with finite sample sizes. A city with 30 heart transplants per year has much more parameter uncertainty than one with 300. The BBN's "confidence intervals" are a fixed ±5% band, not data-derived. We need honest uncertainty quantification.

**Decision:** Add a PyMC-based MCMC hierarchical survival model as a third inference engine (`inference_mode=mcmc`).

1. **Hierarchical structure**: Three levels — national hyperpriors, city random effects, patient-level covariates (blood type, urgency). Each level has learned variance parameters that control partial pooling.
2. **Observation model**: Treats existing SRTR-derived point estimates (city wait factors, mortality factors, blood type multipliers) as noisy observations of true underlying parameters. Observation noise is learned.
3. **Offline fitting + trace caching**: NUTS sampler runs offline (2-30 min per organ) and saves posterior traces as ArviZ NetCDF files. At query time, parameters are sampled from the cached trace (~50-200ms).
4. **One model per organ**: 6 independent models, each with ~92 free parameters. Total ~552 parameters across all organs.
5. **Forward simulation**: For each posterior draw, constructs log-normal wait time distributions and exponential competing risk distributions, then runs the same outcome determination logic as standard Monte Carlo. Credible intervals reflect both sampling noise and parameter uncertainty.

**Architecture:**
- `mcmc_survival.py`: Model specification (`build_organ_model`), fitting (`fit_organ_model`), trace I/O
- `mcmc_inference.py`: Query-time simulation using cached traces (`simulate_mcmc`)
- `scripts/fit-mcmc-model.py`: CLI for offline fitting (per-organ or all, configurable draws/chains)
- `data/mcmc-traces/*.nc`: Cached ArviZ traces (gitignored, ~10-50MB each)

**Alternatives considered:**
- **Stan/CmdStan**: More mature sampler but harder Python integration. PyMC has native NumPy arrays.
- **Variational inference (ADVI)**: Faster fitting but biased posteriors. NUTS preferred for accuracy.
- **Patient-level survival model**: Requires individual patient data from SRTR research files. We use aggregate center-level statistics. Deferred pending data access.

**Files:** `backend/services/mcmc_survival.py` (new), `backend/services/mcmc_inference.py` (new), `scripts/fit-mcmc-model.py` (new), `backend/routers/simulate.py`, `backend/models/schemas.py`, `backend/config.py`, `backend/tests/test_mcmc_survival.py` (new, 38 tests), `backend/tests/test_mcmc_inference.py` (new, 15 tests)

**Consequences:**
- MCMC confidence intervals are wider than Monte Carlo (reflect parameter uncertainty, not just sampling)
- Cities with sparse data shrink toward national mean (appropriate hierarchical regularization)
- Requires offline fitting before first use (`scripts/fit-mcmc-model.py`)
- PyMC adds ~350MB to the Python environment
- Trace files are per-organ, gitignored, regenerated when SRTR data updates

---

## ADR-027: Shared Frailty via LKJ-Cholesky Correlated City Offsets

**Date:** 2026-03-18
**Status:** Accepted
**Deciders:** Development team
**Relates to:** ADR-025 (Clayton copula), ADR-026 (MCMC hierarchical model), L-059, #96

### Context

The Phase 5 M3 MCMC model fitted city-level mortality and delisting offsets independently (`city_mort_offset` and `city_delist_offset` as separate Normal random effects). The Phase 5 M2 Clayton copula coupled these at query time with a fixed θ=1.0. This meant the MCMC model didn't learn the correlation structure from data — it relied on an externally imposed dependence parameter.

### Decision

Replace the two independent city offset priors with a bivariate MvNormal using an LKJ-Cholesky correlation prior (`pm.LKJCholeskyCov`, η=2). The model now learns the mortality ↔ delisting correlation from the observed city-level data. Wait-time offsets remain independent (supply-side, different causal pathway).

Additionally, replaced bootstrap CIs in MCMC inference with posterior-predictive credible intervals (percentiles across per-draw p24 values), producing proper Bayesian credible intervals.

### Alternatives Considered

1. **Keep independent offsets + external copula**: Simpler but the copula θ is arbitrary and uniform across organs. The MCMC model wouldn't be learning anything the MC engine couldn't.
2. **Full 3×3 MvNormal (wait + mort + delist)**: Wait times are supply-driven (different causal mechanism from mortality/delisting which are demand/patient-health-driven). A 3×3 covariance matrix would be harder to estimate with 22 cities and would conflate unrelated variation.
3. **Shared gamma frailty**: Classical approach in survival analysis. Less flexible than LKJ — assumes positive correlation only and specific distributional form.

### Consequences

- MCMC model now learns organ-specific mortality ↔ delisting correlation (partially addresses L-059)
- External copula becomes redundant for MCMC mode (auto-detected via `mort_delist_corr` in trace)
- Clayton copula remains active for standard MC and BBN engines
- LKJ η=2 prior weakly regularizes toward zero correlation — the data drives the posterior
- 11 new tests (7 survival + 4 inference), total MCMC tests: 64

**Files:** `backend/services/mcmc_survival.py` (model restructured), `backend/services/mcmc_inference.py` (Bayesian HDI + shared frailty detection)
