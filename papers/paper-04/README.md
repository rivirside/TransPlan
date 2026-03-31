# Paper 04: Modeling UNOS Allocation Policy Changes — A Scenario Planning Tool for Transplant Access Equity

## Status: Not Started

## Summary

An applied policy paper modeling the impact of five real/proposed UNOS policy changes on transplant center rankings and access equity. Uses the TransPlan scenario engine with literature-backed parameters (King et al. AJT 2023, Reese et al. NEJM 2023, Croome et al. OPTN data) to simulate: (1) 250nm kidney circles, (2) continuous distribution, (3) increased DCD utilization, (4) broader HCV+ donor acceptance, and (5) travel financial assistance at four price points.

## Paper Type
**Applied policy/simulation study** — heavy on scenario design, parameter justification from literature, and results interpretation. Moderate methods. Strong policy implications section.

## Target Venues (ranked)

| Venue | IF | Fit | Page Limit | Acceptance Rate | Notes |
|-------|-----|-----|------------|-----------------|-------|
| **AJT** (Am J Transplantation) | 8.9 | ⭐⭐⭐ | 5000 words | ~20% | Core transplant audience. Policy papers welcome. |
| **Transplantation** | 5.7 | ⭐⭐⭐ | 4000 words | ~25% | Transplant-specific. Good policy section. |
| **JHPPL** (J Health Pol, Policy & Law) | 2.1 | ⭐⭐ | 10000 words | ~15% | Deep policy analysis, longer format. |
| **Medical Care** | 4.0 | ⭐⭐ | 4000 words | ~20% | Health services. Policy simulation fits. |
| **Health Affairs** | 9.4 | ⭐⭐ | 3500 words | ~8% | High impact but very competitive. |

**Recommended:** AJT first — the transplant community is the primary audience.

## Likelihood of Acceptance
**Moderate (50%)** — Policy simulation is valued in AJT. Literature-backed parameters strengthen credibility. Risk: reviewers may want empirical validation against actual post-2021 policy outcomes.

## Effort Required
**Low** — The scenario engine (backend/services/policy_scenarios.py) has all 5 scenarios implemented with per-center-size modifiers. Just need to run, tabulate, and write.

### What exists already
- `/policy-scenarios` GET endpoint: returns available scenarios with descriptions
- `/policy-scenario` POST endpoint: runs a scenario for a patient profile
- `/travel-subsidy-analysis` POST endpoint: multi-tier travel subsidy analysis
- 5 predefined scenarios with literature references and per-center-size adjustment tables
- `/what-if` POST endpoint: custom donor rate and wait time multipliers

### What needs to be done
- [ ] Run all 5 scenarios for kidney (primary), liver, heart
- [ ] Generate before/after ranking tables per scenario
- [ ] Identify "winner" and "loser" centers per scenario
- [ ] Compute equity impact (run equity audit pre/post each scenario)
- [ ] Literature review: UNOS policy evaluation studies
- [ ] Write manuscript (~4500 words)

## Suggested Structure

1. **Introduction** (500 words)
   - UNOS policy landscape: 250nm circles (2021), continuous distribution (proposed)
   - Supply-side interventions: DCD expansion, HCV+ donors
   - Financial barriers: travel costs as access determinant
   - Gap: no unified tool comparing all five policy dimensions simultaneously

2. **Methods** (1000 words)
   - 2.1 Base model: Monte Carlo competing risks with 248 SRTR centers
   - 2.2 Scenario parameterization (table: each scenario's multipliers and literature source)
   - 2.3 Center-size stratification (large/medium/small respond differently)
   - 2.4 Equity impact: Gini coefficient before/after each scenario
   - 2.5 Sensitivity: vary scenario intensity ±20%

3. **Results** (1500 words)
   - 3.1 Baseline center rankings (reference run)
   - 3.2 250nm circles impact (who gains, who loses)
   - 3.3 Continuous distribution (more dramatic redistribution)
   - 3.4 DCD expansion (global supply increase, uniform vs differential)
   - 3.5 HCV+ donors (kidney/liver only, modest impact)
   - 3.6 Travel subsidy tiers ($5K–$50K: cost-effectiveness)
   - 3.7 Combined scenarios (what if multiple policies enacted simultaneously?)
   - 3.8 Equity impact (Gini change per scenario)

4. **Discussion** (1000 words)
   - Trade-offs: geographic equity vs efficiency
   - Small centers as biggest beneficiaries of redistribution
   - Travel subsidies: diminishing returns above $20K
   - Limitations: parameters from literature, not patient-level data
   - Policy recommendations

5. **Conclusion** (300 words)

## Key Figures
1. Waterfall chart: center ranking shifts per scenario (top 20 movers)
2. Map: geographic redistribution under continuous distribution
3. Gini before/after bar chart (5 scenarios × 3 organs)
4. Travel subsidy dose-response curve ($5K → $50K)
5. Combined scenario heatmap (pairs of policies)

## Key Tables
1. Scenario parameters with literature citations
2. Center-level impact: top-10 winners and losers per scenario
3. Organ-specific equity changes (Gini delta)
4. Cost-effectiveness of travel subsidy tiers
