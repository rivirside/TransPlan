---
sidebar_position: 1
---

# Architecture Overview

TransPlan uses a two-layer architecture: a static frontend (Phase 1) augmented by a Python backend for probabilistic simulation (Phase 2).

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Server (uvicorn)                  │
│                     localhost:8002                            │
│                                                               │
│  ┌─────────────────────────┐  ┌────────────────────────────┐ │
│  │   Static File Serving   │  │       REST API              │ │
│  │   GET /  → index.html   │  │   POST /simulate           │ │
│  │   GET /simulator.html   │  │   POST /sensitivity        │ │
│  │   GET /algorithm.js     │  │   POST /equity-analysis    │ │
│  │   GET /styles.css       │  │   GET  /health             │ │
│  │   GET /data/*.json      │  │   POST /shutdown           │ │
│  └─────────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         ↓ same-origin requests (no CORS needed)
┌──────────────────────────────────────────────────────────────┐
│                   Browser (Frontend)                          │
│                                                               │
│  index.html     ← Landing page (features, CTA)              │
│  simulator.html ← Simulation tool (form, results, map)      │
│  algorithm.js   ← Phase 1: deterministic scoring engine      │
│  api-client.js  ← Phase 2: calls /simulate + /sensitivity   │
│                    + /equity-analysis                         │
│  script.js      ← UI, form handling, results display         │
│  charts.js      ← Chart.js radar/bar/donut                   │
│  probability-charts.js ← CDF curves + competing risks +     │
│                          tornado sensitivity chart            │
│  equity-charts.js ← Blood type/age/Gini equity charts        │
│  data-loader.js ← loads data/*.json from server              │
│  themes.css     ← 4-theme design system overrides            │
│  theme-switcher.js ← Theme picker UI                         │
└──────────────────────────────────────────────────────────────┘
         ↓ data loaded at runtime
┌──────────────────────────────────────────────────────────────┐
│                   Data Layer (data/)                           │
│                                                               │
│  10 JSON files auto-updated by GitHub Actions / manual       │
│  Fallback to hardcoded defaults if unavailable               │
└──────────────────────────────────────────────────────────────┘
         ↑ updated by
┌──────────────────────────────────────────────────────────────┐
│              GitHub Actions (Data Pipeline)                   │
│                                                               │
│  fetch-traffic.js      ← NHTSA FARS (retired; seed only)    │
│  fetch-air-quality.js  ← EPA AQS API                        │
│  fetch-hospital-quality.js ← CMS Provider Data              │
│  fetch-cost-of-living.js   ← BLS API v2                     │
│  fetch-health-data.js      ← CDC SODA API                   │
│  fetch-srtr-excel.py       ← SRTR PSR Excel downloads       │
│  parse-srtr-reports.py     ← Excel → JSON                   │
└──────────────────────────────────────────────────────────────┘
```

## Key Architectural Decisions

### Single-Process Architecture (ADR-015)

FastAPI serves both the API endpoints and the static frontend on a single port. This eliminates CORS complexity and enables same-origin `/simulate` requests. The frontend uses relative URLs (`/simulate`, `/health`) with no hardcoded backend URL.

### No Build Step Frontend

The frontend is plain HTML/CSS/JS with no bundler. This avoids build toolchain complexity and makes the code directly debuggable in browser DevTools. CDN imports (Chart.js, Leaflet) include CDN fallback guards.

### Graceful Degradation

If the backend is not running, the frontend falls back silently to Phase 1 (deterministic scores only). The Phase 2 tab remains hidden. A yellow banner informs the user that probabilistic simulation is unavailable.

### Data at Rest vs Runtime

Public API data is fetched by GitHub Actions on a weekly/bimonthly schedule and committed as JSON to the repo. The frontend loads this JSON at runtime. There is no database and no server-side rendering. This keeps deployment simple (Vercel for the landing page and docs; uvicorn locally for Phase 2 simulation).

## Component Inventory

### Frontend Files

| File | Purpose |
|------|---------|
| `index.html` | Landing page: features, how-it-works, CTA to simulator |
| `simulator.html` | Simulation tool: form, 3-tab results, modals, map, methodology |
| `algorithm.js` | Phase 1 scoring engine: 8 categories × 22 cities |
| `script.js` | UI orchestration: form, results display, map controls, city detail modal, comparison |
| `api-client.js` | API client: POST /simulate, /sensitivity, /equity-analysis, graceful fallback |
| `probability-charts.js` | CDF line charts, competing risks bars, tornado sensitivity chart (Chart.js) |
| `equity-charts.js` | Blood type disparity, age bracket disparity, Gini by city charts (Chart.js) |
| `charts.js` | Phase 1 charts: radar, weighted bar, donut (Chart.js) |
| `data-loader.js` | Runtime JSON loader with hardcoded fallback defaults |
| `session.js` | Session bar: health check, "End Session" button |
| `styles.css` | All CSS: design tokens, landing page, components, responsive breakpoints |
| `themes.css` | Theme overrides: Clinical, Research, Government (+ landing page per-theme) |
| `theme-switcher.js` | Floating theme picker (4 themes) |

### Backend Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, startup data load, static file mounting |
| `backend/config.py` | Configuration: DATA_DIR, SIMULATION_ITERATIONS, ALLOWED_ORIGINS |
| `backend/models/schemas.py` | Pydantic schemas: PatientProfile, SimulationResult, SensitivityResult, EquityAnalysisResult |
| `backend/routers/simulate.py` | POST /simulate endpoint |
| `backend/routers/sensitivity.py` | POST /sensitivity endpoint |
| `backend/routers/equity.py` | POST /equity-analysis endpoint |
| `backend/routers/health.py` | GET /health endpoint |
| `backend/routers/shutdown.py` | POST /shutdown endpoint (local session management) |
| `backend/services/monte_carlo.py` | Monte Carlo simulation engine |
| `backend/services/distributions.py` | Log-normal wait time model |
| `backend/services/competing_risks.py` | Mortality/delisting exponential models |
| `backend/services/sensitivity.py` | Sensitivity analysis: parameter impact on p_transplant_24mo |
| `backend/services/equity.py` | Demographic equity analysis (48 profiles × 22 cities, Gini coefficient) |
| `backend/services/brier_score.py` | Brier score calibration: Monte Carlo vs analytical validation |
| `backend/services/data_loader.py` | Loads and caches data/*.json at startup |

## Data Flow: Simulation Request

```
User submits form
  → script.js collects form values
  → api-client.js normalizes (camelCase → snake_case, string → number)
  → POST /simulate { patient: {...} }
  → backend validates with Pydantic
  → data_loader.py provides wait-time-distributions.json + competing-risks.json
  → monte_carlo.py runs 1000 × 22 simulations
  → returns SimulationResult JSON
  → api-client.js parses response
  → probability-charts.js renders CDF curves + competing risks bars
  → script.js renders probability cards
```

## Deployment Targets

| Mode | Command | Notes |
|------|---------|-------|
| Local (macOS) | Double-click `TransPlan.app` | No Terminal, background app |
| Local (any) | `./start.command` | Bash script, opens browser |
| Local (manual) | `uvicorn backend.main:app` | Full control |
| Static (hosted) | Vercel | Landing page + docs site (no simulation) |
| Production | TBD (Docker Compose) | Future: cloud deployment with backend |
