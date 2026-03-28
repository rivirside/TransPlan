---
sidebar_position: 1
---

# Architecture Overview

TransPlan uses a two-layer architecture: a static frontend (Phase 1) augmented by a Python backend for probabilistic simulation (Phase 2+). The backend is deployed as a Vercel Python function (Phase 3) and simulates across all 248 SRTR transplant centers (Phase 4).

## System Diagram

```
┌──────────────────────────────── Vercel ─────────────────────────────────┐
│                                                                         │
│  ┌──────────────────────────┐   ┌────────────────────────────────────┐ │
│  │    CDN (Static Files)    │   │    Python Function (api/index.py)  │ │
│  │    GET / → index.html    │   │    FastAPI app (backend/main.py)   │ │
│  │    GET /simulator.html   │   │                                    │ │
│  │    GET /algorithm.js     │   │    POST /simulate (248 centers)    │ │
│  │    GET /styles.css       │   │    POST /sensitivity               │ │
│  │    GET /data/*.json      │   │    POST /equity-analysis           │ │
│  │                          │   │    POST /what-if                   │ │
│  │  (rewrites route API     │   │    POST /score                     │ │
│  │   paths to function)     │   │    GET  /centers                   │ │
│  └──────────────────────────┘   │    GET  /health                    │ │
│                                  └────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
         ↓ same-origin requests (Vercel rewrites)
┌──────────────────────────────────────────────────────────────┐
│                   Browser (Frontend)                          │
│                                                               │
│  index.html     ← Landing page (features, CTA)              │
│  simulator.html ← Simulation tool (form, results, map)      │
│  algorithm.js   ← Phase 1: deterministic scoring engine      │
│  api-client.js  ← Phase 2+: calls /simulate + /sensitivity  │
│                    + /equity-analysis + /score + /centers     │
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

### Vercel Deployment (Phase 3)

The Python backend is deployed as a Vercel serverless function (`api/index.py`). Static frontend files are served by Vercel's CDN. API paths (`/simulate`, `/health`, etc.) are routed to the Python function via `vercel.json` rewrites. The frontend uses relative URLs with no hardcoded backend URL, so the same code works locally and on Vercel.

For local development, FastAPI serves both the API endpoints and the static frontend on a single port (same-origin, no CORS needed).

### No Build Step Frontend

The frontend is plain HTML/CSS/JS with no bundler. This avoids build toolchain complexity and makes the code directly debuggable in browser DevTools. CDN imports (Chart.js, Leaflet) include CDN fallback guards.

### Graceful Degradation

If the backend is not running (e.g., GitHub Pages fallback), the frontend falls back silently to Phase 1, providing deterministic scores for 22 cities only. When the backend is available (Vercel deployment), the simulator covers all 248 SRTR centers filtered by the patient's organ.

### Data at Rest vs Runtime

Public API data is fetched by GitHub Actions on a weekly or bimonthly schedule and committed as JSON to the repo. The frontend loads this JSON at runtime. There is no database and no server-side rendering. This keeps deployment simple: Vercel handles the landing page and docs, while uvicorn runs locally for Phase 2 simulation.

## Component Inventory

### Frontend Files

| File | Purpose |
|------|---------|
| `index.html` | Landing page: features, how-it-works, CTA to simulator |
| `simulator.html` | Simulation tool: form, 3-tab results, modals, map, methodology |
| `algorithm.js` | Phase 1 scoring engine: 8 categories (fallback for 22 cities when backend unavailable) |
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
| `backend/services/equity.py` | Demographic equity analysis (48 profiles x all centers, Gini coefficient) |
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
  → monte_carlo.py runs 1000 iterations × N centers (filtered by organ)
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
| Production | Vercel | Static files via CDN + Python function for API |
| Docker | `docker compose up` | Local dev with all dependencies |
