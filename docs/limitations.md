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
- **Normalizers measured and corrected (2026-08-27, #299):** the "rough averages" were not merely unvalidated, they were **wrong**, and checkably so from data already in the repo. Population-weighting the county centroids against county population gives a mean of **25.6** kidney centers within 250nm, not the ~15 the code asserted — so the score averaged **1.71** where its own comment claimed ~1.0. Every organ was understated by 24–72% (kidney 15→25.6, liver 10→15.7, heart 10→16.2, lung 5→8.6, pancreas 7→11.7, intestine 2→2.5).

  Correcting them raises the composite by ~3 points but barely moves the ordering (Spearman ≥ 0.9935, top-20 overlap 18–20/20), so this is a truth-in-labelling fix rather than a results change.

  The 500nm normalizer (2.5× the 250nm figure) was measured on the same footing and is **sound** — actual ratio 2.38–2.51 — so it was kept rather than churned.

  The constants now live at module scope as `AVG_CENTERS_250NM` and are **recomputed and pinned** by `backend/tests/test_competition_normalizers.py`, which fails if they drift from the data. Being function-local round numbers is a large part of why they escaped notice for so long.
- **Still open:** the deeper objection stands — a center count is a crude proxy for competition regardless of how well it is normalized, because it ignores priority scores, acceptance rates, OPO boundaries and match-run mechanics.
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
- **Status:** FIXED (2026-08-25, #304 — center_codes on /score + /simulate, shareable simulator ?centers= URLs, Find-mode "Simulate these N centers" handoff)
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
- **Status:** FIXED (June 2026 — BBN rebuild Step 0.5 + perf)
- **Category:** Performance / Deployment
- **What:** The BBN `bbn_granularity=full` mode builds a 248-state Region model. Originally feared too slow for serverless.
- **Fix:** Profiled with `scripts/bbn-build-profile.py` (note: an initial 62.9s reading was a `tracemalloc` artifact — never time a build under tracemalloc). Real cold full build was **11.5s**, all in `build_wait_category_cpt`, which constructed ~107k scipy `lognorm` objects in a quadruple loop. Vectorized to a single `lognorm.cdf(array scale)` per organ → **0.39s build, 7MB peak, 246ms query** (bit-identical output, golden-gated). Memory was never a concern. The model also caches per process. The remaining open question is the deferred precompute-vs-rebuild choice, now moot since rebuild is sub-second.
- **File:** `backend/services/bbn_parameterizer.py:build_wait_category_cpt`, `scripts/bbn-build-profile.py`

### L-070: Circular import fragility between bbn_parameterizer and bayesian_network
- **Severity:** LOW
- **Status:** FIXED (2026-08-26, #298) — the cycle is gone. `_get_center_region_map` was removed along with the classic granularity in #293, and `get_center_to_region_map` no longer references `bayesian_network` at all; its only deferred import is `data_loader`, which is not circular. Verified by importing each module first in a fresh interpreter (a real cycle fails exactly one order) and by a test that fails if a module-level `bayesian_network` import is reintroduced into `bbn_parameterizer`. See `backend/tests/test_bbn_hardening.py::TestNoCircularImport`.
- **Original report below.**
- **Severity (original):** LOW
- **Category:** Architecture
- **What:** `bbn_parameterizer.get_center_to_region_map("classic")` imports `bayesian_network._get_center_region_map` via a deferred import (inside the function, not at module level) to avoid a circular dependency. `bayesian_network` imports from `bbn_parameterizer` at module level.
- **Why:** If anyone moves the deferred import to module level, or adds a new module-level import in the opposite direction, Python will raise `ImportError` at startup. The deferred import has a comment explaining this, but it's still fragile.
- **How:** Extract `_get_center_region_map()` into a standalone utility module (e.g., `services/center_mapping.py`) that both `bbn_parameterizer` and `bayesian_network` import without circular dependency.
- **File:** `backend/services/bbn_parameterizer.py:108`, `backend/services/bayesian_network.py`

### L-072: BBN p24 is a hybrid — competing-risk split is center-average, not patient-specific
- **Severity:** LOW (was MEDIUM)
- **Status:** LARGELY FIXED 2026-08-25 (#238 option B implemented — see resolution note below)
- **Category:** Statistical Model
- **What:** After the #211 rebuild, the BBN's headline `p_transplant_24mo` is computed by a **hybrid** (`bayesian_network._combine_outcomes`): the **WaitCategory** node drives transplant *timing* (sensitive to blood type / region / donor supply, so p24 varies by patient — AB+ beats O+ by ~0.21), while the empirically-grounded **CompetingOutcome** (the center's OBSERVED SRTR Table B7 outcomes) supplies the competing-loss drain `q = (death+delist)/(tx+death+delist)` and the death/delisting/waiting split of the non-transplant mass.
- **Why it's a limitation:** the competing-risk split is the center's **population average — not patient-specific.** A high-MELD liver candidate (or older / higher-urgency patient) faces higher true waitlist-death risk than the center's average case mix, but the BBN applies the center-average split; patient factors reach p24 only through WaitCategory *timing*, not through the competing risks. A secondary assumption: `p24 = timing × (1 − q)` treats the competing-loss share as independent of where in the wait-time distribution the patient sits.
- **Why chosen anyway:** deliberate choice (this session) of the plan's **option A + hybrid** over full patient-specific modulation (**option B / D2a**), to (a) avoid double-counting the wait signal — the observed transplant rate already embeds wait length — and (b) keep the competing-risk structure observed-grounded and low-risk. The grounding is validated (CompetingOutcome transplant prob tracks observed rates at Spearman 0.80–0.99).
- **How to revisit (#238):** modulate the observed competing-risk vector by patient factors on the cause-specific **hazard scale**, reference-anchored (a reference patient reduces exactly to the center's observed vector), with WaitCategory modulating only death/delisting (plan Q4). Needs careful design + validation.
- **File:** `backend/services/bayesian_network.py` → `_combine_outcomes`; `docs/bbn-rebuild-plan.md` §2 D2/D2a; related #226 (full credible interval, also deferred).
- **Resolution (2026-08-25, #238):** option B is implemented. `_combine_outcomes` now modulates the observed competing-risk vector on the cause-specific hazard scale by the patient's mortality multiplier (`competing_risks.get_patient_mortality_multiplier`: age × urgency × MELD), with the reference anchor (age 50-64 / urgency 2 / MELD 15-25 reduces bit-exactly to the observed vector) and the plan-Q4 double-counting guard (the transplant hazard is never modulated). Along the way the `age_mortality_multipliers` data block — silently deleted by the #104 rewrite, which had killed the BBN AgeGroup edge and MCMC-inference age modulation — was restored, parser-preserved, and CI-guarded. **Remaining residue:** delisting is not patient-modulated (no sourced patient-level delisting multipliers), and the `timing × (1−q)` independence assumption stands; both stay tracked here at LOW severity.

### L-073: BBN does not condition on cPRA / MELD / LAS — clinical severity reaches only the MC engine
- **Severity:** MEDIUM
- **Status:** OPEN (surface with #236 continuous latents; interacts with #214)
- **Category:** Statistical Model
- **What:** `bayesian_network.py` / `bbn_parameterizer.py` contain no cPRA, MELD, or LAS handling at all — WaitCategory conditions on blood type / region / donor supply only. Confirmed 2026-08-24 while closing #244: for a cPRA-98 O+ kidney patient the BBN reports p24 ≈ 0.57 at centers where the MC engine (which applies the cPRA wait multiplier) reports ≈ 0.17. The BBN's *relative* center ranking is less affected (the omission is roughly uniform across centers), but its absolute probabilities are badly over-optimistic for sensitized/high-severity patients.
- **Why:** users comparing inference modes see a large unexplained gap for exactly the patients who most need accurate numbers; the UI does not currently warn that BBN ignores severity inputs.
- **How:** (a) short-term: disclose in the UI/docs that BBN mode ignores cPRA/MELD/LAS; (b) with #236's continuous latent rebuild, add clinical severity as a continuous input to the timing latent, reusing the MC multiplier curves as priors.
- **Files:** `backend/services/bayesian_network.py`, `backend/services/bbn_parameterizer.py`

### L-074: No multi-listing model — per-center probabilities cannot be combined
- **Severity:** LOW (was MEDIUM)
- **Status:** LARGELY FIXED 2026-08-25 (#321: POST /multi-listing joins 2-5 listings via a Gaussian copula with allocation-circle-overlap correlation — see SURV-41 for the retained assumptions; per-center probabilities from /simulate still must not be naively summed)
- **Category:** Statistical Model
- **What:** There is no multiple-listing logic anywhere in the codebase. `grep -ri "multi.?list"` over `backend/` returns nothing outside test files. `/simulate` returns independent per-center probabilities and nothing combines two registrations into a joint probability.
- **Why it's a limitation:** multiple listing is one of the highest-leverage decisions a candidate actually makes, and the tool's whole premise is center comparison, so users naturally read two center estimates as combinable. They are not: the two registrations compete for **many of the same organs** (every deceased-donor match run is national and already contains every compatible candidate, so a second listing improves *rank* on donors near the second center rather than opening a disjoint donor pool). The correct combination is therefore neither the sum nor the max, and depends on the overlap between the two centers' proximity catchments.
- **Interim mitigation (done):** `faq.html#multi-listing-benefit` states explicitly that the simulator does not combine centers and that combined odds beat either alone but by less than the sum.
- **How to fix:** a joint-probability endpoint taking 2+ center IDs, modelling shared-donor overlap as a function of inter-center distance versus the 250 NM kidney circle (and the acuity circles for liver). Needs a correlation assumption that is currently unsupported by any data we hold, so this should not be shipped as a point estimate without an interval.
- **Files:** `backend/routers/simulate.py`, `backend/services/monte_carlo.py`

### L-075: Center discretion is captured only as a center-average, never per-subgroup
- **Severity:** MEDIUM
- **Status:** OPEN (documented 2026-08-25)
- **Category:** Statistical Model / Data
- **What:** Program-level discretion (whether to list a candidate, whether to accept an offer, whether to use A2/A2B, DCD, high-KDPI or HCV+ organs, whether to file urgency status exceptions, and recipient selection in the non-directed-living-donor and out-of-sequence pathways) reaches the model **only** through each center's observed aggregate SRTR numbers. The averaged downstream effect is therefore captured; the distributional effect is not.
- **Why it's a limitation:** the literature shows this discretion is both large and unevenly applied. Adjusted first-offer acceptance ranges roughly 12%–62% across heart programs, and each 10% higher acceptance is associated with ~27% lower one-year waitlist mortality (JAMA Cardiol 2020). Acceptance also differs *by patient race* at equal priority (Black heart candidates ~24% less likely to have a first offer accepted; smaller gaps for liver and lung — PMC11275659). Out-of-sequence kidney placement grew from ~2.3% of placements in 2020 to ~16% in 2023 with a 0–43% spread across OPOs, and its recipients skew older, male, and privately insured. Our per-center factors cannot express any of this, so **equity analyses that use center factors will understate between-group disparity** at a given center.
- **Note:** this is a data-availability limit as much as a modelling one. Public SRTR reporting does not break center outcomes down by demographic subgroup finely enough to fit subgroup-specific acceptance.
- **Opportunity:** SRTR now publishes a risk-adjusted **Offer Acceptance Rate Ratio** per program (OPTN Board approved Dec 2022, effective July 2023, MPSC review below 0.30 adult / 0.35 pediatric). The 2024 program year spans ~0.1 to ~5.12 across 200+ kidney programs. Ingesting this would give a directly observed center-discretion covariate, replacing the current inference-from-outcomes approach. Worth its own issue.
- **Files:** `backend/services/scoring.py`, `backend/services/outcomes.py`, `backend/routers/equity.py`

### L-076: Pediatric median wait times are derived, not observed
- **Severity:** MEDIUM
- **Status:** OPEN (documented 2026-08-26, #335)
- **Category:** Statistical Model / Data
- **What:** SRTR Table B10 (wait-time percentiles) has **no age stratification**, so no published pediatric median wait exists at any center. Pediatric wait medians shown in the app are derived by inverting the model's own 12-month competing-risks integral for the lognormal median that reproduces the center's published pediatric transplant rate.
- **Why it's a limitation:** the inversion was validated on adults, where both quantities are published, and recovers **order** far better than **magnitude** — Spearman 0.888 (kidney), 0.773 (liver), 0.731 (lung), but median absolute level error of 36–143%. Heart failed the pre-registered 0.70 threshold outright (0.670) because heart waits are short and similar across centers, so rate noise swamps the between-center signal.
- **Mitigation:** the headline 12-month probability does **not** use the inversion — the observed pediatric transplant rate sets it directly, so that number carries zero inversion error. The inversion is used only to extrapolate to other horizons and to display a median, and only for organs that pass the gate (`organs_passing` in `docs-site/static/data/pediatric-inversion.json`); failing organs fall back to the national pediatric baseline. Displayed pediatric medians are directional, not quotable.
- **Files:** `scripts/run-pediatric-inversion.py`, `backend/services/monte_carlo.py`, `docs/pediatric-inversion-report.md`

### L-077: Pediatric cohorts are small, and for lung and pancreas they are prior-dominated
- **Severity:** MEDIUM
- **Status:** OPEN (documented 2026-08-26, #335)
- **Category:** Statistical Model / Data
- **What:** Pediatric per-center estimates rest on far thinner exposure than adult ones. 30 of 106 pediatric kidney programs have under 10 person-years of follow-up, and pediatric **lung** has only 39 person-years nationally across all centers.
- **Why it's a limitation:** at that exposure a center's observed rate is mostly noise. Empirical-Bayes shrinkage toward the national pediatric baseline (weight py/(py+10) per center; py/(py+200) for the organ-level mortality multipliers) keeps the estimates stable, but it also means a thin center's number is largely the national prior wearing that center's name. Pediatric lung and pancreas mortality multipliers in particular are prior-dominated rather than measured.
- **Mitigation:** affected centers are tagged `pediatric_small_cohort` in `data_quality`, counted in the response's provenance summary, and named in the pediatric banner the simulator shows above the results table.
- **Files:** `backend/services/monte_carlo.py`, `backend/services/provenance.py`, `scripts/derive-pediatric-mortality.py`, `docs/pediatric-mortality-derivation.md`

### L-079: BBN and MCMC restrict pediatric candidates to pediatric centers but model them with adult rates
- **Severity:** HIGH
- **Status:** OPEN (documented 2026-08-26, #335)
- **Category:** Statistical Model
- **What:** All three engines narrow a pediatric candidate to centers with a pediatric program for the organ, so they agree on WHICH centers appear. Only the Monte Carlo engine also re-anchors the wait distribution to the center's observed pediatric transplant rate. The BBN and MCMC engines produce **adult numbers on a pediatric center list**.
- **Why it's a limitation:** a user who switches `inference_mode` to `bayesian` or `mcmc` gets a materially different answer for the same child with no indication that the pediatric model was not applied. Measured for kidney/O+/urgency 2 at center MOCH, the BBN **24-month** figure (0.706) falls below the Monte Carlo **12-month** figure (0.742), and BBN age 10 vs age 40 differ by only 0.002 — the entire difference coming from the new pediatric mortality multiplier rather than from any pediatric wait model.
- **Mitigation for now:** the pediatric center restriction still applies on all three engines, so no engine scores a child at a center with no pediatric program, and the pediatric mortality multipliers (#335) do reach the BBN. Monte Carlo is the default engine.
- **How to close:** give the BBN a pediatric `WaitCategory` conditioned on the observed pediatric rate, and give MCMC a pediatric likelihood term. Until then the alternative engines should either carry an explicit "adult wait model" flag in their response or refuse pediatric requests.
- **Files:** `backend/services/bayesian_network.py`, `backend/services/mcmc_inference.py`, `backend/services/monte_carlo.py` (`_pediatric_dist`)

### L-080: The published pancreas median is reconstructed, not observed, and is presented as if observed
- **Severity:** MEDIUM (downgraded from HIGH 2026-08-26 after measurement — see below; the displayed median is a misleading CLAIM, but the probabilities it feeds calibrate better than any alternative tested)
- **Status:** OPEN (documented 2026-08-26, #274 sweep; measured and re-scoped the same day)
- **Category:** Data
- **What:** `data/wait-time-distributions.json` publishes a national pancreas median wait of **22.8 months**. SRTR's Table B10 does not report a pancreas national median at all — it is **censored at ">72 months"**. Pancreas is the only organ affected; every other organ's published median is exactly the value SRTR reports.
- **Why it happens:** when the median is censored, `fit_lognormal` reconstructs it from P25 as `exp(ln(P25) + 0.6745·sigma)` with a hardcoded `sigma = 0.8`. With P25 = 13.3 that yields 22.8. The reconstruction is only as good as the sigma, and 0.8 is an arbitrary constant — it is not the value the module's own strategy chain would produce from the same percentiles (2.247), and it is not large enough to be consistent with the censoring it is compensating for.
- **How wrong:** for a lognormal with P25 = 13.3 to have a median above 72, sigma must exceed **2.50**. The published figure understates the registry's own lower bound by roughly a factor of three:

| sigma | implied median |
|---|---|
| 0.8 (published) | 22.8 months |
| 1.2 (the clamp ceiling) | 29.9 months |
| 2.247 (the strategy chain, unclamped) | 60.5 months |
| >2.50 (consistent with ">72") | >72 months |

- **Why it was not simply fixed — measured, 2026-08-26:** the obvious remedy (raise the median toward the censored bound) makes the model **worse**. Predicted p12 against observed SRTR transplant rates across 78 pancreas centers:

| median / sigma | model p12 | observed | ratio |
|---|---|---|---|
| 22.8 / 0.8 (shipped) | 0.141 | 0.127 | **1.11x** |
| 29.9 / 1.2 (chain + clamp) | 0.147 | 0.127 | 1.16x |
| 60.5 / 2.247 (chain, unclamped) | 0.173 | 0.127 | 1.36x |
| 72.0 / 2.5 (consistent with ">72") | 0.178 | 0.127 | 1.40x |

  The shipped value calibrates best — and better than kidney's 0.53x, where the median is not reconstructed at all. The mechanism is a non-monotonicity: sigma must rise with the median to stay consistent with P25, and a larger sigma fattens the **left** tail too, putting more mass below 12 months even as the median moves right. (Same effect as in the #274 clamp sweep.)

- **The real tension:** with a single-median lognormal you can have an honest displayed **median** or a well-calibrated **p12**, not both. That is evidence the parameterisation is inadequate for a censored organ rather than that one value is correct. Note also that pancreas is the organ least able to settle the question — no center has an observed cohort of 25 or more (largest is 16), so the calibration figures above use every center with any observed rate rather than the usual floor.
- **What the fix should be:** disclosure, not substitution. Keep the fitted distribution (it calibrates), mark the median as reconstructed-from-P25 in provenance and the UI, and stop presenting it as SRTR's published median — the same treatment L-076 gives derived pediatric medians. Showing ">72 months (SRTR censored)" alongside is the fuller version. What is clearly wrong is a naive swap to 72, which the first version of this entry invited. See #376.
- **Files:** `scripts/parse-srtr-reports.py` (`fit_lognormal`, censored-median branch), `data/wait-time-distributions.json`

### L-081: Delisting multipliers assume risk rises with waiting time; for most organs it falls
- **Severity:** MEDIUM
- **Status:** OPEN (documented 2026-08-26, #297)
- **Category:** Statistical Model
- **What:** The BBN's `DelistingRisk` node scales the delisting rate by `WaitCategory` with `[0.5, 0.8, 1.2, 1.8]` — one monotonic rise applied to every organ, implying risk 3.6x higher after 24 months than in the first six.
- **What the data says:** SRTR publishes national waitlist removals at 6, 12 **and** 18 months, which gives the interval hazard directly within a single cohort. Ratios to each organ's own first-six-month hazard:

| organ | 6-12mo | 12-18mo |
|---|---|---|
| kidney | 1.34 | 1.50 |
| pancreas | 1.00 | 1.24 |
| intestine | 1.29 | 0.53 |
| liver | 0.65 | 0.45 |
| heart | 0.34 | 0.24 |
| lung | 0.22 | **0.12** |

The shipped values have the **wrong sign** for liver, heart, lung and intestine. Lung's hazard in months 12-18 is roughly an eighth of its first-six-month hazard, where the model applies a 2.4x multiplier.

- **Why the data is credible:** the pattern is clinically coherent — candidates most likely to be removed as "too sick", or to die, are removed early, so the cohort still waiting at 12 months is systematically healthier than the one that started (depletion of susceptibles). It is strongest exactly where early mortality is highest (lung, heart) and reverses for kidney, whose candidates are comparatively stable on dialysis and accumulate comorbidity while waiting.
- **Why it is not yet fixed:** the CPT is a discretized tercile summary rather than a hazard model, so the multipliers do not substitute one-for-one, and any replacement must clear the calibration gate. Band 4 (>24 months) also lies beyond every published horizon and would remain an extrapolation regardless.
- **Mitigating context:** since #211 the `CompetingOutcome` node drives outcomes directly from observed rates, so `DelistingRisk` is a secondary queryable summary rather than the primary path to reported probabilities. That limits the blast radius; it does not make the node correct.
- **Files:** `backend/services/bbn_parameterizer.py` (`build_delisting_risk_cpt`), `docs/delisting-hazard-report.md`, register row BBN-04

### L-087: Centers missing SRTR data are still ranked, using national averages in place of it
- **Severity:** MEDIUM
- **Status:** DISCLOSED, NOT FIXED (documented 2026-08-27, #227 / #228)
- **Category:** Data / Presentation
- **What:** when a center has no published SRTR figure for an input, the engines substitute the national average (a 1.0 multiplier) and rank the center anyway. Measured across all 724 (center, organ) pairs the registry offers: **11** have no center wait-time factor and **35** no competing-risk factors. On the scoring path, degraded centers occupy **10 of the top 10** for pancreas and **6 of 10** for intestine; kidney, liver, heart and lung top-10s are clean.
- **Why it's a limitation:** a national average is not a neutral placeholder. It is a *typical* value, so a center with no data is scored as an average center rather than as an unknown one — and for an organ whose distribution is wide, "average" can outrank most real centers. The substitution is also concentrated in the two organs with the fewest programs, where a reader has least other evidence.
- **What shipped instead of a fix:** the affected rows are now marked `†` with the specific substituted input named, and `/score` returns per-center `data_quality` (#227). The reader can see which recommendation rests on a substitute. That is disclosure, not correction: the ranking still places these centers on borrowed data.
- **Why not shrink toward "unknown":** the honest alternative is to widen the uncertainty for these centers rather than move the point estimate, but the score ranking carries **no** uncertainty interval at all today (#386 / L-082), so there is nothing to widen. Sequencing matters here — a penalty applied to the point estimate would be a second uncited judgement of exactly the kind L-082 documents.
- **How to close:** #386's ranking intervals, with missing inputs contributing width rather than a central value; or exclude centers with no organ-level data from the ranking and list them separately as "no published data".
- **Files:** `backend/services/provenance.py`, `backend/routers/score.py`, `simulator/results-table.js` (`DQ_LABELS`, `_buildDataQualityFlag`), `backend/services/distributions.py:205`, `backend/services/competing_risks.py` (`_center_adjustment`)

### L-086: Centers with 3-patient cohorts are ranked above centers with 700
- **Severity:** MEDIUM (was HIGH — largely fixed 2026-08-27, see below)
- **Status:** PARTIALLY FIXED (documented 2026-08-27, #268 / #294)
- **Fixed for KIDNEY ONLY (#268).** Empirical-Bayes shrinkage now runs **before** the clamp in `scripts/parse-srtr-reports.py`, with prior strength estimated from the counts. Kidney centers pinned to a clamp bound went **60 → 0**, all 11 with n≤10 came off the bounds, and kidney's top 10 now holds **one** tiny-cohort center instead of four — KYKC (n=3), VACH (n=5), MIDV (n=8) and UTPC (n=9) are out; NYUC (n=437) and AZMC (n=706) are in.
- **NOT fixed for the other five, and that is a measured result rather than a scoping choice.** In a controlled comparison — same code, only the factor data differing, all six organs recomputed in **both** arms — shrinkage *degraded* Spearman against observed SRTR transplant rates for **heart (−0.0342)** and **liver (−0.0119)**. It degraded them on the n≥10 subset too (−0.0222, −0.0103), so this is a genuine loss among well-measured centers, not the metric rewarding reproduction of small-cohort noise. Lung (73 centers), pancreas (80) and intestine (17) are not estimable at all. Those five retain the defect below — liver 12/12, heart 20/20, lung 12/12 centers still pinned — and `backend/tests/test_small_cohort_factors.py::test_excluded_organs_are_still_pinned` holds that line so the fix cannot be read as a clean sweep.
- **Why kidney still matters most:** 232 centers and roughly 17,000 transplants a year, the largest population the tool serves.
- **The remaining kidney case:** TXDC (n=9) still reaches the top 10. Shrinkage bounds how much a small cohort's *risk factor* can distort the ranking; it does not stop a center ranking well on the other components.
- **Category:** Statistical Validity / Presentation
- **What:** per-center `mortality_factor` / `delisting_factor` are applied at face value regardless of how many patients they were estimated from. Because a tiny cohort produces an extreme rate estimate, and the factor is then clamped to the range 0.3–3.0, **every center with a cohort of 10 or fewer ends up pinned to a clamp bound**:

| organ | at lower bound 0.3 | at upper bound 3.0 | % of all centers pinned | centers with n≤10 on a bound |
|---|---|---|---|---|
| kidney | 60 | 2 | 27% | **11/11 (100%)** |
| liver | 39 | 8 | 32% | **12/12 (100%)** |
| heart | 64 | 19 | 56% | **20/20 (100%)** |

  A center pinned to 0.3 — the most favourable value available — then ranks near the top of the list. Applying empirical-Bayes shrinkage drops four centers out of kidney's top 10 with cohorts of **3, 5, 8 and 9**, promoting centers with **437, 706, 200 and 29**. Median cohort dropped 6, median added 318.

- **Why it's a limitation:** this is the recommendation a patient reads. A program appearing in the top 10 because three of its patients did well is not a finding about that program, and nothing in the interface signals the cohort size behind it.
- **The factors are demonstrably noise-driven at low volume:** deviation from 1.0 correlates *negatively* with cohort size for kidney (−0.344), liver (−0.340), heart (−0.288) and lung (−0.349), and small-n centers scatter more than large-n ones. Pancreas inverts (+0.427), but its median cohort is 3, so that split carries no information — it should not be shrunk on this evidence.
- **Not visible in the usual aggregate check.** Shrinkage moves mean p24 by ≤0.005 and leaves rank correlation at 0.987–0.999, which reads as "nothing changes", while kidney's top-10 membership changes by 40%. This is the third instance of the same lesson in this project (L-082's weights, L-083's lung near-tie): **a high rank correlation is not evidence of a stable top**, and any sweep reporting only ρ can miss the thing users see.
- **This qualifies #294's "passes" verdict.** That sweep perturbed the clamp bound by ±20% and reported worst ρ 0.973. It tested sensitivity to the bound's *value*, not the interaction between the clamp and *cohort size*, and aggregate ρ cannot show a top-10 reshuffle.
- **What would help:** empirical-Bayes shrinkage toward the organ mean, with strength `k` estimated from the data rather than chosen — `Var(f) = tau² + c/n` solved on a small-n/large-n split gives k = 18.4 (kidney), 32.4 (liver), 22.4 (heart), 10.6 (lung). **Shrinkage must be applied before the clamp**, or the clamp re-pins the centers it is meant to rescue. Failing that, disclose the cohort size next to any center whose factor rests on a small n.
- **Files:** `data/competing-risks-centers.json`, `backend/services/competing_risks.py` (`_center_adjustment`), `data/srtr-observed-rates.json` (the cohort sizes, already shipped)

### L-085: Blood type cannot change which center is recommended
- **Severity:** HIGH
- **Status:** OPEN (documented 2026-08-26, `docs/patient-sensitivity-report.md`)
- **Category:** Model Structure / Presentation
- **What:** sweeping one patient attribute at a time across its realistic range, blood type reaches **exactly one** sub-score — `medicalCompatibility` — which is the sub-score that is identical at every center (L-084). The O− and AB+ orderings are not merely similar but **literally the same list**, for every organ:

| organ | attribute | sub-scores reached | ρ | order identical |
|---|---|---|---|---|
| kidney | blood_type | `medicalCompatibility` | **1.00000** | **yes** |
| kidney | cpra | `waitTime` | 0.760 | no |
| liver | blood_type | `medicalCompatibility` | **1.00000** | **yes** |
| liver | meld | `waitTime` | 0.760 | no |
| heart | blood_type | `medicalCompatibility` | **1.00000** | **yes** |
| lung | blood_type | `medicalCompatibility` | **1.00000** | **yes** |
| lung | las | `waitTime` | 0.947 | no |

- **Magnitudes are personalised; the ranking is not.** In the Monte Carlo path, sweeping kidney blood type O−→AB+ moves the mean 24-month probability by **+0.2524** — a large and correct effect — while the center ordering moves by ρ 0.99875. Blood type changes a candidate's numbers a great deal and their recommended center not at all.
- **The two engines also disagree about how much the patient matters.** For kidney cPRA the scoring path reports ρ 0.760 and the simulation path ρ 0.996 — a large disagreement on the same question, with both shown to users in the same table. Blood type is what they agree on, and they agree it changes nothing.
- **Also reaching nothing:** `sex` reaches no scoring sub-score for kidney or liver and only the inert `medicalCompatibility` for heart and lung; in simulation it moves kidney p24 by +0.0265 and **liver, heart and lung by exactly 0.0000**. So for liver, heart and lung it is a required field that changes no output at all. `urgency` reaches nothing for liver and lung, which are MELD- and LAS-driven.
- **Important counterweight — the ranking IS patient-dependent, but coarsely.** A one-at-a-time sweep cannot establish that everyone gets the same list, and concluding that would overstate this row. Walking a grid of realistic patients:

| organ | patients | distinct rankings | distinct #1 | median pairwise ρ | median top-10 overlap |
|---|---|---|---|---|---|
| kidney | 108 | **15** | 2 | 0.8147 | 7/10 |
| liver | 36 | 9 | 1 | 0.9314 | 9/10 |
| heart | 36 | 9 | 1 | 0.9853 | 9/10 |
| lung | 36 | 6 | 3 | **0.9997** | 10/10 |

  Kidney genuinely personalises (median ρ 0.81 between two real candidates, top-10 overlap down to 2/10) — cPRA does real work. Lung essentially does not (ρ 0.9997, 10/10 overlap); its 3 distinct leaders are L-083's near-tie, not personalisation. But 108 kidney candidates yielding only **15** distinct rankings shows the personalisation is coarse: a small menu of lists rather than a per-patient result, which follows from only two or three inputs reordering anything.
- **Why it's a limitation:** the inconsistency, not the invariance. cPRA reorders centers substantially (ρ 0.760) while blood type reorders nothing (ρ 1.000). Both are immunological constraints on donor-pool access, and both plainly interact with a center — a program's sensitised-patient protocol matters for a high-cPRA candidate, and a center's ABO-specific donor pool matters for an O candidate. One has a center interaction and the other has none, with no documented reason. That reads as an artifact of where each attribute was wired rather than a modelling position.
- **What this does NOT say:** that the ranking *should* turn on blood type. Much of what makes a center good is a property of the center, and it is reasonable that the best center for one candidate is often the best for another. The defect is that this is undisclosed — a candidate entering their blood type reasonably infers it personalises the recommendation.
- **What would help:** (1) state plainly which inputs affect the ranking and which affect only the numbers; (2) stop requiring inputs that reach nothing, or say they are recorded for other purposes.
- **(3) was attempted and failed — see `docs/abo-center-competition-report.md` (2026-08-27).** A per-center ABO competition term was built and gated. It worked mechanically: blood type began reordering centers at ρ 0.878 (kidney), 0.858 (liver), 0.902 (heart), comparable to cPRA's 0.760. But it *degraded* agreement between the composite score and observed SRTR transplant rates — mean −0.0195, improved in 2 of 12 organ/blood-type combinations — and the premise behind it is unsupported: a center's share of a blood group does not predict its transplant rate for that group (1 of 12 correlations reaches p<0.05 in the assumed direction, which is chance; several run the opposite way).

  Likely because allocation is ABO-matched on both sides — a program serving a population richer in type B also receives more type B donors from its OPO, so competition and supply largely cancel.

  **This changes the status from "pending work" to "known structural property".** Fixing it would need a center-by-ABO *outcome* measure — observed transplant rate per center per blood group — which SRTR does not publish; Tables B8-B9 give the mix, not the rate. The term was reverted, not shipped.
- **Files:** `scripts/run-patient-sensitivity.py`, `docs-site/static/data/patient-sensitivity.json`, `backend/services/scoring.py` (`_medical_compatibility`, `_wait_time_score`)

### L-084: A quarter of the composite score is a constant that cannot affect the ranking
- **Severity:** HIGH
- **Status:** OPEN (documented 2026-08-26, `docs/category-variance-report.md`)
- **Category:** Model Structure / Presentation
- **What:** `medicalCompatibility` carries the **largest weight in the model (0.25)** and is **identical for every center**. `_medical_compatibility()` (`backend/services/scoring.py:86`) takes only the patient profile — its own docstring says *"Pure patient-profile scoring — no geographic data needed"* — so it is center-invariant by construction. Measured across all six organs, its between-center SD is 0.0 (2.8e-14, float noise; one distinct value, e.g. 92.8 for the kidney reference patient at all 233 centers).
- **Why it's a limitation:** a weight can only move the ranking through a sub-score that *varies* between centers. This one contributes the same constant to every total, so a quarter of the advertised weighting is inert. Three consequences:
  1. **The weight slider for the highest-weighted category does not work.** Changing it from 0.25 to 0.0 leaves the ranking identical up to rounding (ρ 0.99995; the 51 of 233 positions that move are near-ties reshuffled by `total` being rounded to 1 dp, not a real re-ranking). A user who decides medical compatibility matters most to them, and drags the slider up, gets the same answer.
  2. **The displayed weights misdescribe the ranking.** What actually drives it is `weight × between-center SD`:

| organ | waitTime | hospitalQuality | donorAvailability | everything else | medicalCompatibility |
|---|---|---|---|---|---|
| kidney | 50.6% | 21.2% | 13.4% | 14.9% | **0.0%** |
| liver | 52.9% | 21.0% | 12.3% | 13.8% | **0.0%** |
| heart | 52.3% | 21.5% | 10.3% | 15.9% | **0.0%** |
| lung | 31.4% | 33.2% | 14.7% | 20.7% | **0.0%** |
| pancreas | 54.4% | 14.2% | 12.5% | 18.9% | **0.0%** |
| intestine | 58.0% | 18.1% | 11.2% | 12.7% | **0.0%** |

  3. **It compresses the visible score range,** making centers look more alike than the model says they are. For the kidney reference patient the constant adds 23.2 points to every center; the displayed spread is 57.8–85.3 (27.5 points) where the rank-relevant spread is 46.2–82.8 (36.6 points).
- **This also explains L-082 and L-083.** The ordinal-simplex study found the weight *magnitudes* nearly inert partly because the largest one sits on a constant and the ranking is carried by `waitTime`. And lung's undetermined top (L-083) is exactly the organ where `waitTime` (31.4%) and `hospitalQuality` (33.2%) are near-tied for dominance instead of `waitTime` winning outright — so which one the sampled weights favour decides the leader.
- **What this does NOT say:** that medical compatibility is irrelevant to a transplant candidate, or that the sub-score is wrong. It is a real property of the patient and belongs in a patient-level match score. The defect is that it is presented as a *center* comparison input and given the largest weight there.
- **What would help:** (1) disclose what actually drives the ranking rather than only the weight vector — the `rank_driving_share` table above is cheap to surface; (2) decide whether the sub-score *should* be center-specific — **the ABO route was measured and rejected** (`docs/abo-center-competition-report.md`): it degraded score-vs-observed agreement and its premise is unsupported in the data. CPRA handling, size matching and acceptance thresholds remain untested routes; (3) until then, stop implying the slider affects the ranking.
- **Files:** `backend/services/scoring.py:86` (`_medical_compatibility`), `scripts/run-category-variance.py`, `docs-site/static/data/category-variance.json`, register row SCORE-01

### L-083: For lung, the top-ranked center is a near-tie among eight programs
- **Severity:** MEDIUM
- **Status:** OPEN (documented 2026-08-26, `docs/ordinal-weight-robustness-report.md`)
- **Category:** Presentation
- **What:** sampling the weight magnitudes over everything the shipped category ordering permits (see L-082), the center that ranks #1 changes constantly for lung and not at all for kidney or heart:

| organ | shipped top center | share of draws it leads | distinct centers that lead |
|---|---|---|---|
| kidney | OHCC | 100% | 1 |
| heart | COUC | 100% | 1 |
| liver | FLUF | 98% | 3 |
| intestine | OHCC | 86% | 5 |
| pancreas | ILUI | 65% | 4 |
| lung | INIM | **25%** | **8** |

- **Why it's a limitation:** overall rank correlation stays at ρ 0.99 for lung throughout, so the aggregate stability statistics the project reports look reassuring while the specific claim a user actually reads — "this is your best center" — is not supportable there. A high ρ and a determinate top are different properties, and only the first is currently measured anywhere.
- **What this does NOT say:** that INIM is the wrong answer for lung. It remains both the modal choice and the rank-order-centroid choice; it is simply not distinguishable from seven others on this evidence. Pancreas (65%, 4 centers) is a milder version.
- **Surfaced (2026-08-27).** The results table now states how many centers could be ranked #1 whenever that is more than one: *"N centers could be ranked #1 on this evidence — …"*. Measured against the live API: **lung 3, heart 7, liver 7, kidney 10**.

  Two things learned building it. The endpoint's own `tie_groups` are **unusable** for this — their overlap test is transitive (A overlaps B, B overlaps C ⇒ one group), so the leading group is *every* center for every organ (74/74 lung, 233/233 kidney). Counting intervals that include rank 1 is non-transitive and answers the reader's actual question. And on this measure **kidney's top is the least determined (10), not lung's (3)** — L-083's original evidence came from *weight* perturbation (#382's ordinal-simplex draws) whereas this is *data* bootstrap. Both are real; they are different uncertainty sources and rank the organs differently, which is worth keeping in view.
- **Files:** `scripts/run-ordinal-weight-robustness.py`, `docs-site/static/data/ordinal-weight-robustness.json`, `docs/ordinal-weight-robustness-report.md`

### L-082: The headline center ranking depends materially on eight uncited weights
- **Severity:** HIGH
- **Status:** OPEN (documented 2026-08-26, SCORE-01)
- **Category:** Clinical Assumption / Presentation
- **What:** Every center score is a weighted sum of eight categories (`medicalCompatibility` 0.25, `waitTime` 0.20, `donorAvailability` 0.18, `hospitalQuality` 0.15, `geographic` 0.10, `healthDemographics` 0.07, `policy` 0.03, `socioeconomic` 0.02). The register records these magnitudes as `uncited`. The results table sorts by score by default, so this is the headline output.
- **Why it's a limitation:** the existing assumption sweep perturbs one category by ±20% and finds the ranking stable — but that tests robustness to a *nudge*, not dependence on *whose judgement produced the numbers*. Measured against defensible alternative weightings (a candidate prioritising speed of access; one prioritising program outcomes; one with no view at all):

| | |
|---|---|
| worst Spearman vs shipped | **0.624** |
| worst top-10 overlap | **3/10** |
| **top-ranked center changes in** | **13 of 16 comparisons** |

  A candidate reading "the best center for me" gets a different answer under most defensible weightings. For contrast, every other constant measured this way in this project is inert — the BBN discretization split holds at ρ 0.9987 swung from near-deterministic to barely informative, and removing the donor-supply effect entirely leaves ρ 0.9957.

- **Not covered by the uncertainty already reported:** the rank intervals (#313) bootstrap the *probability* estimates and rank by `p24` — a different quantity from the composite score, and an interval that varies the data while holding the weights fixed. **The score ranking carries no interval at all.**
- **What this does NOT say:** that the shipped weights are wrong. There is no ground truth — "which center is best for me" is a preference, not a fact, and a weighted composite is a reasonable way to express one. Sourcing the magnitudes would help but cannot resolve it: no literature fixes how one candidate should trade program quality against travel distance.
- **What would help:** (1) make the dependence visible — the weights are already user-adjustable, so the ranking should say it reflects a particular weighting and ideally show how much it moves under others; (2) report a weight-uncertainty interval alongside the sampling one. Neither is "pick better numbers".
- **Partially mitigated (2026-08-26, #386):** (1) is now shipped. `POST /weight-range` re-scores every center under the app's own four published presets and the results table annotates each row with its rank span, so the dependence is visible at the point of use rather than only in this document. On kidney the median center's span is 34 positions (max 107), while the top of the ranking is genuinely stable — which is the useful distinction a candidate needs.

  **This does not close the limitation.** Four presets are a lower bound on the disagreement, not an interval: they are four points chosen by the same authors as the shipped weights, so they under-sample the space that produced the 0.624 worst-case above. (2) — a principled weight-uncertainty interval on the composite score — remains open, and the score ranking still carries no interval of its own.

- **Sharpened (2026-08-26, `docs/ordinal-weight-robustness-report.md`):** the eight weights encode two separable claims — an **ordering** (medical compatibility above travel above local socioeconomics) and **magnitudes** (`.25` rather than `.30`). Only the magnitudes are uncited. Holding the ordering fixed and sampling uniformly from the ordered simplex `{w₁≥…≥w₈, Σ=1}` — which needs no spread parameter, and whose sampler is verified against the closed-form order statistics — gives **worst-case ρ 0.905 across all six organs**, against 0.624 above.

  **So the uncited magnitudes are not what this limitation caught.** The 0.624 comes from *reordering* the categories, i.e. from a genuinely different patient preference, which the presets and sliders already expose and which is not an error. Corroborating: the rank-order centroid, derived from the ordering alone, agrees with the shipped weights at ρ 0.9899–0.9973 and picks the same top center for all six organs.

  **Caveat — part of that result is an artifact, see L-084.** The first slot in the ordering receives the largest share of sampled mass by construction, and it is `medicalCompatibility`, which is *identical at every center*. Every draw therefore spends its biggest component on a constant, so the sampling is systematically less potent than it looks. The honest form of the finding is narrower: *given the shipped ordering **and the current sub-scores**, the uncited magnitudes do not materially move the ranking.* If `medicalCompatibility` is made center-specific (#390), this must be re-run before the conclusion carries over.

  This retargets rather than closes the row: **the ordering is now the uncited assumption that matters**, and justifying it is the SCORE-01 clinical question. Severity stays HIGH because the headline output still depends on an unjustified judgement — just a different one than recorded above.

- **Related finding — see L-083:** high ρ does not mean the *top* is determined. For lung, 8 different centers take first place across the draws while ρ holds at 0.99.
- **Files:** `backend/services/scoring.py` (`DEFAULT_WEIGHTS`), `backend/services/weight_range.py`, `docs/scoring-weight-sensitivity-report.md`, register row SCORE-01

### L-078: PELD is mapped onto MELD's priority thresholds without a published equivalence
- **Severity:** MEDIUM
- **Status:** OPEN (documented 2026-08-26, #335)
- **Category:** Clinical Assumption
- **What:** A pediatric liver candidate's PELD score drives the same allocation-priority multiplier that MELD drives, using identical thresholds (>=35, >=25, >=15).
- **Why it's a limitation:** the two scores order candidates within the same allocation system, but they are computed from different inputs — PELD uses albumin, INR, bilirubin, growth failure and age at listing, where MELD uses creatinine, INR, bilirubin and sodium — and PELD's distribution sits lower. Applying MELD's cut-points to PELD therefore probably **under-prioritizes** pediatric candidates, in the direction that matters least for a tool meant to help them.
- **Why it is nonetheless wired:** the alternative shipped worse. `peld` was accepted by the schema, range-validated, and rendered in the simulator and shared patient form while being read by no backend code at all — a candidate with PELD 40 and one with PELD -5 produced byte-identical results with no warning. A field that silently does nothing is a stronger failure than one with a documented assumption behind it.
- **How to close:** map PELD to allocation priority from OPTN pediatric liver policy or an SRTR pediatric liver cohort, rather than by analogy to MELD. This is on the list for the faculty face-validity review (#107).
- **Files:** `backend/services/scoring.py`, register row SCORE-31

### L-071: Documentation still references "22 cities" in ~15 places
- **Severity:** LOW
- **Status:** FIXED (2026-08-25, #305 — docs-site/README swept; remaining mentions are explicitly historical. Backend comments/docstrings retire with the final #293 code deletion.)
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
