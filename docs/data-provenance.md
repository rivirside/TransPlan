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
| National median wait times (per organ) | OPTN/SRTR 2023 Annual Data Report | None | No | `data/wait-time-distributions.json` | Manual; derived from literature |
| Log-normal sigma (distribution spread) | Published transplant statistics literature | None | No | `data/wait-time-distributions.json` | Manual; calibrate against SRTR data |
| Blood type wait time multipliers | OPTN wait time data by blood type | None | No | `data/wait-time-distributions.json` | Manual; derived from OPTN ratios |
| cPRA wait time multipliers (kidney) | OPTN allocation data + literature | None | No | `data/wait-time-distributions.json` | Manual; based on OPTN cPRA point tiers |
| MELD wait time multipliers (liver) | OPTN MELD allocation policy | None | No | `data/wait-time-distributions.json` | Manual; based on MELD allocation rules |
| LAS wait time multipliers (lung) | OPTN LAS allocation policy | None | No | `data/wait-time-distributions.json` | Manual; based on LAS allocation rules |
| City wait time factors (22 cities) | SRTR relative wait times | None | No | `data/wait-time-distributions.json` | Manual; copied from algorithm.js |
| Waitlist annual mortality rates (per organ) | OPTN/SRTR 2023 ADR (heart 8.5, liver 12.9, lung 13.3/100 pt-yr) | None | No | `data/competing-risks.json` | Manual; from 2023 ADR |
| Waitlist annual delisting rates (per organ) | OPTN/SRTR 2023 ADR + literature estimates | None | No | `data/competing-risks.json` | Manual; from 2023 ADR |
| Urgency mortality multipliers | OPTN allocation status categories | None | No | `data/competing-risks.json` | Manual |
| MELD mortality multipliers (liver) | OPTN MELD allocation policy | None | No | `data/competing-risks.json` | Manual |
| City mortality/delisting adjustments (22 cities) | Derived from Phase 1 hospital quality tiers | None | No | `data/competing-risks.json` | Manual |
| SRTR center-level percentiles | SRTR Program-Specific Reports (HTML) | Planned: `scripts/parse-srtr-reports.py` (M5) | Planned (M5) | Planned: `data/srtr-distributions.json` | Not yet created |
| SRTR survival/delisting rates | SRTR public datasets | Planned: `scripts/fetch-srtr-survival.py` (M5) | Planned (M5) | Planned: `data/competing-risks.json` | Not yet created |

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
| No SRTR API | Can't automate wait time distributions | Literature-derived params + manual review | M5 scraper |
| No Donate Life API | Donor registration data is manual | Seed data; review annually | Deferred (L-033) |
| Competing risks use national averages | No center-level mortality/delisting data | Literature-derived rates + city adjustments | M5 (SRTR scraper) |
| City factors duplicated | In both algorithm.js and wait-time-distributions.json | FIXME: single source of truth in data file | M6 (frontend integration) |
