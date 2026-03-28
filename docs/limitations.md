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
- **Status:** PARTIALLY ADDRESSED
- **Details:** Pittsburgh and Philadelphia are both in Pennsylvania but served by different OPOs (CORE and Gift of Life) with meaningfully different operations. The algorithm uses state-level donor registration rates, treating all cities in a state as equivalent. OPO quality is one of the most cited factors in real transplant outcomes.
- **Progress:** 55 US OPOs cataloged with names, regions, and primary states. All 248 SRTR centers mapped to their serving OPOs (95 auto, 152 geographic, 1 manual). Data in `data/opo-mapping.json`. County-level CMS mapping (42 CFR Part 486) not available as structured download — searched eCFR, HRSA/OPTN, SRTR, and CMS data.cms.gov; no public structured dataset exists.
- **Fix remaining:** County-to-OPO mapping requires FOIA request to CMS, formal SRTR data request, or manual transcription from OPO certification letters. See GitHub #138.
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
- **Status:** FIXED
- **Details:** Originally, health data was fabricated city-level numbers derived from state averages. Now fixed: (1) 22 focus cities use real county-level CDC PLACES data via FIPS-code lookup (`fetch-health-data.js`). (2) All 248 SRTR centers mapped to nearest county from 2,956-county dataset (`generate-center-health-data.js`), median match distance 11.8 km. (3) CKD rate estimated via linear model (ckdRate = 9.0 + 0.5 × diabetesRate, R² ≈ 0.85) since CDC PLACES lacks county-level kidney measure. Dallas and Houston now show genuinely different rates reflecting Dallas County vs Harris County health data.
- **File:** `data/health-demographics.json` (270 entries), `scripts/generate-center-health-data.js`, `scripts/fetch-health-data.js`
- **Fix complexity:** Done.

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
- **Status:** PARTIALLY RESOLVED
- **Details:** `stateRegistrationRates` now sourced from Donate Life America 2019 Annual Report (2018 Donor Designation Rate by state, page 27). DDR available for 38 states; EDDR used as proxy for 13 states without DDR data. Added `stateDesignations`, `ndlrRegistrations`, and `eddr` fields from the same report. Two sub-fields remain manually curated by design:
  - `livingDonorProgramStrength`: 22-city scores (80–95 range) — no public dataset ranks transplant center living donor programs
  - `populationFactors`: city-level population adjustment scores — composite of metro population, donor pool density, and healthcare infrastructure; no single API provides this
- **File:** `data/donor-registration.json`
- **Fix remaining:** DLA report is 2018 vintage; re-extract when DLA publishes newer data. `livingDonorProgramStrength` and `populationFactors` are manual by design — review annually for accuracy.

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
- **Status:** FIXED (March 2026)
- **Details:** The `crashviewer.nhtsa.dot.gov` API was retired in late 2025. Rewrote `fetch-traffic.js` to download annual FARS CSV bulk archives from `static.nhtsa.gov/nhtsa/downloads/FARS/{year}/National/FARS{year}NationalCSV.zip`, extract ACCIDENT.CSV via `execFileSync('unzip', ...)`, and sum fatalities per state FIPS code. Computes per-capita rates (per 100k population) and trauma scores (0-100 scale). Successfully parsed FARS 2023 data for all 17 states covering 22 cities. See GitHub #103.
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
- **Severity:** HIGH → LOW (cross-validated)
- **Status:** VALIDATED (March 2026)
- **Details:** The 6×5 organ recovery rate matrix originated from PMC10329409 (Sundaram et al. 2023, OPTN data 2005–2019). In March 2026, all 30 organ×COD cells were cross-validated against OPTN 2023 national data (hrsa.unos.org, "Deceased Donors Recovered by Cause of Death", 16,336 total donors). 15 of 30 cells were updated where drift exceeded 10%: kidney rates increased (expanded DCD, machine perfusion, HCV+ acceptance), pancreas rates decreased (declining transplant volumes, shift to islet cell), heart stroke/anoxia/drug_intox rates decreased (more conservative selection), lung/liver anoxia/drug_intox rates decreased. Weighted-average validation: kidney 0.920 vs OPTN 0.947 (−2.9%), liver 0.713 vs 0.671 (+6.3%), heart 0.270 vs 0.285 (−5.3%), lung 0.193 vs 0.201 (−4.0%), pancreas 0.076 vs 0.075 (+1.3%). All within 7% of OPTN benchmarks. Cardiovascular rates unchanged (no OPTN equivalent category); drug_intox/anoxia split preserved from PMC ratio (OPTN lumps both as ANOXIA).
- **File:** `data/cause-of-death-by-region.json` → `organRecoveryRates`, `scripts/validate-recovery-rates.py`
- **Remaining:** Re-run validation annually when new OPTN reports are released. Consider Beta distribution priors for stochastic modeling of rate uncertainty (L-053 already applies kappa=50 stochastic sampling).

