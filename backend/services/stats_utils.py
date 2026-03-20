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
