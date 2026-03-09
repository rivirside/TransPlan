# TransPlan - Known Limitations & Issue Tracker

> **Grep-searchable.** Read when auditing data quality, algorithm accuracy, or planning fixes. Update when discovering new issues or resolving existing ones.

## How This File Works

Each limitation has a severity, status, and category. When we fix one, change status to `FIXED` and add a note about which commit/session resolved it. When we discover new ones, append to the relevant section.

**Severities:**
- `CRITICAL` — Could mislead patients, produce wrong results, or break functionality
- `HIGH` — Significant quality gap but won't cause harm in current form
- `MEDIUM` — Should fix eventually, doesn't affect core results
- `LOW` — Nice to have, minor polish

**Statuses:** `OPEN` | `IN PROGRESS` | `FIXED` | `WONT FIX` (with rationale)

---

## 1. Medical Accuracy

### L-001: No PRA/cPRA (Panel Reactive Antibody) input
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** PRA is arguably the single most important individual factor in kidney transplant wait time and compatibility. A patient with cPRA of 95% (sensitized) may wait 10+ years regardless of city. A patient with cPRA of 0% may wait 2-3 years. The algorithm has no field for this and treats all patients as if they have zero sensitization.
- **Impact:** Kidney wait time estimates are meaningless for sensitized patients.
- **Fix complexity:** Medium — add cPRA slider to form, multiply wait time factor by sensitization penalty.

### L-002: No MELD score for liver allocation
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** Liver allocation in the US is MELD-based — sicker patients go first regardless of wait time. A patient with MELD 35 gets a liver in weeks anywhere. MELD 15 may wait years in competitive regions. Our single urgency 1-4 scale doesn't model this.
- **Impact:** Liver wait time and ranking accuracy is poor.
- **Fix complexity:** Medium — add conditional MELD input when organ=liver, replace urgency factor with MELD-based scoring.

### L-003: No LAS (Lung Allocation Score) for lungs
- **Severity:** HIGH
- **Status:** FIXED
- **Details:** Lung allocation uses the Lung Allocation Score, a composite of medical urgency and expected benefit. Our urgency 1-4 scale doesn't capture this.
- **Fix complexity:** Medium — similar approach to L-002.

### L-004: Status 1 relocation advice is clinically inapplicable
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** A Status 1A heart patient has days to weeks to live. Recommending relocation to another city is not actionable and could cause distress or harmful action. The tool has no logic to detect when urgency makes relocation advice unreasonable.
- **Fix complexity:** Low — add a warning banner when Status 1 is selected: "Status 1 patients are typically too urgent for relocation. These results are informational only."

### L-005: Sex penalty is oversimplified
- **Severity:** HIGH
- **Status:** FIXED
- **Details:** `algorithm.js` line 195 assigns a flat 5% penalty to all females across all organ types. True for heart/lung (body size matching matters), not meaningful for kidney/liver/pancreas. Stated in methodology as fact without nuance.
- **File:** `algorithm.js` line 195
- **Fix complexity:** Low — make sex modifier organ-specific (only apply to heart/lung).

### L-006: Insurance field is collected but completely ignored
- **Severity:** HIGH
- **Status:** FIXED
- **Details:** `insuranceAcceptanceRates` is defined in `algorithm.js` (lines 86-95) but never used in any scoring function. The form collects `formData.insurance` but it's a dead field. A Medicaid patient and privately insured patient get identical scores.
- **File:** `algorithm.js` lines 86-95, `index.html` lines 91-98
- **Fix complexity:** Medium — incorporate insurance rates into hospital quality score or add insurance-specific scoring.

### L-007: "Match Probability" metric is fabricated
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** `script.js` displays a "Match Probability" (e.g., "74%") calculated as `Math.round(60 + (medScore + donorScore) / 200 * 35)`. This has zero clinical basis. Real match probability requires HLA typing, crossmatch, and cPRA. Displaying a made-up percentage to transplant patients as "match probability" is misleading.
- **File:** `script.js` `deriveDisplayMetrics()` function
- **Options:** (a) Remove the metric entirely, (b) Rename to something honest like "Relative Compatibility Index" with a note that it's a composite of algorithm scores not a clinical prediction, (c) Add tooltip explaining it's derived from algorithm scores.

### L-008: Traffic fatalities as donor proxy is scientifically outdated
- **Severity:** HIGH
- **Status:** FIXED
- **Details:** Only ~20-25% of modern deceased donors died in motor vehicle accidents. Most come from brain death due to strokes, overdoses, and cardiac events. Traffic fatality rates are a poor proxy for total deceased donor availability. The algorithm uses them as 15% of donor availability scoring.
- **File:** `algorithm.js` `calculateDonorAvailabilityScore`, `script.js` traffic heatmap
- **Fix complexity:** Medium — reduce weight or replace with OPO-level donor recovery statistics.

