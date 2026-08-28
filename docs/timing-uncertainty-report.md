# The uncertainty the interval still leaves out (#296 / #226)

**Date:** 2026-08-28
**Verdict:** the omitted wait-timing component is **material** — up to 0.56× the reported interval's own width for kidney — but it is not a variance that can honestly be added, because its two endpoints are not equally credible.

---

## What was deferred

`_data_uncertainty_ci`'s docstring has said since #226:

> this is the *data-sampling* uncertainty in the observed rates […] It is NOT the full credible interval on p24, which would also propagate the WaitCategory-timing uncertainty; that requires the CPT-parameter Monte Carlo deferred to a follow-up.

#296's Dirichlet half was measured in #420 and found **narrower** than the shipped binomial band, so it would have reduced disclosed uncertainty. This is the other half: how big is the timing component?

## A band grounded in the data, not invented

Wait times are lognormal, fitted from SRTR percentiles. `sigma_from_percentiles` clamps σ to **[0.3, 1.2]**, and recomputing the same strategy chain **without** the clamp against the shipped workbooks:

| organ | P10 | P25 | raw σ | shipped σ | ratio |
|---|---|---|---|---|---|
| kidney | 1.4 | 6.5 | **2.529** | 1.200 | **2.11×** |
| liver | 0.2 | 0.5 | 1.509 | 1.200 | 1.26× |
| heart | 0.2 | 0.5 | 1.509 | 1.200 | 1.26× |
| lung | 0.2 | 0.4 | 1.142 | 1.140 | 1.00× |
| pancreas | 3.4 | 13.3 | 2.247 | 0.800 | 2.81× |
| intestine | 0.8 | 2.9 | 2.121 | 1.200 | 1.77× |

Five of six are clamped. Kidney — the largest population the tool serves — is clamped to less than half the value its own percentiles imply. (Pancreas is 0.800 for a different reason: its median is censored, so `fit_lognormal` takes the reconstruction branch. See L-080.)

So [shipped, raw] is a defensible band: one end is what the model uses, the other is what the percentiles say, and nothing in the repo establishes which is right.

## The induced spread

Re-running the Monte Carlo engine at each endpoint, seeded, 3000 iterations:

| organ | mean p24 shipped → raw | mean \|Δp24\| | max \|Δ\| | median reported CI width | Δ / CI |
|---|---|---|---|---|---|
| kidney | 0.3772 → 0.4310 | **0.0968** | 0.1820 | 0.1718 | **0.56×** |
| pancreas | 0.3278 → 0.4034 | 0.1544 | 0.2310 | 0.4875 | 0.32× |
| liver | 0.7771 → 0.7434 | 0.0338 | 0.0594 | 0.1770 | 0.19× |
| heart | 0.8762 → 0.8394 | 0.0369 | 0.0590 | 0.2061 | 0.18× |
| intestine | 0.6271 → 0.5821 | 0.0804 | 0.1447 | 0.6460 | 0.12× |
| lung | 0.9472 → 0.9470 | 0.0002 | 0.0007 | 0.1139 | 0.00× |

Lung is the control: its σ is effectively unclamped, so there is no band and the spread is zero. That the method returns ~0 exactly where it should is what makes the other rows believable.

**The reported interval propagates none of this.** For kidney the omitted component is over half the current width again; folding it in by quadrature would widen the band by roughly 50%.

One precision, because a first draft of this got it wrong and the test caught it: the interval *does* move when σ moves — `_data_uncertainty_ci` uses √(p(1−p)/n), so a shift in p24 shifts the binomial SE, and 99 of 233 kidney widths changed by more than 0.02 across the band. That is the interval tracking the **point estimate's curvature**, not accounting for uncertainty **about** σ. The distinction is the whole finding: no width in the app is wider because σ is unknown.

## Why it is not simply added

Two reasons, and both matter.

**The endpoints are not equally credible.** #274 measured that raising the clamp *degrades* calibration against observed SRTR transplant rates on every assessable organ. So the raw σ is not the truth with the clamp as an approximation — it is the value the percentiles imply and the outcomes contradict. A band whose ends differ in credibility is not a sampling distribution.

**Turning it into a variance requires a prior over σ** — how much weight on the percentile fit versus the calibration evidence. That is a modelling judgement, and inventing one to widen a "95% CI" would be its own overclaim: the interval would then mean neither what its name says nor what the prior says.

So this is measured and disclosed rather than folded in. The same disposition as #274's clamp raise and #376's median substitution: the obvious change is not an improvement.

## What this means for the reported interval

Since #420 the Monte Carlo interval combines simulation error with data-sampling uncertainty at the center's cohort size. It is honest about what it covers and it is now the dominant, correct signal for sparse centers.

It still **understates** total uncertainty, most for kidney, by an amount now quantified rather than hand-waved. That belongs in the limitations register (L-097), not in a silently widened band.

`backend/tests/test_timing_uncertainty_scope.py` pins what this rests on: that the clamp is still binding for those organs, that lung remains the unclamped control, and that σ moves the estimate far more than it moves the interval — so a later change that folds the component in fails the test rather than leaving this page stale.