### L-050: State-level granularity instead of OPO/DSA boundaries
- **Severity:** HIGH → LOW (sufficiently addressed)
- **Status:** SUFFICIENTLY ADDRESSED (March 2026)
- **Details:** Organ procurement operates at the OPO (Organ Procurement Organization) / DSA (Donor Service Area) level — 56 OPOs in the US — but our cause-of-death data is aggregated at state level. OPO boundaries do not align with state lines. Pittsburgh (CORE) and Philadelphia (Gift of Life) are both in Pennsylvania but have very different donor pools and operational characteristics. This is the same granularity gap identified in L-009.
- **File:** `data/cause-of-death-by-region.json` → `stateCauseOfDeathProportions`, `data/opo-mapping.json`
- **Resolution:** OPO geographic mapping is now authoritative via HRSA Data Warehouse Excel file (`data.hrsa.gov`). `data/opo-mapping.json` contains: 60 OPOs with OPTN codes, 3,225 county FIPS → OPO assignments (with 98 multi-OPO overlap counties noted), and all 248 SRTR centers mapped to OPOs via `hrsa_county` method with 40 corrections from prior proximity-based mapping. Script: `scripts/build-opo-mapping-hrsa.py`. See GitHub #138 (closed).
- **Remaining gap:** `stateCauseOfDeathProportions` remains at state level (CDC mortality data is state-aggregated). OPO-level COD proportions would require either county-level CDC WONDER data (blocked by programmatic API policy) or SRTR OPO-specific donor COD reports. This gap is well-mitigated by: (1) Beta-distribution stochastic sampling (L-053, kappa=50, ~3.5% CV), (2) sublinear supply-wait elasticity (L-056), and (3) most project states having only 1–2 cities, making state ≈ OPO a reasonable proxy.
- **Future:** Optional enhancement — aggregate county-level CDC data to OPO level using the HRSA county-to-OPO mapping. Low priority given existing mitigations.

### L-051: Static cause-of-death proportions with no automated refresh
- **Severity:** MEDIUM
- **Status:** FIXED (March 2026)
- **Details:** Automated `scripts/fetch-cod-data.js` added to CI pipeline. Uses CDC SODA API (`data.cdc.gov`) to fetch state-level cause-of-death proportions with donor-eligibility calibration weights. Runs weekly via GitHub Actions. See GitHub #13.
- **File:** `scripts/fetch-cod-data.js`, `data/cause-of-death-by-region.json`

### L-052: Only 4 of 6 cause-of-death categories modeled
- **Severity:** MEDIUM
- **Status:** FIXED (March 2026) — anoxia-NOS added as 5th category; "other" (1.7% of donors) deferred as negligible
- **Details:** Added anoxia-NOS (9.2% of donors nationally) as a 5th COD category. Recovery rates estimated from PMC10329409 OR 0.848 vs trauma. State-level anoxia shares estimated from CDC drowning rate geographic patterns (range 0.05–0.14, mean 0.091). Existing 4 categories scaled down proportionally. CDC WONDER ICD-10 data (W65-W74, T71, T58, W75-W84) would provide exact state values but has no REST API. "Other" category (1.7% of donors) not added — too small and heterogeneous to model meaningfully.
- **File:** `data/cause-of-death-by-region.json`, `algorithm.js`, `backend/services/monte_carlo.py`, `scripts/fetch-cod-data.js`, `data-loader.js`
- **Fix:** Anoxia-NOS added across data file, fetch script, frontend, and backend. See GitHub #14 for full methodology.

### L-053: COD multiplier is deterministic, not stochastic
- **Severity:** MEDIUM
- **Status:** FIXED (March 2026)
- **Details:** The backend `_get_cod_multiplier()` now draws recovery rates from `Beta(rate*κ, (1-rate)*κ)` distributions (κ=50) per iteration, producing stochastic COD multipliers that vary across Monte Carlo iterations. The frontend `_computeCodMultiplier()` remains deterministic (browser-side performance).
- **File:** `backend/services/monte_carlo.py` → `_get_cod_multiplier(n_samples=..., rng=...)`
- **Fix:** Implemented — Beta-distributed recovery rate sampling with concentration κ=50 (~5-10% relative std dev).

### L-054: Intestine organ uses pancreas recovery rates as proxy
- **Severity:** LOW
- **Status:** FIXED (March 2026)
- **Details:** PMC10329409 does not report intestine-specific recovery rates. Replaced pancreas-proxy rates with COD-specific estimates derived from OPTN 2023 OTPD ratio (intestine/pancreas = 0.104) and clinical adjustment factors accounting for intestine's extreme sensitivity to donor quality (trauma 0.12x, cardiovascular 0.06x, drug_intox 0.10x, stroke 0.08x of pancreas). New rates: trauma=0.030, cardiovascular=0.003, drug_intox=0.010, stroke=0.004.
- **File:** `data/cause-of-death-by-region.json` → `organRecoveryRates.intestine`
- **Fix:** Replaced proxy with OTPD-derived COD-specific rates. See GitHub #16 for full methodology.

