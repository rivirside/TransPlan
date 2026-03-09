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
