---
sidebar_position: 3
---

# Roadmap

TransPlan's development plan covers 5 phases from open-source educational tool to FDA-cleared Software as a Medical Device (SaMD).

## Phase 1: MVP (Complete)

Phase 1 delivered a static site scoring 22 cities across 8 weighted categories using 40+ data points. The core scoring algorithm covers all 8 categories and all 6 organs, with organ-specific inputs for cPRA, MELD, and LAS. Visualizations use Chart.js (stacked bar, radar, donut) and a Leaflet interactive map. The data pipeline runs on GitHub Actions with 5 API sources. 98 Jest unit tests provide coverage. Accessibility features (ARIA, keyboard navigation) and CDN fallback guards are in place. The UI received a professional redesign introducing the Inter font and a design token system. The architecture is multi-page with a landing page and simulator, and a 4-theme system (Default, Clinical, Research, Government) provides distinct visual identities.

## Phase 2: Probabilistic Engine (Complete)

Phase 2 introduced Monte Carlo simulation and competing risks modeling. All 7 milestones are complete with 193 pytest tests providing coverage. The milestones progressed from the FastAPI backend scaffold (M1) through log-normal wait time distributions (M2), the Monte Carlo simulation engine (M3), the competing risks model (M4), the SRTR data pipeline for Excel PSR parsing (M5), frontend integration (M6), and validation and documentation (M7). M7 deliverables included Brier score retrospective validation (BS < 0.001 for all organs), sensitivity analysis with tornado charts, and this documentation site.

## Phase 3: Vercel Backend Deployment (Complete)

The Python backend (FastAPI) is now deployed as a Vercel serverless function, making probabilistic simulation available to all visitors at transplant.today without running a local server. The deployment uses Vercel rewrites to route API paths to the Python function while serving static files via CDN. MCMC mode is gracefully disabled on Vercel (missing pymc dependency); Monte Carlo and Bayesian inference are fully available.

## Phase 4: All-Program Expansion (Complete)

The simulation engine now covers all 248 SRTR transplant centers (previously limited to 22 cities). Center-level data for wait-time factors, competing risks, and post-transplant outcomes was already available; Phase 4 rewired the services to use center codes instead of city names. All simulation parameters (iterations, copula theta, supply-wait elasticity) are now adjustable via API query params. The BBN and MCMC engines map 248 centers to 22 regions as an interim measure; full center-level BBN (#206) and MCMC (#207) are planned.

## Phase 5: Advanced Modeling

Phase 5 will add real-time SRTR integration, IRB study partnerships, rebuild BBN with 248-center Region node (#206), refit MCMC with 248-center hierarchy (#207), and pursue prospective validation with transplant centers.

## Phase 5: FDA Clearance Path

TransPlan targets FDA clearance as Class II Software as a Medical Device (SaMD) via the 510(k) pathway. The predicate device is the SRTR Kidney Waiting Times Calculator, a similar patient-facing probability tool. Required studies include algorithm validation (Brier score), a usability study, and a clinical decision quality study. The regulatory pathway follows FDA CDSS Guidance (2022 updated); if intended for clinician use, it may qualify as a non-device CDSS. No PHI is stored currently, and EHR integration (post-clearance) would require a BAA.

---

## Contributing to the Roadmap

:::info Pre-Release
TransPlan is being developed in the open but the repository is currently private. The project will be open-sourced at a future stable release milestone. Until then, contributions are coordinated through the development team.
:::

Once open-sourced, contributions will be welcome through the [Development Guide](/contributing/development-guide) for setup and conventions, the [Data Curation](/contributing/data-curation) guide for improving data quality, and [GitHub Issues](https://github.com/rivirside/TransPlan/issues) for bug reports and feature requests. The full roadmap with ADR context is in `docs/roadmap.md` in the repository.
