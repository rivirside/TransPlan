# Transplant Modeling & Decision Support Landscape

A systematic mapping of existing tools, platforms, and software for transplant allocation modeling, waitlist outcome prediction, and center selection decision support. Maintained as a living document to inform TransPlan's positioning and identify benchmarking opportunities.

## Comparison Matrix

| Tool | Type | Organs | Centers | Competing Risks | Acceptance Model | Score Progression | Equity Audit | Policy Sim | Spatial Data | Patient-Facing | Open Source | Active |
|------|------|--------|---------|-----------------|------------------|-------------------|--------------|------------|--------------|----------------|-------------|--------|
| **SRTR PSR** | Registry reports | All 6 | 248 | Yes (Fine-Gray) | No | No | No | No | No | Yes (srtr.org) | No (data available) | Yes |
| **KPSAM** | Discrete-event sim | Kidney, Pancreas | ~248 | Yes (implicit) | No | No | No | Yes (primary purpose) | No | No | No (request access) | Maintained |
| **LSAM** | Discrete-event sim | Liver | ~140 | Yes (implicit) | No | No | No | Yes (primary purpose) | No | No | No (request access) | Maintained |
| **TSAM** | Discrete-event sim | Heart, Lung | ~120 | Yes (implicit) | No | No | No | Yes (primary purpose) | No | No | No (request access) | Maintained |
| **COMET** | Agent-based sim | Lung (extensible) | 70+ | Yes (modular) | Yes (agent-based) | No | No | Yes | No | No | Yes (GitHub) | 2024 |
| **LivSim** | Discrete-event sim | Liver | ~140 | Yes (implicit) | No | Yes (DES) | No | Yes | No | No | Yes (GitHub) | 2018 |
| **TransplantCenterSearch** | Decision aid | Kidney, Liver | ~248 | No | No | No | No | No | No | Yes (web) | No | 2024 |
| **TransPlan** | Multi-engine sim | All 6 | 248 | Yes (parametric + copula) | Yes (parametric) | Yes (piecewise) | Yes (Gini) | Yes (5 scenarios) | Yes (24 layers) | Yes (web) | Yes (GitHub) | 2026 |

## What Each Tool Does Well

### SRTR Program-Specific Reports
The gold standard for transplant center performance data. Uses Cox regression and Fine-Gray competing risks models on actual patient-level OPTN data. Published semiannually. Every transplant researcher cites SRTR.

**TransPlan does not replace SRTR.** SRTR uses real patient outcomes; TransPlan uses model-derived estimates from publicly available aggregate data.

### KPSAM / LSAM / TSAM (SRTR Simulated Allocation Models)
The official UNOS/SRTR tools for evaluating allocation policy changes. Discrete-event simulations that replay historical candidate and donor populations under alternative allocation rules. Used by OPTN committees to evaluate policy proposals before implementation.

**Key advantage over TransPlan:** Trained on patient-level OPTN data (not public). Validated against real policy outcomes (e.g., 2021 kidney 250nm circles).

**Key limitation:** Not publicly accessible (must request access from SRTR), not patient-facing, organ-specific (separate tool per organ), no equity or spatial analysis.

### COMET (Cleveland Clinic, 2024)
The most directly comparable platform to TransPlan. Agent-based, modular, open-source. Currently implemented for lung (COMET-Lung). Uses data-driven probability models for donor/candidate generation. Validated against 2018-2019 lung outcomes and the Composite Allocation Score transition.

**Key advantage over TransPlan:** Agent-based (models individual donor-candidate interactions), validated against real outcomes, modular architecture designed for extension to other organs.

**Key limitation:** Currently lung-only, not patient-facing, no equity audit, no spatial data integration, no interactive web interface.

### LivSim (Kilambi et al. 2018)
Open-source Python discrete-event simulation of liver allocation. Designed as a community alternative to LSAM. Models MELD progression, listing/delisting, organ procurement, and acceptance decisions.

**Key advantage over TransPlan:** Discrete-event simulation with individual candidate tracking, MELD progression modeling, organ acceptance decisions.

**Key limitation:** Liver-only, not updated since 2018, no web interface, no equity analysis, no spatial data.

### TransplantCenterSearch.org (Hennepin/UMN)
AHRQ-funded patient decision aid. Matches patient characteristics (donor type, medical profile) to center-level SRTR outcomes data. Currently supports kidney and liver. Underwent RCT evaluation (McKinney et al. 2024).

**Key advantage over TransPlan:** Clinically validated via RCT, designed with patient input (human-centered design), uses real SRTR outcome data.

**Key limitation:** No simulation or modeling (descriptive only), no competing risks, no policy scenarios, limited to kidney/liver.

## TransPlan's Actual Differentiation

