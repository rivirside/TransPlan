"""
Shared statistical utility functions used across multiple services.

Consolidated from equity.py, bias_audit.py, distributions.py, and
competing_risks.py to avoid duplication (Issue #64).
"""
import logging

import numpy as np

logger = logging.getLogger(__name__)

# Exponential scale (months) used when an annual rate is zero — mean
# time-to-event of ~83,000 years, i.e. the event effectively never fires.
# A zero rate is never a true zero in this domain (SRTR base mortality/
# delisting rates are all positive), so hitting this fallback indicates
# missing or corrupt upstream data and is logged (#229).
ZERO_RATE_SCALE_MONTHS: float = 1e6


def gini(values: np.ndarray) -> float:
    """Compute Gini coefficient. 0 = perfect equality, 1 = total inequality.

    Only defined for non-negative inputs — with mixed signs the normalization
    breaks down and the result can exceed 1 or lose meaning (#225). Callers
    pass probabilities or wait times, so negatives indicate a bug upstream.

    Raises:
        ValueError: if any value is negative or non-finite (NaN/inf).
    """
    values = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("gini() requires finite values; got NaN or inf")
    if np.any(values < 0):
        raise ValueError("gini() is only defined for non-negative values")
    if len(values) < 2 or np.sum(values) == 0:
        return 0.0
    s = np.sort(values)
    n = len(s)
    idx = np.arange(1, n + 1)
    return max(0.0, float((2 * np.sum(idx * s) - (n + 1) * np.sum(s)) / (n * np.sum(s))))


def gini_weighted(values: np.ndarray, weights: np.ndarray) -> float:
    """Population-weighted Gini coefficient via the discrete Lorenz curve.

    Equivalent to the pairwise definition
        G = sum_ij w_i w_j |x_i - x_j| / (2 W^2 mu_w)
    but computed in O(n log n). With equal weights it reduces exactly to
    ``gini()``. Zero-weight cells are ignored; weight scale is irrelevant.

    Raises:
        ValueError: on negative/non-finite values or weights.
    """
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if values.shape != weights.shape:
        raise ValueError("gini_weighted() values and weights must match in length")
    if not (np.all(np.isfinite(values)) and np.all(np.isfinite(weights))):
        raise ValueError("gini_weighted() requires finite values and weights")
    if np.any(values < 0) or np.any(weights < 0):
        raise ValueError("gini_weighted() is only defined for non-negative inputs")

    mask = weights > 0
    values, weights = values[mask], weights[mask]
    if len(values) < 2 or np.sum(values * weights) == 0:
        return 0.0

    order = np.argsort(values, kind="stable")
    x, w = values[order], weights[order]
    cum_w = np.cumsum(w)
    cum_v = np.cumsum(x * w)
    p = cum_w / cum_w[-1]
    lorenz = cum_v / cum_v[-1]
    p_prev = np.concatenate(([0.0], p[:-1]))
    l_prev = np.concatenate(([0.0], lorenz[:-1]))
    return max(0.0, float(1.0 - np.sum((p - p_prev) * (lorenz + l_prev))))


def rate_to_exponential_scale(annual_rate: float, event: str, context: str = "") -> float:
    """Convert an annual event rate to an exponential scale in months.

    Returns 12 / rate for positive rates. A non-positive rate signals a data
    problem (true rates are always > 0 — see ZERO_RATE_SCALE_MONTHS), so it is
    logged and the event is modeled as effectively never occurring (#229).
    """
    if annual_rate > 0:
        return 12.0 / annual_rate
    logger.warning(
        "Non-positive annual %s rate (%s)%s — modeling as near-zero risk. "
        "This usually indicates missing or corrupt source data.",
        event, annual_rate, f" for {context}" if context else "",
    )
    return ZERO_RATE_SCALE_MONTHS


def spearman_between(ranks_a: list[str], ranks_b: list[str]) -> float | None:
    """Spearman rank correlation between two ordered label lists, over their
    common members. Returns None if fewer than 3 labels overlap."""
    from scipy import stats as sp_stats
    common = [c for c in ranks_a if c in ranks_b]
    if len(common) < 3:
        return None
    a = [ranks_a.index(c) for c in common]
    b = [ranks_b.index(c) for c in common]
    rho, _ = sp_stats.spearmanr(a, b)
    return float(rho)


def top5_jaccard(ranks_a: list[str], ranks_b: list[str]) -> float:
    """Jaccard overlap of the top-5 labels of two ordered lists."""
    sa, sb = set(ranks_a[:5]), set(ranks_b[:5])
    if not (sa | sb):
        return 1.0
    return len(sa & sb) / len(sa | sb)


def get_range_multiplier(value: int | float, ranges: dict[str, float]) -> float:
    """
    Look up a multiplier from a range-keyed dict.

    Keys like "0-20", "21-80", "81-97", "98-100".
    Returns 1.0 if no matching range is found.
    """
    for range_key, multiplier in ranges.items():
        parts = range_key.split("-")
        if len(parts) == 2:
            lo, hi = float(parts[0]), float(parts[1])
            if lo <= value <= hi:
                return multiplier
    return 1.0


def result_to_ranks(result) -> list[str]:
    """Ordered center keys from a SimulationResult (#264: shared by the
    cross-engine comparisons in routers/validation.py and services)."""
    return [c.center_code or c.city for c in result.cities]


def truncated_wait_times(dist, t0: float, size: int, rng) -> "np.ndarray":
    """Draw remaining wait times (T - t0 | T > t0) from a frozen wait
    distribution (#329).

    Inverse-CDF sampling on the conditional: u ~ U(F(t0), 1), T = ppf(u),
    remaining = T - t0. At t0 = 0 this is exactly unconditional sampling.
    """
    import numpy as np
    if t0 <= 0:
        return dist.rvs(size=size, random_state=rng)
    f0 = float(dist.cdf(t0))
    # Guard: essentially the whole mass already passed (numerically) —
    # sample the far tail uniformly just below 1
    f0 = min(f0, 1.0 - 1e-12)
    u = rng.uniform(f0, 1.0, size=size)
    return np.maximum(dist.ppf(u) - t0, 1e-9)


def conditional_p_within(dist, t0: float, horizon: float,
                         competing_hazard: float) -> float:
    """P(transplant first AND within *horizon* months | already waited t0).

    The left-truncated analog of the #216 closed form: integrate the
    conditional wait density f(t0+x)/S(t0) against the competing-risk
    survival exp(-hazard*x) over x in [0, horizon]. Competing-risk clocks
    restart at t0 (they are memoryless exponentials in this model).
    """
    import numpy as np
    sf0 = float(dist.sf(t0)) if t0 > 0 else 1.0
    if sf0 <= 1e-12:
        return 0.0
    x = np.linspace(0.0, horizon, 241)
    integrand = dist.pdf(t0 + x) / sf0 * np.exp(-competing_hazard * x)
    _trapz = getattr(np, "trapezoid", None) or np.trapz
    return float(np.clip(_trapz(integrand, x), 0.0, 1.0))
