---
sidebar_position: 1
---

# Quick Start

Get transplant location insights in under a minute.

## Use the Web App

1. Open TransPlan at the hosted URL or `http://localhost:8002` (after [local setup](/getting-started/local-setup)).
2. Click **Start Simulation** on the landing page to open the simulator.
3. Select your **organ type** (kidney, liver, heart, lung, pancreas, or intestine).
4. Enter your **blood type**, **age**, **sex**, and **urgency level**.
5. For organ-specific scores: enter your **cPRA** (0–100%) for kidney, **MELD score** (6–40) for liver, or **LAS** (0–100) for lung.
6. Optionally select a **Home Center** to compare relocation benefit, and enable the **Cause of Death Multiplier** for organ-specific donor availability adjustment.
7. Optionally adjust category weights using the methodology section.
8. Click **Calculate Suitability Scores**.

## Reading the Results

Results are displayed in three tabs:

### Tab 1: Location Scores

Cities are ranked by a composite score (0–100) across 8 categories. Each card shows the overall score and rank, a per-category breakdown bar, and a radar chart of category scores. Click any card for a detailed breakdown; use checkboxes to compare up to 3 cities side-by-side. If a Home Center is selected, each card shows the score difference (e.g., +5.2 pts).

### Tab 2: Simulation Probabilities

If the backend is running, cities are ranked by estimated 24-month transplant probability. Each result shows **P(transplant 24mo)** as the primary ranking metric, the **median wait** in months estimated across 1,000 Monte Carlo iterations, a **95% CI** from those iterations, a **competing risks** stacked bar showing transplant / mortality / delisting / still waiting, and a **CDF curve** showing cumulative probability over time. A sensitivity analysis tornado chart shows which input parameters most affect outcomes.

### Tab 3: Equity Analysis

If the backend is running, this tab displays demographic fairness analysis across a 48-profile matrix (8 blood types × 3 age brackets × 2 sexes). Charts show blood type disparity, age bracket disparity, and a Gini coefficient ranking of cities by outcome equality.

:::info Graceful Degradation
If the backend is unavailable, only Tab 1 (location scores) will be shown. The app displays a yellow banner in this case.
:::

## Interpreting Scores

| Score Range | Interpretation |
|-------------|----------------|
| 80–100 | Highly favorable: strong match across most factors |
| 60–79 | Favorable: good match with some trade-offs |
| 40–59 | Moderate: notable limitations in some categories |
| below 40 | Limited: significant barriers present |

Scores are **relative**, not absolute. A score of 75 does not mean a 75% transplant probability; it means that city ranks well compared to alternatives for your profile.

## Map View

The interactive map shows all 22 cities with colored markers indicating relative suitability. Toggle overlay layers using the checkboxes in the map controls panel. If a Home Center is selected, a green "H" marker highlights it on the map.

## Next Steps

1. [Local Setup](/getting-started/local-setup): run the full stack locally with Phase 2 enabled
2. [Scoring Methodology](/theory/scoring-methodology): understand how scores are calculated
3. [Monte Carlo Simulation](/theory/monte-carlo): understand the probability estimates
