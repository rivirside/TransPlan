"""
Shared statistical utility functions used across multiple services.

Consolidated from equity.py, bias_audit.py, distributions.py, and
competing_risks.py to avoid duplication (Issue #64).
"""
import numpy as np


def gini(values: np.ndarray) -> float:
    """Compute Gini coefficient. 0 = perfect equality, 1 = total inequality."""
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or np.sum(values) == 0:
        return 0.0
    s = np.sort(values)
    n = len(s)
    idx = np.arange(1, n + 1)
    return max(0.0, float((2 * np.sum(idx * s) - (n + 1) * np.sum(s)) / (n * np.sum(s))))


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
