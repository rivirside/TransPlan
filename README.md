# TransPlan

Data-driven transplant location insights. TransPlan analyzes 50+ factors across 8 categories to help patients identify the best cities for their specific transplant needs.

## Architecture

```
GitHub Actions (weekly cron)
  -> Node.js fetch scripts hit free APIs (NHTSA, EPA, CMS, BLS, CDC)
  -> Write JSON to data/ directory
  -> Commit to repo
  -> GitHub Pages serves updated static site

Frontend loads JSON at runtime, falls back to hardcoded defaults if unavailable
```

### Files

| File | Purpose |
|------|---------|
| `index.html` | Main page with form, methodology, results, and map |
| `algorithm.js` | Scoring engine: 8 weighted categories, 22 cities |
| `script.js` | UI logic, Leaflet map, form handling, results display |
| `data-loader.js` | Fetches JSON data files, falls back to defaults |
| `charts.js` | Chart.js visualizations (radar, bar, donut) |
| `styles.css` | All styling |
| `data/` | JSON data files (auto-updated by GitHub Actions) |
| `data/manual/` | Manually curated data (SRTR, climate, policy, socioeconomic) |
| `scripts/` | Node.js fetch scripts for each API source |

### Scoring Categories

1. **Medical Compatibility** (25%) - Blood type, age, sex, organ size
2. **Wait Time & Competition** (20%) - Regional wait times, urgency
3. **Donor Availability** (18%) - Registration rates, population, living donor programs
4. **Hospital Quality** (15%) - Volume, reputation, specialization
5. **Geographic & Logistical** (10%) - Cost of living, climate, air quality
6. **Health Demographics** (7%) - Disease prevalence affecting donor pool
7. **Policy & Legal** (3%) - State donation laws
8. **Socioeconomic** (2%) - Support systems, community resources

## Data Pipeline

### Automated Sources

| Source | API | Frequency | Auth Required |
|--------|-----|-----------|---------------|
| Traffic fatalities | NHTSA FARS | Weekly | None |
| Air quality | EPA AQS | Weekly | `EPA_EMAIL`, `EPA_API_KEY` |
| Hospital quality | CMS Provider Data | Weekly | None |
| Cost of living | BLS API v2 | Weekly | `BLS_API_KEY` |
| Health demographics | CDC SODA API | Weekly | None |
| SRTR report check | SRTR website | Bimonthly | None |

### Manual Sources

Files in `data/manual/` are curated by hand:
- `srtr-reports.json` - Center volumes, specializations (from SRTR biannual reports)
- `climate-scores.json` - Recovery-favorable climate scores (no API exists)
- `policy-tiers.json` - State donation policy rankings
- `socioeconomic.json` - Socioeconomic support scores

### Triggering Data Fetches

**Automatic:** GitHub Actions runs weekly (Monday 6am UTC) and bimonthly (1st/15th).

**Manual:** Go to Actions tab > select workflow > "Run workflow".

**Local:**
```bash
npm ci
node scripts/fetch-traffic.js
node scripts/fetch-air-quality.js    # requires EPA_EMAIL, EPA_API_KEY env vars
node scripts/fetch-hospital-quality.js
node scripts/fetch-cost-of-living.js  # requires BLS_API_KEY env var
node scripts/fetch-health-data.js
node scripts/validate-data.js
```

### Required Secrets (GitHub Settings > Secrets)

Single secret called `EPA_BLS_KEYS` containing all API keys in `KEY=VALUE` format (one per line):

```
EPA_EMAIL=your-email@example.com
EPA_API_KEY=your-epa-key
BLS_API_KEY=your-bls-key
```

- EPA key: Free signup at [EPA AQS](https://aqs.epa.gov/aqsweb/documents/data_api.html)
- BLS key: Free at [BLS Registration](https://data.bls.gov/registrationEngine/)

### Notifications

All alerts go to GitHub Issues:
- **Fetch failure**: `[Data Pipeline] Fetch failed: <source>` (labeled `data-pipeline, failure`)
- **Validation failure**: `[Data Pipeline] Data validation failed`
- **SRTR update**: `[Manual Update] New SRTR reports available` (with checklist)

## Curating Manual Data

1. Edit the relevant file in `data/manual/`
2. Update `_meta.fetchedAt` to the current date
3. Ensure all 22 cities are covered
4. Run `node scripts/validate-data.js` to verify
5. Commit and push

## Adding a New City

1. Add coordinates to `cityCoordinates` in `script.js`
2. Add state mapping to `cityStateMap` in `script.js`
3. Add health data entry to `regionalHealthData` in `algorithm.js`
4. Add entries to all `data/*.json` and `data/manual/*.json` files
5. Add the city to `CITIES` array in `scripts/utils.js`
6. Add entries in all hardcoded data objects (costOfLivingIndex, climateScores, etc.)
7. Run validation: `node scripts/validate-data.js`

## Local Development

Open `index.html` in a browser. The site works fully offline using hardcoded fallback data. For the data loader to fetch JSON files, serve via a local HTTP server:

```bash
npx serve .
```

## Deployment

The site is designed for GitHub Pages. Enable it in repository Settings > Pages > Source: main branch.
