# TransPlan - Project Status

> **Read this file at the start of every session.**

## What TransPlan Is

A static-site tool that helps transplant patients identify the best US cities for their specific organ transplant needs. It scores 22 cities across 8 weighted categories using 50+ data points, displays results on an interactive Leaflet map, and visualizes score breakdowns with Chart.js.

## Current State: All Limitations Resolved (32 fixed, 3 deferred, 2 won't fix)

Batches 1-10 complete. All 40 tracked limitations have been resolved: 32 fixed, 3 deferred (no API available for OPO/SRTR outcomes/donor registration), 2 won't fix (cost > benefit), 1 false positive. Pipeline is safe to run. Comprehensive review passed on 2026-03-01.

### What's Done

| Area | Status | Notes |
|------|--------|-------|
| Core algorithm | ✅ Done | 8 categories, organ-specific inputs (cPRA/MELD/LAS), deduped data |
| Data directory (data/) | ✅ Done | 10 JSON seed files, real SRTR volumes, corrected policy tiers |
| Data loader (data-loader.js) | ✅ Done | Runtime JSON loader, DEFAULTS as single source of truth |
| Clinical inputs | ✅ Done | cPRA slider (kidney), MELD (liver), LAS (lung) — conditional fields |
| Ethical/legal fixes | ✅ Done | Disclaimer expanded, "success probability" → "suitability score" |
| Chart.js visualizations | ✅ Done | Stacked weighted bar chart, radar per card, donut weights |
| Accessibility | ✅ Done | ARIA labels on map/charts/results, mobile collapse overlay controls |
| Methodology text | ✅ Done | Accurate data sources, correct volumes, real factors listed |
| Fetch scripts (scripts/) | ✅ Done | 6 scripts safe (mergeDataFile for partial writes), 1 deferred (donor reg) |
| GitHub Actions | ✅ Done | Single sequential job, no race condition |
| Socioeconomic data | ✅ Done | Transplant-support rubric replacing wealth-correlated scores |
| Browser testing | ✅ Done | All 6 organs, edge cases, map overlays — zero console errors |

### What's NOT Done (Future Work)

- GitHub Pages deployment not yet configured
- Fetch scripts not yet run against live APIs (only seed data)
- No unit tests (Jest/Vitest for algorithm.js)
- No browser tests (Playwright/Cypress)
- **Deferred:** OPO boundaries (L-009), SRTR outcomes (L-017), donor reg fetch (L-033) — need API access
- See `docs/roadmap.md` for future feature ideas

## File Map

```
TransPlan/
  index.html              <- Main page
  algorithm.js            <- Scoring engine (8 categories, 22 cities)
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

**40 tracked issues** in `docs/limitations.md` — all resolved. Read when auditing data quality or planning future work.

| Status | Count | Details |
|--------|-------|---------|
| FIXED | 32 | All critical, most high/medium issues |
| DEFERRED | 3 | L-009 (OPO), L-017 (SRTR outcomes), L-033 (donor reg fetch) — need API access |
| WONT FIX | 2 | L-012 (county health, <0.5pt impact), L-039 (false positive) |

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
