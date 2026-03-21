---
sidebar_position: 2
---

# Data Curation Guide

:::info Pre-Release
TransPlan is being developed in the open but the repository is currently private. These instructions are for the development team and invited collaborators. The project will be open-sourced at a future stable release milestone.
:::

This guide explains how to maintain and update TransPlan's data files.

## Data File Types

### Automated (GitHub Actions)

Several data files are updated weekly by GitHub Actions and should not be manually edited unless correcting an obvious error. `data/air-quality.json` is sourced from the EPA AQS API via `scripts/fetch-air-quality.js`. `data/cost-of-living.json` comes from BLS API v2 via `scripts/fetch-cost-of-living.js`. `data/hospital-quality.json` is pulled from CMS Provider Data through `scripts/fetch-hospital-quality.js`. `data/health-demographics.json` is sourced from the CDC PLACES API (multi-release fallback) via `scripts/fetch-health-data.js`. `data/traffic-fatalities.json` is sourced from NHTSA FARS CSV bulk downloads via `scripts/fetch-traffic.js`. `data/donor-registration.json` has `stateRegistrationRates` from the Donate Life America 2019 Annual Report (2018 Donor Designation Rate by state); `livingDonorProgramStrength` and `populationFactors` are manually curated (no public dataset exists for these).

### Manual (Hand-curated)

Four files live in `data/manual/` and must be maintained by hand. `data/manual/srtr-reports.json` should be updated biannually by downloading SRTR PSR Excel files and checking Table A1 for volumes. `data/manual/climate-scores.json` should be reviewed annually based on NOAA climate normals and recovery criteria. `data/manual/policy-tiers.json` should be checked as needed against HRSA OPO data and state donation law changes. `data/manual/socioeconomic.json` should be reviewed annually for transplant support program availability per city.

### SRTR Pipeline (Semi-automated)

```bash
# Download SRTR PSR Excel files (6 organs, ~200MB)
python scripts/fetch-srtr-excel.py

# Parse Table B10 (wait times) + Table B7 (outcomes) into JSON
python scripts/parse-srtr-reports.py
```

This updates `data/wait-time-distributions.json` and `data/competing-risks.json`.

## Updating Manual Data

### Climate Scores (`climate-scores.json`)

Scores reflect recovery-favorable climate on a 1 to 10 scale per city. The factors considered include temperature extremes (avoiding harsh winters and heat), humidity (lower is preferred for respiratory recovery), air quality (correlated with EPA AQS but scored separately for trend), and UV index (high UV can be a concern for immunosuppressed patients).

### Policy Tiers (`policy-tiers.json`)

Three tiers classify states based on their donation law framework. Tier 1 represents first-person consent combined with mandated choice or a favorable regulatory environment. Tier 2 represents a standard first-person consent framework. Tier 3 represents a weak consent framework or low OPO conversion rates. Check HRSA OPO Performance Reports when updating.

### Socioeconomic Scores (`socioeconomic.json`)

Scores on a 1 to 10 scale are based on a transplant-specific support rubric covering financial assistance programs for transplant patients, housing assistance near transplant centers, community support networks and patient organizations, transportation access to transplant centers, and COBRA/insurance bridge programs.

This scoring deliberately avoids wealth-correlated metrics such as median income and property values to prevent penalizing lower-income patients.

### SRTR Reports (`srtr-reports.json`)

Per-center data extracted from SRTR Program-Specific Reports. Each entry includes annual transplant volume per organ, UNOS performance tier (1-year and 3-year survival vs. expected), pediatric program indicator, and living donor program indicator. Download the source data from [srtr.org](https://www.srtr.org) by navigating to Program-Specific Reports, selecting an organ, and downloading the Excel file.

## Data Validation

After updating any data file, run:

```bash
node scripts/validate-data.js
```

This checks that all 22 cities have entries, numeric values are within expected ranges, and no null or missing required keys are present. Fix any validation warnings before committing.

## Seed Data Philosophy

Each data file contains "seed" values representing the last known-good data from a real API call or manual curation. This ensures the app works offline or when APIs are unavailable, that GitHub Actions failures do not blank out data, and that forks without API keys have reasonable defaults.

Never commit zeros or placeholder values. If you do not have real data for a city, use the national average or a defensible proxy.

## Adding a New City

To add city #23 to TransPlan, start by adding it to `CITIES` in `scripts/utils.js`. Then add entries in each `data/*.json` file, using the closest existing city as a template. Add corresponding entries to all `data/manual/*.json` files and add a city factor to `algorithm.js`. Find SRTR center codes for the new city and add them to `data/srtr-center-mapping.json`. Add wait time params to `data/wait-time-distributions.json` and competing risks params to `data/competing-risks.json`. Run `node scripts/validate-data.js` to verify the data, and update tests in `tests/utils.test.js` to reflect the new CITIES array count.
