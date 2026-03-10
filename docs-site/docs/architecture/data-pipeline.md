---
sidebar_position: 2
---

# Data Pipeline

TransPlan's data is automatically refreshed by GitHub Actions and committed to the repository as JSON files.

## Overview

```
Public APIs (weekly/bimonthly)
  → GitHub Actions workflows
    → Node.js / Python fetch scripts
      → data/*.json updated + committed
        → Frontend loads JSON at runtime
```

No database. No server-side rendering. All data lives as JSON files in the `data/` directory.

## Data Sources

### Automated Sources

| Source | File | Update Frequency | Auth Required |
|--------|------|-----------------|---------------|
| NHTSA FARS (traffic fatalities) | `data/traffic-fatalities.json` | Weekly | None (API retired: seed data only) |
| EPA AQS (air quality) | `data/air-quality.json` | Weekly | `EPA_EMAIL`, `EPA_API_KEY` |
| CMS Provider Data (hospital quality) | `data/hospital-quality.json` | Weekly | None |
| BLS API v2 (cost of living) | `data/cost-of-living.json` | Weekly | `BLS_API_KEY` |
| CDC SODA API (health demographics) | `data/health-demographics.json` | Weekly | None |
| SRTR PSR Excel (wait times + outcomes) | `data/wait-time-distributions.json` `data/competing-risks.json` | Bimonthly check | None |
| Donor registration | `data/donor-registration.json` | Weekly | None |
| SRTR center mapping | `data/srtr-center-mapping.json` | As-needed | None |

### Derived Data

| File | Source | Description |
|------|--------|-------------|
| `data/cause-of-death-by-region.json` | PMC10329409 × CDC WONDER | Organ recovery rates by regional cause-of-death patterns |

### Manual Sources

Curated by hand in `data/manual/`. No API exists for these:

| File | Content | Update Cadence |
|------|---------|----------------|
| `data/manual/srtr-reports.json` | Center volumes, specializations, performance tiers | As-needed (SRTR biannual) |
| `data/manual/climate-scores.json` | Recovery-favorable climate scores (1–10 per city) | Annually |
| `data/manual/policy-tiers.json` | State donation law rankings | As-needed |
| `data/manual/socioeconomic.json` | Transplant support system scores (1–10 per city) | Annually |

## Fetch Scripts

All scripts are in `scripts/`. They use a shared `utils.js` with retry logic and file write helpers.

```bash
# Run all fetch scripts locally
node scripts/fetch-traffic.js
node scripts/fetch-air-quality.js       # EPA_EMAIL + EPA_API_KEY required
node scripts/fetch-hospital-quality.js
node scripts/fetch-cost-of-living.js    # BLS_API_KEY required
node scripts/fetch-health-data.js
node scripts/validate-data.js           # post-fetch validation
```

Each script uses `mergeDataFile()`, which deep-merges new data with existing, only overwriting keys that have fresh data. This prevents an API outage from wiping out previously fetched data.

### SRTR Pipeline (Python)

SRTR publishes Excel files (Program-Specific Reports) biannually. The Python pipeline:

```bash
# Download SRTR Excel files (6 organs, ~200MB)
python scripts/fetch-srtr-excel.py

# Parse Table B10 (wait times) + Table B7 (outcomes)
python scripts/parse-srtr-reports.py
```

Output: `data/wait-time-distributions.json` and `data/competing-risks.json`

The SRTR check workflow (`check-srtr-updates.yml`) runs bimonthly and opens a GitHub issue if new PSR files are detected.

## GitHub Actions Workflows

### `fetch-data.yml`: Weekly Data Refresh

Runs every Monday at 6am UTC. Sequential job:

1. Install Node.js deps
2. Run all 5 automated fetch scripts
3. Run `validate-data.js`
4. If any data changed, commit and push with message `data: automated weekly update`

Required secrets (GitHub Settings > Secrets > Actions): `EPA_EMAIL`, `EPA_API_KEY`, and `BLS_API_KEY`.

### `check-srtr-updates.yml`: Bimonthly SRTR Check

Runs 1st and 15th of each month. Checks SRTR website for new PSR files by comparing hashes. Opens a GitHub issue if updates are detected.

## Data Loading at Runtime

`data-loader.js` loads all JSON files when the page loads:

```javascript
// Fetch each data file, fall back to hardcoded defaults if unavailable
const data = await loadDataFile('air-quality.json', DEFAULT_AIR_QUALITY);
```

The `DEFAULTS` objects in `data-loader.js` are the last known-good values, serving as a safety net for offline use or CDN failures.

## Data Validation

`scripts/validate-data.js` runs after each fetch cycle and checks that all 22 cities have entries in each data file, numeric values are within expected ranges, no `null` or missing keys appear in required fields, and out-of-range values are logged as warnings (not errors) to avoid blocking the GitHub Action.

## Adding a New Data Source

1. Create `scripts/fetch-<source>.js`
2. Use `mergeDataFile(outputPath, newData)` from `utils.js`
3. Add the script to `.github/workflows/fetch-data.yml`
4. Add validation rules in `scripts/validate-data.js`
5. Add default values to `data-loader.js`
6. Update the algorithm in `algorithm.js` to use the new data

## Known Limitations

The NHTSA FARS API has been retired (L-045): traffic fatality data is now frozen at the last fetched values, and a CSV bulk download alternative exists at NHTSA but is not yet automated. SRTR data may be 6–18 months old since PSR files are released biannually. Without EPA and BLS API keys, those data files will not update in forks.
