# Paper 03: Quantifying Demographic Disparities in Transplant Center Selection — A Gini-Based Algorithmic Equity Audit

## Status: 📝 Not Started

## Summary

An applied policy paper using the TransPlan equity audit tool to quantify demographic disparities across transplant centers. Runs a 48-profile demographic matrix (8 blood types × 3 age groups × 2 sexes) through Monte Carlo simulation for all 6 organ types, computing Gini coefficients as inequality metrics. Identifies which demographic dimensions drive the largest disparities and which centers are most/least equitable.

## Paper Type
**Applied/policy paper** — the contribution is the empirical findings about disparities, using the Gini framework as a lens. Heavy on results tables, equity implications, and policy recommendations. Moderate methods section.

## Target Venues (ranked)

| Venue | IF | Fit | Page Limit | Acceptance Rate | Notes |
|-------|-----|-----|------------|-----------------|-------|
| **Health Affairs** | 9.4 | ⭐⭐⭐ | 3500 words | ~8% | Top health policy journal. Competitive but high impact. |
| **AJPH** (Am J Public Health) | 6.5 | ⭐⭐⭐ | 3500 words | ~15% | Strong equity/disparity focus. |
| **AJT** (Am J Transplantation) | 8.9 | ⭐⭐⭐ | 5000 words | ~20% | Transplant-specific. Audience cares about this. |
| **Transplantation** | 5.7 | ⭐⭐ | 4000 words | ~25% | Second-tier transplant journal. |
| **J Health Politics, Policy & Law** | 2.1 | ⭐⭐ | 10000 words | ~15% | Deep policy analysis. Longer format. |
| **Medical Care** | 4.0 | ⭐⭐ | 4000 words | ~20% | Health services research. Equity is core topic. |

**Recommended:** AJT first (transplant-specific audience who acts on this). If rejected, AJPH (broader public health).

## Likelihood of Acceptance
**Moderate-High (55%)** — Algorithmic fairness in healthcare is a hot topic. Using Gini coefficients for transplant equity is novel. The 48-profile matrix is a rigorous approach. Main risk: reviewers may want real OPTN outcome data rather than model-based analysis.

## Effort Required
🟢 **Low** — The equity endpoint already does everything. Run it for 6 organs, make figures.

### What exists already
- `/equity-analysis` endpoint: runs 48-profile matrix, returns Gini coefficients, per-group means
- Dimension-specific disparity decomposition (blood type, age, sex)
- Built-in disclaimers about model limitations (no race/ethnicity, no insurance type)

### What needs to be done
- [ ] Run equity analysis for all 6 organs (API calls)
- [ ] Compare Gini across organs (which organ has most/least equitable access?)
- [ ] Identify top-5 most/least equitable centers per organ
- [ ] Create disparity decomposition figures (which demographic axis drives most inequality?)
- [ ] Literature review: existing transplant equity studies
- [ ] Write manuscript (~4000 words)
- [ ] Frame policy recommendations carefully

## Suggested Structure

1. **Introduction** (500 words)
   - Known disparities in organ allocation (blood type O, older patients, sex differences)
   - Gap: no systematic multi-center, multi-demographic quantification using Gini
   - Algorithmic auditing as complement to observational studies

2. **Methods** (800 words)
   - 2.1 Demographic matrix design (48 profiles: 8 BT × 3 age × 2 sex)
   - 2.2 Simulation: Monte Carlo competing risks per center
   - 2.3 Gini coefficient computation on p_transplant_24mo distribution
   - 2.4 Dimension-specific decomposition (isolate blood type vs age vs sex contribution)
   - 2.5 Sensitivity analysis on iteration count

3. **Results** (1200 words)
   - 3.1 Overall Gini by organ (table: kidney=?, liver=?, etc.)
   - 3.2 Most/least equitable centers per organ
   - 3.3 Disparity decomposition: blood type dominates for kidney, urgency for liver, etc.
   - 3.4 Age-sex interaction effects
   - 3.5 Geographic patterns (do equitable centers cluster regionally?)

4. **Discussion** (1000 words)
   - What the Gini values mean in clinical context
   - Blood type O as the dominant disparity driver (known, but now quantified per center)
   - Policy implications: should UNOS consider center-level equity metrics?
   - Limitations: model-based (not empirical outcomes), no race/ethnicity, no insurance
   - Ethical framing: tool for awareness, not allocation

5. **Conclusion** (300 words)
   - Gini-based auditing as a generalizable framework
   - Call for clinical validation and integration with OPTN monitoring

## Key Figures
1. Gini coefficient by organ (bar chart, 6 organs)
2. Center-level Gini distribution (histogram or violin, per organ)
3. Disparity decomposition (stacked bar: blood type % + age % + sex % contribution)
4. Geographic map: center equity scores across US
5. Blood type O vs AB comparison (p24 scatter per center)

## Key Tables
1. Gini coefficients by organ (overall, and per demographic dimension)
2. Top-5 most and least equitable centers per organ
3. Mean p24 by demographic group (blood type × organ matrix)
4. Comparison with published OPTN disparity data

## Ethical Considerations
- Explicitly state that this is model-based analysis, not real-world outcomes
- No race/ethnicity modeling (deliberate — avoids reinforcing race-based algorithms)
- Disclaimers about model limitations are built into the tool
- Frame as awareness tool, not an allocation recommendation
