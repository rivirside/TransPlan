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
- **Status:** OPEN
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
- **Status:** OPEN
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
- **Status:** OPEN
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
- **Status:** OPEN
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
- **Status:** OPEN
- **Details:** There is no `fetch-donor-registration.js` in the scripts/ directory. The `donor-registration.json` file is permanent seed data that can never be refreshed by the automated pipeline. This file contains stateRegistrationRates, livingDonorProgramStrength, and populationFactors — three critical inputs to the Donor Availability category (18% weight).
- **File:** Missing: `scripts/fetch-donor-registration.js`
- **Fix:** Create a fetch script sourcing state registration rates from Donate Life America or HRSA. livingDonorProgramStrength and populationFactors may need to remain manually curated.

### L-034: srtr-reports.json is loaded but never read by algorithm
- **Severity:** MEDIUM
- **Status:** OPEN
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
- **Status:** OPEN
- **Details:** Lines 41-44 of `fetch-cost-of-living.js` define `REGION_SERIES` mapping South and Midwest regions to series IDs. This constant is never referenced anywhere in the file — the estimates section uses hardcoded multipliers against specific city results instead.
- **File:** `scripts/fetch-cost-of-living.js` lines 41-44
- **Fix:** Remove the dead constant or refactor estimates to actually use regional series.

### L-038: Orphan city entries in fallback data
- **Severity:** LOW
- **Status:** OPEN
- **Details:** Several fallback data structures contain cities not in our 22-city set: Phoenix in traffic traumaScores fallback (algorithm.js), Montana/Alaska in stateRegistrationRates fallback (not cities — these are states but used as keys alongside city names), Boston/Denver in socioeconomic.json (not in our city list). These are harmless but create confusion about the canonical city list.
- **File:** `algorithm.js` (traffic fallback), `data/manual/socioeconomic.json`
- **Fix:** Remove non-canonical entries; add a lint rule checking all city keys against the canonical list in utils.js.

### L-039: Missouri missing from donor registration data
- **Severity:** LOW
- **Status:** OPEN
- **Details:** `donor-registration.json` has no entry for Missouri, but St. Louis is in Missouri. The algorithm falls back to `35` (default rate) for Missouri. St. Louis donor availability scoring is underweighted because its state registration rate hits the fallback instead of a real value.
- **File:** `data/donor-registration.json`
- **Fix:** Add Missouri registration rate to the JSON file and DEFAULTS.

### L-040: Methodology text inaccuracies (partially fixed)
- **Severity:** MEDIUM
- **Status:** FIXED
- **Details:** Multiple methodology text issues found during review: (a) algorithm.js header still said "success probability" — fixed; (b) Example calculation said "385 kidney transplants/year" but real data is 350 — fixed; (c) Hospital Quality listed "Outcomes data" and "Research activity" as factors not in the algorithm — replaced with "Insurance acceptance" which IS in algorithm; (d) Data sources listed CMS Hospital Compare and CDC WONDER instead of actual sources (SRTR, BLS, NHTSA FARS, EPA AQS) — fixed; (e) Nashville/Indianapolis centerReputation and specializations fallbacks were stale — synced.

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
