---
sidebar_position: 3
---

# Roadmap

TransPlan's development plan covers 5 phases from open-source educational tool to FDA-cleared Software as a Medical Device (SaMD).

## Phase 1: MVP (Complete)

Static site scoring 22 cities across 8 weighted categories using 40+ data points. The core scoring algorithm covers all 8 categories and all 6 organs, with organ-specific inputs (cPRA, MELD, LAS). Visualizations use Chart.js (stacked bar, radar, donut) and a Leaflet interactive map. The data pipeline runs on GitHub Actions with 5 API sources. 98 Jest unit tests provide coverage. Accessibility (ARIA, keyboard navigation) and CDN fallback guards are in place, and a professional UI/UX redesign introduced the Inter font and design token system. Multi-page architecture with landing page and simulator. 4-theme system (Default, Clinical, Research, Government).

## Phase 2: Probabilistic Engine (Complete)

Monte Carlo simulation + competing risks modeling. All 7 milestones complete. 193 pytest tests.

| Milestone | Status |
|-----------|--------|
| M1: FastAPI backend scaffold | ✅ Complete |
| M2: Log-normal wait time distributions | ✅ Complete |
| M3: Monte Carlo simulation engine | ✅ Complete |
| M4: Competing risks model | ✅ Complete |
| M5: SRTR data pipeline (Excel PSR) | ✅ Complete |
| M6: Frontend integration | ✅ Complete |
| M7: Validation & docs | ✅ Complete |

M7 deliverables: Brier score retrospective validation (BS < 0.001 all organs), sensitivity analysis (tornado charts), this documentation site.

## Phase 3: UI Overhaul & Advanced Features (In Progress)

| Milestone | Status |
|-----------|--------|
| M1: Home Center Comparison | ✅ Complete |
| M2: Organ-Specific Donor Model (COD multiplier) | ✅ Complete |
| M3: City Detail & Comparison UI | ✅ Complete |
| M4: Equity Analysis | ✅ Complete |
| M5: UX Polish & Export | Pending |

**M1** added Home Center dropdown for relocation comparison, with score/probability badges and green map marker. **M2** introduced the organ-specific cause-of-death donor multiplier using PMC10329409 recovery rates and CDC WONDER data. **M3** added city detail modals (click any card for 8-category breakdown) and side-by-side comparison (up to 3 cities) with print view. **M4** added demographic equity analysis with a 48-profile matrix, Gini coefficient, and 3 charts.

**M5 remaining work:** dark mode, URL sharing, PDF/CSV/JSON export, sensitivity sliders.

## Phase 4: Advanced Modeling

Phase 4 will add configurable weights (user-adjustable category weights saved in URL), a causal policy simulator (toggle allocation policy changes and see projected effects), real-time SRTR integration via direct API access when SRTR makes data available programmatically, and an IRB study in partnership with transplant centers for prospective validation. COD model data quality improvements (L-049 through L-056) are tracked under the M2b milestone.

## Phase 5: FDA Clearance Path

TransPlan targets FDA clearance as Class II Software as a Medical Device (SaMD) via 510(k) pathway. The predicate device is the SRTR Kidney Waiting Times Calculator, a similar patient-facing probability tool. Required studies include algorithm validation (Brier score), a usability study, and a clinical decision quality study. The regulatory pathway follows FDA CDSS Guidance (2022 updated); if intended for clinician use, it may qualify as a non-device CDSS. No PHI is stored currently, and EHR integration (post-clearance) would require a BAA.

---

## Contributing to the Roadmap

:::info Pre-Release
TransPlan is being developed in the open but the repository is currently private. The project will be open-sourced at a future stable release milestone. Until then, contributions are coordinated through the development team.
:::

Once open-sourced, contributions will be welcome through:

1. [Development Guide](/contributing/development-guide): setup and conventions
2. [Data Curation](/contributing/data-curation): improving data quality
3. [GitHub Issues](https://github.com/rivirside/TransPlan/issues): bug reports and feature requests

The full roadmap with ADR context is in `docs/roadmap.md` in the repository.
