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
| Donor registration rates | Donate Life America reports | None | No | `data/donor-registration.json` | Manual; no API exists (L-033) |
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
| Center geographic coordinates | Nominatim geocoding + `srtr-center-mapping.json` + manual | Three-tier: (1) Nominatim automated for 200+, (2) city_mapping fallback, (3) manual coordinates for edge cases | No | `data/srtr-all-centers.json` | Static once geocoded; review when centers open/close |
| Center-level wait time distributions | SRTR PSR Table B10 (all centers) | `scripts/parse-srtr-reports.py --all-centers` | Semi | `data/wait-time-distributions-centers.json` | Biannual SRTR releases |
| Center-level competing risks | SRTR PSR Table B7 (all centers) | `scripts/parse-srtr-reports.py --all-centers` | Semi | `data/competing-risks-centers.json` | Biannual SRTR releases |
| Center-level post-transplant outcomes | SRTR PSR Tables C5-C20 (all centers) | `scripts/parse-srtr-reports.py --all-centers` | Semi | `data/post-transplant-outcomes-centers.json` | Biannual SRTR releases |
| Center-to-city mapping (22 focus cities) | Manual curation from SRTR center directory | None | No | `data/srtr-center-mapping.json` | Manual; update when centers change |

### Phase 6B: Spatial Interpolation

| Data Point | Source | Processing | Automated? | Data File | Notes |
|------------|--------|-----------|------------|-----------|-------|
| Interpolated spatial surfaces (24 layers) | Derived from center-level + city-level JSON data | `backend/services/spatial_interpolation.py` (RBF/IDW) | Runtime (computed on first query) | In-memory cache | Surfaces built from 20-233 data points depending on layer |
| UNOS allocation circle analysis | Computed from center coordinates + haversine distances | `backend/services/allocation_geography.py` | Runtime | In-memory | 250nm/500nm circles per UNOS allocation policy |
| Haversine distance (nautical miles) | Standard geodesic formula | `backend/utils.py` (`haversine_distance_nm`) | Runtime | N/A | Conversion: miles × 0.868976 = nautical miles |

### Spatial Data Layers

The interpolation engine supports 24 layers, derived from existing data files:

| Layer | Source Data | Point Density | Notes |
|-------|------------|---------------|-------|
| `air_quality` | `data/air-quality.json` (22 cities) | ~20 points | City-level AQI values |
| `cost_of_living` | `data/cost-of-living.json` (22 cities) | ~20 points | City-level CPI index |
| `health_diabetesRate` | `data/health-demographics.json` | ~20 points | County-aggregated CDC PLACES |
| `health_obesityRate` | `data/health-demographics.json` | ~20 points | County-aggregated CDC PLACES |
| `health_ckdRate` | `data/health-demographics.json` | ~20 points | County-aggregated CDC PLACES |
| `health_hypertensionRate` | `data/health-demographics.json` | ~20 points | County-aggregated CDC PLACES |
| `health_smokingRate` | `data/health-demographics.json` | ~20 points | County-aggregated CDC PLACES |
| `wait_time_factor_{organ}` | `data/wait-time-distributions-centers.json` | 100-233 points | Center-level SRTR Table B10 |
| `mortality_factor_{organ}` | `data/competing-risks-centers.json` | 100-233 points | Center-level SRTR Table B7 |
| `graft_survival_{organ}` | `data/post-transplant-outcomes-centers.json` | 80-200 points | Center-level SRTR C-series |

**Data provenance note:** All spatial interpolation layers are derived from existing, provenance-tracked data files. No new external data sources are introduced by the interpolation engine itself. The accuracy of interpolated values depends on the density and spatial distribution of the underlying data points — city-level layers (~20 points) produce coarser surfaces than center-level layers (100-233 points).

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
| No Donate Life API | Donor registration data is manual | Seed data; review annually | Deferred (L-033) |
| Blood type stratification missing | SRTR Table B10 doesn't stratify by blood type | Literature-derived multipliers retained | Future: use OPTN ADR figure data |
| City factors duplicated | In both algorithm.js and wait-time-distributions.json | FIXME: single source of truth in data file | M6 (frontend integration) |
