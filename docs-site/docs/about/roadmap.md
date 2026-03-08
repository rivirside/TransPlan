---
sidebar_position: 3
---

# Roadmap

TransPlan's development plan covers 5 phases from open-source educational tool to FDA-cleared Software as a Medical Device (SaMD).

## Phase 1: MVP (Complete)

Static site scoring 22 cities across 8 weighted categories using 40+ data points. The core scoring algorithm covers all 8 categories and all 6 organs, with organ-specific inputs (cPRA, MELD, LAS). Visualizations use Chart.js (stacked bar, radar, donut) and a Leaflet interactive map. The data pipeline runs on GitHub Actions with 5 API sources. 91 Jest unit tests provide coverage. Accessibility (ARIA, keyboard navigation) and CDN fallback guards are in place, and a professional UI/UX redesign introduced the Inter font and design token system.

## Phase 2: Probabilistic Engine (Mostly Complete)

Monte Carlo simulation + competing risks modeling.

| Milestone | Status |
|-----------|--------|
| M1: FastAPI backend scaffold | ✅ Complete |
| M2: Log-normal wait time distributions | ✅ Complete |
| M3: Monte Carlo simulation engine | ✅ Complete |
| M4: Competing risks model | ✅ Complete |
| M5: SRTR data pipeline (Excel PSR) | ✅ Complete |
| M6: Frontend integration | ✅ Complete |
| **M7: Validation & docs** | In Progress |

**M7 remaining work:**
1. Brier score retrospective validation against SRTR outcomes
2. Sensitivity analysis (tornado charts showing which inputs most affect output)
3. This documentation site

## Phase 3: Advanced Analytics

Phase 3 will introduce a multi-listing optimizer to model probability improvement from listing at N cities simultaneously, clinical trajectory modeling with MELD progression curves and cPRA changes post-desensitization, a policy impact simulator to toggle allocation policy changes and see projected effects, center-level drill-down to compare specific transplant programs within a city, PDF report export for clinical discussions, and Jupyter notebooks for open reproducible research.

## Phase 4: Data Quality and Validation

Phase 4 will add Brier score validation of Monte Carlo estimates against SRTR historical outcomes, an equity analysis to identify and surface disparities by race, insurance status, and geography, real-time SRTR integration via direct API access when SRTR makes data available programmatically, and an IRB study in partnership with transplant centers for prospective validation.

## Phase 5: FDA Clearance Path

TransPlan targets FDA clearance as Class II Software as a Medical Device (SaMD) via 510(k) pathway. The predicate device is the SRTR Kidney Waiting Times Calculator, a similar patient-facing probability tool. Required studies include algorithm validation (Brier score), a usability study, and a clinical decision quality study. The regulatory pathway follows FDA CDSS Guidance (2022 updated); if intended for clinician use, it may qualify as a non-device CDSS. No PHI is stored currently, and EHR integration (post-clearance) would require a BAA.

---

## Contributing to the Roadmap

This is an open-source project. Contributions are welcome:

1. [Development Guide](/contributing/development-guide): setup and conventions
2. [Data Curation](/contributing/data-curation): improving data quality
3. [GitHub Issues](https://github.com/your-github-user/TransPlan/issues): bug reports and feature requests

The full roadmap with ADR context is in `docs/roadmap.md` in the repository.
