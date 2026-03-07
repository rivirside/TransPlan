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
| Traffic fatality rates | NHTSA FARS API | `scripts/fetch-traffic.js` | No (API retired) | `data/traffic-fatalities.json` | Seed data only; FIXME: CSV bulk download |
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

## Data Quality Notes

- **No PHI:** All data is aggregate/population-level. No patient-identifiable information.
- **Seed data pattern:** Every data file has seed values committed to git. Fetch scripts merge new data on top, never delete existing values.
- **Freshness metadata:** Every JSON file has `_meta.fetchedAt` timestamp. Backend `/health` endpoint reports freshness for all files.
- **Manual data review cadence:** SRTR data updates quarterly; policy tiers and socioeconomic scores review annually.

---

## Key Data Gaps

| Gap | Impact | Mitigation | Target Milestone |
|-----|--------|-----------|-----------------|
| FARS API retired | Traffic fatality data is stale | Seed data preserved; FIXME for CSV bulk download | Phase 1 (L-045) |
| No SRTR API | Excel download is semi-manual | `fetch-srtr-excel.py` downloads files; `parse-srtr-reports.py` extracts data | M5 ✅ (semi-automated) |
| No Donate Life API | Donor registration data is manual | Seed data; review annually | Deferred (L-033) |
| Blood type stratification missing | SRTR Table B10 doesn't stratify by blood type | Literature-derived multipliers retained | Future: use OPTN ADR figure data |
| City factors duplicated | In both algorithm.js and wait-time-distributions.json | FIXME: single source of truth in data file | M6 (frontend integration) |
