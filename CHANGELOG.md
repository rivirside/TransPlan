# Changelog

All notable changes to TransPlan are documented in this file.

## [2.0.0] - 2026-04-11

### Added
- **248-center coverage**: Expanded from 22 cities to all 248 SRTR-registered transplant centers
- **Three inference engines**: Monte Carlo (competing risks), Bayesian Belief Network (exact inference), MCMC (hierarchical survival)
- **Seven interactive tools**: Simulator, Equity Audit, Sensitivity Analysis, Scenario Lab, Explorer, Model Validation, Centers
- **Spatial interpolation**: RBF/IDW across 24 data layers from 2,956 counties and 4,000+ EPA monitors
- **Policy scenario engine**: Five UNOS policy simulations with literature-backed parameters
- **Equity audit**: 48-profile demographic matrix with Gini coefficient decomposition
- **Clayton copula**: Organ-specific correlated competing risks (theta 0.8-1.8)
- **MCMC model**: Three-level Bayesian hierarchy with LKJ-Cholesky correlated random effects
- **Acceptance modeling**: Thinned Poisson process using per-center volume-derived acceptance rates
- **Score drift**: Piecewise MELD/LAS progression during wait
- **Trend projection**: Historical trend slopes projected forward from 14 biannual SRTR releases
- **Seed parametrization**: All stochastic endpoints support reproducible runs
- **Tier system**: Web vs local deployment capability gating
- **Automated data pipeline**: Weekly refresh from 6 federal data sources via GitHub Actions
- **CI pipeline**: pytest, Jest, and data validation on every commit
- **Docker support**: Single-container deployment
- **macOS app**: Double-click launcher (`TransPlan.app`)

### Changed
- Modular frontend architecture (simulator/, shared/, components/, explorer/)
- FastAPI backend replaces standalone scripts
- Vercel serverless deployment replaces static hosting

## [1.0.0] - 2026-03-15

### Added
- Initial release with 22-city scoring algorithm
- 8-category weighted scoring (Medical, Wait Time, Donor, Hospital, Geographic, Health, Policy, Socioeconomic)
- Monte Carlo simulation engine
- Interactive Leaflet map
- Landing page and simulator
