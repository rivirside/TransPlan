# Generic Statistical Packages for Transplant Research

These are not transplant-specific tools but are commonly used in transplant outcomes research for survival analysis and competing risks modeling.

## Python Packages

### PyMSM — Multi-State Models for Survival Data
- **URL:** https://github.com/hrossman/pymsm
- **Published:** Rossman et al. JOSS 2022
- **Purpose:** Competing risks and multi-state models
- **Method:** Semiparametric Cox models for transition-specific hazards
- **Features:** Time-dependent covariates, left truncation, competing events
- **Transplant use:** Waitlist state transitions (listed → transplanted / died / delisted)

### PyDTS — Discrete-Time Survival
- **URL:** https://github.com/tomer1812/pydts
- **Published:** Meir et al. 2022
- **Purpose:** Discrete-time survival with competing risks and penalization
- **Transplant use:** Waitlist event analysis with regularized estimation

### lifelines
- **URL:** https://github.com/CamDavidsonPilon/lifelines
- **Purpose:** General survival analysis (Kaplan-Meier, Cox PH, parametric models)
- **Transplant use:** Post-transplant survival modeling

## R Packages

### survival
- **Purpose:** Comprehensive survival analysis (Cox PH, parametric, frailty)
- **Transplant use:** Foundation for most SRTR and registry-based analyses

### cmprsk
- **Purpose:** Fine-Gray competing risks regression
- **Transplant use:** Waitlist outcome modeling (standard in transplant literature)

### mstate
- **Purpose:** Multi-state models (illness-death, competing risks)
- **Transplant use:** Disease progression and waitlist state transitions

## Relationship to TransPlan
TransPlan does not use these packages directly. Instead, it implements equivalent parametric models:
- **Log-normal distributions** for transplant wait times (vs. semiparametric Cox in PyMSM/survival)
- **Exponential distributions** for mortality and delisting (vs. Fine-Gray in cmprsk)
- **Clayton copula** for dependent competing risks (vs. independence assumption in most tools)
- **Bayesian hierarchy** for center-level random effects (vs. frailty in survival)

The key trade-off: TransPlan's parametric approach enables fast interactive simulation (~80ms per run) but makes stronger distributional assumptions than semiparametric alternatives.
