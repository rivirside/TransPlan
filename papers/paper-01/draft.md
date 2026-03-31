# TransPlan: An Open-Source Clinical Decision Support System for Multi-Engine Transplant Center Evaluation

**Authors:** [Author List]

**Affiliations:** [Affiliations]

**Corresponding Author:** [Corresponding Author], tomer@arizona.edu

**Keywords:** transplant center selection, clinical decision support, Monte Carlo simulation, Bayesian inference, competing risks, health equity, open-source software

---

## Abstract

Transplant candidates in the United States must choose among 248 transplant centers with widely varying wait times, outcomes, and geographic accessibility, yet existing tools address these factors individually --- through center-level outcome reports, organ-specific allocation simulators, or descriptive decision aids --- without integrating them into a unified, patient-specific assessment spanning all organ types. We present TransPlan, an open-source clinical decision support system that combines three complementary inference engines --- Monte Carlo simulation with competing risks, a Bayesian Belief Network with exact variable elimination, and a Markov chain Monte Carlo hierarchical survival model --- to rank all 248 SRTR-registered US transplant centers across six organ types. The system incorporates an eight-category scoring algorithm, 24 spatially interpolated data layers, five literature-backed UNOS policy simulations, and a 48-profile equity audit with Gini coefficient decomposition. TransPlan is deployed as a web application at transplant.today with a Python/FastAPI backend and vanilla JavaScript frontend. Cross-engine validation yields Spearman rank correlations exceeding 0.5 between the Monte Carlo and Bayesian Belief Network engines, and Brier score self-consistency checks confirm calibration below 0.001 across all six organ types. The system is covered by 594 backend and 123 frontend automated tests, and all stochastic endpoints support seed parametrization for full computational reproducibility. TransPlan is freely available under an open-source license at https://github.com/rivirside/TransPlan.

---

## 1. Introduction

Organ transplantation remains the definitive treatment for end-stage organ failure, yet the decision of *where* to list for transplantation is among the most consequential choices a patient can make. The United States is served by 248 transplant centers registered with the Scientific Registry of Transplant Recipients (SRTR), spanning all 50 states and covering six solid organ types: kidney, liver, heart, lung, pancreas, and intestine [OPTN, 2023]. Median wait times vary by more than threefold across centers for a given organ, and post-transplant graft survival rates differ significantly based on center volume, geographic donor availability, and regional allocation policy [Axelrod et al., 2010; King et al., 2023].

Several tools address aspects of this problem. The SRTR Program-Specific Reports (PSRs) are the gold standard for center-level outcome evaluation, using patient-level data with Fine-Gray competing risks models and published semiannually for all 248+ centers [SRTR, 2023]. However, the PSRs present population-level statistics and do not integrate individual clinical factors (blood type, urgency, organ-specific acuity measures such as cPRA, MELD, or LAS) into personalized wait time forecasts. SRTR also maintains the Kidney-Pancreas Simulated Allocation Model (KPSAM), Liver Simulated Allocation Model (LSAM), and Thoracic Simulated Allocation Model (TSAM), which are discrete-event simulations used by OPTN committees to evaluate allocation policy changes, though these are not publicly accessible and are organ-specific [Taranto et al., 2015]. More recently, COMET (Cleveland Clinic, 2024) introduced an open-source agent-based simulation for organ allocation, currently implemented for lung transplantation, which models individual agent behavior and organ acceptance decisions [Egan et al., 2024]. LivSim provides an open-source liver allocation simulator for policy analysis [Kilambi et al., 2018]. On the patient-facing side, TransplantCenterSearch.org (Hennepin Healthcare/University of Minnesota, AHRQ-funded) is a descriptive patient decision aid for kidney and liver center selection that has been validated through a randomized controlled trial [Israni et al., 2017].

While these tools address important individual aspects of waitlist modeling, center evaluation, policy simulation, or patient decision support, no single platform currently integrates patient-specific competing risks simulation, multi-criteria spatial scoring, demographic equity auditing, and interactive policy scenario comparison within an accessible web interface spanning all six solid organ types.

Several methodological challenges have limited progress in this domain. First, transplant outcomes are inherently multivariate: a patient's probability of receiving a transplant within a given time horizon depends on competing events (death and delisting) that are not independent [Wolfe et al., 2010]. Second, the geographic dimension of organ allocation --- recently reformed through the 250 nautical mile circle policy [King et al., 2023] --- introduces spatial correlation structures that simple center-level comparisons ignore. Third, health equity analysis requires evaluating how the system responds to demographic variation across blood type, age, and sex, demanding a structured simulation framework rather than ad hoc comparison [Wesselman et al., 2021]. Finally, any tool intended for clinical or research use must support computational reproducibility: the ability to regenerate identical results from identical inputs.

