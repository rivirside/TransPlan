---
sidebar_position: 4
---

# Frontend Architecture

TransPlan's frontend is plain HTML, CSS, and JavaScript with no bundler, no framework, and no build step.

## Design Philosophy

The frontend follows a static-first, progressively enhanced approach. The Phase 1 scoring engine runs entirely in the browser. Phase 2 (Monte Carlo simulation) loads asynchronously and degrades gracefully to Phase 1 if the backend is unavailable. This means the app works offline for Phase 1, requires no Node.js to view, has no webpack or Vite or Rollup to configure, and the actual source is always visible in browser DevTools.

## Multi-Page Architecture

TransPlan uses a two-page architecture. `index.html` serves as the landing page with a features overview, how-it-works steps, and a call-to-action linking to the simulator. It is lightweight and does not load Chart.js, Leaflet, or `algorithm.js`. `simulator.html` is the full simulation tool with the patient profile form, three-tab results panel, city detail modal, comparison table, map, and methodology accordion. Both pages share `styles.css`, `themes.css`, `theme-switcher.js`, and `session.js`. The simulator page loads all additional JS files for scoring, charting, and API interaction.

## File Responsibilities

### Landing Page (`index.html`)

The landing page presents features, how-it-works steps, a data source credibility section, and a CTA button linking to `simulator.html`. It only loads `styles.css`, `themes.css`, `session.js`, and `theme-switcher.js`.

### Simulator (`simulator.html`)

The simulator is the core application. It contains a patient profile form grouped into fieldsets (including a Home Center dropdown and COD multiplier toggle), a methodology accordion built with native `<details>` and `<summary>` elements for accessibility, and a results panel with three tabs: Location Scores, Simulation Probabilities, and Equity Analysis. Users can click any city card to open a detail modal with an 8-category breakdown, or select up to 3 cities for side-by-side comparison. An interactive Leaflet map and info buttons linking to docs pages round out the interface. A session bar appears only on localhost.

### Scoring Engine (`algorithm.js`)

This is the Phase 1 deterministic scoring engine. It consists of pure functions with no side effects. The main function, `calculateScores(profile, data)`, returns a score for all 22 cities. Eight scoring category functions each return values from 0 to 100. An optional COD multiplier is available through `_computeCodMultiplier()`. Category weights are configurable via form inputs. The module is exported as the browser global `window.TransPlanAlgorithm`.

### UI Orchestration (`script.js`)

This file handles all user interaction. It manages form change events (conditional field show/hide for cPRA, MELD, and LAS; Home Center population), form submission (calling both `algorithm.js` and `api-client.js`), and results rendering for city cards (Phase 1), probability cards (Phase 2), and equity results (Phase 3). It also handles the Home Center comparison badges showing score and probability differences, the city detail modal with its 8-category breakdown and radar and probability charts, the 3-city comparison table with best-value highlighting, Leaflet map initialization and overlay controls, and rank badge coloring via CSS classes.

### API Client (`api-client.js`)

The API client handles Phase 2+ endpoints. It normalizes form values from camelCase to snake_case and from strings to typed values, then POSTs to `/simulate`, `/sensitivity`, and `/equity-analysis` using relative URLs for same-origin requests. If any fetch fails, it falls back gracefully and returns `null`. Request payloads include `home_center` and `adjust_for_cause_of_death` fields.

### Phase 2 Charts (`probability-charts.js`)

This module renders Chart.js visualizations for Phase 2 results. `renderCDFCurves(cities)` produces a multi-line CDF chart with an optional Home Center reference line. `renderCompetingRisks(city)` produces a horizontal stacked bar chart. `renderTornadoChart(impacts)` produces a sensitivity analysis tornado chart. Chart instances are stored in module scope for cleanup on re-render.

### Equity Charts (`equity-charts.js`)

An IIFE module following the same pattern as `probability-charts.js`, this file renders three equity analysis charts: a blood type disparity bar chart, an age bracket disparity bar chart, and a Gini coefficient by city horizontal bar chart.

### Phase 1 Charts (`charts.js`)

Chart.js charts for Phase 1 results, including a weighted bar chart showing the score breakdown per city, a radar chart per city card, and a donut chart for category weights.

### Data Loader (`data-loader.js`)

The runtime data loader fetches each of the 10 `data/*.json` files from the server. If a fetch fails, it falls back to hardcoded `DEFAULT_*` constants representing the last known-good values. When loading completes, it sets `window.TransPlanData`.

### Session Manager (`session.js`)

Handles localhost session management. It polls `/health` to detect whether the backend is running, shows or hides the green session bar accordingly, and provides an "End Session" button that calls `POST /shutdown`. It works on any page as an IIFE that auto-detects localhost.

### Styles (`styles.css`)

All CSS lives in one file. It includes design tokens in `:root` (colors, typography, spacing, shadows), landing page styles, component styles for the nav, form, cards, accordion, map, and modals, two responsive breakpoints at 768px (tablet) and 480px (mobile), info button styles, nav active state, and `@media print` rules for print-friendly output.

### Themes (`themes.css`)

Theme overrides for Clinical (compact, uppercase, muted teal), Research (serif Lora headings, editorial, warm tones), and Government (USWDS-inspired, gov banner, bordered panels). Each theme is a genuinely different design language rather than a simple color swap. Per-theme landing page overrides are included.

### Theme Switcher (`theme-switcher.js`)

A floating theme picker with 4 theme options: Default, Clinical, Research, and Government. Preference is stored in `localStorage` and works on both the landing and simulator pages.

## Data Flow

```
Simulator page load
  -> data-loader.js fetches data/*.json (10 files)
  -> window.TransPlanData populated
  -> User fills form (organ, blood type, clinical scores, home center, COD toggle)
  -> "Calculate" clicked
  -> algorithm.js.calculateScores(profile, data) -> Phase 1 scores
  -> api-client.js.simulate(profile) -> POST /simulate -> Phase 2 probabilities
  -> api-client.js.sensitivity(profile, topCity) -> POST /sensitivity -> tornado data
  -> api-client.js.equityAnalysis(profile) -> POST /equity-analysis -> equity data
  -> script.js renders city cards (Tab 1) + probability cards (Tab 2) + equity (Tab 3)
  -> charts.js renders radar/bar charts
  -> probability-charts.js renders CDF + competing risks + tornado charts
  -> equity-charts.js renders blood type / age / Gini charts
```

## CDN Dependencies

TransPlan depends on two CDN-hosted libraries: Chart.js 4.x and Leaflet 1.9.x. Both libraries include CDN failure guards that show gray placeholder containers if the CDN is unreachable. The app remains functional for scoring and simulation even without these libraries.

## Styling System

CSS custom properties (design tokens) are defined in `:root`:

```css
:root {
  --color-primary-500: #5B6FE6;  /* indigo */
  --color-accent-500: #6B52AE;   /* purple */
  --font: 'Inter', system-ui, sans-serif;
  --shadow-md: 0 1px 3px rgba(...), 0 4px 6px rgba(...), 0 10px 15px rgba(...);
}
```

Components use tokens exclusively, with no hardcoded hex colors outside `:root`.

## Accessibility

The frontend includes ARIA labels on the map, charts, and result containers. Focus-visible styles appear on all interactive elements. The methodology accordion uses native `<details>` and `<summary>` elements for keyboard support. The mobile collapse overlay uses ARIA controls, and toggle switches are built on `<input type="checkbox">` for keyboard accessibility.
