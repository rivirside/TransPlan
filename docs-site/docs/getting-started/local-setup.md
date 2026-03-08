---
sidebar_position: 2
---

# Local Setup

Run the full TransPlan stack locally with Phase 2 Monte Carlo simulation enabled.

## Prerequisites

You need **macOS** (primary platform; Linux works via `start.command`), **Python 3.11+** with pip, **Node.js 18+** (for data pipeline scripts and tests), and **Git**.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-github-user/TransPlan.git
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

Double-click `TransPlan.app` in Finder. The app starts the FastAPI backend (uvicorn) on a free port starting from 8002, opens your default browser to the app, and runs as a background process with no Terminal window.

To stop: Double-click `stop.command` or click "End Session" in the app.

### Option B: Terminal

```bash
./start.command
```

This script:
1. Scans for a free port starting at 8002
2. Starts uvicorn serving both API and static files
3. Opens the browser

To stop:
```bash
./stop.command
```

### Option C: Manual uvicorn

```bash
backend/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
```

Then open `http://127.0.0.1:8003` in your browser.

## Verifying the Setup

Once running, visit `http://127.0.0.1:<port>/health`:

```json
{
  "status": "ok",
  "version": "2.0.0",
  "data_files_loaded": 8,
  "data_freshness": { ... }
}
```

The green session bar at the bottom of the app also confirms the backend is running.

## Data Pipeline (Optional)

To refresh data from public APIs:

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
# JavaScript unit tests (91 tests)
npm test

# Python backend tests (120 tests)
cd backend
python -m pytest
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port already in use | The launcher scans for a free port automatically. If `start.command` fails, manually specify a port with the Option C method. |
| `ModuleNotFoundError: backend` | Run uvicorn from the repo root, not from inside `backend/`. Use `backend.main:app` as the module path. |
| Phase 2 tab not showing | Backend is not running. Check that uvicorn started and `/health` returns `"status": "ok"`. |
| `pip install` fails (PEP 668) | Use the venv at `backend/.venv/`: `backend/.venv/bin/pip install -r backend/requirements.txt` |