We present TransPlan, an open-source clinical decision support system that addresses these gaps. TransPlan integrates three complementary probabilistic inference engines with an eight-category scoring algorithm, 24 spatially interpolated geographic data layers, five literature-backed policy simulations, and a demographic equity audit. The system covers all 248 SRTR-registered centers across six organ types and is deployed as a freely accessible web application. This paper describes the system architecture, inference methodology, implementation, and internal validation. TransPlan is not yet clinically validated and is intended as a research and educational tool; prospective validation with transplant faculty is an active area of development.

---

## 2. System Description

### 2.1 Architecture Overview

TransPlan follows a client-server architecture with a Python/FastAPI backend serving a RESTful API and a vanilla JavaScript frontend [Figure 1]. The backend encapsulates all statistical computation, data loading, and spatial interpolation, while the frontend provides seven interactive tools: Simulator, Equity Audit, Sensitivity Analysis, Scenario Lab, Explorer, Model Validation, and Centers. The system is designed for deployment on serverless infrastructure (Vercel) for the web tier and as a local application for the research tier, with a tiered capability system that gates computationally intensive features (e.g., MCMC inference, copula parametrization) to the local deployment.

All API endpoints accept a structured `PatientProfile` schema specifying organ type, blood type (ABO with Rh factor), age, sex, urgency level (1--4), and organ-specific acuity scores: cPRA for kidney (0--100%), MELD for liver (6--40), and LAS for lung (0--100). Optional parameters include cause-of-death donor adjustment, copula dependence, and custom scoring weights.

### 2.2 Data Sources

TransPlan integrates data from six federal sources, refreshed on a weekly automated schedule via GitHub Actions [Table 1]:

1. **SRTR/OPTN (2023 Annual Data Report):** Center-level wait time distribution parameters, competing risk rates (mortality and delisting), post-transplant graft and patient survival, and transplant volumes for all 248 centers across six organs. Historical data spans 15 biannual SRTR releases from 2019 to 2025. Wait time distributions are modeled as organ- and blood-type-specific log-normal distributions with center-level scale factors and clinical acuity multipliers (cPRA, MELD, LAS).

2. **CDC PLACES (2023):** County-level health indicators --- diabetes prevalence, obesity, chronic kidney disease, hypertension, and smoking rates --- for 2,956 US counties. These serve as inputs to the Health Demographics scoring category and as spatial interpolation layers.

3. **EPA Air Quality System (AQS):** Per-monitor air quality measurements from approximately 4,000 monitoring stations nationwide, used as a dense spatial interpolation layer for the Geographic scoring category.

4. **Bureau of Labor Statistics (BLS):** Consumer Price Index for All Urban Consumers (CPI-U) cost-of-living indices, contributing to the Geographic scoring category.

5. **CDC WONDER:** State-level cause-of-death proportions for five donor-eligible categories (trauma, cardiovascular, drug intoxication, cerebrovascular/stroke, and anoxia), calibrated with organ-specific recovery rates from the Organ Procurement and Transplantation Network.

6. **CMS Provider Data:** Hospital quality metrics including transplant program volumes and performance ratings.

### 2.3 Scoring Algorithm

TransPlan employs an eight-category weighted scoring algorithm that produces a composite suitability score (0--100) for each center relative to a given patient profile [Table 2]. The default weights, informed by transplant medicine literature, are: Medical Compatibility (25%), Wait Time (20%), Donor Availability (18%), Hospital Quality (15%), Geographic Factors (10%), Health Demographics (7%), Policy Environment (3%), and Socioeconomic Support (2%). Users may customize these weights through an interactive slider interface with four presets (Balanced, Clinical Priority, Patient Quality of Life, Research) and automatic renormalization.

For the 248-center deployment, geographic data layers (cost of living, air quality, county health indicators) that are not available at center-level granularity are obtained through spatial interpolation to center coordinates, described in Section 2.6.

### 2.4 Inference Engines

The system provides three complementary inference engines, each offering different trade-offs between computational cost, statistical assumptions, and uncertainty characterization.

**Monte Carlo Simulation with Competing Risks.** The primary engine samples from per-center log-normal wait time distributions with organ- and blood-type-specific parameterization. For each of *N* iterations (default 1,000), three competing event times are drawn: (i) transplant time from the center-specific log-normal distribution; (ii) waitlist mortality time from an exponential distribution with center-specific annual mortality rate; and (iii) delisting time from an exponential distribution with center-specific annual delisting rate. The event with the shortest realization determines the patient's outcome. Optionally, mortality and delisting times are drawn jointly via a Clayton copula with organ-specific dependence parameter (theta ranging from 0.8 for kidney to 1.8 for heart), capturing the clinical reality that declining health simultaneously increases both mortality and delisting risk [Nelsen, 2006]. A sublinear supply-wait elasticity (exponent 0.65) models the relationship between donor supply and wait times. Cause-of-death adjustment applies organ-specific recovery rates to state-level donor cause-of-death proportions, modeled stochastically with Beta-distributed recovery rates (kappa = 50, approximately 3.5% coefficient of variation). The engine produces transplant probabilities at 6, 12, 24, and 36-month horizons with bootstrap 95% confidence intervals, median wait time estimates, and full competing risks breakdowns. Typical execution time is approximately 80 milliseconds for 1,000 iterations across all 248 centers.

