# Sensitivity Analysis Report

> Generated March 2026. Sweep: 6 organs x 3 patient profiles x 10 cities, 500 iterations per run.

## Overview

This report documents which input parameters most strongly influence TransPlan's 24-month transplant probability (p24) estimates. For each organ, we swept clinical parameters from their most favorable to least favorable extreme values and measured the resulting change in p24. This validates that the model responds to inputs in clinically expected ways and identifies any parameters that may be over- or under-sensitive.

## Methods

For each organ, three representative patient profiles were constructed:

| Profile | Blood Type | Urgency | Clinical Score |
|---------|-----------|---------|----------------|
| Standard | O+ (common, longest wait) | 2 (moderate) | Median (cPRA 30, MELD 20, LAS 50) |
| Rare | AB+ (shortest wait) | 1 (low) | Favorable (cPRA 0, MELD 10, LAS 30) |
| Extreme | O- (longest wait) | 3-4 (high) | Severe (cPRA 95, MELD 35, LAS 80) |

Each profile was run through the sensitivity analysis service across 10 geographically diverse cities: Houston, Pittsburgh, Chicago, Cleveland, Minneapolis, Nashville, New York, Los Angeles, San Francisco, and Palo Alto. The "swing" for each parameter is the absolute difference in p24 between the most favorable and least favorable values, averaged across all 10 cities.

## Results by Organ

### Kidney

| Parameter | Avg Swing (p24) | Dominance |
|-----------|----------------|-----------|
| cPRA (0 vs 98%) | 0.271 | **Dominant** |
| Urgency (1 vs 4) | 0.029 | Secondary |

**Interpretation:** cPRA is the overwhelming driver for kidney, producing a ~27 percentage point swing in p24. This is clinically expected — highly sensitized patients (cPRA 98%) wait dramatically longer due to the scarcity of compatible donors. Urgency has a modest effect (~3pp), consistent with kidney's relatively low acuity compared to heart/lung. This pattern held across all 3 profiles (cross-profile consistent).

### Liver

| Parameter | Avg Swing (p24) | Dominance |
|-----------|----------------|-----------|
| MELD (7 vs 38) | 0.252 | **Dominant** |
| Urgency (1 vs 4) | 0.032 | Secondary |

**Interpretation:** MELD dominates liver as expected — it directly determines allocation priority. The ~25pp swing reflects the difference between a MELD 7 (stable, low priority) and MELD 38 (critically ill, highest priority). The dual effect of high MELD (faster allocation but higher mortality) creates a non-linear relationship where the net benefit depends on the mortality-priority balance. Urgency adds a ~3pp secondary effect.

### Heart

| Parameter | Avg Swing (p24) | Dominance |
|-----------|----------------|-----------|
| Urgency (1 vs 4) | 0.028 | **Only parameter** |

**Interpretation:** Heart transplant has no organ-specific clinical score input (no equivalent of cPRA/MELD/LAS in the current model). Urgency is the sole tunable parameter and produces a modest ~3pp swing. The relatively small swing reflects heart's short baseline wait times (national median 2.2 months) — most patients receive a transplant quickly regardless of urgency level, so parameter variation has less room to affect p24.

### Lung

| Parameter | Avg Swing (p24) | Dominance |
|-----------|----------------|-----------|
| LAS (20 vs 85) | 0.080 | **Dominant** |
| Urgency (1 vs 4) | 0.010 | Secondary |

**Interpretation:** LAS dominates lung allocation, producing an ~8pp swing. The effect is smaller than cPRA/MELD for kidney/liver because lung baseline wait times are already short (national median 1.0 months) and the LAS system effectively prioritizes the sickest patients. Urgency contributes minimally (~1pp).

### Pancreas

| Parameter | Avg Swing (p24) | Dominance |
|-----------|----------------|-----------|
| Urgency (1 vs 4) | 0.022 | **Only parameter** |

**Interpretation:** Like heart, pancreas has no organ-specific clinical score. The modest urgency swing (~2pp) reflects pancreas's moderate wait times and low competing risk rates.

### Intestine

| Parameter | Avg Swing (p24) | Dominance |
|-----------|----------------|-----------|
| Urgency (1 vs 4) | 0.035 | **Only parameter** |

**Interpretation:** Intestine shows the largest urgency-only swing (~3.5pp) among organs without organ-specific scores, consistent with its higher acuity and stronger mortality-delisting coupling (copula theta = 1.5).

## Cross-Organ Summary

| Organ | #1 Parameter | Swing | #2 Parameter | Swing | Consistent? |
|-------|-------------|-------|-------------|-------|-------------|
| Kidney | cPRA | 0.271 | Urgency | 0.029 | Yes |
| Liver | MELD | 0.252 | Urgency | 0.032 | Yes |
| Heart | Urgency | 0.028 | — | — | Yes |
| Lung | LAS | 0.080 | Urgency | 0.010 | Yes |
| Pancreas | Urgency | 0.022 | — | — | Yes |
| Intestine | Urgency | 0.035 | — | — | Yes |

All 6 organs showed **cross-profile consistency** — the same parameters dominated regardless of which patient profile was tested. This indicates the model's sensitivity structure is stable and not dependent on specific input values.

## Key Findings

1. **Organ-specific clinical scores dominate when available.** cPRA (kidney), MELD (liver), and LAS (lung) each produce the largest p24 swings for their respective organs. This matches the transplant allocation system's design — these scores are specifically constructed to prioritize patients.

2. **No parameters show concerning over-sensitivity.** The largest swing (cPRA at ~27pp) is clinically justified — a cPRA of 98% genuinely represents a dramatically different patient situation than cPRA of 0%. No parameter produces an implausibly large effect.

3. **Heart, pancreas, and intestine have limited tunable sensitivity.** These organs only vary by urgency, which produces modest (2-3.5pp) effects. This is a model limitation — future work could add status codes (heart Status 1-6) or other clinical parameters to increase model expressiveness for these organs.

4. **Urgency is consistently secondary.** Across all organs, urgency produces 1-3.5pp swings — meaningful but never dominant when organ-specific scores are present. This aligns with clinical reality where allocation priority is driven primarily by medical compatibility and disease severity scores.

## Limitations

- Sensitivity analysis tests parameters one at a time (one-way sensitivity). Interaction effects between parameters are not captured.
- The sweep uses fixed extreme values rather than a continuous gradient; the true sensitivity surface may have non-linearities not captured by two-point estimation.
- Heart, pancreas, and intestine lack organ-specific clinical inputs, limiting the model's sensitivity to clinically relevant variation for these organs.
- 500 iterations per run introduces Monte Carlo noise (~1-2pp), which affects the precision of small swings more than large ones.
