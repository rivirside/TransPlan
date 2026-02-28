# TransPlan - Project Status

> **Read this file at the start of every session.**

## What TransPlan Is

A static-site tool that helps transplant patients identify the best US cities for their specific organ transplant needs. It scores 21 cities across 8 weighted categories using 50+ data points, displays results on an interactive Leaflet map, and visualizes score breakdowns with Chart.js.

## Current State: v0.2 Complete, Browser Tested

All v0.2 work has been committed (10 commits) and pushed to GitHub. API keys configured as `EPA_BLS_KEYS` secret. Browser testing completed with zero errors.

### What's Done

| Area | Status | Notes |
|------|--------|-------|
| Algorithm bug fixes | ✅ Done | 3 bugs fixed (multiplicative scoring, /100 error, random jitter) |
| Data directory (data/) | ✅ Done | 10 JSON seed files extracted from hardcoded data |
| Data loader (data-loader.js) | ✅ Done | Fetches JSON, falls back to defaults, freshness banner |
| Algorithm refactor | ✅ Done | All 8 scoring functions check `window.TransPlanData` first |
| script.js refactor | ✅ Done | Dynamic scoring of all 22 cities, async form submit |
| Derived metrics | ✅ Done | Wait times, match rates, donor rates, factors derived from algorithm data |
| Chart.js visualizations | ✅ Done | Radar (per card), bar (comparison), donut (weights) — browser verified |
| Fetch scripts (scripts/) | ✅ Done | 6 scripts: NHTSA, EPA, CMS, BLS, CDC, SRTR checker |
| Validation script | ✅ Done | Schema, ranges, coverage, staleness checks |
| GitHub Actions workflows | ✅ Done | Weekly fetch + bimonthly SRTR check, single EPA_BLS_KEYS secret |
| README | ✅ Done | Architecture, data pipeline, how to add cities |
| Documentation system | ✅ Done | This file + design.md, adr-log.md, roadmap.md, brand-bible.md |
| Browser testing | ✅ Done | Form submit, 22 cities ranked, charts render, zero console errors |
| package-lock.json | ✅ Done | Generated via npm install |
| API keys | ✅ Done | EPA_BLS_KEYS secret configured in GitHub |

### What's NOT Done

- GitHub Pages deployment not yet configured (Settings > Pages > Source: main)
- Fetch scripts not yet run against live APIs (only seed data)
- No unit tests (Jest/Vitest for algorithm.js)
- No browser tests (Playwright/Cypress)
- See `docs/roadmap.md` for future feature ideas

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

## Known Limitations

**30 tracked issues** in `docs/limitations.md` — 14 fixed, 16 open. Read when auditing data quality, algorithm accuracy, or planning fixes.

| Severity | Open | Fixed | Key Open Examples |
|----------|------|-------|-------------------|
| CRITICAL | 3 | 5 | No PRA/cPRA input (L-001), no MELD for liver (L-002), fake SRTR volumes (L-010) |
| HIGH | 5 | 4 | No LAS for lungs, broken FARS normalization, CMS ratings not transplant-specific, traffic-as-donor-proxy |
| MEDIUM | 6 | 2 | State-level health data as city data, stale COL, no accessibility, mobile responsiveness |
| LOW | 2 | 3 | City count inconsistency (L-028), mobile overlay panel (L-030) |

## Documentation Tiers

| Tier | When to Read | Files |
|------|-------------|-------|
| Always | Start of every session | `docs/status.md` |
| Context | When touching that area | `docs/design.md`, `docs/limitations.md` |
| Grep | Only search when needed | `docs/adr-log.md`, `docs/roadmap.md`, `docs/brand-bible.md` |

## Commit & Documentation Habits

- Commit after each logical unit of work with a descriptive message
- Update `docs/status.md` when project state changes meaningfully
- Update `docs/limitations.md` when discovering or resolving issues
- Add an ADR entry when making a non-obvious architectural choice
- Update roadmap when completing items or discovering new work
