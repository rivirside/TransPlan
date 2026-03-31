# Paper 07: Temporal Stability of Transplant Center Ranking Models — A Six-Year Walk-Forward Validation

## Status: 📝 Not Started

## Summary

A validation study examining how stable transplant center rankings are over time. Uses walk-forward validation (train on years 1..Y, test on year Y+1) across 14 biannual SRTR releases (2019-2025) to measure Spearman rank correlation and top-5 Jaccard overlap year-over-year. Identifies centers whose rankings are volatile vs stable, and evaluates whether model predictions from one year generalize to the next.

## Paper Type
**Validation/evaluation study** — the contribution is empirical evidence about ranking stability over time. Moderate methods, heavy results and interpretation. Clinically relevant: if rankings are unstable, the tool is less useful for long-term decisions.

## Target Venues (ranked)

| Venue | IF | Fit | Page Limit | Acceptance Rate | Notes |
|-------|-----|-----|------------|-----------------|-------|
| **Medical Care** | 4.0 | ⭐⭐⭐ | 4000 words | ~20% | Health services quality measurement. |
| **Health Services Research** | 3.4 | ⭐⭐⭐ | 5000 words | ~15% | Quality/ranking studies fit well. |
| **Medical Decision Making** | 3.8 | ⭐⭐ | 12 pages | ~25% | Decision model validation. |
| **AJT** | 8.9 | ⭐⭐ | 5000 words | ~20% | If framed as transplant center quality measurement. |
| **BMC Health Services Research** | 2.4 | ⭐⭐ | No limit | ~40% | Fast review, open access. Good fallback. |

**Recommended:** Medical Care (quality measurement angle) or Health Services Research.

## Likelihood of Acceptance
**Moderate (50%)** — Temporal validation of hospital/center rankings is a recognized need. Six years of SRTR data is substantial. The walk-forward design is methodologically sound.

## Effort Required
🟡 **Medium** — The temporal validation endpoint exists but may need more systematic runs across organs and patient profiles. Need to extract and format SRTR temporal data.

### What exists already
- `/validation/temporal` POST endpoint: walk-forward validation
- `backend/services/temporal_validation.py`: walk-forward engine with trend perturbation
- `data/srtr-historical.json`: 14 biannual SRTR releases with trend data
- Year-over-year trend slopes per city

### What needs to be done
- [ ] Run temporal validation for all 6 organs × 3 patient profiles = 18 runs
- [ ] Extract per-center ranking trajectories over 6 years
- [ ] Identify most volatile and most stable centers
- [ ] Correlation analysis: what predicts ranking volatility (volume, region, organ)?
- [ ] Generate temporal stability figures
- [ ] Write manuscript (~4000 words)

## Suggested Structure

1. **Introduction** (500 words)
   - Hospital rankings are widely used but rarely validated temporally
   - Transplant center rankings: CMS star ratings, SRTR reports, TransPlan
   - Question: do rankings persist year-over-year, or are they noise?

2. **Methods** (800 words)
   - 2.1 Data: 248 SRTR centers, 14 biannual releases (2019-2025)
   - 2.2 Walk-forward design: train(2019-Y) → predict(Y+1) → compare
   - 2.3 Metrics: Spearman ρ, top-5 Jaccard, rank displacement
   - 2.4 Center-level volatility score (SD of rank over time)
   - 2.5 Predictors of volatility: volume, organ, region

3. **Results** (1200 words)
   - 3.1 Overall temporal stability (mean Spearman ρ per fold)
   - 3.2 Organ-specific stability (kidney most stable, intestine most volatile?)
   - 3.3 Top-5 persistence (how often do top-5 centers remain in top-5?)
   - 3.4 Most volatile centers: characteristics
   - 3.5 Volume as predictor of stability (larger centers = more stable?)

4. **Discussion** (1000 words)
   - Implications for patient decision-making (rankings are guide, not gospel)
   - Which organs can patients trust rankings for?
   - Low-volume centers: should rankings come with volatility warnings?
   - Comparison to CMS star rating stability studies
   - Limitations: model-based, not outcome-based temporal validation

5. **Conclusion** (300 words)

## Key Figures
1. Temporal stability heatmap: Spearman ρ by fold × organ
2. Top-5 persistence: Sankey diagram showing center movement in/out of top-5
3. Center volatility distribution (histogram per organ)
4. Volume vs stability scatter plot
5. Example center trajectories: stable vs volatile (line charts over 6 years)

## Key Tables
1. Walk-forward results: Spearman ρ, top-5 Jaccard per fold per organ
2. Most stable centers (top 10, by low rank-SD)
3. Most volatile centers (top 10, by high rank-SD)
4. Volume-stability regression results