### L-009: OPO (Organ Procurement Organization) boundaries are ignored
- **Severity:** HIGH
- **Status:** DEFERRED
- **Details:** Pittsburgh and Philadelphia are both in Pennsylvania but served by different OPOs (CORE and Gift of Life) with meaningfully different operations. The algorithm uses state-level donor registration rates, treating all cities in a state as equivalent. OPO quality is one of the most cited factors in real transplant outcomes.
- **Fix complexity:** High — requires mapping cities to OPOs and sourcing OPO-level performance data.

---

## 2. Data Quality

### L-010: Transplant volumes are estimated, not real SRTR data
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** `data/manual/srtr-reports.json` claims source as "SRTR Biannual Reports (manually curated)" but contains round-number estimates that were never fetched from SRTR. Intestinal transplant volumes are especially suspect (e.g., Portland: 5, when fewer than 300 total are done in the US annually).
- **File:** `data/manual/srtr-reports.json`, `algorithm.js` `centerVolumes`
- **Fix complexity:** Medium — manually look up real volumes from SRTR program-specific reports at srtr.org.

### L-011: Florida donor registration rate is wrong
- **Severity:** HIGH
- **Status:** FIXED
- **Details:** Listed at 26% in `data/donor-registration.json`. Florida implemented broad DMV-based registration and actual rates are ~70%+. Off by a factor of 2-3x.
- **File:** `data/donor-registration.json`, `algorithm.js` line 268
- **Fix complexity:** Low — update the value.

### L-012: Health demographics are state-level data labeled as city data
- **Severity:** MEDIUM
- **Status:** WONT FIX
- **Details:** `regionalHealthData` lists per-city values but Dallas (11.9%) and Houston (12.5%) show different diabetes rates despite both being Texas cities. These are clearly fabricated city-level numbers derived loosely from state averages.
- **File:** `algorithm.js` lines 20-50
- **Fix complexity:** High — would need county-level CDC data (PLACES dataset) for real city-level estimates.

### L-013: CDC fetch script only gets diabetes, will cause NaN cascade
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** `fetch-health-data.js` only fetches `diabetesRate`. When loaded, `calculateHealthDemographicsScore` reads `health.obesityRate`, `health.ckdRate`, etc. — all `undefined`. Subtraction from undefined produces NaN, which propagates through the entire weighted score, turning all results to NaN.
- **File:** `scripts/fetch-health-data.js`, `algorithm.js` lines 384-398
- **Fix complexity:** Medium — either fetch all 5 indicators from CDC BRFSS/PLACES, or add null-safety guards in the scoring function.

### L-014: Cost of living data is stale and some cities are estimated from others
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** The BLS fetch script covers only 15 of 22 cities. The other 7 (Madison, Rochester, Durham, Nashville, Omaha, Indianapolis, Palo Alto) are estimated via fixed ratios from nearby cities. Nashville estimated from Baltimore * 1.07 is particularly wrong given Nashville's post-2020 cost surge.
- **File:** `scripts/fetch-cost-of-living.js` lines 93-100

### L-015: Air quality scores conflate measurements
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** Hardcoded air quality values treat AQ as a 0-100 score (higher = better) but the EPA AQI is the opposite (lower = better). The fetch script subtracts raw ozone ppb from 100, which isn't a standard AQI conversion. Also ignores PM2.5.
- **File:** `scripts/fetch-air-quality.js` line 84, `algorithm.js` lines 22-50

### L-016: FARS traffic normalization is broken
- **Severity:** HIGH
- **Status:** FIXED
- **Details:** `fetch-traffic.js` divides total state fatalities by 500 and caps at 2.0. All large states (CA, TX, FL) cap at the same value, making the data useless for distinguishing them. Also misreads the API response — uses `.length` of first results array instead of parsing individual fatality records.
- **File:** `scripts/fetch-traffic.js` lines 34-35

### L-017: Hospital quality fetch gets general CMS ratings, not transplant data
- **Severity:** HIGH
- **Status:** DEFERRED
- **Details:** `fetch-hospital-quality.js` fetches CMS overall hospital star ratings (1-5 stars), which measure general hospital quality (patient experience, mortality across all conditions). A hospital can have 5 stars overall with a mediocre transplant program and vice versa.
- **File:** `scripts/fetch-hospital-quality.js`

---

## 3. Ethical & Legal

### L-018: Disclaimer is inadequate
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** One sentence in the footer for a tool that says "personalized transplant success probability." Given target audience (patients facing life-threatening conditions), this needs a prominent, specific disclaimer about what the tool cannot account for.
- **File:** `index.html` line 384
- **Fix complexity:** Low — expand disclaimer, add prominent callout box at top of results.

