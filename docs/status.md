# TransPlan - Project Status

> **Read this file at the start of every session.**

## What TransPlan Is

A static-site tool that helps transplant patients identify the best US cities for their specific organ transplant needs. It scores 21 cities across 8 weighted categories using 50+ data points, displays results on an interactive Leaflet map, and visualizes score breakdowns with Chart.js.

## Current State: Post-MVP, Uncommitted

Everything below was built in the first implementation session and is **not yet committed**. The repo has only 2 prior commits (`Initial commit` and `Created files` with the original hardcoded codebase).

### What's Done

| Area | Status | Notes |
|------|--------|-------|
| Algorithm bug fixes | Done | 3 bugs fixed (multiplicative scoring, /100 error, random jitter) |
| Data directory (data/) | Done | 10 JSON seed files extracted from hardcoded data |
| Data loader (data-loader.js) | Done | Fetches JSON, falls back to defaults, freshness banner |
| Algorithm refactor | Done | All 8 scoring functions check `window.TransPlanData` first |
| script.js refactor | Done | Dynamic scoring of all 21 cities, async form submit |
| Chart.js visualizations | Done | Radar (per card), bar (comparison), donut (weights) |
| Fetch scripts (scripts/) | Done | 6 scripts: NHTSA, EPA, CMS, BLS, CDC, SRTR checker |
| Validation script | Done | Schema, ranges, coverage, staleness checks |
| GitHub Actions workflows | Done | Weekly fetch + bimonthly SRTR check |
| README | Done | Architecture, data pipeline, how to add cities |
| Documentation system | Done | This file + design.md, adr-log.md, roadmap.md, brand-bible.md |

### What's NOT Done

- No commits of the new work yet
- No `npm install` / `package-lock.json` generated
- No end-to-end browser testing (only Node.js algorithm test)
- No GitHub Pages deployment configured
- No API keys configured (EPA_EMAIL, EPA_API_KEY, BLS_API_KEY)
- Charts not visually verified in browser yet
- Data freshness banner not visually verified

## File Map

```
TransPlan/
  index.html              <- Main page
  algorithm.js            <- Scoring engine (8 categories, 21 cities)
  script.js               <- UI, map, form, results display
  data-loader.js          <- Runtime JSON loader with fallbacks
  charts.js               <- Chart.js radar/bar/donut charts
  styles.css              <- All CSS
  package.json            <- Node deps (xml2js)
  README.md               <- User-facing docs
  data/                   <- JSON data files (seed + auto-updated)
    air-quality.json
    cost-of-living.json
    donor-registration.json
    health-demographics.json
    hospital-quality.json
    traffic-fatalities.json
    metadata.json
    manual/               <- Hand-curated data (no API available)
      srtr-reports.json
      climate-scores.json
      policy-tiers.json
      socioeconomic.json
  scripts/                <- Node fetch scripts for GitHub Actions
    utils.js              <- Shared retry, write, city list
    fetch-traffic.js      <- NHTSA FARS
    fetch-air-quality.js  <- EPA AQS (needs API key)
    fetch-hospital-quality.js <- CMS Provider Data
    fetch-cost-of-living.js   <- BLS API (needs API key)
    fetch-health-data.js      <- CDC SODA
    check-srtr-updates.js     <- SRTR website hash check
    validate-data.js          <- Post-fetch validation
  .github/workflows/
    fetch-data.yml        <- Weekly data fetch (Mon 6am UTC)
    check-srtr-updates.yml <- Bimonthly SRTR check
  docs/
    status.md             <- THIS FILE (read every session)
    design.md             <- Read when touching UI/UX/CSS
    adr-log.md            <- Grep-searchable decision log
    roadmap.md            <- Grep-searchable future plans
    brand-bible.md        <- Grep-searchable visual identity
```

## Scoring Algorithm Summary

8 categories, weights sum to 100%:

| # | Category | Weight | Key Data |
|---|----------|--------|----------|
| 1 | Medical Compatibility | 25% | Blood type, age, sex, BMI |
| 2 | Wait Time | 20% | City wait factors, urgency |
| 3 | Donor Availability | 18% | Registration rates, population, living donors |
| 4 | Hospital Quality | 15% | Volume, reputation, specialization |
| 5 | Geographic | 10% | Cost of living, climate, air quality |
| 6 | Health Demographics | 7% | Diabetes, obesity, CKD, hypertension, smoking |
| 7 | Policy | 3% | State donation laws |
| 8 | Socioeconomic | 2% | Support systems |

## Documentation Tiers

| Tier | When to Read | Files |
|------|-------------|-------|
| Always | Start of every session | `docs/status.md` |
| Context | When touching that area | `docs/design.md` |
| Grep | Only search when needed | `docs/adr-log.md`, `docs/roadmap.md`, `docs/brand-bible.md` |

## Commit & Documentation Habits

- Commit after each logical unit of work with a descriptive message
- Update `docs/status.md` when project state changes meaningfully
- Add an ADR entry when making a non-obvious architectural choice
- Update roadmap when completing items or discovering new work
