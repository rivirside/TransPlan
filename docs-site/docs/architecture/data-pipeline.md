---
sidebar_position: 2
---

# Data Pipeline

TransPlan's data is automatically refreshed by GitHub Actions and committed to the repository as JSON files. There is no database and no server-side rendering. All data lives as JSON files in the `data/` directory, and the frontend loads them at runtime.

## Overview

```
Public APIs (weekly/bimonthly)
  -> GitHub Actions workflows
    -> Node.js / Python fetch scripts
      -> data/*.json updated + committed
        -> Frontend loads JSON at runtime
```

## Data Sources

### Automated Sources

Several public APIs provide regularly updated data. The EPA AQS API supplies air quality data to `data/air-quality.json` on a weekly schedule and requires `EPA_EMAIL` and `EPA_API_KEY` credentials. CMS Provider Data feeds hospital quality scores into `data/hospital-quality.json` weekly with no authentication needed. The BLS API v2 provides cost-of-living data to `data/cost-of-living.json` weekly, requiring a `BLS_API_KEY`. The CDC SODA API populates `data/health-demographics.json` weekly without credentials, and donor registration data goes into `data/donor-registration.json` through the same script. Traffic fatality data in `data/traffic-fatalities.json` was sourced from the NHTSA FARS API, which has since been retired, so this data is now frozen as seed values.

SRTR Program-Specific Reports provide the statistical backbone of the simulation. A bimonthly check downloads Excel files and parses them into `data/wait-time-distributions.json` and `data/competing-risks.json`. The center mapping file `data/srtr-center-mapping.json` is updated as needed.

### Derived Data

The file `data/cause-of-death-by-region.json` combines data from the published study PMC10329409 with CDC WONDER statistics to estimate organ recovery rates by regional cause-of-death patterns.

### Manual Sources

Some data files are curated by hand in `data/manual/` because no API exists for the underlying information. These include `data/manual/srtr-reports.json` (center volumes, specializations, and performance tiers, updated as needed with each biannual SRTR release), `data/manual/climate-scores.json` (recovery-favorable climate scores on a 1 to 10 scale per city, reviewed annually), `data/manual/policy-tiers.json` (state donation law rankings, updated as needed), and `data/manual/socioeconomic.json` (transplant support system scores on a 1 to 10 scale per city, reviewed annually).

## Fetch Scripts

All scripts live in `scripts/` and share a common `utils.js` module with retry logic and file write helpers.

```bash
# Run all fetch scripts locally
node scripts/fetch-traffic.js
node scripts/fetch-air-quality.js       # EPA_EMAIL + EPA_API_KEY required
node scripts/fetch-hospital-quality.js
node scripts/fetch-cost-of-living.js    # BLS_API_KEY required
node scripts/fetch-health-data.js
node scripts/validate-data.js           # post-fetch validation
```

Each script uses `mergeDataFile()`, which deep-merges new data with existing records and only overwrites keys that have fresh data. This design prevents an API outage from wiping out previously fetched values.

### SRTR Pipeline (Python)

SRTR publishes Excel files (Program-Specific Reports) biannually. The Python pipeline downloads these files and parses the relevant tables into JSON.

```bash
# Download SRTR Excel files (6 organs, ~200MB)
python scripts/fetch-srtr-excel.py

# Parse Table B10 (wait times) + Table B7 (outcomes)
python scripts/parse-srtr-reports.py
```

This produces `data/wait-time-distributions.json` and `data/competing-risks.json`. The SRTR check workflow (`check-srtr-updates.yml`) runs bimonthly and opens a GitHub issue if new PSR files are detected.

## GitHub Actions Workflows

### Weekly Data Refresh (`fetch-data.yml`)

This workflow runs every Monday at 6am UTC as a sequential job. It installs Node.js dependencies, runs all five automated fetch scripts, then runs `validate-data.js` to verify the results. If any data changed, it commits and pushes with the message `data: automated weekly update`. The workflow requires three secrets configured in GitHub Settings: `EPA_EMAIL`, `EPA_API_KEY`, and `BLS_API_KEY`.

### Bimonthly SRTR Check (`check-srtr-updates.yml`)

This workflow runs on the 1st and 15th of each month. It checks the SRTR website for new PSR files by comparing hashes and opens a GitHub issue if updates are detected.

## Data Loading at Runtime

`data-loader.js` loads all JSON files when the page loads:

```javascript
// Fetch each data file, fall back to hardcoded defaults if unavailable
const data = await loadDataFile('air-quality.json', DEFAULT_AIR_QUALITY);
```

The `DEFAULTS` objects in `data-loader.js` contain the last known-good values, serving as a safety net for offline use or CDN failures.

## Data Validation

`scripts/validate-data.js` runs after each fetch cycle. It checks that all 22 cities have entries in each data file, that numeric values fall within expected ranges, and that no `null` or missing keys appear in required fields. Out-of-range values are logged as warnings rather than errors to avoid blocking the GitHub Action.

## Adding a New Data Source

To add a new data source, start by creating a fetch script at `scripts/fetch-<source>.js` that uses `mergeDataFile(outputPath, newData)` from `utils.js`. Then add the script to the workflow in `.github/workflows/fetch-data.yml` so it runs as part of the weekly refresh. Next, add validation rules in `scripts/validate-data.js` to cover the new data, and add default fallback values to `data-loader.js` so the frontend can function even if the fetch fails. Finally, update the scoring algorithm in `algorithm.js` to incorporate the new data into its calculations.

## Known Limitations

The NHTSA FARS API has been retired (L-045), so traffic fatality data is now frozen at the last fetched values. A CSV bulk download alternative exists at NHTSA but is not yet automated. SRTR data may be 6 to 18 months old since PSR files are released biannually. Forks of the repository will not be able to update EPA or BLS data files without their own API keys.