### L-055: Only 17 of 50 states have COD proportions
- **Severity:** LOW
- **Status:** FIXED (March 2026)
- **Details:** Expanded `stateCauseOfDeathProportions` from 17 to all 50 states + DC via CDC SODA API with donor-eligibility calibration weights. National average is now truly national. See GitHub #17.
- **File:** `scripts/fetch-cod-data.js`, `data/cause-of-death-by-region.json`

### L-056: Linear supply→wait assumption in Monte Carlo backend
- **Severity:** MEDIUM
- **Status:** FIXED (March 2026)
- **Details:** Wait time adjustment now uses sub-linear elasticity: `wait_time / cod_mult^ε` where ε = `SUPPLY_WAIT_ELASTICITY` = 0.65 (configurable in `config.py`). This means 10% more donors → ~6.5% shorter waits, reflecting nonlinear queuing dynamics. Applied consistently across all three simulation paths (MC, what-if, MCMC).
- **File:** `backend/config.py` → `SUPPLY_WAIT_ELASTICITY`, `backend/services/monte_carlo.py`, `backend/services/what_if.py`, `backend/services/mcmc_inference.py`
- **Fix:** Implemented — configurable elasticity exponent, default 0.65 based on queuing theory + SRTR empirical range (0.5–0.8).

### L-057: Pancreas lacks adult graft survival data in SRTR
- **Severity:** LOW
- **Status:** MITIGATED (March 2026)
- **Details:** SRTR Program-Specific Reports do not publish adult pancreas graft survival rates. The `GSR_AD_ACT_C1Y` column in the PA.xls C-series table is empty for all 331 rows. This is because most pancreas transplants are simultaneous kidney-pancreas (SPK), and graft outcomes are tracked under the kidney organ file. As a result, `get_graft_survival_1yr("pancreas", ...)` returns `None` for all cities. The compound success metric falls back to patient survival (96.6% national) with an annotation (`compound_success_note`). This is clinically reasonable — pancreas patient survival is a valid proxy — but it means pancreas compound success is not directly comparable to other organs where graft survival is used.
- **File:** `backend/services/outcomes.py` lines 142-149, `data/post-transplant-outcomes.json`
- **Fix:** Future work could extract SPK graft survival from the kidney file and attribute it to pancreas centers, or use OPTN View Data Reports which may publish pancreas-specific graft data separately. Low priority since the patient survival fallback is clinically sound.

---

## 8. Statistical Model (discovered 2026-03-18 review)