### L-019: "Transplant success probability" language is misleading
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** The methodology section says the algorithm "calculates your personalized transplant success probability for each city." Real transplant success probability requires HLA typing, crossmatch, cPRA, disease etiology, comorbidities, and functional status — none of which are in the tool.
- **File:** `index.html` line 110
- **Fix complexity:** Low — change language to "location suitability score" or "city compatibility score."

### L-020: Traffic fatality framing is insensitive
- **Severity:** HIGH
- **Status:** FIXED
- **Details:** The traffic heatmap popup says "Higher fatality areas may have increased deceased donor availability." This frames deaths as a benefit for transplant recipients. Would be disturbing to patients and families.
- **File:** `script.js` line 693-697
- **Fix complexity:** Low — remove or rephrase the tooltip text.

### L-021: Opt-out registry claims are factually wrong
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** `policy-tiers.json` gives CA, OR, WA scores of 100. Methodology says "Opt-out registries (CA, OR, WA)." Oregon has opt-out (2021). California's AB 2408 has a transitional period and doesn't function as simple opt-out. Washington does not have full opt-out.
- **File:** `index.html` line 211, `data/manual/policy-tiers.json`
- **Fix complexity:** Low — correct the claims and adjust scores.

### L-022: Socioeconomic scores have no basis in data
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** `data/manual/socioeconomic.json` scores correlate with general wealth (SF: 95, Palo Alto: 94) rather than transplant-specific support (patient housing, financial assistance, advocacy groups). Cleveland Clinic has one of the best transplant support programs but Cleveland scores 81.
- **File:** `data/manual/socioeconomic.json`

---

## 4. Frontend & Architecture

### L-023: Map legend accumulation bug
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** Every `createXxxLayer()` function adds a new Leaflet legend. These are never removed when layers are toggled off. Toggling layers repeatedly creates duplicate overlapping legends.
- **File:** `script.js` — all `createXxxLayer()` functions

### L-024: Triple data duplication with no sync check
- **Severity:** HIGH
- **Status:** FIXED
- **Details:** Same data exists in: (a) inline constants in `algorithm.js`, (b) DEFAULTS in `data-loader.js` (~300 lines), (c) JSON files in `data/`. No automated check that these stay in sync. When Actions updates JSON files, the JS defaults become stale.
- **File:** `algorithm.js`, `data-loader.js`, `data/*.json`

### L-025: Duplicate "Cleveland" key in livingDonorProgramStrength
- **Severity:** LOW
- **Status:** FIXED
- **Details:** `algorithm.js` line 76 and 83 both define "Cleveland" key. Second silently overwrites first. Value is the same (93) so behavior is correct, but the code is confusing.
- **File:** `algorithm.js` lines 76, 83

### L-026: Comparison chart shows raw scores, not weighted contributions
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** The bar chart shows Medical Compatibility (25% weight) and Socioeconomic (2% weight) as equal-height bars. Visually misleading — users can't understand why a city with a higher Socioeconomic bar scored lower overall.
- **File:** `charts.js` `createComparisonChart`

### L-027: No accessibility attributes on map, charts, or interactive elements
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** No `aria-label` on map div, chart canvases, or overlay checkboxes. Screen reader users encounter map and charts as invisible content. Given target audience (people with serious medical conditions who may have disabilities), this is a significant gap.
- **File:** `index.html`, `script.js`

### L-028: City count inconsistency (22 actual, documented as 21)
- **Severity:** LOW
- **Status:** FIXED
- **Details:** Palo Alto is the 22nd city. README, status.md summary line, and brand bible all say "21 cities." Actual city count across all data structures is 22.
- **Fix complexity:** Low — update documentation to say 22.

### L-029: data-loader.js promise error handler drops source key names
- **Severity:** LOW
- **Status:** FIXED
- **Details:** When `Promise.allSettled` rejects, the error handler records `sourceStatuses['unknown']` instead of the actual file key. Multiple failures overwrite the same key.
- **File:** `data-loader.js` lines 274-276

### L-030: Mobile responsiveness of map overlays
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** The 10 overlay checkboxes in a side panel are a desktop-only UX pattern. On mobile viewports, the map and controls will likely overlap or controls will be inaccessible.
- **File:** `styles.css`, `index.html`

---

## 5. Pipeline & Automation (discovered 2026-03-01 review)

