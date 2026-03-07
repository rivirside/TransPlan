# TransPlan - Project Status

> **Read this file at the start of every session.**

## What TransPlan Is

A patient-facing clinical decision support tool that helps transplant patients identify the best US cities for their specific organ transplant needs. Currently a static site scoring 22 cities across 8 weighted categories using 40+ data points. On a path to become a probabilistic forecasting engine with Monte Carlo simulation, competing risks modeling, and policy impact analysis. See `docs/ideas.md` for the full SRS and `docs/roadmap.md` for phased development plan.

## Current State: Phase 2 In Progress — SRTR Data Pipeline Complete (M5)

Phase 1 MVP complete (91 Jest tests, 48 limitations resolved). Phase 2 probabilistic engine: M1-M5 done. 120 pytest tests passing. Data now uses empirical SRTR center-level percentiles (Table B10 wait times, Table B7 mortality/delisting) instead of literature estimates. POST /simulate returns ranked city probabilities with competing risks, 95% CIs, in ~80ms.

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
| Fetch scripts (scripts/) | ✅ Done | All scripts use mergeDataFile, skip-on-empty guards added |
| GitHub Actions | ✅ Done | Single sequential job, weekly cron + manual dispatch |
| Socioeconomic data | ✅ Done | Transplant-support rubric replacing wealth-correlated scores |
| Unit tests | ✅ Done | 91 tests (Jest): 68 algorithm + 23 utilities, 0 failures |
| CDN fallback | ✅ Done | Graceful degradation when Leaflet/Chart.js CDN unavailable |
| CMS API fix | ✅ Done | Multi-strategy query (SQL/filter/legacy); filter works for 22 cities |
| Browser testing | ✅ Done | All 6 organs, edge cases, map overlays — zero console errors |

### Phase 2 Progress

| Milestone | Status | Notes |
|-----------|--------|-------|
| M1: Backend scaffold | ✅ Done | FastAPI app, Pydantic schemas, data loader, /health, 22 pytest tests |
| M2: Wait time distributions | ✅ Done | Log-normal models, 6 organs, 8 blood types, cPRA/MELD/LAS multipliers, 22 tests |
| M3: Monte Carlo engine | ✅ Done | 1000-iteration simulation, POST /simulate, 80ms perf, 25 tests |
| M4: Competing risks | ✅ Done | Mortality/delisting model, outcomes sum to 1.0, 17 tests |
| M5: SRTR data pipeline | ✅ Done | Excel downloader, parser, center mapping, 22 cities × 6 organs, 34 tests |
| M6: Frontend integration | Pending | API client, CDF charts, dual-mode results |
| M7: Validation & docs | Pending | Brier score, sensitivity analysis, documentation |

### What's NOT Done (Next Steps)

- ~~**Phase 2 M5:** SRTR data pipeline~~ ✅ Done
- **Phase 2 M6:** Frontend integration — API client, CDF curves, competing risks chart, dual-mode results, graceful degradation
- **Phase 2 M7:** Validation & docs — Brier score retrospective validation, sensitivity analysis (tornado charts), backend architecture docs
- **Deploy:** Configure GitHub Pages (Settings > Pages > Source: main)
- **FARS API (L-045):** MITIGATED — entire NHTSA FARS API appears retired; seed data preserved; FIXME for CSV bulk download alternative
- **Deferred:** OPO boundaries (L-009), SRTR outcomes (L-017), donor reg fetch (L-033)
- See `docs/roadmap.md` for full phased plan (5 phases through FDA clearance)
- See `docs/ideas.md` for full SRS with architecture, governance, and regulatory details

## File Map

```
TransPlan/
  index.html              <- Main page
  algorithm.js            <- Scoring engine (8 categories, 22 cities)
  script.js               <- UI, map, form, results display
  data-loader.js          <- Runtime JSON loader with fallbacks
  charts.js               <- Chart.js radar/bar/donut charts
  styles.css              <- All CSS
  package.json            <- Node deps (xml2js, jest)
  README.md               <- User-facing docs
  tests/                  <- Unit tests (Jest)
    algorithm.test.js     <- 67 tests: all 8 scoring categories + comprehensive
    utils.test.js         <- 23 tests: deepMerge, writeDataFile, mergeDataFile, CITIES
  data/                   <- JSON data files (seed + auto-updated)
    air-quality.json
    cost-of-living.json
    donor-registration.json
    health-demographics.json
    hospital-quality.json
    traffic-fatalities.json
    wait-time-distributions.json  <- Log-normal params from SRTR Table B10
    competing-risks.json          <- Mortality/delisting from SRTR Table B7
    srtr-center-mapping.json      <- SRTR center codes → 22 TransPlan cities
    srtr-raw/                     <- Downloaded SRTR Excel files (gitignored)
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
    fetch-srtr-excel.py       <- Download SRTR PSR Excel files (6 organs)
    parse-srtr-reports.py     <- Parse Excel → wait-time-distributions.json + competing-risks.json
  .github/workflows/
    fetch-data.yml        <- Weekly data fetch (Mon 6am UTC)
    check-srtr-updates.yml <- Bimonthly SRTR check
  backend/                <- Phase 2 Python FastAPI backend
    main.py               <- FastAPI app, CORS, startup data load
    config.py             <- DATA_DIR, SIMULATION_ITERATIONS, ALLOWED_ORIGINS
    requirements.txt      <- Python dependencies
    models/
      schemas.py          <- Pydantic: PatientProfile, SimulationResult, etc.
    routers/
      health.py           <- GET /health (data freshness)
      simulate.py         <- POST /simulate (stub → M3)
    services/
      data_loader.py      <- Loads data/*.json at startup
      distributions.py    <- Log-normal wait time distributions (6 organs)
      monte_carlo.py      <- Monte Carlo simulation engine (22 cities × 1000 iter)
      competing_risks.py  <- Competing risks: mortality/delisting rates (6 organs)
    tests/                <- pytest suite (120 tests)
  docs/
    status.md             <- THIS FILE (read every session)
    ideas.md              <- Full SRS: requirements, architecture, FDA pathway
    design.md             <- Read when touching UI/UX/CSS
    adr-log.md            <- Grep-searchable decision log
    roadmap.md            <- Phased development plan (5 phases)
    limitations.md        <- Issue tracker (48 items, L-001 through L-048)
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

**48 tracked issues** in `docs/limitations.md`. Read when auditing data quality or planning future work.

| Status | Count | Details |
|--------|-------|---------|
| FIXED | 36 | All critical + most high/medium issues (L-001–L-044) |
| OPEN | 4 | L-045 (FARS API), L-046 (CMS API), L-047 (CDN fallback), L-048 (COL range) |
| DEFERRED | 3 | L-009 (OPO), L-017 (SRTR outcomes), L-033 (donor reg fetch) |
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