**Bayesian Belief Network (BBN).** The BBN engine implements exact inference on a 12-node directed acyclic graph using variable elimination via the pgmpy library [Ankan and Panda, 2015]. The network structure encodes conditional dependencies among organ type, blood type, age group, urgency, region, wait time category, donor supply, mortality risk, delisting risk, competing outcomes, graft survival, and compound success. Seven conditional probability tables (CPTs) are derived programmatically from the same SRTR data used by the Monte Carlo engine, ensuring no data duplication. For each query, evidence is set on the five observable patient nodes and marginal probabilities are computed for all outcome nodes by iterating over the region node. The BBN produces deterministic results (no sampling variance) in approximately 30 milliseconds, making it suitable for real-time interactive exploration. Cross-validation against the Monte Carlo engine confirms Spearman rank correlations exceeding 0.5 for center rankings and directional consistency on blood type, organ, and urgency effects.

**MCMC Hierarchical Survival Model.** The third engine implements a three-level Bayesian hierarchical model fitted with the No-U-Turn Sampler (NUTS) in PyMC [Salvatier et al., 2016]. The hierarchy spans national hyperpriors, city-level random effects (22 regions), and patient-level covariates (blood type and urgency). The model includes 92 free parameters per organ across six independent models. City-level random effects for wait time, mortality, and delisting are drawn from a bivariate multivariate normal distribution with an LKJ-Cholesky prior (eta = 2), which learns the mortality-delisting correlation from data rather than imposing a fixed external copula parameter [Lewandowski et al., 2009]. Offline NUTS fitting takes 2--30 minutes per organ; cached ArviZ NetCDF traces (10--50 MB each) enable query-time inference in 200--500 milliseconds by drawing 50 posterior parameter sets and running forward simulation. Convergence is gated by strict thresholds: R-hat below 1.01 and effective sample size above 400 for all parameters.

### 2.5 Policy Scenario Engine

TransPlan includes five literature-backed UNOS policy simulations that modify the Monte Carlo engine's donor supply and wait time parameters at the center level:

1. **250 Nautical Mile Circles** --- Models the 2021 kidney allocation reform replacing donation service area boundaries with geographic circles, expanding donor pools for small and rural centers [King et al., 2023; OPTN, 2020].

2. **Continuous Distribution** --- Simulates the ongoing OPTN shift to a points-based allocation system that de-emphasizes geographic proximity [OPTN, 2022].

3. **Increased DCD Utilization** --- Models expanded use of donation after circulatory death donors, increasing organ supply by 10--20% [Croome et al., 2020].

4. **Broader HCV+ Donor Acceptance** --- Simulates expanded use of hepatitis C positive donors with direct-acting antiviral treatment, expanding the donor pool by 5--8% for kidney and liver [Reese et al., 2023].

5. **Travel Financial Assistance** --- A demand-side scenario modeling patient travel subsidies at four price points ($5K--$50K) with cost-of-living-proportional adjustments [Axelrod et al., 2010].

Each scenario defines global baseline adjustments and per-center overrides reflecting heterogeneous policy impacts (e.g., small rural centers benefit more from circle-based allocation than large urban centers). Scenarios are organ-specific where applicable.

### 2.6 Spatial Interpolation

Geographic scoring variables that are not available at center-level resolution are interpolated from dense observation networks using Radial Basis Function (RBF) interpolation via SciPy's `RBFInterpolator`, with Inverse Distance Weighting (IDW) as a fallback. The system maintains 24 spatial data layers covering air quality (from approximately 4,000 EPA monitors), county-level health indicators (from 2,956 CDC PLACES counties), organ-specific wait time and competing risk surfaces (from 248 centers), and cost-of-living indices. Interpolation surfaces are computed lazily and cached in memory for the duration of the application lifetime. The UNOS allocation geography module further models 250 and 500 nautical mile allocation circles around each center, computing competition scores based on overlapping donor catchment areas and composite distance scores (proximity 40%, competition 35%, donor pool density 25%).

### 2.7 Equity Audit

The equity audit tool evaluates how the simulation model responds to demographic variation by running Monte Carlo simulations across a 48-profile matrix (8 blood types times 3 age brackets times 2 sexes) while holding clinical parameters fixed. For each center, the tool computes a Gini coefficient measuring inequality in transplant probability across the demographic matrix, enabling identification of centers where model-predicted outcomes are most and least equitable. The tool includes mandatory disclaimers noting that the current model does not stratify competing risks by demographics, does not model race or ethnicity (simulating underlying clinical drivers instead), and does not capture insurance-related disparities. Actual disparities may exceed model predictions due to referral bias, evaluation criteria, and social determinants of health not represented in the model.

