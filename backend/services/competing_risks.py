"""
Competing risks model: P(transplant) vs P(mortality) vs P(delisting).

Models three competing events as independent exponential processes:
  1. Transplant — drawn from log-normal wait time distribution (from M2)
  2. Death on waitlist — exponential with organ/urgency/city-adjusted rate
  3. Delisting — exponential with organ/city-adjusted rate

The event that occurs first determines the outcome for each simulation iteration.
Rates sourced from data/competing-risks.json (OPTN/SRTR 2023 Annual Data Report).
"""
import json
import logging
import math
import threading
from functools import lru_cache
from pathlib import Path

from config import DATA_DIR

logger = logging.getLogger(__name__)

_RISKS: dict | None = None
_CITY_ADJUSTMENTS: dict[str, dict[str, float]] = {}
_lock = threading.Lock()


def _load_risks() -> tuple[dict, dict]:
    """Load competing risks parameters from JSON."""
    path = DATA_DIR / "competing-risks.json"
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    city_adj = raw.get("city_adjustments", {})
    city_adj = {k: v for k, v in city_adj.items() if k != "_notes"}

    organs = {}
    for organ in ("kidney", "liver", "heart", "lung", "pancreas", "intestine"):
        if organ in raw:
            organs[organ] = raw[organ]

    logger.info("Competing risks loaded for %d organs, %d cities", len(organs), len(city_adj))
    return organs, city_adj


def _ensure_loaded() -> None:
    """Lazy-load competing risks data on first call (thread-safe)."""
    global _RISKS, _CITY_ADJUSTMENTS
    if _RISKS is None:
        with _lock:
            if _RISKS is None:  # double-checked locking
                _RISKS, _CITY_ADJUSTMENTS = _load_risks()


# Issue #64: Use shared implementation from stats_utils
from services.stats_utils import get_range_multiplier as _get_range_multiplier


def _raw_center_adjustment(center_code: str, organ: str) -> dict[str, float]:
    """Raw (un-shrunk) per-organ mortality/delisting factors for a center."""
    from services.data_loader import get_data
    center_adj = get_data().center_competing_risks.get("center_adjustments", {})
    return center_adj.get(center_code, {}).get(organ, {})


def _shrink_factor(factor: float, n: int, K: float) -> float:
    """Empirical-Bayes shrinkage of a relative factor toward the baseline (1.0).

    Center factors are ratios to the organ baseline, so the natural shrinkage
    target is 1.0 (no center effect). We shrink in log space with weight
    w = n / (n + K): low-volume centers (small n) are pulled toward 1.0, while
    high-volume centers (n >> K) keep their observed factor. At n == K the
    weight is 0.5 (geometric half-way). K is the median cohort size for the
    organ (data-derived), so it is not a hand-tuned constant (#268)."""
    if factor <= 0 or n <= 0 or K <= 0:
        return factor
    w = n / (n + K)
    return math.exp(w * math.log(factor))


@lru_cache(maxsize=16)
def _shrinkage_K(organ: str) -> float:
    """Median observed cohort size (SRTR Table B7 n) across the organ's centers,
    used as the empirical-Bayes prior strength. Returns 0.0 (→ no shrinkage) if
    no per-center cohort data is available."""
    from services.data_loader import get_data
    d = get_data()
    ns = []
    for code in d.center_competing_risks.get("center_adjustments", {}):
        rec = d.observed_outcome(organ, code)
        if rec and rec.get("n"):
            ns.append(int(rec["n"]))
    if not ns:
        return 0.0
    ns.sort()
    return float(ns[len(ns) // 2])


def _center_adjustment(center_code: str, organ: str) -> dict[str, float]:
    """Per-organ mortality/delisting factors for a center, with empirical-Bayes
    shrinkage applied to stabilize noisy low-volume centers (#268)."""
    from services.data_loader import get_data
    raw = _raw_center_adjustment(center_code, organ)
    if not raw:
        return raw
    rec = get_data().observed_outcome(organ, center_code)
    n = int(rec["n"]) if rec and rec.get("n") else 0
    K = _shrinkage_K(organ)
    if not (n and K):
        return raw
    return {
        key: (_shrink_factor(val, n, K) if key in ("mortality_factor", "delisting_factor") else val)
        for key, val in raw.items()
    }


def get_annual_mortality_rate(
    organ: str,
    city: str = "",
    urgency: int = 2,
    meld: int | None = None,
    center_code: str = "",
) -> float:
    """
    Return adjusted annual mortality rate while on waitlist.

    Adjustments applied:
      - Urgency-specific multiplier (higher urgency -> higher mortality)
      - MELD-specific multiplier (liver only; higher MELD -> higher mortality)
      - Center or city factor (better hospitals -> lower mortality)
    """
    _ensure_loaded()

    organ_data = _RISKS.get(organ)
    if organ_data is None:
        return 0.08  # fallback

    base = organ_data["annual_mortality_rate"]

    # Urgency multiplier
    urg_mults = organ_data.get("urgency_mortality_multipliers", {})
    urg_mult = urg_mults.get(str(urgency), 1.0)

    # MELD multiplier (liver only)
    meld_mult = 1.0
    if organ == "liver" and meld is not None:
        meld_mults = organ_data.get("meld_mortality_multipliers", {})
        meld_mult = _get_range_multiplier(meld, meld_mults)

    # Location adjustment — prefer center-code, fall back to city
    if center_code:
        adj = _center_adjustment(center_code, organ)
        city_mult = adj.get("mortality_factor", 1.0)
    else:
        city_adj = _CITY_ADJUSTMENTS.get(city, {})
        city_mult = city_adj.get("mortality_factor", 1.0)

    return base * urg_mult * meld_mult * city_mult


def get_annual_delisting_rate(organ: str, city: str = "", center_code: str = "") -> float:
    """
    Return adjusted annual delisting rate (too sick, improved, non-compliant).
    """
    _ensure_loaded()

    organ_data = _RISKS.get(organ)
    if organ_data is None:
        return 0.05  # fallback

    base = organ_data["annual_delisting_rate"]

    if center_code:
        adj = _center_adjustment(center_code, organ)
        city_mult = adj.get("delisting_factor", 1.0)
    else:
        city_adj = _CITY_ADJUSTMENTS.get(city, {})
        city_mult = city_adj.get("delisting_factor", 1.0)

    return base * city_mult


def get_organ_risks(organ: str) -> dict | None:
    """Return raw risk parameters for an organ (for inspection/testing)."""
    _ensure_loaded()
    return _RISKS.get(organ)


def get_city_adjustments() -> dict[str, dict[str, float]]:
    """Return city adjustment factors (for inspection/testing)."""
    _ensure_loaded()
    return dict(_CITY_ADJUSTMENTS)
