---
sidebar_position: 2
---

# Data Curation Guide

How to maintain and update TransPlan's data files.

## Data File Types

### Automated (GitHub Actions)

These files are updated weekly by GitHub Actions. You should not manually edit them unless correcting an obvious error:

| File | Source | Script |
|------|--------|--------|
| `data/air-quality.json` | EPA AQS API | `scripts/fetch-air-quality.js` |
| `data/cost-of-living.json` | BLS API v2 | `scripts/fetch-cost-of-living.js` |
| `data/hospital-quality.json` | CMS Provider Data | `scripts/fetch-hospital-quality.js` |
| `data/health-demographics.json` | CDC SODA API | `scripts/fetch-health-data.js` |
| `data/traffic-fatalities.json` | NHTSA FARS (retired: seed data only) | `scripts/fetch-traffic.js` |
| `data/donor-registration.json` | State health dept APIs | `scripts/fetch-health-data.js` |

### Manual (Hand-curated)

These files live in `data/manual/` and must be maintained by hand:

| File | How to Update | Cadence |
|------|--------------|---------|
| `data/manual/srtr-reports.json` | Download SRTR PSR Excel, check Table A1 for volumes | Biannually |
| `data/manual/climate-scores.json` | Review based on NOAA climate normals and recovery criteria | Annually |
| `data/manual/policy-tiers.json` | Check HRSA OPO data and state donation law changes | As-needed |
| `data/manual/socioeconomic.json` | Review transplant support program availability per city | Annually |

### SRTR Pipeline (Semi-automated)

```bash
# Download SRTR PSR Excel files (6 organs, ~200MB)
python scripts/fetch-srtr-excel.py

# Parse Table B10 (wait times) + Table B7 (outcomes) → JSON
python scripts/parse-srtr-reports.py
```

This updates `data/wait-time-distributions.json` and `data/competing-risks.json`.

## Updating Manual Data

### Climate Scores (`climate-scores.json`)

Scores reflect recovery-favorable climate (1–10 per city). The factors considered are temperature extremes (avoiding harsh winters and heat), humidity (low humidity is preferred for respiratory recovery), air quality (correlated with EPA AQS but scored separately for trend), and UV index (high UV can be a concern for immunosuppressed patients).

### Policy Tiers (`policy-tiers.json`)

Three tiers based on state donation law:

1. **Tier 1**: First-person consent + mandated choice or favorable regulatory environment
2. **Tier 2**: Standard first-person consent framework
3. **Tier 3**: Weak consent framework or low OPO conversion rates

Check HRSA OPO Performance Reports when updating.

### Socioeconomic Scores (`socioeconomic.json`)

Scores (1–10) based on a transplant-specific support rubric covering financial assistance programs for transplant patients, housing assistance near transplant centers, community support networks and patient organizations, transportation access to transplant centers, and COBRA/insurance bridge programs.

*Important: This deliberately avoids wealth-correlated metrics (median income, property values) to prevent penalizing lower-income patients.*

### SRTR Reports (`srtr-reports.json`)

Per-center data extracted from SRTR Program-Specific Reports. Fields include annual transplant volume per organ, UNOS performance tier (1-year/3-year survival vs. expected), pediatric program indicator, and living donor program indicator.

Download from [srtr.org](https://www.srtr.org) → Program-Specific Reports → select organ → download Excel.

## Data Validation

After updating any data file, run:

```bash
node scripts/validate-data.js
```

This checks that all 22 cities have entries, numeric values are within expected ranges, and no null or missing required keys are present. Fix any validation warnings before committing.

## Seed Data Philosophy

Each data file contains "seed" values: the last known-good data from a real API call or manual curation. This ensures the app works offline or when APIs are unavailable, GitHub Actions failures don't blank out data, and forks without API keys have reasonable defaults.

Never commit zeros or placeholder values. If you don't have real data for a city, use the national average or a defensible proxy.

## Adding a New City

To add city #23 to TransPlan:

1. Add to `CITIES` in `scripts/utils.js`
2. Add entries in each `data/*.json` file (use closest existing city as template)
3. Add to `data/manual/*.json` files
4. Add city factor to `algorithm.js`
5. Find SRTR center codes for that city
6. Add to `data/srtr-center-mapping.json`
7. Add wait time params to `data/wait-time-distributions.json`
8. Add competing risks params to `data/competing-risks.json`
9. Run `node scripts/validate-data.js`
10. Update tests in `tests/utils.test.js` (CITIES array check)