### L-031: fetch-hospital-quality.js destroys centerVolumes/specializations/insuranceAcceptanceRates
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** Line 55: `writeDataFile('hospital-quality.json', { centerReputation }, ...)` writes ONLY centerReputation. When the pipeline runs, it overwrites the entire `hospital-quality.json` (which contains 4 keys: centerVolumes, centerReputation, specializations, insuranceAcceptanceRates) with a file containing only centerReputation. This destroys the real SRTR volume data we added in L-010.
- **File:** `scripts/fetch-hospital-quality.js` line 55
- **Fix:** Either (a) merge fetched centerReputation into existing JSON file, or (b) split into separate files per key, or (c) restructure writeDataFile to support partial updates.

### L-032: fetch-health-data.js destroys 4 of 5 health fields
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** Lines 57-59: Each city only gets `{ diabetesRate: sd.diabetesRate }`. When the pipeline runs, it overwrites `health-demographics.json` with ONLY diabetesRate per city, destroying obesityRate, ckdRate, hypertensionRate, and smokingRate. The scoring function expects all 5 fields; the L-013 fix added null-safety guards so it won't NaN, but scores will degrade to fallbacks.
- **File:** `scripts/fetch-health-data.js` lines 57-59
- **Fix:** Fetch all 5 indicators from CDC BRFSS/PLACES, or merge fetched data into existing JSON rather than overwriting.

### L-033: No fetch script for donor-registration.json
- **Severity:** HIGH
- **Status:** DEFERRED
- **Details:** There is no `fetch-donor-registration.js` in the scripts/ directory. The `donor-registration.json` file is permanent seed data that can never be refreshed by the automated pipeline. This file contains stateRegistrationRates, livingDonorProgramStrength, and populationFactors — three critical inputs to the Donor Availability category (18% weight).
- **File:** Missing: `scripts/fetch-donor-registration.js`
- **Fix:** Create a fetch script sourcing state registration rates from Donate Life America or HRSA. livingDonorProgramStrength and populationFactors may need to remain manually curated.

### L-034: srtr-reports.json is loaded but never read by algorithm
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** `data-loader.js` loads `manual/srtr-reports.json` into `window.TransPlanData.srtrReports`, but no scoring function in `algorithm.js` ever reads `srtrReports`. The algorithm reads transplant volumes from `hospitalQuality.centerVolumes` instead. This is a dead data path — the file exists, is loaded at runtime, consumes bandwidth, but has zero effect on scoring.
- **File:** `data-loader.js`, `algorithm.js`
- **Fix:** Either (a) remove SRTR loading from data-loader.js (keep file as documentation), or (b) have algorithm.js read from srtrReports and remove centerVolumes from hospitalQuality.

### L-035: Git push race condition in parallel CI jobs
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** All 5 fetch jobs (traffic, air-quality, hospital-quality, cost-of-living, health-data) run in parallel. Each independently does `git push` after committing. The second job to finish will fail because main has moved forward. The validate job checks out `ref: main` but may get stale data if pushes failed silently.
- **File:** `.github/workflows/fetch-data.yml`
- **Fix:** Serialize jobs (add `needs: previous-job`) or use a single final commit job that runs after all fetches, or use `git pull --rebase` before push in each job.

### L-036: validate-data.js passes undefined filename to checkStaleness
- **Severity:** LOW
- **Status:** FIXED
- **Details:** Lines 82, 91, etc: `checkStaleness(airQuality)` — the `filename` parameter is omitted. The function signature is `checkStaleness(data, filename)`, so warning messages will say "undefined has no _meta.fetchedAt" instead of the actual filename.
- **File:** `scripts/validate-data.js` lines 82, 91, 101, 119, etc.
- **Fix:** Pass filename string to each `checkStaleness()` call.

### L-037: REGION_SERIES dead code in cost-of-living script
- **Severity:** LOW
- **Status:** FIXED
- **Details:** Lines 41-44 of `fetch-cost-of-living.js` define `REGION_SERIES` mapping South and Midwest regions to series IDs. This constant is never referenced anywhere in the file — the estimates section uses hardcoded multipliers against specific city results instead.
- **File:** `scripts/fetch-cost-of-living.js` lines 41-44
- **Fix:** Remove the dead constant or refactor estimates to actually use regional series.

### L-038: Orphan city entries in fallback data
- **Severity:** LOW
- **Status:** FIXED
- **Details:** Several fallback data structures contain cities not in our 22-city set: Phoenix in traffic traumaScores fallback (algorithm.js), Montana/Alaska in stateRegistrationRates fallback (not cities — these are states but used as keys alongside city names), Boston/Denver in socioeconomic.json (not in our city list). These are harmless but create confusion about the canonical city list.
- **File:** `algorithm.js` (traffic fallback), `data/manual/socioeconomic.json`
- **Fix:** Remove non-canonical entries; add a lint rule checking all city keys against the canonical list in utils.js.

