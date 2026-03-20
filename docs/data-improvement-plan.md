# Data Improvement Plan

> Prioritized roadmap for data provenance and replacement of seed/synthetic data.
> Created March 2026 to close GitHub issue #105.

## Data Provenance Audit

| File | Source | Status | Fetch Method | Notes |
|------|--------|--------|-------------|-------|
| `air-quality.json` | EPA AQS API | Real | `fetch-air-quality.js` (weekly CI) | Requires EPA API key |
| `cost-of-living.json` | BLS API v2 | Real | `fetch-cost-of-living.js` (weekly CI) | Requires BLS API key |
| `health-demographics.json` | CDC PLACES API | Real | `fetch-health-data.js` (weekly CI) | 5 county-level indicators for 20/22 cities |
| `traffic-fatalities.json` | NHTSA FARS CSV | Real | `fetch-traffic.js` (weekly CI) | Bulk CSV download from static.nhtsa.gov |
| `wait-time-distributions.json` | SRTR PSR Jan 2025 | Real | `parse-srtr-reports.py` (manual) | Log-normal params from Table B10 |
| `competing-risks.json` | SRTR PSR Jan 2025 | Real | `parse-srtr-reports.py` (manual) | Mortality/delisting from Table B7 |
| `post-transplant-outcomes.json` | SRTR PSR Jan 2025 | Real | `parse-srtr-reports.py` (manual) | Graft/patient survival from C-series |
| `srtr-historical.json` | SRTR PSR (14 releases) | Real | `fetch-srtr-historical.yml` (GH Actions) | 2019-2025 biannual time series |
| `hospital-quality.json` | CMS + manual | Mixed | `fetch-hospital-quality.js` (partial) | centerReputation is manual; centerVolumes partially manual |
| `cause-of-death-by-region.json` | PMC10329409 + CDC SODA | Mixed | `fetch-cod-data.js` (CDC part) | Recovery rates from 2023 paper, state proportions from CDC |
| `donor-registration.json` | UNOS/Donate Life America | Seed | None | No public API available |
| `manual/srtr-reports.json` | SRTR + center reports | Mixed | None | waitTimeFactors now redundant with SRTR parse pipeline |
| `manual/climate-scores.json` | Manual curation | Seed | None | No climate-transplant API exists |
| `manual/policy-tiers.json` | Research literature | Seed | None | Based on state organ donation laws |
| `manual/socioeconomic.json` | Manual curation | Seed | None | Transplant-support rubric |

## Summary

- **8 files** fully automated with real data (53%)
- **2 files** mixed (real + manual components, 13%)
- **5 files** seed/manual data (33%)

## Priority Tiers

### P0: Done

All critical data files now use real sources:
- `srtr-historical.json` — replaced synthetic data with real 14-release SRTR time series (#104)
- `wait-time-distributions.json`, `competing-risks.json`, `post-transplant-outcomes.json` — parsed from SRTR Excel

### P1: Next (medium effort, high impact)

1. **Derive centerVolumes from srtr-historical.json**
   - Sum biannual volumes from SRTR historical releases to get annual estimates
   - Replaces manual estimates in `hospital-quality.json`
   - Resolves volume inconsistency across files (#87)

2. **Retire `manual/srtr-reports.json` waitTimeFactors**
   - Now redundant with city-level wait time factors from SRTR parse pipeline
   - Keep center names for display purposes only

### P2: Medium (moderate effort, moderate impact)

3. **donor-registration.json**
   - Donate Life America publishes state-level registration stats annually
   - No API; would need annual manual update or lightweight scraper
   - Weight: 3% of total score (low urgency)

4. **hospital-quality.json centerReputation**
   - Currently uses simplified tier system (high/medium/low)
   - Could derive from SRTR program-specific reports (observed/expected ratios)
   - Partially blocked by center identification complexity

### P3: Low Priority (stable, low-weight categories)

5. **manual/climate-scores.json** — Weight: part of Geographic (10%). Climate data is stable year-to-year. Manual curation is acceptable.

6. **manual/policy-tiers.json** — Weight: Policy (3%). Based on state organ donation laws which change rarely. Manual is fine.

7. **manual/socioeconomic.json** — Weight: Socioeconomic (2%). Transplant-support rubric based on research. Manual is acceptable.

## Volume Data Inconsistency (#87)

Pittsburgh kidney volume appears differently across files because they measure different things:

| File | Value | What It Measures |
|------|-------|-----------------|
| `hospital-quality.json` | 350 | Estimated annual transplant count (CMS/manual) |
| `srtr-historical.json` | ~322 | Per-release count (SRTR Table B10, ~6-month period) |
| `post-transplant-outcomes.json` | 454 | Survival cohort sample size (SRTR C-series, multi-year accumulation) |

These are not inconsistencies — they are different metrics from different SRTR tables and time periods. This is documented in `hospital-quality.json` `_meta.volume_notes`.