---

## 3. Implementation

### 3.1 Technology Stack

The backend is implemented in Python 3.13 using FastAPI with Pydantic schema validation, NumPy and SciPy for numerical computation, pgmpy for Bayesian network inference, PyMC and ArviZ for MCMC fitting and trace management, and SciPy's RBFInterpolator for spatial interpolation. The frontend uses vanilla JavaScript (no build step or framework dependency) with Leaflet for map rendering and Chart.js for visualization. The application is structured as IIFE (Immediately Invoked Function Expression) modules loaded via script tags to minimize deployment complexity.

The system is deployed on Vercel with the FastAPI backend serving as a serverless function and static files served via CDN. Local deployment is supported through Docker (single-container configuration) and a native macOS application bundle. The backend serves both the API and static frontend on a single port (default 8002), eliminating CORS configuration complexity for local deployments.

### 3.2 Tiered Deployment

TransPlan implements a two-tier capability system. The web tier, deployed at transplant.today, caps Monte Carlo iterations at 1,000, equity analysis at 30 centers, and disables MCMC inference (which requires PyMC and cached trace files not available in the serverless environment). The local tier, intended for researchers, removes all caps and enables the full MCMC engine, configurable copula theta, supply-wait elasticity parameters, and uncapped iteration counts. The frontend fetches the current tier configuration from a `GET /tier` endpoint and hides (rather than disabling) features unavailable in the current tier, following a progressive disclosure design pattern.

### 3.3 Reproducibility

All stochastic API endpoints accept an optional integer `seed` parameter (0 to 2,147,483,647). When provided, the seed is threaded through all random number generators (NumPy `default_rng`) to produce deterministic results. The response includes a `seed_used` field reporting the actual seed (either user-provided or auto-generated). A `RunArtifact` export schema captures the full provenance of a simulation run: tool identifier, timestamp, seed, patient profile, parameters, results, and deployment tier. This enables exact reproduction of any published result.

### 3.4 API Design

The backend exposes a RESTful API with endpoints for simulation (`POST /simulate`), scoring (`POST /score`), sensitivity analysis (`POST /sensitivity`), equity analysis (`POST /equity-analysis`), what-if scenarios (`POST /what-if`), policy scenarios (`POST /policy-scenario`), cross-engine validation (`POST /validation/cross-engine`), calibration checks (`POST /validation/calibration`), convergence diagnostics (`GET /validation/convergence/{organ}`), and spatial queries (six endpoints under `/spatial-*`). A public API (v1) under `/api/v1/` provides rate-limited access with optional API key authentication. All endpoints return structured JSON responses with Pydantic-validated schemas. Interactive API documentation is auto-generated at `/docs` (Swagger UI) and `/redoc`.

### 3.5 Data Pipeline

An automated data pipeline refreshes source data on a weekly schedule via GitHub Actions workflows. Six fetch scripts retrieve data from SRTR, CDC PLACES, EPA AQS, BLS, CDC WONDER, and CMS APIs. A bimonthly workflow monitors SRTR for new releases and triggers historical archive downloads. A CI pipeline runs three parallel jobs (594 pytest tests, 123 Jest tests, and data validation) on every push and pull request. SRTR Excel files are parsed into center-level JSON files by a dedicated script (`parse-srtr-reports.py`), producing wait time distributions, competing risk rates, and post-transplant outcomes for all 248 centers.

---

## 4. Evaluation

### 4.1 Cross-Engine Validation

We evaluated inter-engine agreement by running all three inference engines on a standardized set of patient profiles and comparing center rankings [Table 3]. The cross-engine validation service executes Monte Carlo (1,000 iterations), BBN (exact inference), and MCMC (50 posterior draws with forward simulation) on identical patient inputs and computes pairwise Spearman rank correlation coefficients, mean absolute probability differences at the 24-month horizon, and top-5 center overlap.

For the reference profile (kidney, blood type O+, age 45, male, urgency 2), the Monte Carlo and BBN engines produced a Spearman rank correlation rho exceeding 0.5, confirming that the structurally different models yield concordant center rankings from the same underlying data. Mean absolute probability differences at 24 months were within clinically acceptable ranges. Top-5 center overlap between engine pairs was typically 3--4 out of 5 centers. The BBN and MCMC engines showed directional consistency on all tested clinical effects: blood type O patients had longer predicted waits than blood type AB patients; higher urgency scores yielded shorter waits; and organ-specific acuity measures (cPRA, MELD, LAS) modulated predictions in the expected directions [Figure 2].

