"""Empirical-Bayes shrinkage for small-cohort center factors (#268 / L-086).

A per-center factor is a ratio estimated from that center's own cohort. At
n = 3 the ratio is essentially noise, it lands at an extreme, the [0.3, 3.0]
clamp pins it to the most favourable value, and the center ranks near the top
of the recommendation list. Measured before building: **every** center with a
cohort of 10 or fewer sits on a clamp bound (kidney 11/11, liver 12/12, heart
20/20), and the pinning is asymmetric — 60 kidney centers at the favourable
bound against 2 at the unfavourable one — so the noise systematically promotes
small centers rather than scattering them.

Shrinking a center's factor toward the organ mean in proportion to how much
data stands behind it is the standard fix. The only free choice is *how much*,
and that is derived here rather than picked:

    Var(f) = tau^2 + c/n

Splitting centers into small-n and large-n halves gives two equations in two
unknowns, so tau^2 (real between-center variance) and c (sampling variance
scale) both fall out by method of moments, and

    k = c / tau^2,    w = n / (n + k),    f_shrunk = 1 + (f - 1) * w

A hand-picked k would be exactly the kind of uncited constant this project
keeps finding at the bottom of its own findings.

IMPORTANT: apply this BEFORE clamping. Shrinking after the clamp is useless,
because the clamp has already replaced the estimate with a bound.
"""
from __future__ import annotations

import statistics

# Minimum centers before tau^2 is worth estimating at all. tau^2 is an
# excess-of-variance estimate — a variance of a variance — so it is unusable on
# a small panel. This only gates ESTIMABILITY; whether shrinking actually helps
# is decided per organ by the calibration gate (see SHRINKABLE_ORGANS).
MIN_CENTERS = 100

# Organs where shrinkage was MEASURED not to degrade per-center calibration.
#
# This is an allowlist rather than a threshold because the outcome does not
# follow any structural property of the organ. Controlled comparison — same
# code, only the factor data differing, all six organs recomputed in both arms
# (`run-center-calibration.py --organ all`) — Spearman of predicted p12 against
# observed SRTR transplant rates:
#
#     kidney     +0.0002   (n>=10 subset: -0.0001)   -> shrink
#     heart      -0.0342   (n>=10 subset: -0.0222)   -> do NOT shrink
#     liver      -0.0119   (n>=10 subset: -0.0103)   -> do NOT shrink
#     lung/pancreas/intestine: not estimable anyway
#
# Heart and liver degrade on the n>=10 subset too, so this is not the metric
# rewarding the model for reproducing small-cohort noise — it is a real loss
# among well-measured centers. Kidney is also where the defect matters most:
# 232 centers and roughly 17,000 transplants a year.
#
# To revisit, re-run that comparison. Do not add an organ without it.
SHRINKABLE_ORGANS = frozenset({"kidney"})

# Floor on how much of its own estimate a MEDIAN-sized center must retain.
#
# Set from measured calibration, not intuition. An earlier cap on the raw prior
# strength was removed as unjustifiable — that constant is not interpretable
# without a cohort size. This bound is, and the evidence is direct: shrinking
# with a median weight of 0.04 (lung) degraded Spearman against observed SRTR
# transplant rates by 0.095, while median weights of 0.17 (kidney), 0.31
# (heart) and 0.53 (liver) left it unchanged to four decimal places.
#
# Below this floor the estimator is flattening the variable rather than
# shrinking it, and flattening measurably loses signal.
MIN_MEDIAN_WEIGHT = 0.10


def shrink(raw: float, n: float, k: float) -> float:
    """Shrink *raw* toward 1.0 given cohort size *n* and strength *k*.

    n = 0 returns 1.0 (no evidence, fall back to the organ mean); large n
    returns essentially *raw*. The result never crosses 1.0, so a favourable
    factor cannot become unfavourable.
    """
    if k is None or k <= 0:
        return raw
    if n <= 0:
        return 1.0
    w = n / (n + k)
    return 1.0 + (raw - 1.0) * w


def implied_weight(k: float | None, n: float) -> float:
    """How much of its own estimate a center of size *n* keeps."""
    if not k or k <= 0:
        return 1.0
    return n / (n + k)


def estimate_k(rates: list[float], ns: list[float],
               national_rate: float) -> float | None:
    """Beta-binomial shrinkage strength from per-center RATES and cohort sizes.

    Estimated on the count scale, not from the ratio's variance. Measuring the
    latter first showed why it has to be: the factor is a rate ratio with a
    tiny denominator, so `Var = tau^2 + c/n` misfits badly — it produced
    k = 106 for kidney, "not estimable" for heart, and a confident estimate for
    pancreas, which is the one organ that should decline. Those numbers
    disagreed with each other and with the shipped factors, which is what a
    misspecified model looks like.

    The real failure mode is zero counts, not variance scale: **all 11** kidney
    centers with n <= 10 recorded exactly zero waitlist deaths, as did 70 of 75
    pancreas centers. At p ~ 0.019 and n = 3, P(zero) = 0.94 — that is no
    information, not low mortality, and the raw ratio of 0 then clamps to the
    most favourable bound.

    So model the counts: x_i ~ Binomial(n_i, p_i), p_i ~ Beta with mean equal
    to the national rate. The prior strength M = alpha + beta is the shrinkage
    constant, and the posterior mean gives

        w_i = n_i / (n_i + M),   p_hat = w_i*p_i + (1-w_i)*national

    which rearranges to exactly `shrink()`'s `1 + w*(ratio - 1)`, so the
    applied formula is unchanged — only its constant is now estimated somewhere
    the maths holds.

    M comes from the standard moment identity: the observed spread of rates
    exceeds binomial sampling noise by the true between-center variance.
    Returns None when that excess is non-positive (no recoverable signal) or
    when M is too large to be shrinkage rather than flattening.
    """
    pairs = [(float(r), float(n)) for r, n in zip(rates, ns)
             if r is not None and n and n > 0]
    if len(pairs) < MIN_CENTERS or not national_rate or national_rate <= 0:
        return None

    m = national_rate
    total_n = sum(n for _, n in pairs)
    if total_n <= 0:
        return None

    # Observed between-center variance of the rate, weighted by cohort size so
    # a 3-patient center does not count as much as a 700-patient one.
    mean_r = sum(r * n for r, n in pairs) / total_n
    var_obs = sum(n * (r - mean_r) ** 2 for r, n in pairs) / total_n

    # Expected sampling contribution to that SAME weighted variance. This has
    # to be weighted identically or the comparison is meaningless: an
    # n-weighted observed variance is dominated by large centers (low noise)
    # while an unweighted mean of m(1-m)/n is dominated by small ones (high
    # noise), which yields an impossible negative tau^2 for every organ.
    #   sum(n_i * m(1-m)/n_i) / sum(n_i)  =  m(1-m) * n_centers / total_n
    var_sampling = m * (1.0 - m) * len(pairs) / total_n

    tau2 = var_obs - var_sampling
    if tau2 <= 0:
        return None                      # spread is entirely sampling noise

    M = m * (1.0 - m) / tau2 - 1.0
    if M <= 0:
        return None

    median_n = statistics.median([n for _, n in pairs])
    if implied_weight(M, median_n) < MIN_MEDIAN_WEIGHT:
        return None          # flattening, not shrinking — see the constant above
    return M
