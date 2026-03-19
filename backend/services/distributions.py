"""
Wait-time distribution models per organ/blood type/city.

Models wait times as log-normal distributions parameterized by:
  - National median wait time (months) per organ
  - Blood type multipliers (O waits longest, AB shortest)
  - City-level factors (relative to national average)
  - Organ-specific clinical multipliers (cPRA for kidney, MELD for liver, LAS for lung)

Data source: data/wait-time-distributions.json (OPTN/SRTR 2023 Annual Data Report + literature)
"""
import json
import logging
import threading
from pathlib import Path

import numpy as np
import scipy.stats

from config import DATA_DIR

logger = logging.getLogger(__name__)

_DISTRIBUTIONS: dict | None = None
_CITY_FACTORS: dict[str, float] = {}
_lock = threading.Lock()


def _load_distributions() -> tuple[dict, dict[str, float]]:
    """Load distribution parameters from JSON. Called once at first use."""
    path = DATA_DIR / "wait-time-distributions.json"
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    city_factors = raw.get("city_wait_time_factors", {})
    # Remove non-city keys
    city_factors = {k: v for k, v in city_factors.items() if k != "_notes"}

    # Build per-organ distribution params
    organs = {}
    for organ in ("kidney", "liver", "heart", "lung", "pancreas", "intestine"):
        if organ in raw:
            organs[organ] = raw[organ]

    logger.info("Distribution params loaded for %d organs, %d cities", len(organs), len(city_factors))
    return organs, city_factors


def _ensure_loaded() -> None:
    """Lazy-load distribution data on first call (thread-safe)."""
    global _DISTRIBUTIONS, _CITY_FACTORS
    if _DISTRIBUTIONS is None:
        with _lock:
            if _DISTRIBUTIONS is None:  # double-checked locking
                _DISTRIBUTIONS, _CITY_FACTORS = _load_distributions()


def _get_range_multiplier(value: int | float, ranges: dict[str, float]) -> float:
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


def get_wait_time_distribution(
    organ: str,
    blood_type: str,
    city: str,
    cpra: int | None = None,
    meld: int | None = None,
    las: float | None = None,
) -> scipy.stats.rv_continuous:
    """
    Return a log-normal distribution for wait time in months.

    The distribution's median (50th percentile) is the national median adjusted
    by blood type, city factor, and organ-specific clinical score.

    Parameters
    ----------
    organ : str
        One of: kidney, liver, heart, lung, pancreas, intestine.
    blood_type : str
        ABO/Rh blood type, e.g. "O+", "AB-".
    city : str
        City name matching keys in city_wait_time_factors.
    cpra : int, optional
        Calculated Panel Reactive Antibody (kidney only, 0-100).
    meld : int, optional
        Model for End-Stage Liver Disease score (liver only, 6-40).
    las : float, optional
        Lung Allocation Score (lung only, 0-100).

    Returns
    -------
    scipy.stats.rv_continuous
        A frozen log-normal distribution. Call .rvs(size=N) to sample,
        .median() for median, .ppf(q) for percentiles.
    """
    _ensure_loaded()

    organ_params = _DISTRIBUTIONS.get(organ)
    if organ_params is None:
        # Fallback: generic 24-month median
        logger.warning("No distribution params for organ '%s', using fallback", organ)
        return scipy.stats.lognorm(s=0.8, scale=24.0)

    median = organ_params["national_median_months"]
    sigma = organ_params["log_sigma"]

    # Blood type modifier
    bt_mult = organ_params.get("blood_type_multipliers", {}).get(blood_type, 1.0)

    # City modifier
    city_mult = _CITY_FACTORS.get(city, 1.0)

    # Organ-specific clinical modifiers
    clinical_mult = 1.0
    clinical_multipliers = organ_params.get("clinical_multipliers", {})

    if organ == "kidney" and cpra is not None and "cpra" in clinical_multipliers:
        clinical_mult = _get_range_multiplier(cpra, clinical_multipliers["cpra"])

    if organ == "liver" and meld is not None and "meld" in clinical_multipliers:
        clinical_mult = _get_range_multiplier(meld, clinical_multipliers["meld"])

    if organ == "lung" and las is not None and "las" in clinical_multipliers:
        clinical_mult = _get_range_multiplier(las, clinical_multipliers["las"])

    # Adjusted median = national × blood_type × city × clinical
    adjusted_median = median * bt_mult * city_mult * clinical_mult

    # scipy.stats.lognorm(s=sigma, scale=exp(mu)) has median = scale = exp(mu)
    # So scale = adjusted_median gives the desired median directly
    return scipy.stats.lognorm(s=sigma, scale=adjusted_median)


def get_lognorm_params(dist) -> tuple[float, float, float]:
    """
    Safely extract (s, loc, scale) from a frozen lognorm distribution.

    Handles both positional-arg and keyword-arg construction patterns
    used by scipy.stats.lognorm. Centralises the fragile introspection
    so callers don't depend on frozen-dist internals.
    """
    # Shape 's' may be in args[0] (positional) or kwds (keyword)
    if dist.args:
        s = dist.args[0]
    else:
        s = dist.kwds.get('s', 1.0)
    loc = dist.kwds.get('loc', 0)
    scale = dist.kwds.get('scale', 1.0)
    return s, loc, scale


def get_city_factors() -> dict[str, float]:
    """Return the city wait time factor dict (for inspection/testing)."""
    _ensure_loaded()
    return dict(_CITY_FACTORS)


def get_organ_params(organ: str) -> dict | None:
    """Return raw distribution parameters for an organ (for inspection/testing)."""
    _ensure_loaded()
    return _DISTRIBUTIONS.get(organ)
