# TransPlan

Clinical decision support for transplant patients. TransPlan helps identify the best US cities and centers for organ transplantation by analyzing 40+ factors across 8 weighted categories, backed by Monte Carlo simulation, Bayesian inference, and MCMC posterior sampling.

> **Pre-release.** Under active development. Contact: tomer@arizona.edu

## Quick Start

```bash
# Prerequisites: Python 3.12+, Node.js 18+

# Clone and install
git clone https://github.com/rivirside/TransPlan.git
cd TransPlan
npm ci                           # Frontend dependencies (Jest tests, fetch scripts)
pip install -r backend/requirements.txt  # Backend dependencies

# Run
uvicorn backend.main:app --port 8002
# Open http://localhost:8002
```

Or use Docker:

```bash
docker compose up
# Open http://localhost:8002
```

Or double-click `TransPlan.app` (macOS).

## Architecture

```
Frontend (static HTML/JS)              Backend (FastAPI)
  simulator/   ─── simulation ───────  POST /simulate ──── Monte Carlo (1000 iter)
  shared/      ─── API client ───────  POST /simulate?inference_mode=bayesian
  components/  ─── site chrome ──────  POST /simulate?inference_mode=mcmc
  explorer/    ─── data layers ──────  POST /sensitivity, /equity-analysis, /what-if
  algorithm.js ─── scoring fallback    GET  /centers, /trends, /spatial-layers
                                       GET  /api/v1/... (public API with rate limiting)
```

Single-process: FastAPI serves both API and static frontend on one port. Frontend degrades gracefully when backend is unavailable, using local scoring as fallback.

### Public REST API

All endpoints available under `/api/v1/` with rate limiting:

| Tier | Unauthenticated | With `X-Api-Key` |
|------|----------------|-------------------|
| Simulation | 30 req/min | 150 req/min |
| Data | 120 req/min | 600 req/min |
| Spatial | 60 req/min | 300 req/min |

Set `TRANSPLAN_API_KEYS=key1,key2` environment variable. Interactive docs at `/docs` and `/redoc`.

## Scoring Categories

| # | Category | Weight | Data Source |
|---|----------|--------|-------------|
| 1 | Medical Compatibility | 25% | Blood type, age, sex, organ match |
| 2 | Wait Time | 20% | SRTR center-level wait factors |
| 3 | Donor Availability | 18% | Registration rates, COD-based supply model |
| 4 | Hospital Quality | 15% | CMS volume, SRTR outcomes |
| 5 | Geographic | 10% | BLS cost of living, EPA air quality |
| 6 | Health Demographics | 7% | CDC PLACES county-level (2,956 counties) |
| 7 | Policy | 3% | State donation laws |
| 8 | Socioeconomic | 2% | Support systems |

Weights are configurable via UI sliders or `custom_weights` in the API.

## Inference Engines

| Engine | Method | Speed | Use Case |
|--------|--------|-------|----------|
| Monte Carlo | 1000-iteration simulation with competing risks | ~80ms | Default, most tested |
| Bayesian (BBN) | 12-node DAG, exact inference via pgmpy | ~30ms | Fast, deterministic |
| MCMC | PyMC hierarchical survival model, posterior sampling | ~500ms | Honest uncertainty quantification |

All engines produce: per-city transplant probabilities at 6/12/24/36 months, 95% confidence intervals, competing risks (transplant/mortality/delisting), and median wait times.

## Data Pipeline

### Automated (GitHub Actions weekly)

| Source | Script | Auth |
|--------|--------|------|
| NHTSA FARS (traffic fatalities) | `fetch-traffic.js` | None |
| EPA AQS (air quality) | `fetch-air-quality.js` | `EPA_EMAIL`, `EPA_API_KEY` |
| CMS Provider Data (hospitals) | `fetch-hospital-quality.js` | None |
| BLS (cost of living) | `fetch-cost-of-living.js` | `BLS_API_KEY` |
| CDC PLACES (health, 22 cities) | `fetch-health-data.js` | None |
| CDC PLACES (health, 2,956 counties) | `fetch-health-data-counties.js` | None |
| EPA AQS (per-monitor air quality) | `fetch-air-quality-monitors.js` | `EPA_EMAIL`, `EPA_API_KEY` |
| CDC WONDER (cause of death) | `fetch-cod-data.js` | None |
| SRTR PSR Excel | `fetch-srtr-excel.py` | None |

### Required Secrets

Set `EPA_BLS_KEYS` in GitHub Actions (Settings > Secrets):

```
EPA_EMAIL=your-email@example.com
EPA_API_KEY=your-epa-key
BLS_API_KEY=your-bls-key
```

Free signups: [EPA AQS](https://aqs.epa.gov/aqsweb/documents/data_api.html), [BLS](https://data.bls.gov/registrationEngine/).

## Project Structure

```
TransPlan/
  index.html              # Landing page
  simulator.html          # Simulation tool (form, results, map)
  algorithm.js            # Client-side scoring engine (8 categories)
  simulator/              # Modular simulator JS (index, map, results, form, tier-panel)
  shared/                 # Cross-page utilities (api-client, export, data-loader, geo)
  components/             # Site chrome (nav + footer)
  explorer/               # Explorer page modules (data layers, spatial analysis)
  centers-page.js         # Centers tabbed page (Find/Browse/Estimate)
  data/                   # JSON data files (auto-updated + manual)
  scripts/                # Node.js fetch scripts + Python analysis scripts
  backend/
    main.py               # FastAPI app (API + static serving)
    config.py             # Settings (iterations, elasticity, copula params)
    routers/              # API endpoint handlers
    services/             # Business logic (simulation, interpolation, etc.)
    middleware/            # Rate limiting
    tests/                # pytest suite (800+ tests)
  tests/                  # Jest suite (123 tests)
  docs/                   # Project docs (status, design, limitations, roadmap)
  docs-site/              # Docusaurus documentation site (22 pages)
  notebooks/              # Validation Jupyter notebooks (6 notebooks, 39 figures)
  paper.md                # JOSS submission paper
```

## Testing

```bash
# Backend (from backend/)
python -m pytest tests/ -v           # 800+ tests

# Frontend (from repo root)
npx jest                             # 123 tests

# Data validation
node scripts/validate-data.js
```

## Key Features

- **248 SRTR transplant centers** with geographic coordinates
- **Spatial interpolation** (RBF/IDW) across 24 data layers from 2,956 counties
- **UNOS allocation circle modeling** (250nm/500nm radius analysis)
- **Clayton copula** for correlated mortality/delisting competing risks
- **Policy scenario engine** (4 UNOS scenarios with literature-backed parameters)
- **Equity analysis** (48-profile demographic matrix, Gini coefficient)
- **Historical trends** (14 biannual SRTR releases, 2019-2025)
- **Dark and light mode** with automatic OS preference detection
- **Cross-engine validation** service for model comparison
- **Model iteration comparison** scripts for tracking changes across versions

## Documentation

- `docs/status.md` — Current project state (read every session)
- `docs/roadmap.md` — Phased development plan
- `docs/limitations.md` — 65 tracked issues with status
- `docs/adr-log.md` — Architectural decision records
- `docs-site/` — Full Docusaurus site with interactive visualizations

## Deployment

**Vercel** (primary): `vercel.json` at repo root, zero-config.

**Docker**: `docker compose up` — single container, data volume-mounted.

**Local**: `cd backend && uvicorn main:app --port 8002`

## License

MIT. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
