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
import threading
from pathlib import Path

from config import DATA_DIR

logger = logging.getLogger(__name__)

_RISKS: dict | None = None
_lock = threading.Lock()


def _load_risks() -> dict:
    """Load competing risks parameters from JSON.

    (#293: the 22-city city_adjustments block was retired — location
    adjustment is center-code-based only.)
    """
    path = DATA_DIR / "competing-risks.json"
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    organs = {}
    for organ in ("kidney", "liver", "heart", "lung", "pancreas", "intestine"):
        if organ in raw:
            organs[organ] = raw[organ]

    logger.info("Competing risks loaded for %d organs", len(organs))
    return organs


def _ensure_loaded() -> None:
    """Lazy-load competing risks data on first call (thread-safe)."""
    global _RISKS
    if _RISKS is None:
        with _lock:
            if _RISKS is None:  # double-checked locking
                _RISKS = _load_risks()


# Issue #64: Use shared implementation from stats_utils
from services.stats_utils import get_range_multiplier as _get_range_multiplier


def _center_adjustment(center_code: str, organ: str) -> dict[str, float]:
    """Look up per-organ mortality/delisting factors for a center code."""
    from services.data_loader import get_data
    center_adj = get_data().center_competing_risks.get("center_adjustments", {})
    return center_adj.get(center_code, {}).get(organ, {})


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

    # Location adjustment — center-code only (#293: 22-city fallback retired;
    # no code → neutral 1.0, surfaced via data_quality provenance)
    city_mult = 1.0
    if center_code:
        adj = _center_adjustment(center_code, organ)
        city_mult = adj.get("mortality_factor", 1.0)

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

    city_mult = 1.0
    if center_code:
        adj = _center_adjustment(center_code, organ)
        city_mult = adj.get("delisting_factor", 1.0)

    return base * city_mult


def get_organ_risks(organ: str) -> dict | None:
    """Return raw risk parameters for an organ (for inspection/testing)."""
    _ensure_loaded()
    return _RISKS.get(organ)

