---
sidebar_position: 3
---

# Backend API

TransPlan's Phase 2 backend is a FastAPI application serving both the Monte Carlo simulation API and the static frontend.

## Application Structure

```
backend/
  main.py               ← FastAPI app, startup, static file mount
  config.py             ← DATA_DIR, SIMULATION_ITERATIONS, ALLOWED_ORIGINS
  models/
    schemas.py          ← Pydantic schemas (PatientProfile, SimulationResult, etc.)
  routers/
    simulate.py         ← POST /simulate
    health.py           ← GET /health
    shutdown.py         ← POST /shutdown
  services/
    data_loader.py      ← Loads data/*.json at startup, cached in memory
    monte_carlo.py      ← Monte Carlo simulation engine (22 cities × 1000 iter)
    distributions.py    ← Log-normal wait time distributions
    competing_risks.py  ← Exponential mortality/delisting models
```

## Startup Sequence

When `backend/main.py` starts:

1. `data_loader.py` loads all `data/*.json` files into memory
2. `distributions.py` initializes log-normal parameters from `wait-time-distributions.json`
3. `competing_risks.py` initializes hazard rates from `competing-risks.json`
4. FastAPI mounts static files at `/` from the repo root (serves `index.html`, `algorithm.js`, etc.)
5. API router prefixes: `/simulate`, `/health`, `/shutdown`

## Static File Serving

The main app serves the frontend directly:

```python
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```

This is what enables same-origin API requests from the frontend, with no CORS headers needed.

## Configuration

`backend/config.py` exports:

| Setting | Default | Description |
|---------|---------|-------------|
| `DATA_DIR` | `data/` | Path to JSON data files |
| `SIMULATION_ITERATIONS` | `1000` | Monte Carlo iterations per city |
| `ALLOWED_ORIGINS` | `["http://localhost:*"]` | CORS origins (not used in single-process mode) |

## Endpoints

See the full [API Reference](/api-reference/simulate) for request/response schemas.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/simulate` | Run Monte Carlo simulation |
| `GET` | `/health` | Data freshness and status |
| `POST` | `/shutdown` | Graceful session termination (local only) |

## Running the Backend

```bash
# From repo root:
backend/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8003

# Or use the launcher:
./start.command
```

## Error Handling

Pydantic validation errors return 422 Unprocessable Entity with field-level details. A missing data file causes the backend to log a warning and use fallback parameters for the simulation. Simulation timeouts are not implemented (current runtime is ~80ms, well under any reasonable limit). An unknown city returns an empty result set because the city is not in `srtr-center-mapping.json`.

## Logging

uvicorn logs all requests to stdout. The launcher captures these in the terminal (if using `start.command`) or macOS Console.app (if using `TransPlan.app`).
