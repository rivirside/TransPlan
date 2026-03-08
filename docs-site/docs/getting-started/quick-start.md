---
sidebar_position: 1
---

# Quick Start

Get transplant location insights in under a minute.

## Use the Web App

1. Open TransPlan at `http://localhost:8003` (after [local setup](/getting-started/local-setup)) or the hosted URL.
2. Select your **organ type** (kidney, liver, heart, lung, pancreas, or intestine).
3. Enter your **blood type**, **age**, **sex**, and **urgency level**.
4. For organ-specific scores: enter your **cPRA** (0–100%) for kidney, **MELD score** (6–40) for liver, or **LAS** (0–100) for lung.
5. Optionally adjust category weights using the methodology section.
6. Click **Calculate Suitability Scores**.

## Reading the Results

### Phase 1 Tab: Suitability Scores

Cities are ranked by a composite score (0–100) across 8 categories. Each card shows the overall score and rank, a per-category breakdown bar, and a radar chart of category scores.

### Phase 2 Tab: Transplant Probabilities

If the backend is running, cities are ranked by estimated 24-month transplant probability. Each result shows **P(transplant 24mo)** as the primary ranking metric, the **median wait** in months estimated across 1,000 Monte Carlo iterations, a **95% CI** from those iterations, a **competing risks** stacked bar showing transplant / mortality / delisting / still waiting, and a **CDF curve** showing cumulative probability over time.

:::info Graceful Degradation
If the backend is unavailable, only Phase 1 (suitability scores) will be shown. The app displays a yellow banner in this case.
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

The interactive map shows all 22 cities with colored markers indicating relative suitability. Toggle overlay layers (hospitals, OPO boundaries) using the checkboxes in the map controls panel.

## Next Steps

1. [Local Setup](/getting-started/local-setup): run the full stack locally with Phase 2 enabled
2. [Scoring Methodology](/theory/scoring-methodology): understand how scores are calculated
3. [Monte Carlo Simulation](/theory/monte-carlo): understand the probability estimates
