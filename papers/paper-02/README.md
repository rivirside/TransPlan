# Paper 02: Comparative Validation of Three Probabilistic Inference Engines for Transplant Outcome Prediction

## Status: 📝 Not Started

## Summary

A methods comparison paper evaluating Monte Carlo simulation, Bayesian Belief Networks, and MCMC posterior inference for ranking transplant centers. Uses Spearman rank correlation, top-5 Jaccard overlap, Brier score calibration, and temporal stability as validation metrics. All three engines operate on the same data and patient profiles, enabling direct comparison.

## Paper Type
**Methods comparison** — the contribution is the systematic comparison framework itself, plus empirical results across 6 organs and multiple patient profiles. Moderate methods section, heavy results/tables.

## Target Venues (ranked)

| Venue | IF | Fit | Page Limit | Acceptance Rate | Notes |
|-------|-----|-----|------------|-----------------|-------|
| **Medical Decision Making** | 3.8 | ⭐⭐⭐ | 12 pages | ~25% | Perfect fit: decision models, validation. |
| **Statistics in Medicine** | 2.5 | ⭐⭐⭐ | 15 pages | ~20% | Methods-heavy, allows detailed comparison. |
| **JAMA Network Open** | 13.4 | ⭐⭐ | 4500 words | ~12% | High impact but competitive. Needs clinical framing. |
| **BMC Medical Research Methodology** | 4.0 | ⭐⭐ | No limit | ~40% | Open access. Methods-focused. Fast review. |
| **Artificial Intelligence in Medicine** | 7.0 | ⭐⭐ | 12 pages | ~22% | AI/ML in healthcare angle. |

**Recommended:** Medical Decision Making first. If rejected, Statistics in Medicine.

## Likelihood of Acceptance
**Moderate-High (60%)** — Multi-engine comparison on real clinical data is novel. Transplant center ranking is a well-understood problem domain. The validation framework itself is a contribution.

## Effort Required
🟢 **Low** — The validation tool (Phase 4) already implements all comparisons. Need to run systematically across organs/profiles and write up results.

### What exists already
- `/validation/cross-engine` endpoint: runs MC + BBN + MCMC, computes Spearman ρ, top-5 Jaccard
- `/validation/calibration` endpoint: Brier scores at 6/12/24 months
- `/validation/temporal` endpoint: walk-forward validation
- `/validation/reference-run/{organ}` endpoint: deterministic seed=12345 runs
- Backend tests validating cross-engine consistency (test_bbn_cross_validation.py)

### What needs to be done
- [ ] Run cross-engine comparison for all 6 organs × 4 patient profiles = 24 runs
- [ ] Run calibration for all 6 organs
- [ ] Run temporal validation for kidney, liver, heart (most data)
- [ ] Generate comparison tables and figures
- [ ] Write manuscript (~5000 words)

## Suggested Structure

1. **Introduction** (600 words)
   - Problem: multiple inference approaches exist but rarely compared on same clinical data
   - Context: transplant center ranking as case study
   - Contribution: systematic three-engine comparison framework

2. **Methods** (1200 words)
   - 2.1 Monte Carlo with competing risks (brief — detailed in paper 06)
   - 2.2 Bayesian Belief Network with exact inference (brief — detailed in paper 05)
   - 2.3 MCMC hierarchical model (brief)
   - 2.4 Validation metrics: Spearman ρ, Jaccard overlap, Brier score, temporal stability
   - 2.5 Patient profiles and experimental design

3. **Results** (1500 words)
   - 3.1 Ranking agreement (Spearman ρ tables per organ)
   - 3.2 Top-5 center overlap (Jaccard per organ)
   - 3.3 Calibration (Brier scores per horizon per organ)
   - 3.4 Temporal stability (year-over-year ranking persistence)
   - 3.5 Computational performance (speed vs accuracy trade-off)

4. **Discussion** (1000 words)
   - When to use which engine (BBN for speed, MC for flexibility, MCMC for uncertainty)
   - Implications for clinical decision support design
   - Limitations: shared data biases, no external validation

5. **Conclusion** (200 words)

## Key Figures
1. Heatmap: Spearman ρ between engine pairs across 6 organs
2. Bar chart: Brier scores by horizon (6/12/24mo) per engine
3. Scatter plot: MC p24 vs BBN p24 per center (kidney example)
4. Speed vs accuracy trade-off plot (ms vs ρ)

## Key Tables
1. Engine characteristics (type, speed, determinism, uncertainty quantification)
2. Cross-engine Spearman ρ for all organ × profile combinations
3. Top-5 center agreement (Jaccard) by organ
4. Brier score calibration by organ and time horizon
