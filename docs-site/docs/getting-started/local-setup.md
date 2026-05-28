---
sidebar_position: 2
---

# Local Setup

Run the full TransPlan stack locally with Monte Carlo simulation, Bayesian inference, and all interactive tools.

## Prerequisites

You need **macOS** as the primary platform (Linux also works via `start.command`), **Python 3.11+** with pip, **Node.js 18+** for data pipeline scripts and tests, and **Git**.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/rivirside/TransPlan.git
cd TransPlan
```

### 2. Set Up Python Environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 3. Install Node Dependencies (optional, for tests/data scripts)

```bash
npm install
```

## Launching the App

### Option A: Double-Click (macOS)

Double-click `TransPlan.app` in Finder. The app starts the FastAPI backend (uvicorn) on a free port starting from 8002, opens your default browser to the app, and runs as a background process with no Terminal window. To stop, double-click `stop.command` or click "End Session" in the app.

### Option B: Terminal

```bash
./start.command
```

This script scans for a free port starting at 8002, starts uvicorn serving both API and static files, and opens the browser. To stop, run the following.

```bash
./stop.command
```

### Option C: Manual uvicorn

```bash
backend/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8002
```

Then open `http://127.0.0.1:8002` in your browser.

## Verifying the Setup

Once running, visit `http://127.0.0.1:<port>/health`:

```json
{
  "status": "ok",
  "version": "2.0.0",
  "data_files_loaded": 10,
  "data_freshness": { ... }
}
```

The green session bar at the bottom of the app also confirms the backend is running.

## Data Pipeline (Optional)

To refresh data from public APIs, first set the required API keys (only needed for EPA and BLS), then run the fetch scripts.

```bash
# Set API keys first (only needed for EPA and BLS)
export EPA_EMAIL=you@example.com
export EPA_API_KEY=your_key
export BLS_API_KEY=your_key

node scripts/fetch-traffic.js
node scripts/fetch-air-quality.js
node scripts/fetch-hospital-quality.js
node scripts/fetch-cost-of-living.js
node scripts/fetch-health-data.js
node scripts/validate-data.js
```

See [Data Pipeline](/architecture/data-pipeline) for details on each data source.

## Running Tests

```bash
# JavaScript unit tests (123 tests)
npm test

# Python backend tests (800+ tests)
cd backend
python -m pytest
```

## Troubleshooting

If a **port is already in use**, the launcher scans for a free port automatically. If `start.command` still fails, manually specify a port using the Option C method.

If you see a **`ModuleNotFoundError: backend`**, you are likely running uvicorn from inside the `backend/` directory. Run it from the repo root instead, using `backend.main:app` as the module path.

If **simulation results are not showing**, the backend is not running. Check that uvicorn started successfully and that `/health` returns `"status": "ok"`.

If **`pip install` fails with a PEP 668 error**, use the venv at `backend/.venv/` directly: `backend/.venv/bin/pip install -r backend/requirements.txt`.
