---
sidebar_position: 3
---

# Backend API

TransPlan's Phase 2 backend is a FastAPI application serving both the Monte Carlo simulation API and the static frontend.

## Application Structure

```
backend/
  main.py               <- FastAPI app, startup, static file mount
  config.py             <- DATA_DIR, SIMULATION_ITERATIONS, ALLOWED_ORIGINS
  models/
    schemas.py          <- Pydantic schemas (PatientProfile, SimulationResult,
                           SensitivityResult, EquityAnalysisResult, etc.)
  routers/
    simulate.py         <- POST /simulate
    sensitivity.py      <- POST /sensitivity
    equity.py           <- POST /equity-analysis
    health.py           <- GET /health
    shutdown.py         <- POST /shutdown
  services/
    data_loader.py      <- Loads data/*.json at startup, cached in memory
    monte_carlo.py      <- Monte Carlo simulation engine (22 cities x 1000 iter)
    distributions.py    <- Log-normal wait time distributions
    competing_risks.py  <- Exponential mortality/delisting models
    sensitivity.py      <- Parameter impact analysis (tornado chart data)
    equity.py           <- Demographic equity (48 profiles x 22 cities, Gini)
    brier_score.py      <- Brier score calibration validation
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

`backend/config.py` exports three key settings. `DATA_DIR` defaults to `data/` and points to the JSON data files. `SIMULATION_ITERATIONS` defaults to `1000` and controls the number of Monte Carlo iterations per city. `ALLOWED_ORIGINS` defaults to `["http://localhost:*"]` and specifies CORS origins, though these are not used in single-process mode.

## Endpoints

See the full [API Reference](/api-reference/simulate) for request/response schemas.

The `POST /simulate` endpoint runs the Monte Carlo simulation across 22 cities with 1000 iterations each. `POST /sensitivity` performs parameter sensitivity analysis and returns tornado chart data. `POST /equity-analysis` runs demographic equity analysis across 48 profiles for all 22 cities. `GET /health` reports data freshness and system status. `POST /shutdown` performs graceful session termination and is restricted to local use only.

## Running the Backend

```bash
# From repo root:
backend/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8002

# Or use the launcher:
./start.command
```

## Error Handling

Pydantic validation errors return 422 Unprocessable Entity with field-level details. If a data file is missing, the backend logs a warning and uses fallback parameters for the simulation instead of failing outright. Simulation timeouts are not implemented because the current runtime is approximately 80ms, well under any reasonable limit. An unknown city returns an empty result set because the city is not found in `srtr-center-mapping.json`.

## Logging

uvicorn logs all requests to stdout. The launcher captures these in the terminal when using `start.command`, or in macOS Console.app when using `TransPlan.app`.