### L-039: Missouri missing from donor registration data
- **Severity:** LOW
- **Status:** WONT FIX
- **Details:** Initially reported as missing, but audit was incorrect — `donor-registration.json` already has `"Missouri": 32` in stateRegistrationRates, and data-loader.js DEFAULTS has it too. No fix needed.

### L-040: Methodology text inaccuracies (partially fixed)
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** Multiple methodology text issues found during review: (a) algorithm.js header still said "success probability" — fixed; (b) Example calculation said "385 kidney transplants/year" but real data is 350 — fixed; (c) Hospital Quality listed "Outcomes data" and "Research activity" as factors not in the algorithm — replaced with "Insurance acceptance" which IS in algorithm; (d) Data sources listed CMS Hospital Compare and CDC WONDER instead of actual sources (SRTR, BLS, NHTSA FARS, EPA AQS) — fixed; (e) Nashville/Indianapolis centerReputation and specializations fallbacks were stale — synced.

---

## 6. Post-Test Audit (discovered 2026-03-01 unit tests + live API run)

### L-041: fetch-traffic.js destroys seed data when FARS API fails
- **Severity:** CRITICAL
- **Status:** FIXED
- **Details:** `fetch-traffic.js` used `writeDataFile()` (not `mergeDataFile()`). When the NHTSA FARS API returned 403 Forbidden for all states, the script overwrote `traffic-fatalities.json` with empty `stateFatalityRates` and fallback `traumaScores` (all 48), destroying the curated seed data including real `accidentHotspots` coordinates. Same class of bug as L-031/L-032.
- **File:** `scripts/fetch-traffic.js`
- **Fix:** Changed to `mergeDataFile()` + added guard to skip write when zero states are fetched.

### L-042: NaN in donor availability score for unknown cities
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** `calculateDonorAvailabilityScore()` looked up `populationFactors[city]` and `traumaScores[city]` without fallback defaults. For any city not in the lookup tables, these returned `undefined`, and `undefined / 100 * 100 * 0.25 = NaN`, which propagated through the final score. Discovered by unit tests.
- **File:** `algorithm.js` lines 186, 206
- **Fix:** Added `|| 50` fallback to both lookups.

### L-043: Boston/Denver orphans still in algorithm.js socioeconomic fallback (L-038 incomplete)
- **Severity:** LOW
- **Status:** FIXED
- **Details:** The L-038 cleanup removed Boston/Denver from `data/manual/socioeconomic.json` and `data-loader.js` DEFAULTS, but missed the inline fallback in `calculateSocioeconomicScore()` in `algorithm.js`. The fallback also had stale wealth-correlated scores instead of the transplant-support rubric values from L-022.
- **File:** `algorithm.js` lines 353-362
- **Fix:** Replaced with transplant-support rubric values matching socioeconomic.json; removed Boston/Denver.

### L-044: Algorithm header comment says "50+ factors" but actual count is ~43
- **Severity:** LOW
- **Status:** FIXED
- **Details:** Line 4 of `algorithm.js` claimed "50+ factors" but counting explicit factors across all 8 categories yields approximately 43. Updated to "40+ factors" for accuracy.
- **File:** `algorithm.js` line 4
- **Fix:** Changed "50+" to "40+".

### L-045: NHTSA FARS API endpoint unreachable
- **Severity:** MEDIUM
- **Status:** MITIGATED
- **Details:** Both FARS endpoints (`GetCrashesByLocation`, `GetFARSData`) return non-JSON responses (HTML error pages). The entire `crashviewer.nhtsa.dot.gov` API appears retired. Script now tries multi-year fallback (year-2/year-3), correctly records `'error'` metadata status, and preserves seed data via skip-on-empty guard. FIXME comments note CSV bulk download alternative at `nhtsa.gov/file-downloads/fars`.
- **File:** `scripts/fetch-traffic.js`

### L-046: CMS Provider Data API endpoint returns 400 Bad Request
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** The legacy `conditions[]` query syntax was deprecated. Replaced with multi-strategy approach (SQL, filter, legacy). The `filter` strategy succeeds and fetched hospital ratings for all 22 cities. Strategy auto-locks after first success to avoid retrying dead approaches. FIXME notes dataset ID `xubh-q36u` may change.
- **File:** `scripts/fetch-hospital-quality.js`

### L-047: No CDN fallback for Leaflet, Chart.js, or leaflet-heat
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** Added `onerror` handlers on CDN script tags, inline gate-check script (`window.TransPlanCDN`), and guard clauses in `initializeMap()`, `createTrafficAccidentHeatmap()`, `renderWeightsDonutChart()`, `createRadarChart()`, and `createComparisonChart()`. When CDN is down, yellow warning banners appear instead of crashes. Form, algorithm, and text results still work.
- **Files:** `index.html`, `script.js`, `charts.js`, `styles.css`

