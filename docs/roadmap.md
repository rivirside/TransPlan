# TransPlan - Roadmap

> **Grep-searchable.** Search for specific features or areas to check their status.

## Completed

### v0.1 - Original Codebase
- [x] 8-category scoring algorithm with 50+ factors
- [x] 21 cities across 6 organ types
- [x] Interactive Leaflet map with 10 overlay layers
- [x] Health profile form (organ, blood type, age, sex, urgency, weight, height, insurance)
- [x] Methodology section explaining the algorithm
- [x] Responsive design

### v0.2 - Bug Fixes + Data Pipeline + Charts (current session)
- [x] Fix multiplicative scoring bug in `calculateMedicalCompatibilityScore`
- [x] Fix `/100` normalization bug in `calculateDonorAvailabilityScore`
- [x] Remove non-deterministic random jitter from `calculateComprehensiveScore`
- [x] Extract hardcoded data into `data/` JSON files
- [x] Create `data-loader.js` with fallback defaults
- [x] Refactor algorithm.js to use `window.TransPlanData`
- [x] Refactor script.js to dynamically score all 21 cities
- [x] Add Chart.js: radar (per city), bar (comparison), donut (weights)
- [x] Data freshness banner
- [x] Create 6 fetch scripts (NHTSA, EPA, CMS, BLS, CDC, SRTR)
- [x] Create validation script
- [x] GitHub Actions: weekly fetch + bimonthly SRTR check
- [x] Documentation system (status, design, ADR, roadmap, brand bible)
- [x] README with architecture and usage docs

### v0.2.1 - Browser Testing & Derived Metrics (current session)
- [x] Generate `package-lock.json` via `npm install`
- [x] Browser test: open index.html, submit form, verify charts render
- [x] Browser test: verify freshness banner appears with 10 source dots
- [x] Browser test: verify radar charts appear in city cards (22 canvases)
- [x] Browser test: verify comparison bar chart renders
- [x] Browser test: verify donut chart renders in methodology
- [x] Verify no console errors (zero errors confirmed)
- [x] Fix N/A metrics: derive wait times, match rates, donor rates from algorithm data
- [x] Fix N/A factors: generate city-specific factors from scoring breakdown
- [x] Fix "1 months" pluralization bug
- [x] All v0.2 work committed (10 commits) and pushed
- [x] API keys configured as `EPA_BLS_KEYS` secret
- [x] Add `.gitignore` for node_modules, .DS_Store

## Not Yet Done

### Short-term
- [ ] Configure GitHub Pages deployment (Settings > Pages > Source: main)
- [ ] Run fetch scripts locally and verify output against live APIs
- [ ] Test GitHub Actions workflow with manual trigger

## Future Ideas (not committed to)

### Data Quality
- [ ] Add more granular CDC data (county-level instead of state-level)
- [ ] Add OPTN waiting list data as a direct source
- [ ] Track historical data to show trends over time
- [ ] Add confidence intervals to scores instead of point estimates

### UI/UX
- [ ] City detail modal with full score breakdown
- [ ] Side-by-side city comparison mode
- [ ] Print-friendly results view for sharing with care team
- [ ] Dark mode
- [ ] Save/share results via URL parameters
- [ ] Form validation with inline error messages
- [ ] Loading spinner during data fetch + calculation

### Algorithm
- [ ] Add travel distance scoring (user provides their location)
- [ ] Insurance-specific scoring (which centers accept which plans)
- [ ] Add pediatric-specific scoring adjustments
- [ ] Multi-organ transplant support
- [ ] Time-series wait time predictions

### Infrastructure
- [ ] Add Playwright or Cypress browser tests
- [ ] Add unit tests for algorithm.js (Jest or Vitest)
- [ ] Lighthouse CI for performance monitoring
- [ ] Dependabot for CDN dependency updates
- [ ] Data diff notifications (show what changed in each fetch)
