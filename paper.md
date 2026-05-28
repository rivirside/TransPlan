---
title: 'TransPlan: An Open-Source Decision Support Platform for Transplant Center Evaluation'
tags:
  - Python
  - transplantation
  - clinical decision support
  - Monte Carlo simulation
  - Bayesian inference
  - competing risks
  - health equity
authors:
  - name: Tomer Rivir Yonatan Zilbershtein
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
  - name: University of Arizona College of Medicine – Phoenix, Phoenix, AZ, USA
    index: 1
date: 11 April 2026
bibliography: paper.bib
---

# Summary

TransPlan is an open-source clinical decision support platform that helps transplant candidates evaluate all 248 US transplant centers registered with the Scientific Registry of Transplant Recipients (SRTR). The system integrates three probabilistic inference engines --- Monte Carlo simulation with competing risks, a Bayesian Belief Network with exact variable elimination, and a Markov chain Monte Carlo hierarchical survival model --- with an eight-category weighted scoring algorithm, 24 spatially interpolated geographic data layers, five literature-backed policy simulations, and a 48-profile demographic equity audit. TransPlan is deployed as a web application with a Python/FastAPI backend and vanilla JavaScript frontend, freely accessible at [transplant.today](https://transplant.today) and available as an open-source repository at [github.com/rivirside/TransPlan](https://github.com/rivirside/TransPlan).

# Statement of Need

Transplant candidates in the United States face a consequential decision when choosing where to list for transplantation. Median wait times vary by more than threefold across centers for a given organ, and post-transplant outcomes differ significantly based on center volume, geographic donor availability, and regional allocation policy [@axelrod2010; @king2023]. Several tools address individual aspects of this problem: SRTR Program-Specific Reports provide population-level center outcome statistics [@srtr2023]; KPSAM, LSAM, and TSAM are organ-specific discrete-event simulations used by OPTN committees for policy evaluation [@taranto2015]; COMET provides agent-based lung allocation simulation [@egan2024]; and TransplantCenterSearch.org offers a descriptive patient decision aid [@israni2017]. However, no existing tool integrates patient-specific competing risks simulation, multi-criteria spatial scoring, demographic equity auditing, and policy scenario comparison within an accessible interface spanning all six solid organ types (kidney, liver, heart, lung, pancreas, and intestine).

TransPlan addresses this gap by providing a unified platform where patients, clinicians, and researchers can explore how individual clinical factors --- blood type, organ-specific acuity scores (cPRA, MELD, LAS), urgency, age, and sex --- interact with center-level data to produce personalized transplant probability estimates with uncertainty quantification.

# Functionality

TransPlan provides seven interactive tools accessible through a web interface:

- **Simulator**: Scores all 248 centers using the eight-category algorithm and runs Monte Carlo simulation to produce transplant probabilities at 6, 12, 24, and 36-month horizons with 95% confidence intervals and competing risks decomposition (transplant, mortality, delisting, still waiting).
- **Equity Audit**: Evaluates demographic fairness by simulating outcomes across a 48-profile matrix (8 blood types, 3 age brackets, 2 sexes) and computing Gini coefficients per center.
- **Sensitivity Analysis**: Produces tornado charts showing which input parameters most affect outcomes for a given patient profile.
- **Scenario Lab**: Compares five literature-backed UNOS policy simulations including the 2021 kidney 250nm circle allocation reform [@king2023] and expanded DCD utilization [@croome2020].
- **Explorer**: Visualizes 24 spatial data layers via choropleth and heatmap overlays with RBF/IDW interpolation from EPA, CDC, BLS, and SRTR sources.
- **Model Validation**: Cross-engine comparison (Spearman rank correlation, top-5 overlap), Brier score calibration, and temporal stability analysis.
- **Centers**: Browse, search, and filter all 248 SRTR centers with per-center detail pages.

The three inference engines offer complementary trade-offs: Monte Carlo simulation (~80ms, 1000 iterations) provides the most detailed competing risks modeling with optional Clayton copula dependence [@nelsen2006]; the Bayesian Belief Network (~30ms) uses exact inference via pgmpy [@ankan2015] for deterministic real-time results; and the MCMC hierarchical survival model (~500ms) provides honest posterior uncertainty via PyMC [@salvatier2016] with LKJ-Cholesky correlated random effects [@lewandowski2009].

Data is sourced from six federal agencies (SRTR, CDC PLACES, EPA AQS, BLS, CMS, CDC WONDER) and refreshed weekly via automated GitHub Actions pipelines. All stochastic endpoints accept a seed parameter for computational reproducibility. The system includes 805 backend (pytest) and 123 frontend (Jest) automated tests, and a CI pipeline validates code and data integrity on every commit.

TransPlan is not clinically validated and is intended as a research and educational tool. Prospective validation with transplant faculty is planned.

# Acknowledgements

The author acknowledges the Scientific Registry of Transplant Recipients (SRTR) for providing the center-level data that underlies this system, and the open-source communities behind FastAPI [@fastapi], pgmpy [@ankan2015], PyMC [@salvatier2016], and SciPy [@scipy2020] for the computational infrastructure on which TransPlan is built.

# References
