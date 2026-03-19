---
sidebar_position: 1
---

# Development Guide

:::info Pre-Release
TransPlan is being developed in the open but the repository is currently private. These instructions are for the development team and invited collaborators. The project will be open-sourced at a future stable release milestone.
:::

This guide explains how to set up TransPlan for local development.

## Prerequisites

You need **Python 3.11+** for the backend, **Node.js 18+** for tests and data scripts, and **Git**. macOS is the preferred platform, though Linux works via `start.command`.

## Setup

```bash
git clone https://github.com/rivirside/TransPlan.git
cd TransPlan

# Python venv
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# Node deps (for tests + data scripts)
npm install
```

## Running in Development

```bash
# Start the full stack (backend + static files on one port)
backend/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8002 --reload
```

The `--reload` flag enables hot reload when Python files change. For frontend changes (HTML, CSS, or JS), just refresh the browser since there is no build step.

## Running Tests

```bash
# JavaScript unit tests (98 tests)
npm test

# Python backend tests (193 tests)
cd backend
python -m pytest

# With verbose output
python -m pytest -v

# Run a specific test file
python -m pytest tests/test_monte_carlo.py -v
```

## Project Conventions

### JavaScript

The frontend uses vanilla JS with no framework and no bundler. ES modules are not used; instead, browser globals are shared via `window.TransPlan*`. Semicolons are optional and omitted in most files. Use `const` and `let` rather than `var`. Avoid `console.log` in production code.

### Python

PEP 8 style is used throughout the backend. Pydantic schemas define all API inputs and outputs. Services return typed data while routers handle HTTP concerns. Avoid globals and inject dependencies via function parameters where possible.

### CSS

All tokens live in `:root` with no hardcoded hex colors in components. Use `var(--token-name)` everywhere. The layout is desktop-first with responsive breakpoints at 768px and 480px.

### Data Files

All data files in `data/` are JSON. SRTR raw Excel files should never be committed (`data/srtr-raw/` is gitignored). Fetch scripts must use `mergeDataFile()` and should never overwrite files with empty data.

## Making Changes

### Frontend

Edit any `.html`, `.js`, or `.css` file directly and refresh the browser to see changes. The backend serves static files directly from the repo root.

### Backend

Edit Python files in `backend/`. With `--reload`, uvicorn restarts automatically. Check `http://localhost:8002/health` after making changes to confirm the backend is healthy.

### Adding a New City

To add a new city, start by adding it to `CITIES` in `scripts/utils.js`, then add initial data to each `data/*.json` file (or run the fetch scripts). Add the city to `algorithm.js` city factors, to `data/srtr-center-mapping.json`, to `data/wait-time-distributions.json`, and to `data/competing-risks.json`. Finally, update the relevant tests.

### Adding a New Data Category

Create a fetch script at `scripts/fetch-<category>.js`, then add `data/<category>.json` with seed data. Add defaults to `data-loader.js` and scoring logic to `algorithm.js`. Add the category weight to the form in `simulator.html` and write unit tests in `tests/algorithm.test.js`.

## Git Workflow

Commit after each logical unit of work with a descriptive message. Update `docs/status.md` when project state changes. Add ADR entries in `docs/adr-log.md` for non-obvious architectural choices. Run tests before committing.

```bash
npm test && cd backend && python -m pytest && cd ..
git add <specific files>
git commit -m "feat: description of change"
```

## Directory Reference

```
TransPlan/
  backend/         <- FastAPI Python backend (193 pytest tests)
  data/            <- JSON data files (10 files, seed + auto-updated)
  docs/            <- Project documentation (status, design, ADR, roadmap)
  docs-site/       <- Docusaurus documentation site (you are here)
  scripts/         <- Node.js/Python data fetch scripts
  tests/           <- JavaScript Jest tests (98 tests)
  .github/         <- GitHub Actions workflows
  index.html       <- Landing page (features, CTA)
  simulator.html   <- Simulation tool (form, results, map)
  algorithm.js     <- Phase 1 scoring engine
  script.js        <- UI orchestration
  styles.css       <- All CSS + design tokens + landing page
  themes.css       <- 4-theme system overrides
```
