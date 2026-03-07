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
from pathlib import Path

from config import DATA_DIR

logger = logging.getLogger(__name__)

_RISKS: dict | None = None
_CITY_ADJUSTMENTS: dict[str, dict[str, float]] = {}


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
    global _RISKS, _CITY_ADJUSTMENTS
    if _RISKS is None:
        _RISKS, _CITY_ADJUSTMENTS = _load_risks()


def _get_range_multiplier(value: int | float, ranges: dict[str, float]) -> float:
    """Look up a multiplier from a range-keyed dict (e.g. '6-14': 0.5)."""
    for range_key, multiplier in ranges.items():
        parts = range_key.split("-")
        if len(parts) == 2:
            lo, hi = float(parts[0]), float(parts[1])
            if lo <= value <= hi:
                return multiplier
    return 1.0


def get_annual_mortality_rate(
    organ: str,
    city: str,
    urgency: int,
    meld: int | None = None,
) -> float:
    """
    Return adjusted annual mortality rate while on waitlist.

    Adjustments applied:
      - Urgency-specific multiplier (higher urgency → higher mortality)
      - MELD-specific multiplier (liver only; higher MELD → higher mortality)
      - City factor (better hospitals → lower mortality)
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

    # City adjustment
    city_adj = _CITY_ADJUSTMENTS.get(city, {})
    city_mult = city_adj.get("mortality_factor", 1.0)

    return base * urg_mult * meld_mult * city_mult


def get_annual_delisting_rate(organ: str, city: str) -> float:
    """
    Return adjusted annual delisting rate (too sick, improved, non-compliant).
    """
    _ensure_loaded()

    organ_data = _RISKS.get(organ)
    if organ_data is None:
        return 0.05  # fallback

    base = organ_data["annual_delisting_rate"]

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
