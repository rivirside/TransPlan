# TransPlan - Data Provenance Registry

> **Track every data dependency:** what data we use, where it comes from, whether it's automated, and what file it lives in.

---

## Phase 1 Data (Scoring Engine)

| Data Point | Source | API/Fetch Script | Automated? | Data File | Freshness |
|------------|--------|-----------------|------------|-----------|-----------|
| Air quality index (per city) | EPA AQS API | `scripts/fetch-air-quality.js` | Yes (weekly CI) | `data/air-quality.json` | Requires `EPA_API_KEY` |
| Cost of living index | BLS CPI API | `scripts/fetch-cost-of-living.js` | Yes (weekly CI) | `data/cost-of-living.json` | Requires `BLS_API_KEY` |
| Hospital quality metrics | CMS Provider Data API | `scripts/fetch-hospital-quality.js` | Yes (weekly CI) | `data/hospital-quality.json` | Multi-strategy query (SQL/filter/legacy) |
| Health demographics (diabetes, obesity, etc.) | CDC SODA API | `scripts/fetch-health-data.js` | Yes (weekly CI) | `data/health-demographics.json` | Public, no key needed |
| Traffic fatality rates | NHTSA FARS CSV bulk download | `scripts/fetch-traffic.js` | Yes (weekly CI) | `data/traffic-fatalities.json` | CSV from static.nhtsa.gov (L-045 fixed) |
| Donor registration rates | Donate Life America 2019 Annual Report (2018 DDR) | Manual extraction from PDF (p.27) | No (report-based) | `data/donor-registration.json` | `stateRegistrationRates` from DLA DDR/EDDR. `livingDonorProgramStrength` and `populationFactors` remain manually curated (no public dataset). |
| SRTR transplant volumes | SRTR Program-Specific Reports | `scripts/check-srtr-updates.js` (hash check only) | Partial | `data/manual/srtr-reports.json` | Manual data entry from srtr.org; script checks for updates |
| Center specializations | SRTR + center press releases | None | No | `data/manual/srtr-reports.json` | Manual curation |
| Climate comfort scores | Derived from NOAA/historical data | None | No | `data/manual/climate-scores.json` | Static; changes rarely |
| State donation policy tiers | HRSA + state legislation review | None | No | `data/manual/policy-tiers.json` | Manual; review annually |
| Socioeconomic support scores | Transplant support rubric (custom) | None | No | `data/manual/socioeconomic.json` | Manual curation |
| City wait time factors | Derived from SRTR relative wait times | None (hardcoded in algorithm.js) | No | `algorithm.js` (cityWaitTimeFactors) | Hardcoded; duplicated in `data/wait-time-distributions.json` |

### Automation Infrastructure

- **GitHub Actions workflow:** `.github/workflows/fetch-data.yml` — runs weekly (Monday 6am UTC) + manual dispatch
- **SRTR check workflow:** `.github/workflows/check-srtr-updates.yml` — bimonthly hash check
- **All scripts use `continue-on-error`** so one API failure doesn't block others
- **`mergeDataFile` pattern** prevents fetch scripts from destroying seed data on empty responses

---

## Phase 2 Data (Probabilistic Engine)

