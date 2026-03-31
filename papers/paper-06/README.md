# Paper 06: Modeling Dependent Competing Risks in Transplant Waiting Lists — A Clayton Copula Approach

## Status: Not Started

## Summary

A statistical methods paper developing a Clayton copula model for dependent competing risks (transplant, mortality, delisting) in organ transplant waiting lists. Biological motivation: patients experiencing health decline face both higher mortality AND delisting risk simultaneously, creating positive lower-tail dependence. Implements conditional sampling (Nelsen 2006 §4.2) with organ-specific θ parameters learned from MCMC posterior.

## Paper Type
**Statistical methods paper** — focused contribution on copula methodology for competing risks. Moderate length, strong mathematical content, comparison against independent competing risks baseline.

## Target Venues (ranked)

| Venue | IF | Fit | Page Limit | Acceptance Rate | Notes |
|-------|-----|-----|------------|-----------------|-------|
| **Lifetime Data Analysis** | 1.3 | ⭐⭐⭐ | 20 pages | ~30% | Niche but perfect fit: survival + copulas. |
| **Statistics in Medicine** | 2.5 | ⭐⭐⭐ | 15 pages | ~20% | Broad medical stats audience. |
| **Biometrics** | 1.9 | ⭐⭐ | 12 pages | ~15% | Copulas in biostatistics angle. |
| **Computational Statistics & Data Analysis** | 1.8 | ⭐⭐ | 15 pages | ~25% | Computational methods focus. |
| **SMMR** | 2.3 | ⭐⭐ | 15 pages | ~20% | Medical stats methods. |

**Recommended:** Lifetime Data Analysis (specialist journal, highest acceptance odds) or Statistics in Medicine (broader reach).

## Likelihood of Acceptance
**Moderate (45%)** — Clayton copula for medical competing risks is known conceptually but rarely applied to transplant data. The organ-specific θ parameterization is a genuine contribution. Risk: may need simulation study comparing copula vs independent vs other copula families.

## Effort Required
**Medium** — Core copula code exists. Need formal comparison study (copula vs no-copula), possibly simulation from known DGP, and systematic parameter estimates.

### What exists already
- `backend/services/copula.py` (143 lines): Clayton copula with conditional sampling
- `backend/services/monte_carlo.py`: competing risks engine with `use_copula` flag
- Organ-specific θ parameters (kidney=0.8, liver=1.2, heart=1.8, lung=1.5)
- Built-in A/B comparison: `use_copula=True` vs `use_copula=False`

### What needs to be done
- [ ] Formal comparison: run MC with copula ON vs OFF for all 6 organs, measure ranking differences
- [ ] Simulation study: generate data from known Clayton DGP, verify recovery of θ
- [ ] Compare against other copula families (Gumbel, Frank) — may need new code
- [ ] Estimate θ from SRTR data (currently semi-empirical from MCMC posterior)
- [ ] Write mathematical exposition of Clayton conditional sampling
- [ ] Write manuscript (~5000 words)

## Suggested Structure

1. **Introduction** (500 words)
   - Competing risks in transplant: transplant, mortality, delisting
   - Standard assumption: independence (biologically unrealistic)
   - Copulas as tool for modeling dependence without specifying marginals
   - Clayton copula: lower-tail dependence (sickest patients face worst on both axes)

2. **Methods** (1500 words)
   - 2.1 Competing risks setup: T_transplant, T_mortality, T_delisting
   - 2.2 Marginal distributions: log-normal (wait), exponential (mortality/delisting)
   - 2.3 Clayton copula: C(u,v) = (u^{-θ} + v^{-θ} - 1)^{-1/θ}
   - 2.4 Conditional sampling algorithm (Nelsen 2006)
   - 2.5 Kendall's τ relationship: τ = θ/(θ+2)
   - 2.6 Organ-specific parameterization
   - 2.7 Numerical stability considerations

3. **Simulation Study** (800 words)
   - 3.1 Data generating process with known θ
   - 3.2 Recovery of θ under various sample sizes
   - 3.3 Bias when assuming independence (θ=0) when true θ>0

4. **Application to SRTR Data** (1000 words)
   - 4.1 Data: 248 centers × 6 organs × 14 SRTR releases
   - 4.2 θ estimation results per organ
   - 4.3 Impact on center rankings: copula vs independent
   - 4.4 Impact on transplant probability estimates (p24 shift)
   - 4.5 Impact on confidence interval widths

5. **Discussion** (800 words)
   - Modest dependence (τ < 0.15) but meaningful for ranking
   - Heart/lung show stronger dependence (θ=1.5-1.8) than kidney (θ=0.8)
   - Clinical interpretation: why lung patients face correlated risks
   - Limitations: bivariate (not trivariate) copula, parametric marginals

6. **Conclusion** (300 words)

## Key Figures
1. Clayton copula density plot at θ=0.8, 1.2, 1.8 (showing lower-tail concentration)
2. Simulation study: θ recovery across sample sizes
3. Ranking comparison: copula ON vs OFF (Spearman ρ per organ)
4. p24 shift distribution: how much do probabilities change with copula?
5. Kendall's τ by organ (bar chart)

## Key Tables
1. Organ-specific θ estimates with 95% CIs
2. Kendall's τ by organ (from θ)
3. Ranking changes: number of centers moving ≥5 ranks with copula
4. Simulation study: bias and coverage at n=100, 500, 1000, 5000
