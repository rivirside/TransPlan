---
sidebar_position: 3
---

# Roadmap

TransPlan's development plan covers 5 phases from open-source educational tool to FDA-cleared Software as a Medical Device (SaMD).

## Phase 1: MVP (Complete)

Phase 1 delivered a static site scoring 22 cities across 8 weighted categories using 40+ data points. The core scoring algorithm covers all 8 categories and all 6 organs, with organ-specific inputs for cPRA, MELD, and LAS. Visualizations use Chart.js (stacked bar, radar, donut) and a Leaflet interactive map. The data pipeline runs on GitHub Actions with 5 API sources. 98 Jest unit tests provide coverage. Accessibility features (ARIA, keyboard navigation) and CDN fallback guards are in place. The UI received a professional redesign introducing the Inter font and a design token system. The architecture is multi-page with a landing page and simulator, and a 4-theme system (Default, Clinical, Research, Government) provides distinct visual identities.

## Phase 2: Probabilistic Engine (Complete)

Phase 2 introduced Monte Carlo simulation and competing risks modeling. All 7 milestones are complete with 193 pytest tests providing coverage. The milestones progressed from the FastAPI backend scaffold (M1) through log-normal wait time distributions (M2), the Monte Carlo simulation engine (M3), the competing risks model (M4), the SRTR data pipeline for Excel PSR parsing (M5), frontend integration (M6), and validation and documentation (M7). M7 deliverables included Brier score retrospective validation (BS < 0.001 for all organs), sensitivity analysis with tornado charts, and this documentation site.

## Phase 3: UI Overhaul and Advanced Features (In Progress)

Four of five milestones are complete. M1 added the Home Center dropdown for relocation comparison, with score and probability badges and a green map marker. M2 introduced the organ-specific cause-of-death donor multiplier using PMC10329409 recovery rates and CDC WONDER data. M3 added city detail modals (click any card for an 8-category breakdown) and side-by-side comparison of up to 3 cities with print view. M4 added demographic equity analysis with a 48-profile matrix, Gini coefficient, and 3 charts.

M5 (UX Polish and Export) remains pending. The remaining work includes dark mode, URL sharing, PDF/CSV/JSON export, and sensitivity sliders.

## Phase 4: Advanced Modeling

Phase 4 will add configurable weights (user-adjustable category weights saved in the URL), a causal policy simulator (toggle allocation policy changes and see projected effects), real-time SRTR integration via direct API access when SRTR makes data available programmatically, and an IRB study in partnership with transplant centers for prospective validation. COD model data quality improvements (L-049 through L-056) are tracked under the M2b milestone.

## Phase 5: FDA Clearance Path

TransPlan targets FDA clearance as Class II Software as a Medical Device (SaMD) via the 510(k) pathway. The predicate device is the SRTR Kidney Waiting Times Calculator, a similar patient-facing probability tool. Required studies include algorithm validation (Brier score), a usability study, and a clinical decision quality study. The regulatory pathway follows FDA CDSS Guidance (2022 updated); if intended for clinician use, it may qualify as a non-device CDSS. No PHI is stored currently, and EHR integration (post-clearance) would require a BAA.

---

## Contributing to the Roadmap

:::info Pre-Release
TransPlan is being developed in the open but the repository is currently private. The project will be open-sourced at a future stable release milestone. Until then, contributions are coordinated through the development team.
:::

Once open-sourced, contributions will be welcome through the [Development Guide](/contributing/development-guide) for setup and conventions, the [Data Curation](/contributing/data-curation) guide for improving data quality, and [GitHub Issues](https://github.com/rivirside/TransPlan/issues) for bug reports and feature requests. The full roadmap with ADR context is in `docs/roadmap.md` in the repository.