| Data Point | Source | API/Fetch Script | Automated? | Data File | Freshness |
|------------|--------|-----------------|------------|-----------|-----------|
| National median wait times (per organ) | SRTR PSR Table B10 (Jan 2025 release) | `scripts/parse-srtr-reports.py` | Semi (run manually) | `data/wait-time-distributions.json` | Biannual SRTR releases |
| Log-normal sigma (distribution spread) | Fitted from SRTR P10/P25 percentiles | `scripts/parse-srtr-reports.py` | Semi | `data/wait-time-distributions.json` | Biannual SRTR releases |
| Blood type wait time multipliers | OPTN wait time data by blood type | None | No | `data/wait-time-distributions.json` | Literature-derived; Table B10 doesn't stratify by blood type |
| cPRA wait time multipliers (kidney) | OPTN allocation data + literature | None | No | `data/wait-time-distributions.json` | Manual; based on OPTN cPRA point tiers |
| MELD wait time multipliers (liver) | OPTN MELD allocation policy | None | No | `data/wait-time-distributions.json` | Manual; based on MELD allocation rules |
| LAS wait time multipliers (lung) | OPTN LAS allocation policy | None | No | `data/wait-time-distributions.json` | Manual; based on LAS allocation rules |
| City wait time factors (22 cities) | SRTR PSR Table B10 center-level P50 / national P50 | `scripts/parse-srtr-reports.py` | Semi | `data/wait-time-distributions.json` | Biannual SRTR releases |
| Waitlist annual mortality rates (per organ) | SRTR PSR Table B7 (12-month died-on-waitlist %) | `scripts/parse-srtr-reports.py` | Semi | `data/competing-risks.json` | Biannual SRTR releases |
| Waitlist annual delisting rates (per organ) | SRTR PSR Table B7 (12-month removal rates) | `scripts/parse-srtr-reports.py` | Semi | `data/competing-risks.json` | Biannual SRTR releases |
| Urgency mortality multipliers | OPTN allocation status categories | None | No | `data/competing-risks.json` | Manual; literature-derived |
| MELD mortality multipliers (liver) | OPTN MELD allocation policy | None | No | `data/competing-risks.json` | Manual; literature-derived |
| City mortality/delisting adjustments (22 cities) | SRTR PSR Table B7 center / national ratios | `scripts/parse-srtr-reports.py` | Semi | `data/competing-risks.json` | Biannual SRTR releases |
| SRTR center-to-city mapping | SRTR center directory | None | No | `data/srtr-center-mapping.json` | Manual; update when centers change |
| SRTR raw Excel files | SRTR PSR National Summary Data | `scripts/fetch-srtr-excel.py` | Semi | `data/srtr-raw/` (gitignored) | Biannual; re-downloadable |
| Organ recovery rates (6 organs × 5 COD) | PMC10329409 (Sundaram 2023, OPTN 2005–2019), cross-validated against OPTN 2023 national data (hrsa.unos.org, March 2026) | `scripts/validate-recovery-rates.py` | No (manual cross-validation) | `data/cause-of-death-by-region.json` → `organRecoveryRates` | 15/30 cells updated where OPTN 2023 drift >10%. Re-validate annually. |
| State COD proportions (51 states) | CDC 2017 mortality data (data.cdc.gov bi63-dtpu + xkb8-kh2a) | `scripts/fetch-cod-data.js` | Yes (weekly CI) | `data/cause-of-death-by-region.json` → `stateCauseOfDeathProportions` | Donor-eligibility calibration via Nelder-Mead weights |

---

## Phase 4 Data (Historical Trends)

| Data Point | Source | API/Fetch Script | Automated? | Data File | Freshness |
|------------|--------|-----------------|------------|-----------|-----------|
| Historical SRTR PSR Excel archives (2019–2025) | SRTR Program-Specific Reports archive | Manual download (see below) | No | `data/srtr-raw/historical/*.zip` (gitignored) | Biannual SRTR releases |
| Historical trend metrics (year-over-year) | Parsed from historical Excel archives | `scripts/parse-srtr-reports.py` (`parse_historical_trends()`) | Semi | `data/srtr-historical.json` | Depends on historical downloads |

### How to Download Historical SRTR PSR Archives

The SRTR website provides archived national center-level summary data as zip files containing per-organ Excel files. These are **not** available via a direct/predictable URL pattern — you must use the dropdown on the website or follow the mapping below.

**Steps:**
1. Go to https://www.srtr.org/reports/program-specific-reports/
2. Scroll to **"National Center-Level Summary Data by Organ"** section
3. Find the text: *"Access archived national center-level summary data below (the zip files contain all organs)."*
4. Select a period from the **second dropdown** (the archive dropdown, not the current organ dropdown)
5. Click the **Download** link that appears

**URL pattern:** `https://www.srtr.org/assets/media/PSRdownloads/csrs_tables_all/csrs_final_tables_{YYMM}all.zip`

The `{YYMM}` code is **not** the release date — it's approximately 2 months before. The complete mapping:

| Release Period | File Code | Zip Filename |
|---|---|---|
| January 2019 | 1811 | `csrs_final_tables_1811all.zip` |
| July 2019 | 1905 | `csrs_final_tables_1905all.zip` |
| January 2020 | 1911 | `csrs_final_tables_1911all.zip` |
| August 2020 | 2006 | `csrs_final_tables_2006all.zip` |
| January 2021 | 2011 | `csrs_final_tables_2011all.zip` |
| July 2021 | 2105 | `csrs_final_tables_2105all.zip` |
| January 2022 | 2111 | `csrs_final_tables_2111all.zip` |
| July 2022 | 2205 | `csrs_final_tables_2205all.zip` |
| January 2023 | 2211 | `csrs_final_tables_2211all.zip` |
| July 2023 | 2305 | `csrs_final_tables_2305all.zip` |
| January 2024 | 2311 | `csrs_final_tables_2311all.zip` |
| July 2024 | 2405 | `csrs_final_tables_2405all.zip` |
| January 2025 | 2411 | `csrs_final_tables_2411all.zip` |
| July 2025 | 2505 | `csrs_final_tables_2505all.zip` |

