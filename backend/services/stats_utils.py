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