TransPlan does NOT claim to replace SRTR, KPSAM/LSAM/TSAM, or COMET. Instead, it occupies a different niche:

1. **Integration breadth:** Only tool combining competing risks simulation, multi-criteria scoring (8 categories), spatial environmental data (24 layers), equity auditing (Gini), and policy scenario comparison in one platform.

2. **Multi-engine validation:** Three independent inference approaches (MC, BBN, MCMC) cross-validated against each other — no other transplant tool does this.

3. **Patient accessibility:** Interactive web interface with both patient-oriented and professional tools. TransplantCenterSearch.org is the only comparable patient-facing tool, but it's descriptive (no modeling).

4. **All-organ coverage:** Covers all 6 solid organs in a single platform with 248 centers. COMET is lung-only; LivSim is liver-only; SAMs are organ-specific.

5. **Equity auditing:** The Gini-based demographic equity audit (48 profiles) is unique — no existing tool systematically quantifies center-level demographic disparities.

**What TransPlan lacks vs. competitors:**
- No patient-level data (uses aggregate SRTR data, not individual records)
- No clinical validation (no RCT, no prospective outcome comparison)
- No discrete-event or agent-based simulation (uses parametric Monte Carlo)
- Organ acceptance modeling is parametric (thinned Poisson with volume-derived factors), not agent-based like COMET
- MELD/LAS progression is piecewise-linear (interval-specific clinical multipliers), not discrete-event like LivSim

## Benchmarking Opportunities

### 1. COMET-Lung Comparison (Highest Priority)
**What:** Run TransPlan for lung transplant with same patient profiles as COMET-Lung validation (2018-2019 cohort). Compare center rankings.
**How:** COMET is open-source on GitHub. Extract their validation patient profiles and predicted outcomes. Run TransPlan on same profiles. Compute Spearman rank correlation.
**Value:** Direct comparison against the most comparable tool. If rankings correlate (rho > 0.7), validates TransPlan's parametric approach against an agent-based model.

### 2. SRTR PSR Calibration (Medium Priority)
**What:** Compare TransPlan predicted p_transplant_24mo against SRTR reported waiting times and transplant rates per center.
**How:** SRTR publishes center-level waiting time medians and 1-year transplant rates in PSRs. Compare TransPlan's predictions for equivalent patient profiles.
**Value:** Validates model calibration against the gold-standard registry.

### 3. TransplantCenterSearch.org Comparison (Lower Priority)
**What:** For kidney and liver, compare TransPlan's center rankings against TransplantCenterSearch.org's recommendations for the same patient characteristics.
**How:** Use TransplantCenterSearch.org interactively for a set of test profiles, record their center rankings. Run TransPlan on same profiles.
**Value:** Tests whether a modeling approach and a data-lookup approach agree on center recommendations.

### 4. LivSim Liver Policy Scenarios (Lower Priority)
**What:** Compare TransPlan's liver policy scenario predictions against LivSim for equivalent policy changes.
**How:** LivSim is on GitHub. Run the same MELD-based allocation changes in both tools.
**Value:** Validates TransPlan's parametric policy engine against a discrete-event simulator.

## Generic Statistical Packages

These are not transplant-specific tools but are widely used in transplant research for survival and competing risks analysis:

| Package | Language | Purpose | Transplant Use |
|---------|----------|---------|----------------|
| **PyMSM** | Python | Multi-state models, competing risks | Waitlist state transitions |
| **PyDTS** | Python | Discrete-time survival with competing risks | Waitlist event analysis |
| **lifelines** | Python | General survival analysis (KM, Cox) | Post-transplant survival |
| **survival** | R | Comprehensive survival analysis | SRTR and registry studies |
| **cmprsk** | R | Fine-Gray competing risks regression | Waitlist outcome modeling |
| **mstate** | R | Multi-state models | Disease progression |

TransPlan does not use these packages directly but implements equivalent parametric models (log-normal + exponential competing risks with Clayton copula).

## References

- SRTR Technical Methods: https://www.srtr.org/about-the-data/technical-methods-for-the-program-specific-reports/
- COMET: Castleberry et al. JHLT 2024. https://github.com/ClevelandClinicQHS/COMET
- LivSim: Kilambi et al. Transplantation 2018. https://github.com/LivSim2017/LivSim-Codes
- TransplantCenterSearch: McKinney et al. Clinical Transplantation 2024. https://transplantcentersearch.org
- KPSAM User Guide: https://www.srtr.org/media/1295/kpsam-2015-user-guide.pdf
- TSAM User Guide: https://www.srtr.org/media/1201/tsam.pdf
- PyMSM: Rossman et al. JOSS 2022. https://github.com/hrossman/pymsm
- Fine-Gray in transplant: Noordzij et al. Nephrol Dial Transplant 2013
