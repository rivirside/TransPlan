---
sidebar_position: 4
---

# Frontend Architecture

TransPlan's frontend is plain HTML/CSS/JavaScript, with no bundler, no framework, and no build step.

## Design Philosophy

**Static-first, progressively enhanced.** The Phase 1 scoring engine runs entirely in the browser. Phase 2 (Monte Carlo simulation) is loaded asynchronously and degrades gracefully to Phase 1 if the backend is unavailable.

This means the app works offline (Phase 1 only), requires no Node.js to view, has no webpack/Vite/Rollup to configure, and the actual source is always visible in browser DevTools.

## Multi-Page Architecture

TransPlan uses a two-page architecture:

- **`index.html`** — Landing page: features overview, how-it-works steps, CTA to simulator. Lightweight (no Chart.js, Leaflet, or algorithm.js).
- **`simulator.html`** — Full simulation tool: form, 3-tab results, city detail modal, comparison table, map, methodology accordion.

Both pages share `styles.css`, `themes.css`, `theme-switcher.js`, and `session.js`. The simulator page loads all additional JS files for scoring, charting, and API interaction.

## File Responsibilities

### `index.html`

Landing page with features, how-it-works steps, data source credibility section, and CTA button linking to `simulator.html`. Only loads `styles.css`, `themes.css`, `session.js`, and `theme-switcher.js`.

### `simulator.html`

Full simulation tool containing a patient profile form grouped into fieldsets (including Home Center dropdown and COD multiplier toggle), a methodology accordion (`<details>`/`<summary>` for accessibility), a results panel with three tabs (Location Scores, Simulation Probabilities, Equity Analysis), city detail modal and 3-city comparison table, an interactive map container (Leaflet), info buttons (ⓘ) linking to docs pages, and a session bar visible only on localhost.

### `algorithm.js`

Phase 1 deterministic scoring engine. Pure functions, no side effects. `calculateScores(profile, data)` returns `{ city: score }` for all 22 cities. It includes 8 scoring category functions each returning 0–100, an optional COD multiplier via `_computeCodMultiplier()`, supports configurable weights via form inputs, and is exported as the browser global `window.TransPlanAlgorithm`.

### `script.js`

UI orchestration. Handles form change events (conditional field show/hide for cPRA/MELD/LAS, Home Center population), form submission (calls both `algorithm.js` and `api-client.js`), results rendering for city cards (Phase 1), probability cards (Phase 2), and equity results (Phase 3), Home Center comparison badges (+/- pts and +/- %), city detail modal (8-category breakdown, radar, probabilities), 3-city comparison table with best-value highlighting, Leaflet map initialization and overlay controls, and rank badge coloring via CSS classes.

### `api-client.js`

API client for Phase 2+ endpoints. Normalizes form values (camelCase to snake_case, string to typed), POSTs to `/simulate`, `/sensitivity`, and `/equity-analysis` (relative URLs, same-origin), falls back gracefully if any fetch fails (returns `null`), and includes `home_center` and `adjust_for_cause_of_death` fields.

### `probability-charts.js`

Chart.js charts for Phase 2 results. `renderCDFCurves(cities)` produces a multi-line CDF chart (with optional Home Center reference line), `renderCompetingRisks(city)` produces a horizontal stacked bar, `renderTornadoChart(impacts)` produces a sensitivity analysis tornado chart, and chart instances are stored in module scope for cleanup on re-render.

### `equity-charts.js`

Chart.js charts for equity analysis (IIFE module following `probability-charts.js` pattern). Renders blood type disparity bar chart, age bracket disparity bar chart, and Gini coefficient by city horizontal bar chart.

### `charts.js`

Chart.js charts for Phase 1 results: a weighted bar chart (score breakdown per city), a radar chart per city card, and a donut chart for category weights.

### `data-loader.js`

Runtime data loader. Fetches each `data/*.json` from the server (10 files total), falls back to hardcoded `DEFAULT_*` constants if a fetch fails, and sets `window.TransPlanData` when loading completes.

### `session.js`

Localhost session management. Polls `/health` to detect whether the backend is running, shows or hides the green session bar accordingly, and provides an "End Session" button that calls `POST /shutdown`. Works on any page (IIFE, auto-detects localhost).

### `styles.css`

All CSS in one file, including design tokens in `:root` (colors, typography, spacing, shadows), landing page styles, component styles (nav, form, cards, accordion, map, modals), two responsive breakpoints at 768px (tablet) and 480px (mobile), info button styles, nav active state, and `@media print` rules for print-friendly output.

### `themes.css`

Theme overrides for Clinical (compact, uppercase, muted teal), Research (serif Lora headings, editorial, warm tones), and Government (USWDS-inspired, gov banner, bordered panels) themes. Each is a genuinely different design language, not just color swaps. Includes per-theme landing page overrides.

### `theme-switcher.js`

Floating theme picker with 4 theme options (Default, Clinical, Research, Government). Stores preference in `localStorage`. Works on both landing and simulator pages.

## Data Flow

```
Simulator page load
  → data-loader.js fetches data/*.json (10 files)
  → window.TransPlanData populated
  → User fills form (organ, blood type, clinical scores, home center, COD toggle)
  → "Calculate" clicked
  → algorithm.js.calculateScores(profile, data) → Phase 1 scores
  → api-client.js.simulate(profile) → POST /simulate → Phase 2 probabilities
  → api-client.js.sensitivity(profile, topCity) → POST /sensitivity → tornado data
  → api-client.js.equityAnalysis(profile) → POST /equity-analysis → equity data
  → script.js renders city cards (Tab 1) + probability cards (Tab 2) + equity (Tab 3)
  → charts.js renders radar/bar charts
  → probability-charts.js renders CDF + competing risks + tornado charts
  → equity-charts.js renders blood type / age / Gini charts
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
