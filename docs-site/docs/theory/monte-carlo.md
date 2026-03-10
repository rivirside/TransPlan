---
sidebar_position: 2
---

# Monte Carlo Simulation

TransPlan's Phase 2 engine uses Monte Carlo simulation to estimate transplant probability distributions for each city.

## Why Monte Carlo?

Wait time on a transplant list is inherently stochastic. A patient might wait 6 months or 36 months for the same organ in the same city, depending on donor availability, organ compatibility matches, and clinical status changes. A single point estimate ("expected wait: 18 months") loses this uncertainty.

Monte Carlo simulation captures the full distribution by sampling from calibrated statistical models 1,000 times per city.

## Algorithm Overview

For each city, the engine:

1. **Samples a wait time** from a log-normal distribution parameterized by SRTR data for that city, organ, and blood type
2. **Applies clinical multipliers** based on cPRA / MELD / LAS
3. **Applies a competing risks check**: at each time step, the patient may receive a transplant, die, or be delisted
4. **Records the outcome** (transplant / mortality / delisting / still waiting) at 6, 12, 24, and 36 months
5. **Repeats 1,000 times** to build the outcome distribution

### Performance

22 cities × 1,000 iterations runs in approximately 80ms on a typical laptop. Results are not cached; each request recomputes fresh.

## Log-Normal Wait Time Model

Wait time `T` for a given (city, organ, blood_type) combination is modeled as:

```
T ~ LogNormal(μ, σ)
```

where `μ` and `σ` are estimated from SRTR Table B10 (Program-Specific Reports, biannual).

### City Factor and Clinical Multiplier

The raw sampled wait time is scaled by up to three independent terms:

```
T_adjusted = T × city_factor × clinical_multiplier / cod_multiplier
```

The **city factor** captures how a city's historical median compares to the national median for that organ and blood type. A city_factor > 1.0 means longer waits than average; < 1.0 means shorter. These are derived from SRTR Table B10 by computing each city's median divided by the national median across all centers.

The **clinical multiplier** adjusts for the patient's organ-specific clinical score, which affects allocation priority independently of city:

| Score | Range | Multiplier direction | Rationale |
|-------|-------|---------------------|-----------|
| cPRA (kidney) | 0–100% | > 1.0 at high values | Highly sensitized patients need a rare antigen-negative donor, making each match attempt less likely to succeed |
| MELD (liver) | 6–40 | < 1.0 at high values | High MELD patients receive allocation priority; the sickest patients are offered organs first |
| LAS (lung) | 0–100 | < 1.0 at high values | High LAS patients receive allocation priority by the same urgency-based logic |

A cPRA of 80% produces a multiplier of roughly 1.5× to 3.0×, meaning the adjusted wait is 50–200% longer than baseline. A MELD of 35+ produces a multiplier around 0.3×, reflecting emergency-level allocation priority.

### Cause-of-Death (COD) Multiplier (Optional)

When `adjust_for_cause_of_death` is enabled, the simulation divides wait times by a COD multiplier that reflects regional organ-specific donor availability. The multiplier combines organ recovery rates from published literature (PMC10329409) with state-level cause-of-death proportions from CDC WONDER. It is normalized and centered at 1.0, with typical variation of 1–15% depending on the organ type. More donors in a region means shorter expected wait. This is computed per-city using `data/cause-of-death-by-region.json`.

## Output: Probability Estimates

After 1,000 iterations, the fraction of runs that resulted in a transplant by each horizon is the probability estimate:

```
P(transplant ≤ t) = count(outcome == transplant AND time ≤ t) / 1000
```

### Reported Metrics

| Metric | Definition |
|--------|------------|
| `p_transplant_6mo` | Fraction transplanted within 6 months |
| `p_transplant_12mo` | Fraction transplanted within 12 months |
| `p_transplant_24mo` | Fraction transplanted within 24 months (primary ranking metric) |
| `p_transplant_36mo` | Fraction transplanted within 36 months |
| `median_wait_months` | Median wait across all 1,000 iterations |
| `confidence_interval_95` | Bootstrap 95% CI for 24-month probability |

## CDF Curves

The cumulative distribution function (CDF) shows `P(transplant ≤ t)` for `t` from 0 to 60 months, computed from the 1,000 simulation outcomes. The CDF is plotted in the app as a line chart per city.

Cities with steeper CDFs offer faster access for this patient profile.

## Confidence Intervals

The 95% CI is computed via bootstrap resampling of the 1,000 simulation outcomes:

1. Resample 1,000 outcomes with replacement (200 bootstrap resamples)
2. Compute `p_transplant_24mo` for each resample
3. Report the 2.5th and 97.5th percentile

Wide CIs indicate high variance, often due to rare blood types or extreme clinical scores that hit data-sparse regions of the model.

## Ranking

Cities are ranked by `p_transplant_24mo` descending. For ties, `median_wait_months` ascending is used as a tiebreaker.

## Limitations

The model is calibrated on historical SRTR data; future policy changes (e.g., kidney allocation score updates) may not be reflected. Blood type–organ combinations with low SRTR sample counts have higher uncertainty. The model does not account for center-specific acceptance practices or multi-listing (being listed at multiple centers).

See [Competing Risks](/theory/competing-risks) for the mortality and delisting models.