Where the engines diverge, the disagreements are attributable to structural differences in modeling assumptions rather than data inconsistencies. The Monte Carlo engine treats center-level parameters as fixed point estimates; the BBN discretizes continuous variables into categorical states (e.g., three wait time categories); and the MCMC model applies hierarchical shrinkage that pulls small-volume centers toward the national mean. These structural differences are a feature rather than a limitation: they provide users with a triangulated assessment that is robust to any single model's assumptions.

### 4.2 Calibration Assessment

We assessed the internal calibration of the Monte Carlo engine using a self-consistency Brier score that compares simulation-derived probabilities against analytically computed expectations from the same SRTR-derived distributional parameters. For each center and patient profile, the analytical 12-month transplant probability was computed by numerical integration over the joint competing risks survival function, and the Monte Carlo estimate was obtained from 1,000-iteration simulation. The Brier score (mean squared difference between predicted and analytical probabilities) was computed across all centers.

Across all six organ types, the Brier score was below 0.001 [Table 4], confirming that the Monte Carlo engine accurately recovers the analytical predictions implied by its own distributional assumptions. This self-consistency check verifies the correctness of the simulation implementation but does not constitute external validation against observed patient outcomes. We emphasize that a true external Brier score would require a held-out cohort of transplant candidates with known outcomes, which is planned as a prospective IRB-approved study.

### 4.3 Sensitivity Analysis

Parameter sensitivity was assessed using a one-at-a-time tornado chart methodology. For each organ type, clinical input parameters (urgency for all organs; cPRA for kidney; MELD for liver; LAS for lung) were varied from their most favorable to least favorable values while holding other inputs constant. The change in 24-month transplant probability (delta p24) was measured at a representative center.

Urgency was the dominant parameter across all organ types, consistent with the UNOS allocation system's priority structure. For kidney, cPRA was the second most influential parameter, reflecting the impact of sensitization on donor compatibility. For liver, MELD was the dominant parameter, consistent with the MELD-based allocation system. For lung, LAS had the largest effect, reflecting the LAS-based allocation policy. These findings provide face validity: the model's parameter sensitivities align with known clinical and policy mechanisms [Figure 3].

### 4.4 Model Sensitivity

Model sensitivity analysis assessed the stability of center rankings under perturbation of structural parameters: copula dependence theta (0.5 to 2.0), supply-wait elasticity (0.3 to 1.0), and Monte Carlo iteration count (100 to 10,000). Rankings were highly stable: Spearman rank correlations between perturbed and baseline runs exceeded 0.95 for copula theta and elasticity variations, and exceeded 0.99 for iteration counts above 500. This indicates that the system's center rankings are robust to reasonable uncertainty in structural modeling choices.

### 4.5 MCMC Convergence Diagnostics

Convergence of the MCMC hierarchical model was verified using standard Bayesian diagnostics. For all six organ-specific models, the Gelman-Rubin statistic (R-hat) was below 1.01 for all parameters, and the effective sample size (ESS) exceeded 400 for all parameters, meeting the strict convergence gates enforced by the fitting script. Posterior predictive checks compared MCMC-derived predictions against observed SRTR statistics, including national median wait times, center-level wait time factors, blood type multipliers, mortality and delisting rates, and urgency monotonicity. All checks passed within acceptable tolerance bounds [Figure 4].

### 4.6 Test Coverage

The system is covered by 594 pytest tests (backend) and 123 Jest tests (frontend), organized into the following categories [Table 5]:

- **Monte Carlo engine:** 25 tests covering simulation correctness, competing risks consistency (outcome probabilities summing to 1.0), confidence interval coverage, and performance benchmarks.
- **Bayesian Belief Network:** 72 tests covering DAG structure, CPT normalization, inference validity, organ-specific behavior, and cross-validation against Monte Carlo.
- **MCMC model:** 53 tests covering data loading, model building, posterior sampling, and clinical sanity checks.
- **Clayton copula:** 26 tests covering marginal uniformity, Kendall's tau recovery, edge cases, and integration with simulation paths.
- **Spatial interpolation:** 32 tests covering RBF/IDW surfaces, layer extraction, allocation circles, and distance scoring.
- **Scoring algorithm:** 89 Jest tests covering all eight categories, organ-specific inputs, configurable weights, and cause-of-death adjustment.
- **Cross-engine validation:** 14 tests covering rank correlation computation, probability difference metrics, and multi-engine execution.
- **Policy scenarios:** 24 tests covering scenario registration, per-center multiplier application, and organ-specific filtering.
- **Equity analysis:** 19 tests covering Gini coefficient computation, demographic matrix enumeration, and disparity metrics.

All tests run in a CI pipeline triggered on every push and pull request. The test suite includes both unit tests (isolated service functions) and integration tests (full API endpoint round-trips).

### 4.7 Performance Benchmarks

Latency was measured on the Vercel serverless deployment (web tier) for representative requests [Table 6]:

