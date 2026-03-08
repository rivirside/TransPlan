---
sidebar_position: 4
---

# Frontend Architecture

TransPlan's frontend is plain HTML/CSS/JavaScript, with no bundler, no framework, and no build step.

## Design Philosophy

**Static-first, progressively enhanced.** The Phase 1 scoring engine runs entirely in the browser. Phase 2 (Monte Carlo simulation) is loaded asynchronously and degrades gracefully to Phase 1 if the backend is unavailable.

This means the app works offline (Phase 1 only), requires no Node.js to view, has no webpack/Vite/Rollup to configure, and the actual source is always visible in browser DevTools.

## File Responsibilities

### `index.html`

Single-page app structure containing a header with gradient and tagline, a methodology accordion (`<details>`/`<summary>` for accessibility), a patient profile form grouped into fieldsets, a results panel with dual-mode tabs (Phase 1 / Phase 2), an interactive map container (Leaflet), and a session bar visible only on localhost.

### `algorithm.js`

Phase 1 deterministic scoring engine. Pure functions, no side effects. `calculateScores(profile, data)` returns `{ city: score }` for all 22 cities. It includes 8 scoring category functions each returning 0–100, supports configurable weights via form inputs, and is exported as the browser global `window.TransPlanAlgorithm`.

### `script.js`

UI orchestration. Handles form change events (conditional field show/hide for cPRA/MELD/LAS), form submission (calls both `algorithm.js` and `api-client.js`), results rendering for city cards (Phase 1) and probability cards (Phase 2), Leaflet map initialization and overlay controls, and rank badge coloring via CSS classes (`rank-1`, `rank-2`, `rank-3`).

### `api-client.js`

Phase 2 API client. Normalizes form values (camelCase to snake_case, string to typed), POSTs to `/simulate` (relative URL, same-origin), falls back gracefully if the fetch fails (returns `null`), and is used by `script.js` to request simulation results.

### `probability-charts.js`

Chart.js charts for Phase 2 results. `renderCDFCurves(cities)` produces a multi-line CDF chart, `renderCompetingRisks(city)` produces a horizontal stacked bar, and chart instances are stored in module scope for cleanup on re-render.

### `charts.js`

Chart.js charts for Phase 1 results: a weighted bar chart (score breakdown per city), a radar chart per city card, and a donut chart for category weights.

### `data-loader.js`

Runtime data loader. Fetches each `data/*.json` from the server, falls back to hardcoded `DEFAULT_*` constants if a fetch fails, and sets `window.TransPlanData` when loading completes.

### `session.js`

Localhost session management. Polls `/health` to detect whether the backend is running, shows or hides the green session bar accordingly, and provides an "End Session" button that calls `POST /shutdown`.

### `styles.css`

All CSS in one file, including design tokens in `:root` (colors, typography, spacing, shadows), component styles (header, form, cards, accordion, map), two responsive breakpoints at 768px (tablet) and 480px (mobile), and CSS-only toggle switches for map overlays.

## Data Flow

```
Page load
  → data-loader.js fetches data/*.json
  → window.TransPlanData populated
  → User fills form
  → "Calculate" clicked
  → algorithm.js.calculateScores(profile, data) → Phase 1 scores
  → api-client.js.simulate(profile) → POST /simulate → Phase 2 probabilities
  → script.js renders city cards (Phase 1) + probability cards (Phase 2)
  → charts.js renders radar/bar charts
  → probability-charts.js renders CDF + competing risks charts
```

## CDN Dependencies

| Library | Version | Fallback |
|---------|---------|---------|
| Chart.js | 4.x | Local stub (empty chart containers) |
| Leaflet | 1.9.x | Local stub (gray map container) |

Both libraries include CDN failure guards, so the app remains functional even if the CDN is unreachable.

## Styling System

CSS custom properties (design tokens) in `:root`:

```css
:root {
  --color-primary-500: #5B6FE6;  /* indigo */
  --color-accent-500: #6B52AE;   /* purple */
  --font: 'Inter', system-ui, sans-serif;
  --shadow-md: 0 1px 3px rgba(...), 0 4px 6px rgba(...), 0 10px 15px rgba(...);
  /* ... */
}
```

Components use tokens exclusively, with no hardcoded hex colors outside `:root`.

## Accessibility

The frontend includes ARIA labels on map, charts, and result containers, focus-visible styles on all interactive elements, native `<details>`/`<summary>` accordion for keyboard support, a mobile collapse overlay with ARIA controls, and keyboard-accessible toggle switches built on `<input type="checkbox">`.