### L-058: Competing risks drawn as independent exponentials
- **Severity:** HIGH
- **Status:** FIXED (March 2026)
- **Details:** The Monte Carlo engine draws mortality and delisting times as independent exponential random variables. In reality, a patient whose health is declining faces both higher mortality AND higher delisting risk simultaneously — positive lower-tail dependence. The independence assumption underestimates the probability of clustered adverse events, leading to overly optimistic transplant probability estimates for high-acuity patients.
- **File:** `backend/services/monte_carlo.py` lines 220-232, `backend/services/what_if.py` lines 101-111, `backend/services/sensitivity.py` lines 44-55
- **Fix:** Added Clayton copula (`services/copula.py`) with opt-in `use_copula: true` toggle. Default θ=1.0 (Kendall's τ ≈ 0.33). Marginal distributions preserved exactly; only the dependence structure changes. ADR-025.

### L-059: Single fixed copula parameter (θ) for all organs
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** The Clayton copula parameter θ=1.0 was applied uniformly across all 6 organ types. Now each organ has a literature-derived θ based on clinical acuity: kidney=0.8 (τ≈0.29), liver=1.2 (τ≈0.37), heart=1.8 (τ≈0.47), lung=1.5 (τ≈0.43), pancreas=0.9 (τ≈0.31), intestine=1.5 (τ≈0.43). Applied across all 4 copula call sites (monte_carlo, what_if, sensitivity, mcmc_inference).
- **File:** `backend/config.py` → `ORGAN_COPULA_THETA`
- **Fix:** Per-organ θ values added to config.py and consumed by all simulation engines.

### L-060: MCMC model uses aggregate center-level data, not patient-level
- **Severity:** HIGH
- **Status:** OPEN
- **Details:** The PyMC hierarchical model treats SRTR center-level summary statistics (median wait times, mortality rates, delisting rates) as noisy observations. It does not have access to patient-level event times, which means it cannot learn individual-level covariate effects (age × blood type interactions, time-varying hazards, etc.) from data. Patient-level effects (blood type multipliers, urgency multipliers) are applied deterministically at query time using the same fixed factors as the Monte Carlo engine. The hierarchical structure adds uncertainty quantification and partial pooling across cities, but the patient-level model is no richer than the standard Monte Carlo approach.
- **File:** `backend/services/mcmc_survival.py` → `build_organ_model()`, `backend/services/mcmc_inference.py` → `simulate_mcmc()`
- **Fix:** Would require patient-level SRTR Standard Analysis Files (SAFs), which are restricted-access research datasets requiring a Data Use Agreement. With SAFs, the model could learn age×blood type×urgency interactions directly from event histories.

### L-061: Informative priors anchored to existing point estimates
- **Severity:** MEDIUM
- **Status:** OPEN
- **Details:** The MCMC model's priors are centered on the same SRTR-derived point estimates used by the Monte Carlo engine (e.g., `mu=np.log(data["national_median"])` with `sigma=0.3`). This means posteriors will not deviate dramatically from the frequentist estimates unless there is strong tension in the data. The model is essentially a Bayesian meta-analysis that adds uncertainty bands and partial pooling, not an independent re-estimation from raw data. Users should not interpret MCMC results as "more accurate" — they are "better calibrated for uncertainty."
- **File:** `backend/services/mcmc_survival.py` → `build_organ_model()` prior specifications
- **Fix:** Document clearly in the UI that MCMC mode provides uncertainty quantification, not fundamentally different point estimates. Consider weakening priors (larger sigma) if independent data sources become available for validation.

### L-062: Quick-fit mode (--quick) may produce unreliable posteriors
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** The `--quick` flag runs only 200 draws / 1 chain / 100 tuning steps. This is fast (~5s) but may not achieve convergence for all parameters. Now a `--strict` flag gates trace saving on R-hat < 1.01 AND ESS (bulk) > 400. If either threshold fails, the trace file is deleted and the script raises an error. For production use, recommend `--samples 2000 --chains 4 --strict`.
- **File:** `scripts/fit-mcmc-model.py` → `--strict` flag
- **Fix:** `--strict` convergence gate implemented. Checks both R-hat and ESS bulk before allowing trace save.

### L-063: Spatial interpolation uses sparse city-level data for some layers
- **Severity:** MEDIUM
- **Status:** PARTIALLY FIXED
- **Details:** The RBF/IDW interpolation engine builds continuous surfaces from as few as ~20 data points for city-level layers. With Phase 6B (#125, #126), health demographics now use ~2,956 county-level points (was ~20) and air quality uses ~2,000-4,000 monitor-level points (was ~20). The engine auto-prefers dense sources with fallback. Remaining sparse layers: `cost_of_living` (~20 points, no dense source) and `health_ckdRate` (~20 points, CKD not in CDC PLACES). Thin-plate spline RBF kernel can still produce edge artifacts for query points far from any data center.
- **Impact:** Most layers now have 100-200x more data points. Cost of living and CKD rate remain city-level sparse. Edge artifacts possible at CONUS boundaries.
- **File:** `backend/services/spatial_interpolation.py` → `_extract_layer_points()`
- **Mitigation:** Phase 6C #134 would add kriging variance estimates to quantify interpolation uncertainty. Cost of living could be improved with BLS MSA-level data. CKD rate could potentially be derived from diabetes+hypertension proxy.

### L-064: UNOS allocation circles use simplified center-level competition model
- **Severity:** LOW
- **Status:** OPEN
- **Details:** The allocation circle model counts transplant centers within 250nm/500nm radii as a proxy for competition and donor pool access. The real UNOS allocation system is far more complex — it considers patient priority scores, organ acceptance rates, OPO boundaries, center listing practices, and match-run mechanics. The competition score is normalized against rough averages (e.g., ~15 kidney centers within 250nm for an average US metro) that are not empirically validated.
- **Impact:** Distance score provides directional guidance (dense vs. sparse transplant geography) but should not be interpreted as a precise allocation prediction.
- **File:** `backend/services/allocation_geography.py` → `allocation_circles()`, `distance_score()`
- **Mitigation:** Document as directional proxy. Could improve with OPO-level data (#122) and center-specific acceptance rate data.

### L-065: Frontend graceful degradation uses undocumented fallback data
- **Severity:** LOW
- **Status:** OPEN
- **Details:** When the backend API is unavailable, `script.js` falls back to a hardcoded `cityData` mock result object and `cityStateMap` for the home center dropdown. These fallback values are legitimate graceful degradation but are not documented as such — there's no comment explaining they are intentional fallbacks or how they were derived. Similarly, `data-loader.js` DEFAULTS provide static fallback values for all data files.
- **Impact:** No data quality impact (fallbacks only activate when API is down). Documentation gap only.
- **File:** `script.js` → `cityData`, `cityStateMap`; `data-loader.js` → `DEFAULTS`
- **Mitigation:** Add inline comments documenting these as intentional fallback data for graceful degradation.

### L-066: Continuous transplant probability surface (spatial probability heatmap)
- **Severity:** LOW (enhancement)
- **Status:** DEFERRED (Phase 8 / post-funding)
- **Category:** Spatial / Simulation
- **What:** Instead of ranking 248 discrete centers, generate a continuous heatmap showing P(transplant at 24mo) across the entire US for a given patient profile. Users could identify optimal zip codes to relocate to, not just optimal centers.
- **Why:** Patients often ask "where should I move?" not "which center should I list at?" A continuous surface would answer the relocation question directly. The spatial interpolation engine (RBF/IDW) already produces continuous surfaces for individual data layers (wait times, mortality, etc.) -- extending to a composite probability surface is architecturally feasible.
- **How:** New endpoint `GET /spatial-probability-grid` that: (1) at each grid point, interpolates center-level factors (wait time, mortality, delisting, graft survival), (2) runs a lightweight analytical approximation (BBN-style, not full MC) to compute P(transplant|location), (3) returns the same lat/lon/intensity format as `/spatial-grid` for Leaflet heatmap rendering. Patient-specific: organ, blood type, urgency affect the surface. Resolution-dependent: web tier ~30x30 (900 mini-simulations), local tier ~100x100 (10,000).
- **Deferral rationale:** (1) Computationally expensive: 900-10,000 inference calls per request, even with BBN. (2) Clinical interpretation unclear: interpolated probabilities at non-center locations are extrapolations, not observed data. A patient can't actually get a transplant at a random geographic point -- they'd go to the nearest center. (3) Better framed as "nearest center analysis with travel contours" than "probability at any point." (4) Infrastructure is ~80% there (spatial engine, heatmap renderer, tier system), but validation and clinical framing need careful thought.
- **Prerequisites:** BBN full-mode benchmarking on Vercel (L-069), tier system validation, spatial.html mature enough for complex overlays.
- **File:** Would create `backend/services/spatial_probability.py`, new endpoint in `backend/routers/spatial.py`, new layer option in `spatial.html`.

### L-067: Custom city set / user-defined focus centers
- **Severity:** MEDIUM (enhancement)
- **Status:** DEFERRED
- **Category:** Configuration / UX
- **What:** Allow users to define their own subset of centers to analyze (e.g., "the 10 centers nearest to me," "all centers in Texas," or a hand-picked list) rather than choosing between the fixed 22-city classic set, ~50 state groups, or all 248 centers.
- **Why:** The 22-city "classic" set was chosen for SRTR data density but has no clinical justification for any individual patient. A patient in rural Montana cares about different centers than one in NYC. The full 248-center mode is computationally expensive and returns too many results. A user-defined subset would give the right granularity for each patient's situation.
- **How:** (1) Add `center_codes: list[str]` optional parameter to PatientProfile schema. When provided, simulation only runs for those centers. (2) Frontend: "My Centers" picker on simulator page with multi-select or geographic filter (state, radius from zip, organ program). (3) URL-shareable via query param (`?centers=TNMT,PAPT,MNRM`). (4) Works with all 3 inference engines (MC already iterates a center list, BBN/MCMC would filter their output).
- **Deferral rationale:** Lower priority than completing the tier system and analysis pages. The existing granularity modes (classic/state/full) cover most use cases. A custom picker adds UI complexity (multi-select with search across 248 centers).
- **File:** `backend/models/schemas.py` (new field), all 3 simulation services (filter logic), `simulator.html` (multi-select picker).

### L-068: 22-city selection rationale undocumented
- **Severity:** MEDIUM
- **Status:** OPEN
- **Category:** Documentation / Reproducibility
- **What:** The original 22 cities (Pittsburgh, Baltimore, Philadelphia, New York, Minneapolis, Madison, Chicago, Cleveland, St. Louis, Indianapolis, Omaha, Rochester, Nashville, Durham, Miami, Dallas, Houston, Portland, Seattle, San Francisco, Los Angeles, Palo Alto) were chosen during Phase 1 without documented rationale. No ADR explains why these 22 and not others.
- **Why:** For peer review and reproducibility, the city selection criteria must be documented. Were they chosen for SRTR data density? Geographic coverage? Program volume? Center of Excellence status? The answer affects how "classic" mode should be interpreted by users and reviewers.
- **How:** (1) Research the original selection criteria (likely: top-volume programs with geographic spread covering all 11 UNOS regions). (2) Document in an ADR (ADR-029). (3) Add a note to the BBN "classic" mode description explaining what the 22 cities represent. (4) Consider whether the classic set should be updated (some cities like Palo Alto are unusual choices for a transplant focus city).
- **File:** `docs/adr-log.md`, `backend/services/bbn_parameterizer.py` (comment on REGIONS list).

### L-069: BBN full-mode (248 regions) performance untested on Vercel
- **Severity:** MEDIUM
- **Status:** OPEN
- **Category:** Performance / Deployment
- **What:** The BBN `bbn_granularity=full` mode creates a pgmpy model with 248 discrete Region states. CPTs are ~11x larger than classic mode. This has been tested locally but never benchmarked on Vercel's serverless function limits (memory, execution time, cold start).
- **Why:** If full mode exceeds Vercel's 1GB memory limit or 300s timeout, it would fail silently or timeout. The tier system currently blocks "full" on the web tier, but this should be validated rather than assumed.
- **How:** (1) Deploy current code to Vercel. (2) Test `POST /simulate?inference_mode=bayesian&bbn_granularity=full` with a standard patient profile. (3) Measure: response time, memory usage (via Vercel function logs), cold start penalty. (4) If it works within limits, consider allowing "full" on web tier. If not, document the limit.
- **Deferral rationale:** Blocked on deployment. Current tier system safely gates this to local-only mode.
- **File:** No code changes needed -- this is a deployment validation task.

### L-070: Circular import fragility between bbn_parameterizer and bayesian_network
- **Severity:** LOW
- **Status:** OPEN (tech debt)
- **Category:** Architecture
- **What:** `bbn_parameterizer.get_center_to_region_map("classic")` imports `bayesian_network._get_center_region_map` via a deferred import (inside the function, not at module level) to avoid a circular dependency. `bayesian_network` imports from `bbn_parameterizer` at module level.
- **Why:** If anyone moves the deferred import to module level, or adds a new module-level import in the opposite direction, Python will raise `ImportError` at startup. The deferred import has a comment explaining this, but it's still fragile.
- **How:** Extract `_get_center_region_map()` into a standalone utility module (e.g., `services/center_mapping.py`) that both `bbn_parameterizer` and `bayesian_network` import without circular dependency.
- **File:** `backend/services/bbn_parameterizer.py:108`, `backend/services/bayesian_network.py`

### L-071: Documentation still references "22 cities" in ~15 places
- **Severity:** LOW
- **Status:** OPEN
- **Category:** Documentation
- **What:** After expanding all 3 inference engines to support 248 centers via granularity modes, ~15 documentation references in `docs/status.md`, `docs-site/docs/` (architecture, frontend, data-pipeline, FAQ, roadmap, testing, data-curation), and backend comments/docstrings still say "22 cities" as if it were a hard limit. The functional code and tests have been updated, but prose documentation has not.
- **Why:** Misleading for new contributors and reviewers who read the docs and think the system is limited to 22 cities. Should reflect the current state: 22 cities is the "classic" default, with state (~50) and full (248) modes available.
- **How:** Batch find-and-replace across docs/ and docs-site/docs/: change "22 cities" to "22 focus cities (classic mode)" or "up to 248 SRTR centers" as appropriate. Update architecture diagrams, FAQ answers, and contributing guides. Backend comments in `bbn_parameterizer.py`, `bayesian_network.py`, `monte_carlo.py`, `brier_score.py` should note the classic set is a configurable default.
- **Files:** `docs/status.md`, `docs-site/docs/architecture/*.md`, `docs-site/docs/about/faq.md`, `docs-site/docs/about/roadmap.md`, `docs-site/docs/contributing/*.md`, `backend/services/bbn_parameterizer.py`, `backend/services/bayesian_network.py`, `backend/services/monte_carlo.py`, `backend/services/brier_score.py`

---

## 9. Data Provenance

> **Every data file audited 2026-03-18.** This table documents the actual source and quality tier of each data file used by the simulation and scoring engines. Files are classified as: **SRTR** (parsed from downloaded SRTR Excel files), **API** (fetched from live government APIs), **Literature** (derived from peer-reviewed publications), **Seed** (hardcoded values never refreshed from a live source), or **Synthetic** (procedurally generated).

### Core Simulation Pipeline (drives transplant probability calculations)

| File | Tier | Source | Vintage | Notes |
|------|------|--------|---------|-------|
| `wait-time-distributions.json` | **SRTR** | SRTR PSR Table B10, Jan 2025 XLS (`data/srtr-raw/`) | Jan 2025 | National medians + 22 city wait factors parsed by `parse-srtr-reports.py`. Blood type & clinical multipliers (cPRA/MELD/LAS) are **literature-estimated** — SRTR Table B10 does not stratify by blood type. |
| `competing-risks.json` | **SRTR** | SRTR PSR Table B7, Jan 2025 XLS | Jan 2025 | Annual mortality/delisting rates + 22 city adjustment factors. Urgency & age mortality multipliers are **literature-estimated** (SRTR 2023 ADR Table 5.3). |
| `post-transplant-outcomes.json` | **SRTR** | SRTR PSR C-series Tables C5–C20, Jan 2025 XLS | Jan 2025 | Graft/patient survival rates, hazard ratios with CIs, performance ratings. Pancreas graft survival correctly `null` (L-057). |
| `cause-of-death-by-region.json` | **API + Literature** | CDC SODA API (`bi63-dtpu` + `xkb8-kh2a`) + PMC10329409 | CDC: 2017; PMC: 2023 | State COD proportions from CDC (all 50 states + DC). Organ recovery rates from PMC10329409 (OPTN 2005–2019). Anoxia shares estimated from CDC drowning patterns. Donor-eligibility calibration weights fitted via Nelder-Mead. **CDC data is 2017 vintage** (L-051). |

### Scoring Engine (drives location suitability scores)

| File | Tier | Source | Vintage | Notes |
|------|------|--------|---------|-------|
| `hospital-quality.json` | **API + Manual** | CMS Provider Data API (centerReputation) + SRTR manual research (centerVolumes) | Mar 2026 (CMS); 2023–2024 (volumes) | CMS ratings are general hospital quality, not transplant-specific (L-017 DEFERRED). Volumes hand-researched from SRTR program-specific reports. |
| `health-demographics.json` | **API** | CDC PLACES API (multi-release: swc5-untb 2025, d3i6-k6z5 2024 GIS, duw2-7jbt 2022) | Mar 2026 | All 5 indicators live-fetched for 22 cities (5/5 each). Primary source: 2025 release. PA counties (Pittsburgh, Philadelphia) use 2024 GIS fallback (PA absent from 2023 data year). CKD (KIDNEY) measure from 2022 release (removed from 2025). |
| `cost-of-living.json` | **API** | BLS CPI data (via CI workflow with `BLS_API_KEY` secret) | Mar 2026 | Live-fetched via GitHub Actions `Fetch Data` workflow. 7 of 22 cities use fixed-ratio estimates from nearby cities (L-014). |
| `donor-registration.json` | **Report** | Donate Life America 2019 Annual Report (2018 data, p.27) | 2018 | `stateRegistrationRates` from DLA Donor Designation Rate (DDR); EDDR used as proxy for 13 states without DDR. `stateDesignations`, `ndlrRegistrations`, `eddr` added. `livingDonorProgramStrength` and `populationFactors` remain manual estimates. |
| `air-quality.json` | **API** | EPA AQS API (via CI workflow with `EPA_API_KEY` secret) | Mar 2026 | Live-fetched via GitHub Actions `Fetch Data` workflow. Per-monitor data in `air-quality-monitors.json` (24K+ entries). |
| `traffic-fatalities.json` | **API** | NHTSA FARS 2023 CSV bulk download | Mar 2026 | 17 states, per-capita fatality rates per 100k, trauma scores (0–100). Downloaded from `static.nhtsa.gov`, extracted ACCIDENT.CSV, summed FATALS by state FIPS. FARS 2024 not yet published (404). |

### Phase 6: Center-Level & Spatial Data

| File | Tier | Source | Vintage | Notes |
|------|------|--------|---------|-------|
| `srtr-all-centers.json` | **SRTR + Geocoded** | SRTR PSR Excel files (center names/codes) + Nominatim/manual geocoding (coordinates) | Jan 2025 (SRTR); Mar 2026 (geocoding verified) | 248 centers with hospital-specific lat/lon. All coordinates verified March 2026: 133 Nominatim, 32 nominatim_verified (upgraded from city-center), 83 manual_verified. No city_mapping sources remain (#136). |
| `wait-time-distributions-centers.json` | **SRTR** | SRTR PSR Table B10 (all centers) | Jan 2025 | Center-level wait time factors for 248 centers × 6 organs. Same parse pipeline as 22-city version. |
| `competing-risks-centers.json` | **SRTR** | SRTR PSR Table B7 (all centers) | Jan 2025 | Center-level mortality/delisting for 248 centers × 6 organs. |
| `post-transplant-outcomes-centers.json` | **SRTR** | SRTR PSR C-series (all centers) | Jan 2025 | Center-level graft/patient survival for 243 centers. Some centers lack C-series data. |
| `opo-mapping.json` | **HRSA** | HRSA Data Warehouse Excel (`OPO Service Area by County` sheet) + FCC Census Area API (center county lookup) | Feb 2026 (HRSA refresh) | **Authoritative county-to-OPO mapping** from HRSA/OPTN. 60 OPOs, 3,225 counties with FIPS codes, 248 centers mapped via county FIPS. 40 center assignments corrected from prior proximity-based method. 98 counties with multi-OPO overlap noted. Includes `countyToOpo` section for spatial interpolation. Resolves #138. |

### Trend Analysis

| File | Tier | Source | Vintage | Notes |
|------|------|--------|---------|-------|
| `srtr-historical.json` | **Real** | SRTR PSR National Summary Data (14 biannual releases, Jan 2019 – Jul 2025) | Jan 2019 – Jul 2025 | **Real SRTR data.** Parsed from archived Excel files via `parse_historical_trends()`. Auto-discovery from `data/srtr-raw/historical/` directories. Automated via `fetch-srtr-historical.yml` GitHub Actions workflow. |

### Manual / Curated

| File | Tier | Source | Notes |
|------|------|--------|-------|
| `manual/socioeconomic.json` | **Manual** | Researcher assessment using transplant-support rubric | Housing programs, financial assistance, support groups — not from a published dataset |
| `manual/climate-scores.json` | **Manual** | Subjective recovery climate scores | No API exists for this concept |
| `manual/policy-tiers.json` | **Manual** | State donation policy research | Reviewed for accuracy (L-021 fix), should be re-reviewed annually |
| `srtr-center-mapping.json` | **Manual** | SRTR center directory | Real SRTR center codes (e.g., PAPT = UPMC), manually maintained |

### Key Takeaways for Paper

1. **Core probability pipeline is real SRTR data** — national medians, city factors, mortality/delisting rates, and post-transplant outcomes all parsed from official January 2025 SRTR Excel releases.
2. **Patient-level modifiers are literature-estimated** — blood type multipliers, cPRA/MELD/LAS effects, urgency/age mortality factors come from published literature, not SRTR-stratified data.
3. **Historical trends are now real SRTR data** — `srtr-historical.json` contains 15-release time-series (2019–2025) parsed from official SRTR PSR archives. Trend charts can be cited as SRTR-sourced.
4. **All scoring-engine inputs now have real data sources** — health demographics (CDC PLACES), traffic fatalities (NHTSA FARS), air quality (EPA AQS), cost of living (BLS CPI), and donor registration (DLA 2018 report) are all sourced from authoritative providers. `livingDonorProgramStrength` and `populationFactors` in donor-registration.json remain manual estimates. These affect the location suitability score (frontend) but NOT the probabilistic simulation engine (backend).
5. **CDC cause-of-death data is from 2017** — drug intoxication distributions have shifted substantially since then (opioid crisis escalation).
6. **Phase 6 center-level data is real SRTR data** — all ~248 center wait times, competing risks, and outcomes are parsed from the same SRTR PSR Excel files using the same pipeline as the 22-city data. Geographic coordinates verified March 2026: all 248 centers have hospital-specific coordinates (Nominatim + manual Google Maps lookup). No city-center approximations remain (#136).
7. **Spatial interpolation is derived, not new source data** — all 24 interpolation layers are computed from existing provenance-tracked data files. No new external data sources are introduced by the interpolation engine.

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
| L-009 | ADR-010 | 2026-03-20 | FIXED — Authoritative county-to-OPO mapping from HRSA Data Warehouse Excel (3,225 counties → 60 OPOs). 248 centers mapped via county FIPS lookup. 40 assignments corrected from prior proximity method. Resolves #138. |
| L-012 | ADR-011 | 2026-03-20 | FIXED — 248 centers mapped to nearest county (2,956→3,144 CDC PLACES counties), ckdRate now live from 2022 KIDNEY measure (replaces linear model estimate) |
| L-017 | ADR-012 | 2026-03-01 | DEFERRED — SRTR outcomes are HTML/PDF only, would need 132 manual data points |
| L-033 | ADR-013 | 2026-03-20 | PARTIALLY RESOLVED — `stateRegistrationRates` from DLA 2019 Annual Report (2018 DDR). `livingDonorProgramStrength` and `populationFactors` remain manually curated by design (no public dataset). |
| L-041 | 0b59fc4 | 2026-03-05 | fetch-traffic.js switched to mergeDataFile + skip-on-empty guard |
| L-042 | 909ff06 | 2026-03-05 | Added `\|\| 50` fallback to populationFactors/traumaScores lookups (found by unit tests) |
| L-043 | 0b59fc4 | 2026-03-05 | Synced algorithm.js socioeconomic fallback with transplant-support rubric; removed orphan cities |
| L-044 | 0b59fc4 | 2026-03-05 | Changed "50+ factors" → "40+ factors" in algorithm header |
| L-045 | 822b778 | 2026-03-06 | FIXED — rewrote to FARS CSV bulk download from static.nhtsa.gov; FARS 2023 parsed (17 states, per-capita rates + trauma scores). API retirement no longer blocks data refresh. |
| L-046 | 822b778 | 2026-03-06 | FIXED — multi-strategy CMS API (SQL/filter/legacy); filter strategy works, 22 cities fetched |
| L-047 | 2b4d542 | 2026-03-06 | FIXED — onerror handlers + TransPlanCDN gate + guard clauses in map/chart init; yellow fallback banners |
| L-048 | 2b4d542 | 2026-03-06 | FIXED — dynamic min/max from loaded COL data; FIXME fallbacks for empty data |
| L-053 | (Phase 5 M2) | 2026-03-18 | FIXED — Beta-distributed recovery rates (κ=50) for stochastic COD multiplier per iteration |
| L-056 | (Phase 5 M2) | 2026-03-18 | FIXED — Sub-linear elasticity (ε=0.65) via SUPPLY_WAIT_ELASTICITY config; applied across MC, what-if, MCMC |
| L-058 | (Phase 5 M2) | 2026-03-18 | FIXED — Clayton copula for correlated mortality/delisting; θ=1.0, opt-in via use_copula flag; ADR-025 |