| Endpoint | Typical Latency | Notes |
|----------|----------------|-------|
| POST /score (248 centers) | ~200 ms | Eight-category scoring with spatial interpolation |
| POST /simulate (MC, 1000 iter) | ~80 ms | Full competing risks simulation |
| POST /simulate (BBN) | ~30 ms | Deterministic exact inference |
| POST /simulate (MCMC) | ~500 ms | 50 posterior draws, local tier only |
| POST /sensitivity | ~2 s | Parameter sweep across value range |
| POST /equity-analysis | ~10 s | 48-profile matrix, 22 centers |

---

## 5. Discussion

### 5.1 Comparison with Existing Tools

TransPlan operates within an ecosystem of established transplant modeling and decision support tools, and an honest comparison requires acknowledging both their strengths relative to TransPlan and TransPlan's distinctive contributions.

**SRTR Program-Specific Reports.** The SRTR PSRs remain the authoritative source for transplant center evaluation, and TransPlan does not replace them. The PSRs use individual patient-level data with Fine-Gray competing risks regression --- a methodologically superior approach to TransPlan's reliance on aggregate, publicly available center-level statistics [SRTR, 2023]. TransPlan's predictions should be interpreted as model-derived estimates that complement SRTR data, not as substitutes for it. TransPlan differs in offering patient-specific parameterization (integrating blood type, urgency, and acuity scores into personalized predictions), explicit competing risks decomposition (transplant, mortality, and delisting probabilities at multiple time horizons), geographic and environmental data layers absent from the PSRs, and counterfactual policy scenario analysis.

**Simulated Allocation Models (KPSAM/LSAM/TSAM).** SRTR's official discrete-event simulated allocation models are used by OPTN committees to evaluate proposed policy changes [Taranto et al., 2015]. These models simulate individual organ offers and acceptance decisions with high fidelity to the actual allocation algorithm --- a level of mechanistic detail that TransPlan does not attempt. TransPlan's parametric approach trades this fidelity for computational speed (sub-second inference), all-organ coverage in a single framework, and public accessibility without institutional data use agreements.

**COMET.** The Comprehensive Organ Matching and Evaluation Tool (COMET) is the most directly comparable recent work [Egan et al., 2024]. COMET uses agent-based modeling, where individual patients and organs are simulated as autonomous agents with organ acceptance behavior learned from historical data. This approach is more realistic than TransPlan's parametric competing risks framework, particularly for modeling the sequential organ offer process. However, COMET is currently implemented only for lung transplantation, whereas TransPlan covers all six solid organ types. TransPlan's lighter parametric approach enables real-time web-based interaction, whereas agent-based simulation typically requires longer runtimes.

**LivSim.** LivSim is an open-source liver allocation simulator designed for policy analysis [Kilambi et al., 2018]. Like the SAMs, LivSim models the allocation process at the individual organ-offer level, providing higher mechanistic fidelity than TransPlan for liver-specific policy questions. TransPlan complements tools like LivSim by offering cross-organ comparison and integration of geographic, environmental, and equity dimensions not addressed by allocation-focused simulators.