### L-048: Cost-of-living normalization uses hardcoded 80-200 range
- **Severity:** LOW
- **Status:** FIXED
- **Details:** Replaced hardcoded `80-200` range with dynamic `min/max` computed from loaded COL data at runtime. FIXME fallbacks (80/200) only activate when no COL data is loaded. Score now normalizes correctly across any data range.
- **File:** `algorithm.js` line 284

---

## 7. M2 Cause-of-Death Model (discovered 2026-03-08)

### L-049: Organ recovery rates from single study (PMC10329409)
- **Severity:** HIGH
- **Status:** OPEN
- **Details:** The 6×4 organ recovery rate matrix comes entirely from one study (PMC10329409, 2023) analyzing OPTN data from 2005–2019. This 15-year window predates significant changes in donor utilization practices including expanded DCD (donation after circulatory death) donors, ex-vivo perfusion technology, and hepatitis C-positive donor acceptance. Recovery rates for hearts and lungs in particular have improved substantially since 2019.
- **File:** `data/cause-of-death-by-region.json` → `organRecoveryRates`
- **Fix:** Cross-validate with OPTN annual data reports or SRTR OPO-specific reports (Excel download). Consider modeling rates as Beta distributions with PMC10329409 counts as priors rather than fixed point estimates.

### L-050: State-level granularity instead of OPO/DSA boundaries
- **Severity:** HIGH
- **Status:** OPEN
- **Details:** Organ procurement operates at the OPO (Organ Procurement Organization) / DSA (Donor Service Area) level — 56 OPOs in the US — but our cause-of-death data is aggregated at state level. OPO boundaries do not align with state lines. Pittsburgh (CORE) and Philadelphia (Gift of Life) are both in Pennsylvania but have very different donor pools and operational characteristics. This is the same granularity gap identified in L-009.
- **File:** `data/cause-of-death-by-region.json` → `stateCauseOfDeathProportions`
- **Fix:** SRTR OPO-specific reports contain donor counts by OPO; could replace state-level with OPO-level data using the existing SRTR Excel parsing infrastructure (Phase 2 M5).

### L-051: Static cause-of-death proportions with no automated refresh
- **Severity:** MEDIUM
- **Status:** OPEN
- **Details:** State-level cause-of-death proportions are a one-time snapshot manually curated from CDC WONDER's web interface. The opioid crisis has dramatically shifted drug intoxication proportions in many states year over year (e.g., West Virginia's drug OD rate tripled 2010–2020). No automated fetch script exists. The `_meta.notes` field contains a FIXME.
- **File:** `data/cause-of-death-by-region.json`
- **Fix:** CDC WONDER's programmatic API does NOT support state filtering (policy restriction). Two alternatives: (1) data.cdc.gov SODA API has partial state-level mortality data (broad categories only), (2) OPTN "Build Advanced Report" generates CSVs with donor cause-of-death by state but requires manual web download.

### L-052: Only 4 of 6 cause-of-death categories modeled
- **Severity:** MEDIUM
- **Status:** OPEN
- **Details:** PMC10329409 identifies 6 donor cause-of-death categories: trauma, cardiovascular, CVA/stroke, drug intoxication, **anoxia NOS**, and **other**. Our model drops anoxia and other entirely. Anoxia (drowning, asphyxiation) is a growing share of the donor pool — the paper found anoxia-related donors rose from 31.4% to 49.4% between 2013 and 2023. Our 4-category proportions are normalized to sum to 1.0, which conflates anoxia deaths into the other categories without matching their actual recovery rate profiles.
- **File:** `data/cause-of-death-by-region.json` → `causeCategories`, `stateCauseOfDeathProportions`
- **Fix:** Add `anoxia` and `other` categories. PMC10329409 likely has recovery rates for these. Requires re-sourcing state proportions from CDC WONDER with ICD-10 codes for anoxia (W65-W74, T71) and computing a 6-category breakdown.

### L-053: COD multiplier is deterministic, not stochastic
- **Severity:** MEDIUM
- **Status:** OPEN
- **Details:** The `_computeCodMultiplier()` (frontend) and `_get_cod_multiplier()` (backend) functions compute a fixed ratio (`stateScore / nationalAvg`). Given the same inputs, the multiplier is always identical. In the Monte Carlo simulation, this means the COD adjustment shifts all 1000 iterations uniformly rather than adding realistic uncertainty about donor supply variation. The recovery rates and proportions are point estimates with no confidence intervals.
- **File:** `algorithm.js` → `_computeCodMultiplier()`, `backend/services/monte_carlo.py` → `_get_cod_multiplier()`
- **Fix:** Model recovery rates as Beta distributions using PMC10329409 sample counts as α/β parameters. Sample a different multiplier for each Monte Carlo iteration, reflecting genuine uncertainty about local donor supply.

