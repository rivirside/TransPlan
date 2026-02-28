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

## Not Yet Done (from v0.2 plan)

### Immediate (before first real commit)
- [ ] Generate `package-lock.json` via `npm install`
- [ ] Browser test: open index.html, submit form, verify charts render
- [ ] Browser test: verify freshness banner appears
- [ ] Browser test: verify radar charts appear in city cards
- [ ] Verify no console errors
- [ ] Initial commit of all v0.2 work

### Short-term
- [ ] Configure GitHub Pages deployment
- [ ] Register for EPA API key and add as GitHub Secret
- [ ] Register for BLS API key and add as GitHub Secret
- [ ] Run fetch scripts locally and verify output
- [ ] Test GitHub Actions workflow with manual trigger
- [ ] Add `.gitignore` for node_modules, .DS_Store

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