**TransplantCenterSearch.org.** This AHRQ-funded patient decision aid for kidney and liver center selection has been validated through a randomized controlled trial demonstrating improved patient knowledge and engagement [Israni et al., 2017]. TransPlan lacks this clinical validation --- prospective validation with transplant faculty is planned but not yet completed (issue #107). TransplantCenterSearch.org is descriptive (presenting observed statistics) rather than model-based, covering kidney and liver only, while TransPlan provides probabilistic modeling across all six organs.

**TransPlan's distinctive contributions** within this landscape are: (1) integration of three complementary inference engines (Monte Carlo, BBN, MCMC) with cross-engine validation providing triangulated uncertainty quantification; (2) coverage of all six solid organ types within a single platform; (3) a 48-profile demographic equity audit with Gini coefficient decomposition; (4) 24 spatially interpolated geographic and environmental data layers integrated into center scoring; and (5) five counterfactual policy scenario simulations with per-center heterogeneous impact modeling. These features are offered through a freely accessible web interface with full computational reproducibility.

### 5.2 Limitations

Several important limitations should be noted. First, TransPlan has not yet undergone clinical validation with observed patient outcomes. The Brier score calibration reported in this paper is a self-consistency check, not an external validation. A prospective validation study with transplant faculty is in progress (tracked as open issue #107). Second, the equity audit does not model race, ethnicity, insurance type, or social determinants of health, all of which are known drivers of transplant disparities [Wesselman et al., 2021]. The model simulates underlying clinical drivers rather than demographic categories, which may underestimate actual disparities. Third, the BBN and MCMC engines currently map 248 centers to 22 representative regions for inference, with center-level adjustment factors applied post-inference; full 248-center parameterization of these engines is planned (issues #206, #207). Fourth, the model relies on aggregate center-level statistics rather than individual patient-level data, which limits the precision of patient-specific predictions. Fifth, spatial interpolation from sparse observation networks (22 centers for some layers, though up to 4,000 points for air quality) introduces geographic smoothing that may not capture local variation.

### 5.3 Future Work

Planned development includes prospective clinical validation through an IRB-approved study with transplant faculty (issue #107); expansion of the BBN and MCMC engines to full 248-center parameterization; integration of individual-level SRTR outcomes data (contingent on data use agreement); and development of a spatial econometric model incorporating OPO boundary effects and kriging-based uncertainty surfaces. We also plan to develop an API SDK and embeddable widget to facilitate integration with electronic health record systems and third-party clinical tools.

---

## 6. Conclusion

TransPlan demonstrates that a multi-engine probabilistic approach to transplant center evaluation is technically feasible and can be deployed as an accessible, open-source web application. By combining Monte Carlo simulation with competing risks, Bayesian network inference, and MCMC hierarchical modeling, the system provides triangulated center rankings that are robust to individual model assumptions. The eight-category scoring algorithm, 24 spatial data layers, five policy simulations, and 48-profile equity audit integrate dimensions of analysis that are individually addressed by existing tools but have not previously been combined in a single all-organ platform. Internal validation confirms self-consistent calibration and concordant cross-engine rankings, while extensive automated testing (717 tests) provides engineering confidence in implementation correctness.

We emphasize that TransPlan is currently a research and educational tool, not a clinically validated decision aid. The system's predictions are model-derived estimates based on aggregate SRTR data and should not be used as the sole basis for clinical decisions. Clinical validation with observed patient outcomes is the critical next step toward potential clinical adoption. TransPlan is freely available at transplant.today and as open-source software at https://github.com/rivirside/TransPlan.

---

## References

[Ankan and Panda, 2015] Ankan, A. and Panda, A. (2015). pgmpy: Probabilistic graphical models using Python. In *Proceedings of the 14th Python in Science Conference (SciPy 2015)*, pages 6--11.

[Axelrod et al., 2010] Axelrod, D.A., Dzebisashvili, N., Schnitzler, M.A., Salvalaggio, P.R., Segev, D.L., Gentry, S.E., Tuttle-Newhall, J., and Lentine, K.L. (2010). The interplay of socioeconomic status, distance to center, and interdonor service area travel on kidney transplant access and outcomes. *Clinical Journal of the American Society of Nephrology*, 5(12):2276--2288.

[Croome et al., 2020] Croome, K.P., Lee, D.D., and Taner, C.B. (2020). The "true" impact of donation after circulatory death on outcomes following liver transplantation. *Transplantation*, 104(6):1180--1190.

[Egan et al., 2024] Egan, T.M., Bose, S., Engel, M., et al. (2024). COMET: Comprehensive Organ Matching and Evaluation Tool --- an open-source agent-based simulation of lung transplant allocation. *Journal of Heart and Lung Transplantation*, 43(8):1265--1276.

[Israni et al., 2017] Israni, A.K., Halpern, S.D., Garg, N., Caplan, A.L., Pruett, T.L., and Ibrahim, H.N. (2017). Transplant center evaluation decision aid for patients: A randomized controlled trial. *American Journal of Transplantation*, 17(S3):475--476.

[Kilambi et al., 2018] Kilambi, V., Mehrotra, S., and Englesbe, M.J. (2018). LivSim: An open-source simulation model of liver transplant allocation in the United States. *Transplantation*, 102(7):e330--e331.

[King et al., 2023] King, K.L., Husain, S.A., Schold, J.D., Patzer, R.E., Roth, N., Wang, W., Friedewald, J.J., Bae, S., Segev, D.L., and Mohan, S. (2023). Major variation in geographic access to kidney transplant after the 2021 OPTN policy change. *American Journal of Transplantation*, 23(1):116--127.

[Lewandowski et al., 2009] Lewandowski, D., Kurowicka, D., and Joe, H. (2009). Generating random correlation matrices based on vines and extended onion method. *Journal of Multivariate Analysis*, 100(9):1989--2001.

[Nelsen, 2006] Nelsen, R.B. (2006). *An Introduction to Copulas*. 2nd ed. Springer Series in Statistics. Springer, New York.

[OPTN, 2020] Organ Procurement and Transplantation Network (2020). OPTN/UNOS Policy Notice: Removal of DSA and Region from Kidney Allocation Policy. U.S. Department of Health and Human Services.

[OPTN, 2022] Organ Procurement and Transplantation Network (2022). Continuous Distribution of Lungs: Policy Framework. U.S. Department of Health and Human Services.

[OPTN, 2023] Organ Procurement and Transplantation Network (2023). 2023 Annual Data Report. U.S. Department of Health and Human Services.

[Reese et al., 2023] Reese, P.P., Abt, P.L., Blumberg, E.A., Van Deerlin, V.M., Bloom, R.D., Potluri, V.S., Levine, M., Porrett, P.M., Sawinski, D., and Goldberg, D.S. (2023). Twelve-month outcomes after transplant of hepatitis C-infected kidneys into uninfected recipients: A single-group trial (THINKER-2). *The Lancet*, 401(10380):939--948.

[Salvatier et al., 2016] Salvatier, J., Wiecki, T.V., and Fonnesbeck, C. (2016). Probabilistic programming in Python using PyMC3. *PeerJ Computer Science*, 2:e55.

[SRTR, 2023] Scientific Registry of Transplant Recipients (2023). Program-Specific Reports. Minneapolis, MN: Hennepin Healthcare Research Institute. Available at https://www.srtr.org/reports/program-specific-reports/.

[Taranto et al., 2015] Taranto, S.E., Harper, A.M., Ames, E.D., Edwards, E.B., and Livingston, M.L. (2015). KPSAM, LSAM, TSAM: OPTN simulated allocation models. In Karp, S.J., et al. (Eds.), *Organ Transplantation: A Clinical Guide*, pages 125--140. Cambridge University Press.

[Tong et al., 2015] Tong, A., Jan, S., Wong, G., Craig, J.C., Irving, M., Chadban, S., Cass, A., and Howard, K. (2015). Patient preferences for the allocation of deceased donor kidneys for transplantation: A mixed methods study. *BMC Nephrology*, 13(1):18.

[Wesselman et al., 2021] Wesselman, H., Ford, C.G., Leyber, Y., Shimkhada, R., Townsend, I., Jara, F.N., Vangala, S.S., and Lum, E.L. (2021). Social determinants of health and race disparities in kidney transplant. *Clinical Journal of the American Society of Nephrology*, 16(2):262--274.

[Wolfe et al., 2010] Wolfe, R.A., McCullough, K.P., Schaubel, D.E., Kalbfleisch, J.D., Murray, S., Stegall, M.D., and Leichtman, A.B. (2010). Calculating life years from transplant (LYFT): Methods for kidney and kidney-pancreas candidates. *American Journal of Transplantation*, 8(4):997--1011.

---

## Figure and Table Captions

**[Figure 1]** System architecture diagram. The Python/FastAPI backend serves a RESTful API consumed by seven frontend tools. Data flows from six federal sources through automated fetch scripts into JSON data files loaded at application startup. Three inference engines (Monte Carlo, BBN, MCMC) share the same data layer but apply structurally different probabilistic models.

**[Figure 2]** Cross-engine validation scatter plot for a reference kidney patient (O+, age 45, male, urgency 2). Each point represents one center; axes show 24-month transplant probability as estimated by the Monte Carlo engine (x-axis) and BBN engine (y-axis). The diagonal line indicates perfect agreement. Spearman rho and mean absolute difference are annotated.

**[Figure 3]** Sensitivity tornado charts for four organ types. Each bar shows the change in 24-month transplant probability when a single clinical parameter is varied from most favorable to least favorable, holding other parameters constant. Parameters are ordered by magnitude of effect. Urgency is the dominant parameter for all organs; organ-specific acuity scores (cPRA, MELD, LAS) are the second most influential for their respective organs.

**[Figure 4]** MCMC convergence diagnostics for the kidney model. (a) Trace plots for three representative parameters showing good mixing. (b) R-hat distribution across all 92 parameters (all below 1.01). (c) Effective sample size distribution (all above 400).

**[Table 1]** Data sources, spatial resolution, refresh frequency, and number of records. Six federal sources provide center-level, county-level, and monitor-level data refreshed weekly or bimonthly.

**[Table 2]** Eight-category scoring algorithm with default weights, data sources, and key factors per category.

**[Table 3]** Cross-engine validation results: Spearman rank correlation, mean absolute probability difference, and top-5 overlap for each engine pair across six organ types.

**[Table 4]** Brier score self-consistency results across six organ types, showing scores below 0.001 for all organs.

**[Table 5]** Test suite summary: 594 pytest tests and 123 Jest tests organized by subsystem.

**[Table 6]** API endpoint latency benchmarks for representative requests on the Vercel serverless deployment.

---

*Conflict of Interest:* The authors declare no conflicts of interest.

*Data Availability:* All source data is derived from publicly available federal datasets (SRTR, CDC, EPA, BLS, CMS). Processed data files are included in the open-source repository.

*Code Availability:* TransPlan is open-source software available at https://github.com/rivirside/TransPlan. The version described in this paper corresponds to commit [commit hash]. A live deployment is accessible at https://transplant.today.

*Ethics:* TransPlan processes only aggregate, de-identified data from public federal sources. No individual patient data is collected, stored, or processed. The system is intended as a research and educational tool and has not undergone clinical validation or FDA review.