### L-054: Intestine organ uses pancreas recovery rates as proxy
- **Severity:** LOW
- **Status:** OPEN
- **Details:** PMC10329409 does not report intestine-specific recovery rates. The intestine row in `organRecoveryRates` is an exact copy of pancreas rates (0.246/0.048/0.095/0.053). Intestinal transplants are rare (~100/year in the US) so the practical impact is small, but it's technically inaccurate.
- **File:** `data/cause-of-death-by-region.json` → `organRecoveryRates.intestine`
- **Fix:** Search for intestine-specific recovery rate literature; if unavailable, document the proxy explicitly in the UI tooltip.

### L-055: Only 17 of 50 states have COD proportions
- **Severity:** LOW
- **Status:** OPEN
- **Details:** `stateCauseOfDeathProportions` covers only the 17 states containing our 22 cities. Cities added in uncovered states would receive no COD adjustment (graceful degradation — multiplier returns `null`). The limited state coverage also means the "national average" denominator is not truly national — it's the average of 17 states.
- **File:** `data/cause-of-death-by-region.json` → `stateCauseOfDeathProportions`
- **Fix:** Expand to all 50 states + DC. OPTN View Data Reports can provide donor cause-of-death by all donor states.

### L-056: Linear supply→wait assumption in Monte Carlo backend
- **Severity:** MEDIUM
- **Status:** OPEN
- **Details:** The backend divides Monte Carlo transplant wait times by the COD multiplier (`transplant_times / cod_mult`). This assumes a linear relationship: 10% more donors → 10% shorter waits. In reality, organ allocation is a complex queuing system where supply-demand dynamics are nonlinear. A 10% increase in local donors may yield anything from 0% improvement (if organs are shared regionally) to 20% improvement (if the center is below allocation thresholds).
- **File:** `backend/services/monte_carlo.py` line ~177
- **Fix:** Use a sub-linear scaling function (e.g., `wait_time / cod_mult^0.7`) or calibrate the elasticity against SRTR historical data.

---

## Resolution Log