Each zip contains 8 per-organ Excel files: `csrs_final_tables_{YYMM}_{organ}.xls` where organ codes are: `HL` (Heart-Lung), `HR` (Heart), `IN` (Intestine), `KI` (Kidney), `KP` (Kidney-Pancreas), `LI` (Liver), `LU` (Lung), `PA` (Pancreas).

**Important notes:**
- The previous `fetch-srtr-excel.py --historical` attempt failed because it used the wrong URL pattern (individual release codes like `1901`, not the actual `1811` codes, and missing `all` suffix)
- These zip files are large (8–12 MB each) and gitignored
- SRTR publishes new PSR data twice yearly (January and July); check the dropdown for new periods

---

## Phase 6 Data (Spatial Geographic Modeling)

### Phase 6A: Center-Level Data

| Data Point | Source | Processing | Automated? | Data File | Freshness |
|------------|--------|-----------|------------|-----------|-----------|
| All SRTR centers (~248) | SRTR PSR Excel files (6 organs) | `scripts/parse-srtr-reports.py --all-centers` | Semi (run manually) | `data/srtr-all-centers.json` | Biannual SRTR releases |
| Center geographic coordinates | Nominatim (OSM) + manual lookup (Google Maps, March 2026) | `scripts/geocode-centers.py` (initial), `scripts/verify-geocoding.py` (verification) | No | `data/srtr-all-centers.json` | All 248 centers verified March 2026. Sources: 133 nominatim, 32 nominatim_verified (upgraded from city-center), 83 manual_verified (cross-validated or Google Maps). No city_mapping sources remain. |
| Center-level wait time distributions | SRTR PSR Table B10 (all centers) | `scripts/parse-srtr-reports.py --all-centers` | Semi | `data/wait-time-distributions-centers.json` | Biannual SRTR releases |
| Center-level competing risks | SRTR PSR Table B7 (all centers) | `scripts/parse-srtr-reports.py --all-centers` | Semi | `data/competing-risks-centers.json` | Biannual SRTR releases |
| Center-level post-transplant outcomes | SRTR PSR Tables C5-C20 (all centers) | `scripts/parse-srtr-reports.py --all-centers` | Semi | `data/post-transplant-outcomes-centers.json` | Biannual SRTR releases |
| Center-to-city mapping (22 focus cities) | Manual curation from SRTR center directory | None | No | `data/srtr-center-mapping.json` | Manual; update when centers change |

### Phase 6B: Dense Spatial Data

| Data Point | Source | API/Fetch Script | Automated? | Data File | Freshness |
|------------|--------|-----------------|------------|-----------|-----------|
| OPO county-to-OPO mapping (3,225 counties → 60 OPOs) | HRSA Data Warehouse Excel (`data.hrsa.gov`) | `scripts/build-opo-mapping-hrsa.py` | No (one-time parse) | `data/opo-mapping.json` | Authoritative county FIPS → OPO assignments. 248 centers mapped. 98 multi-OPO overlap counties noted. |
| County-level health demographics (3,144 counties) | CDC PLACES API (SODA) | `scripts/fetch-health-data-counties.js` | Yes (weekly CI) | `data/health-demographics-counties.json` | Public, no key needed. Multi-release fallback (2025 + 2024 GIS for PA). 4 indicators: diabetes, obesity, hypertension, smoking. CKD not available in CDC PLACES. |
| Per-monitor air quality data (~2,000-4,000 monitors) | EPA AQS annualData API | `scripts/fetch-air-quality-monitors.js` | Yes (weekly CI) | `data/air-quality-monitors.json` | Requires `EPA_EMAIL` + `EPA_API_KEY`. Lat/lon from existing annualData response fields. |

### Phase 6B: Spatial Interpolation

| Data Point | Source | Processing | Automated? | Data File | Notes |
|------------|--------|-----------|------------|-----------|-------|
| Interpolated spatial surfaces (24 layers) | Derived from center-level + city-level + county-level + monitor-level JSON data | `backend/services/spatial_interpolation.py` (RBF/IDW) | Runtime (computed on first query) | In-memory cache | Auto-prefers dense sources (county/monitor) over city-level with fallback |
| UNOS allocation circle analysis | Computed from center coordinates + haversine distances | `backend/services/allocation_geography.py` | Runtime | In-memory | 250nm/500nm circles per UNOS allocation policy |
| Haversine distance (nautical miles) | Standard geodesic formula | `backend/utils.py` (`haversine_distance_nm`) | Runtime | N/A | Conversion: miles × 0.868976 = nautical miles |

