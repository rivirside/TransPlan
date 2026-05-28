---
sidebar_position: 1
---

# Quick Start

Get transplant location insights in under a minute.

## Use the Web App

Open TransPlan at the hosted URL or at `http://localhost:8002` after completing the [local setup](/getting-started/local-setup). Click **Start Simulation** on the landing page to open the simulator. Select your **organ type** (kidney, liver, heart, lung, pancreas, or intestine), then enter your **blood type**, **age**, **sex**, and **urgency level**. If your organ requires a specific clinical score, enter your **cPRA** (0-100%) for kidney, **MELD score** (6-40) for liver, or **LAS** (0-100) for lung. You can optionally select a **Home Center** to compare relocation benefit and enable the **Cause of Death Multiplier** for organ-specific donor availability adjustment. Category weights can also be adjusted in the methodology section. When you are ready, click **Calculate Suitability Scores**.

## Reading the Results

Results are displayed in three tabs.

### Tab 1: Location Scores

Cities are ranked by a composite score (0-100) across 8 categories. Each card shows the overall score and rank, a per-category breakdown bar, and a radar chart of category scores. Click any card for a detailed breakdown, and use checkboxes to compare up to 3 cities side-by-side. If a Home Center is selected, each card shows the score difference (for example, +5.2 pts).

### Tab 2: Simulation Probabilities

If the backend is running, cities are ranked by estimated 24-month transplant probability. Each result shows **P(transplant 24mo)** as the primary ranking metric, the **median wait** in months estimated across 1,000 Monte Carlo iterations, and a **95% CI** from those iterations. A **competing risks** stacked bar breaks down transplant, mortality, delisting, and still waiting, while a **CDF curve** shows cumulative probability over time. A sensitivity analysis tornado chart shows which input parameters most affect outcomes.

### Tab 3: Equity Analysis

If the backend is running, this tab displays demographic fairness analysis across a 48-profile matrix (8 blood types x 3 age brackets x 2 sexes). Charts show blood type disparity, age bracket disparity, and a Gini coefficient ranking of cities by outcome equality.

:::info Graceful Degradation
If the backend is unavailable, only Tab 1 (location scores) will be shown. The app displays a yellow banner in this case.
:::

## Interpreting Scores

Scores range from 0 to 100 and reflect relative suitability, not absolute transplant probability. A score of 75 does not mean a 75% chance of transplant; it means that city ranks well compared to alternatives for your profile. Cities scoring 80-100 are highly favorable with a strong match across most factors. A score of 60-79 indicates a favorable match with some trade-offs. Scores of 40-59 suggest moderate suitability with notable limitations in some categories. Anything below 40 signals limited suitability with significant barriers present.

## Map View

The interactive map shows all 248 SRTR transplant centers with colored markers indicating relative suitability. Toggle overlay layers using the checkboxes in the map controls panel. If a Home Center is selected, a green "H" marker highlights it on the map.

## Next Steps

For a deeper setup, follow the [Local Setup](/getting-started/local-setup) guide to run the full stack locally. To understand how scores are calculated, read the [Scoring Methodology](/theory/scoring-methodology). For details on the probability estimates, see [Monte Carlo Simulation](/theory/monte-carlo).
