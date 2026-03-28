---
sidebar_position: 3
---

# Backend API

TransPlan's backend is a FastAPI application providing Monte Carlo, Bayesian, and MCMC simulation across all 248 SRTR transplant centers. It is deployed as a Vercel Python function in production and can also run locally via uvicorn.

## Application Structure

```
api/
  index.py              <- Vercel function entry point (imports backend.main)
backend/
  main.py               <- FastAPI app, startup, static file mount (skipped on Vercel)
  config.py             <- DATA_DIR, SIMULATION_ITERATIONS, ALLOWED_ORIGINS
  models/
    schemas.py          <- Pydantic schemas (PatientProfile, SimulationResult,
                           SensitivityResult, EquityAnalysisResult, CenterScore, etc.)
  routers/
    simulate.py         <- POST /simulate (MC, BBN, MCMC; iterations, copula_theta, elasticity)
    sensitivity.py      <- POST /sensitivity (accepts center_code)
    equity.py           <- POST /equity-analysis
    what_if.py          <- POST /what-if, /policy-scenario, /travel-subsidy-analysis
    centers.py          <- GET /centers, /centers/{code}
    score.py            <- POST /score (248 centers, deterministic scoring)
    trends.py           <- GET /trends/{organ}, /trends/{city}/{organ}
    health.py           <- GET /health
    shutdown.py         <- POST /shutdown (local only, disabled on Vercel)
    spatial.py          <- GET /spatial-layers, /interpolated-value, etc.
  services/
    data_loader.py      <- Loads data/*.json at startup; centers_for_organ() filter
    monte_carlo.py      <- Monte Carlo engine (all centers for organ x N iterations)
    bayesian_network.py <- BBN exact inference (22-region DAG, mapped to 248 centers)
    mcmc_inference.py   <- MCMC posterior sampling (22-city traces, mapped to 248 centers)
    distributions.py    <- Log-normal wait time distributions (city + center-code lookup)
    competing_risks.py  <- Exponential mortality/delisting (city + center-code lookup)
    outcomes.py         <- Post-transplant outcomes (center-level data for 243 centers)
    sensitivity.py      <- Parameter impact analysis (tornado chart data)
    equity.py           <- Demographic equity (48 profiles x all centers, Gini)
    scoring.py          <- Deterministic 8-category scoring (all 248 centers)
```

## Startup Sequence

When `backend/main.py` starts, it uses `data_loader.py` to load all `data/*.json` files into memory. Then `distributions.py` initializes log-normal parameters from `wait-time-distributions.json`, and `competing_risks.py` initializes hazard rates from `competing-risks.json`. After the data layer is ready, FastAPI mounts static files at `/` from the repo root, which serves `index.html`, `simulator.html`, `algorithm.js`, and all other frontend assets. The API routers are registered at their respective paths: `/simulate`, `/sensitivity`, `/equity-analysis`, `/health`, and `/shutdown`.

## Static File Serving

The main app serves the frontend directly:

```python
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```

This is what enables same-origin API requests from the frontend, with no CORS headers needed.

## Configuration

`backend/config.py` exports key settings. `DATA_DIR` points to the JSON data files. `SIMULATION_ITERATIONS` defaults to `1000` (overridable per request via `?iterations=N`). `ALLOWED_ORIGINS` includes `localhost`, `transplant.today`, and `*.vercel.app`. Additional parameters (`copula_theta`, `elasticity`) are overridable via query params on `/simulate`.

## Endpoints

See the full [API Reference](/api-reference/simulate) for request/response schemas.

`POST /simulate` runs Monte Carlo (default), Bayesian, or MCMC simulation across all SRTR centers for the patient's organ. Iterations, copula theta, and supply-wait elasticity are adjustable via query params. `POST /sensitivity` performs parameter sensitivity for a single center (accepts `center_code`). `POST /equity-analysis` runs demographic equity across 48 profiles for all centers. `POST /score` returns deterministic 8-category scores for all 248 centers. `GET /centers` lists all SRTR centers with metadata. `GET /health` reports data freshness. `POST /shutdown` is local-only (disabled on Vercel).

### Center Counts by Organ

| Organ | Centers |
|-------|---------|
| Kidney | 233 |
| Heart | 149 |
| Liver | 148 |
| Pancreas | 99 |
| Lung | 74 |
| Intestine | 21 |

## Running the Backend

```bash
# From repo root:
backend/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8002

# Or use the launcher:
./start.command
```

## Inference Engines

| Engine | Query Param | Coverage | Speed | Notes |
|--------|-------------|----------|-------|-------|
| Monte Carlo | `inference_mode=monte_carlo` (default) | All 248 centers (center-level data) | ~1-15s depending on organ | Full center-level wait-time and competing-risk factors |
| Bayesian (BBN) | `inference_mode=bayesian` | All 248 centers (mapped to 22 BBN regions) | ~100ms | Exact Variable Elimination; centers sharing a region get same probabilities |
| MCMC | `inference_mode=mcmc` | All 248 centers (mapped to 22 trace cities) | ~500ms | Requires pre-fitted traces (not yet available; returns 503) |

Future work: rebuild BBN with 248-center Region node (#206) and refit MCMC hierarchy (#207).

## Error Handling

Pydantic validation errors return 422 Unprocessable Entity with field-level details. If a data file is missing, the backend logs a warning and uses fallback parameters. If Bayesian/MCMC dependencies are not installed, the endpoint returns 503 with a clear message. An unknown center code returns a 400 error.

## Logging

uvicorn logs all requests to stdout. The launcher captures these in the terminal when using `start.command`, or in macOS Console.app when using `TransPlan.app`.