### Spatial Data Layers

The interpolation engine supports 24 layers, derived from existing data files. The engine auto-prefers dense data sources when available, falling back to city-level aggregates:

| Layer | Source Data | Point Density | Notes |
|-------|------------|---------------|-------|
| `air_quality` | `data/air-quality-monitors.json` (dense) → `data/air-quality.json` (fallback) | ~2,000-4,000 (dense) / ~20 (fallback) | Per-monitor EPA AQS data preferred; city-level fallback when monitors unavailable |
| `cost_of_living` | `data/cost-of-living.json` (22 cities) | ~20 points | City-level CPI index (no dense source available) |
| `health_diabetesRate` | `data/health-demographics-counties.json` (dense) → `data/health-demographics.json` (fallback) | ~2,956 (dense) / ~20 (fallback) | County-level CDC PLACES preferred |
| `health_obesityRate` | `data/health-demographics-counties.json` (dense) → `data/health-demographics.json` (fallback) | ~2,956 (dense) / ~20 (fallback) | County-level CDC PLACES preferred |
| `health_ckdRate` | `data/health-demographics.json` | ~20 points | City-level only — CKD not available in CDC PLACES |
| `health_hypertensionRate` | `data/health-demographics-counties.json` (dense) → `data/health-demographics.json` (fallback) | ~2,956 (dense) / ~20 (fallback) | County-level CDC PLACES preferred |
| `health_smokingRate` | `data/health-demographics-counties.json` (dense) → `data/health-demographics.json` (fallback) | ~2,956 (dense) / ~20 (fallback) | County-level CDC PLACES preferred |
| `wait_time_factor_{organ}` | `data/wait-time-distributions-centers.json` | 100-233 points | Center-level SRTR Table B10 |
| `mortality_factor_{organ}` | `data/competing-risks-centers.json` | 100-233 points | Center-level SRTR Table B7 |
| `graft_survival_{organ}` | `data/post-transplant-outcomes-centers.json` | 80-200 points | Center-level SRTR C-series |

**Data provenance note:** All spatial interpolation layers are derived from existing, provenance-tracked data files. No new external data sources are introduced by the interpolation engine itself. The accuracy of interpolated values depends on the density and spatial distribution of the underlying data points. With Phase 6B dense data, health layers improved from ~20 to ~2,956 points (148x increase) and air quality from ~20 to ~2,000-4,000 points (100-200x increase).

---

## Data Quality Notes

- **No PHI:** All data is aggregate/population-level. No patient-identifiable information.
- **Seed data pattern:** Every data file has seed values committed to git. Fetch scripts merge new data on top, never delete existing values.
- **Freshness metadata:** Every JSON file has `_meta.fetchedAt` timestamp. Backend `/health` endpoint reports freshness for all files.
- **Manual data review cadence:** SRTR data updates quarterly; policy tiers and socioeconomic scores review annually.

---

## Key Data Gaps

| Gap | Impact | Mitigation | Target Milestone |
|-----|--------|-----------|-----------------|
| ~~FARS API retired~~ | ~~Traffic fatality data is stale~~ | **RESOLVED** — rewritten to CSV bulk download from static.nhtsa.gov | L-045 FIXED |
| No SRTR API | Excel download is semi-manual | `fetch-srtr-excel.py` downloads files; `parse-srtr-reports.py` extracts data | M5 ✅ (semi-automated) |
| ~~No Donate Life API~~ | ~~Donor registration data is manual~~ | **RESOLVED** — `stateRegistrationRates` from DLA 2019 Annual Report (2018 DDR). `livingDonorProgramStrength` and `populationFactors` remain manually curated by design (no public dataset). | L-033 partially resolved |
| ~~County-to-OPO mapping unavailable~~ | ~~OPO geography approximate~~ | **RESOLVED** — HRSA Data Warehouse Excel provides authoritative 3,225 county → 60 OPO assignments. `scripts/build-opo-mapping-hrsa.py`. | L-050 sufficiently addressed |
| ~~Organ recovery rates from single study~~ | ~~PMC10329409 may not reflect current trends~~ | **RESOLVED** — cross-validated against OPTN 2023 national data. 15/30 cells updated. All organs within 7% of OPTN benchmarks. `scripts/validate-recovery-rates.py`. | L-049 validated |
| Blood type stratification missing | SRTR Table B10 doesn't stratify by blood type | Literature-derived multipliers retained | Future: use OPTN ADR figure data |
| City factors duplicated | In both algorithm.js and wait-time-distributions.json | FIXME: single source of truth in data file | M6 (frontend integration) |