| ID | Fixed In | Date | Notes |
|----|----------|------|-------|
| L-004 | 973185c | 2026-02-28 | Added red urgency warning banner for Status 1 patients |
| L-005 | e6f5d10 | 2026-02-28 | Sex modifier now organ-specific (heart/lung only) |
| L-006 | 520b13a | 2026-02-28 | Insurance wired into hospital quality scoring (15% of category) |
| L-007 | 973185c | 2026-02-28 | Renamed "Match Probability" to "Compatibility Index" |
| L-011 | e6f5d10 | 2026-02-28 | Florida registration rate corrected 26% → 68% |
| L-013 | 5c89140 | 2026-02-28 | Added nullish coalescing with national averages for all 5 health metrics |
| L-018 | 973185c | 2026-02-28 | Expanded to comprehensive multi-paragraph disclaimer with specific limitations |
| L-019 | 973185c | 2026-02-28 | Replaced "success probability" with "location suitability score" throughout |
| L-020 | 973185c | 2026-02-28 | Replaced insensitive traffic tooltip with neutral language |
| L-021 | 973185c + e6f5d10 | 2026-02-28 | Removed opt-out claims, lowered CA/WA policy scores |
| L-023 | 12a001a | 2026-02-28 | Added legend registry with addLayerLegend/removeLayerLegend helpers |
| L-025 | e6f5d10 | 2026-02-28 | Removed duplicate Cleveland key |
| L-026 | 12a001a | 2026-02-28 | Chart now shows weighted contributions (stacked) with tooltip showing both raw and weighted |
| L-029 | 12a001a | 2026-02-28 | Error handler now uses index to track correct source key |
| L-001 | (batch1) | 2026-02-28 | Added cPRA slider for kidney; sensitization multiplier 1.0-5.0x on wait time |
| L-002 | (batch1) | 2026-02-28 | Added MELD input for liver; MELD-based wait scoring replaces generic urgency |
| L-003 | (batch1) | 2026-02-28 | Added LAS input for lung; LAS-based wait scoring replaces generic urgency |
| L-008 | (batch2) | 2026-02-28 | Reduced traffic weight 15%→8% of donor category; redistributed to registration (39%) and living donor (28%) |
| L-016 | (batch2) | 2026-02-28 | Fixed FARS normalization: per-capita rates with state populations instead of /500 cap |
| L-024 | (batch3) | 2026-03-01 | Removed ~140 lines of inline constants from algorithm.js; data now flows from data-loader.js DEFAULTS → window.TransPlanData; fixed policy tier drift (CA/WA values) |
| L-010 | (batch3) | 2026-03-01 | Replaced fabricated volumes with real 2023-2024 SRTR/OPTN data across all 3 data locations; intestine reduced to 8 real centers |
| L-015 | (batch4) | 2026-03-01 | Replaced naive `100-ppb` with EPA AQI breakpoint conversion for ozone + added PM2.5 (param 88101); composite uses dominant pollutant |
| L-014 | (batch4) | 2026-03-01 | Fixed Nashville ratio (was 1.07x Baltimore, now 1.10x Houston); documented Census ACS basis for all 7 estimated cities |
| L-027 | (batch5) | 2026-03-01 | Added aria-label on map, chart canvas, results container (aria-live), overlay group, urgency warning (role=alert) |
| L-030 | (batch5) | 2026-03-01 | Collapsible "Map Overlays" toggle on mobile (<768px); controls hidden by default, expandable via button |
| L-028 | (batch5) | 2026-03-01 | Updated "21 cities" → "22 cities" across README, status.md, adr-log.md, roadmap.md, script.js, validate-data.js, check-srtr-updates.js |
| L-040 | (review) | 2026-03-01 | Fixed stale methodology text: algorithm.js header, example volume 385→350, removed phantom factors, corrected data source list, synced fallback values |
| L-031 | (batch7) | 2026-03-01 | Added mergeDataFile() to utils.js; fetch-hospital-quality.js now merges centerReputation into existing file instead of overwriting |
| L-032 | (batch7) | 2026-03-01 | fetch-health-data.js now uses mergeDataFile to preserve obesityRate/ckdRate/hypertensionRate/smokingRate when updating diabetesRate |
| L-035 | (batch8) | 2026-03-01 | Collapsed 5 parallel CI jobs into 1 sequential job with single commit+push; eliminates race condition |
| L-036 | (batch8) | 2026-03-01 | Added filename argument to all 8 checkStaleness() calls in validate-data.js |
| L-034 | (batch9) | 2026-03-01 | Removed srtrReports from DATA_FILES map in data-loader.js; file kept as documentation |
| L-037 | (batch9) | 2026-03-01 | Removed dead REGION_SERIES constant from fetch-cost-of-living.js |
| L-038 | (batch9) | 2026-03-01 | Removed Phoenix from traffic fallbacks (algorithm.js, data-loader.js, traffic-fatalities.json); removed Boston/Denver from socioeconomic.json + DEFAULTS; removed Milwaukee from traffic hotspots |
| L-039 | — | 2026-03-01 | False positive — Missouri already present in donor-registration.json and DEFAULTS |
| L-022 | (batch10) | 2026-03-01 | Replaced wealth-correlated scores with transplant-support rubric (housing 30%, financial 25%, support groups 20%, caregiver 15%, health literacy 10%); researched 22 centers |
| L-009 | ADR-010 | 2026-03-01 | DEFERRED — OPO mapping requires 22→58 manual lookups, no API available |
| L-012 | ADR-011 | 2026-03-01 | WONT FIX — 7% weight category, county-vs-state changes scores by <0.5 points |
| L-017 | ADR-012 | 2026-03-01 | DEFERRED — SRTR outcomes are HTML/PDF only, would need 132 manual data points |
| L-033 | ADR-013 | 2026-03-01 | DEFERRED — no machine-readable API for donor registration rates |
| L-041 | 0b59fc4 | 2026-03-05 | fetch-traffic.js switched to mergeDataFile + skip-on-empty guard |
| L-042 | 909ff06 | 2026-03-05 | Added `\|\| 50` fallback to populationFactors/traumaScores lookups (found by unit tests) |
| L-043 | 0b59fc4 | 2026-03-05 | Synced algorithm.js socioeconomic fallback with transplant-support rubric; removed orphan cities |
| L-044 | 0b59fc4 | 2026-03-05 | Changed "50+ factors" → "40+ factors" in algorithm header |
| L-045 | 822b778 | 2026-03-06 | MITIGATED — switched to GetFARSData + multi-year fallback; API still unreachable, seed data preserved, FIXME for CSV alternative |
| L-046 | 822b778 | 2026-03-06 | FIXED — multi-strategy CMS API (SQL/filter/legacy); filter strategy works, 22 cities fetched |
| L-047 | 2b4d542 | 2026-03-06 | FIXED — onerror handlers + TransPlanCDN gate + guard clauses in map/chart init; yellow fallback banners |
| L-048 | 2b4d542 | 2026-03-06 | FIXED — dynamic min/max from loaded COL data; FIXME fallbacks for empty data |
