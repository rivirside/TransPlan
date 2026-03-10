---
sidebar_position: 1
---

# Development Guide

:::info Pre-Release
TransPlan is being developed in the open but the repository is currently private. These instructions are for the development team and invited collaborators. The project will be open-sourced at a future stable release milestone.
:::

How to set up TransPlan for local development.

## Prerequisites

You need **Python 3.11+** for the backend, **Node.js 18+** for tests and data scripts, and **Git**. macOS is preferred; Linux works via `start.command`.

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

The `--reload` flag enables hot reload when Python files change. For frontend changes (HTML/CSS/JS), just refresh the browser; no build step is needed.

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

Vanilla JS, no framework, no bundler. ES modules are not used (browser globals via `window.TransPlan*`). Semicolons are optional and omitted in most files. Use `const`/`let` and avoid `var`. No `console.log` in production code.

### Python

PEP 8 style throughout. Pydantic schemas are used for all API inputs/outputs. Services return typed data and routers handle HTTP concerns. Avoid globals: inject dependencies via function parameters where possible.

### CSS

All tokens live in `:root` with no hardcoded hex colors in components. Use `var(--token-name)` everywhere. Desktop-first with responsive breakpoints at 768px and 480px.

### Data Files

All data files in `data/` are JSON. Never commit SRTR raw Excel files (`data/srtr-raw/` is gitignored). Use `mergeDataFile()` in fetch scripts and never overwrite with empty data.

## Making Changes

### Frontend

Edit any `.html`, `.js`, or `.css` file directly. Refresh the browser to see changes. The backend serves static files directly from the repo root.

### Backend

Edit Python files in `backend/`. With `--reload`, uvicorn restarts automatically. Check `http://localhost:8002/health` after changes.

### Adding a New City

1. Add the city to `CITIES` in `scripts/utils.js`
2. Add initial data to each `data/*.json` file (or run fetch scripts)
3. Add to `algorithm.js` city factors
4. Add to `data/srtr-center-mapping.json`
5. Add to `data/wait-time-distributions.json`
6. Add to `data/competing-risks.json`
7. Update tests

### Adding a New Data Category

1. Create `scripts/fetch-<category>.js`
2. Add `data/<category>.json` with seed data
3. Add defaults to `data-loader.js`
4. Add scoring logic to `algorithm.js`
5. Add category weight to the form in `simulator.html`
6. Add unit tests in `tests/algorithm.test.js`

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
  backend/         ← FastAPI Python backend (193 pytest tests)
  data/            ← JSON data files (10 files, seed + auto-updated)
  docs/            ← Project documentation (status, design, ADR, roadmap)
  docs-site/       ← Docusaurus documentation site (you are here)
  scripts/         ← Node.js/Python data fetch scripts
  tests/           ← JavaScript Jest tests (98 tests)
  .github/         ← GitHub Actions workflows
  index.html       ← Landing page (features, CTA)
  simulator.html   ← Simulation tool (form, results, map)
  algorithm.js     ← Phase 1 scoring engine
  script.js        ← UI orchestration
  styles.css       ← All CSS + design tokens + landing page
  themes.css       ← 4-theme system overrides
```
