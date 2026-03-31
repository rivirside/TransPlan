# Paper 05: Bayesian Hierarchical Survival Models with Shared Frailty for Multi-Center Transplant Waiting Times

## Status: Not Started

## Summary

A statistical methods paper presenting a three-level Bayesian hierarchical model for transplant waiting times. Level 1: national hyperpriors for median wait and dispersion. Level 2: city-level random effects via bivariate MVNormal with LKJ-Cholesky correlated mortality/delisting offsets. Level 3: covariate adjustments (blood type, urgency, clinical scores). Posterior inference via PyMC NUTS sampler with strict convergence gating (R-hat < 1.01, ESS > 400).

## Paper Type
**Statistical methods paper** — the contribution is the hierarchical model structure itself, particularly the LKJ-Cholesky shared frailty for correlated competing risks. Heavy methods, substantial mathematical notation, posterior diagnostics. This is the most technically demanding paper in the portfolio.

## Target Venues (ranked)

| Venue | IF | Fit | Page Limit | Acceptance Rate | Notes |
|-------|-----|-----|------------|-----------------|-------|
| **Biostatistics** | 2.7 | ⭐⭐⭐ | 25 pages | ~15% | Top methods journal. Novel hierarchy + frailty. |
| **Statistics in Medicine** | 2.5 | ⭐⭐⭐ | 15 pages | ~20% | Medical stats staple. Applied Bayesian work welcome. |
| **SMMR** (Stat Methods Med Res) | 2.3 | ⭐⭐⭐ | 15 pages | ~20% | Focused on medical statistics methods. |
| **Bayesian Analysis** | 4.4 | ⭐⭐ | 30 pages | ~25% | Pure Bayesian venue. Methodological novelty required. |
| **Biometrics** | 1.9 | ⭐⭐ | 12 pages | ~15% | Broader biostats. Competitive. |

**Recommended:** Statistics in Medicine (broadest readership in medical stats, accepts applied Bayesian work).

## Likelihood of Acceptance
**Moderate (45%)** — The three-level hierarchy with LKJ frailty is a genuine contribution. Risk: reviewers may want comparison to standard frailty models (gamma, log-normal). Need strong posterior check results.

## Effort Required
**Medium** — Model is built but may need MCMC traces fitted for all 6 organs (currently may only have kidney/liver). Posterior checks exist but need systematic runs.

### What exists already
- `backend/services/mcmc_inference.py` (576 lines): full hierarchical model specification
- `backend/services/mcmc_survival.py` (491 lines): survival model with log-normal + competing risks
- `backend/services/posterior_checks.py` (289 lines): 6 systematic calibration checks
- `backend/services/convergence.py`: R-hat, ESS diagnostics
- `scripts/fit-mcmc-model.py`: offline MCMC fitting script
- ArviZ trace storage in data/mcmc_traces/

### What needs to be done
- [ ] Fit MCMC traces for all 6 organs (if not already done)
- [ ] Run full posterior check suite for each organ
- [ ] Generate trace plots, pair plots, posterior predictive checks
- [ ] Compare against simpler models (no frailty, independent frailty, gamma frailty)
- [ ] Write mathematical exposition of the three-level hierarchy
- [ ] Write manuscript (~6000 words, heavy on equations)

## Suggested Structure

1. **Introduction** (600 words)
   - Multi-center survival data with heterogeneity → frailty models
   - Standard approaches: gamma/log-normal shared frailty
   - Gap: correlated competing risks (mortality ↔ delisting) in transplant setting
   - Contribution: LKJ-Cholesky correlated frailty in Bayesian hierarchy

2. **Model** (2000 words)
   - 2.1 Data structure: organ × blood type × center × patient
   - 2.2 Level 1: National hyperpriors (μ_wait, σ_wait, λ_mort, λ_delist)
   - 2.3 Level 2: City random effects — bivariate MVNormal with LKJ(η=2) Cholesky
   - 2.4 Level 3: Covariate effects (blood type multipliers, urgency, cPRA/MELD/LAS)
   - 2.5 Competing risks likelihood: min(T_transplant, T_mortality, T_delisting)
   - 2.6 Prior specification and justification
   - 2.7 Computation: PyMC NUTS, 4 chains × 2000 draws, 1000 warmup

3. **Posterior Diagnostics** (800 words)
   - 3.1 Convergence: R-hat, ESS, trace plots
   - 3.2 Posterior predictive checks (6 calibration metrics)
   - 3.3 Sensitivity to prior choices

4. **Results** (1000 words)
   - 4.1 Posterior parameter estimates (national + city-level)
   - 4.2 Learned mortality-delisting correlation (LKJ posterior)
   - 4.3 Blood type and urgency effects
   - 4.4 Center ranking with credible intervals
   - 4.5 Comparison to independent-frailty and no-frailty models (DIC/WAIC)

5. **Discussion** (800 words)
   - Learned correlations are modest (|ρ| < 0.15) but improve calibration
   - Computational cost: offline fitting justified by query-time performance
   - Generalizability to other multi-center survival settings
   - Limitations: city-level (not patient-level) frailty, parametric assumptions

6. **Conclusion** (300 words)

## Key Figures
1. DAG (directed acyclic graph) of the three-level hierarchy
2. Trace plots for key parameters (national median, log-sigma, correlation)
3. Posterior predictive check: observed vs posterior 90% CI for city wait factors
4. Forest plot: city-level random effects with 95% CIs
5. LKJ posterior for mortality-delisting correlation

## Key Tables
1. Prior specifications with justification
2. Posterior summaries (mean, sd, 95% CI, R-hat, ESS) for all parameters
3. Model comparison (WAIC/LOO): hierarchical vs flat vs independent frailty
4. Posterior check results: 6 metrics × 6 organs
