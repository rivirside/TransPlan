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

    # Manual top-level age blocks (SRTR ADR Table 5.3). The #104 rewrite
    # dropped them from the file and their consumers silently defaulted to
    # 1.0 for months — validate-data.js now guards their presence.
    organs["_age_mortality_multipliers"] = raw.get("age_mortality_multipliers", {})
    organs["_age_organ_overrides"] = raw.get("age_organ_overrides", {})

    logger.info("Competing risks loaded for %d organs", len(organs) - 2)
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


def _age_bracket(age: int) -> str:
    if age < 35:
        return "18-34"
    elif age < 50:
        return "35-49"
    elif age < 65:
        return "50-64"
    return "65+"


def get_patient_mortality_multiplier(
    organ: str,
    age: int,
    urgency: int = 2,
    meld: int | None = None,
) -> float:
    """Patient-level waitlist-mortality multiplier: age x urgency x MELD.

    Single source for the modulators shared by the BBN option-B hybrid
    (#238) and any engine that scales a center-average death hazard to a
    specific patient. By construction the reference patient (age 50-64,
    urgency 2, MELD 15-25) returns exactly 1.0 — the anchor property the
    option-B tests pin.

    Deliberately EXCLUDES the center mortality factor (that is a property
    of the center, already in the observed vector being modulated) and the
    transplant hazard (the double-counting guard: WaitCategory carries the
    patient's wait signal).
    """
    _ensure_loaded()
    organ_data = _RISKS.get(organ, {})

    bracket = _age_bracket(age)
    overrides = _RISKS.get("_age_organ_overrides", {}).get(organ, {})
    base_age = _RISKS.get("_age_mortality_multipliers", {})
    age_mult = overrides.get(bracket, base_age.get(bracket, 1.0))
    if isinstance(age_mult, str):
        age_mult = 1.0

    urg_mults = organ_data.get("urgency_mortality_multipliers", {})
    urg_mult = urg_mults.get(str(urgency), 1.0)

    meld_mult = 1.0
    if organ == "liver" and meld is not None:
        meld_mults = organ_data.get("meld_mortality_multipliers", {})
        meld_mult = _get_range_multiplier(meld, meld_mults)

    return float(age_mult * urg_mult * meld_mult)


def _probability_to_hazard(p: float) -> float:
    """Annual event probability -> annual hazard rate: lambda = -ln(1 - p).

    The shipped base values are probabilities (the fraction of a cohort dying
    or being delisted within a year), not rates. `12 / p` is the right
    conversion for a rate and the wrong one for a probability.
    """
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        # A base probability of 1 is a data error, not a modelling choice; the
        # caller's zero-rate path already logs and handles degenerate inputs.
        return float("inf")
    return -math.log(1.0 - p)


def _hazard_to_probability(lam: float) -> float:
    """Annual hazard rate -> annual event probability, always in [0, 1)."""
    if lam <= 0.0:
        return 0.0
    return 1.0 - math.exp(-lam)


def _mortality_multiplier(organ_data: dict, organ: str, urgency: int,
                          meld: int | None, center_code: str) -> float:
    """The combined hazard ratio applied to an organ's base mortality."""
    urg_mult = organ_data.get("urgency_mortality_multipliers", {}).get(str(urgency), 1.0)

    meld_mult = 1.0
    if organ == "liver" and meld is not None:
        meld_mult = _get_range_multiplier(meld, organ_data.get("meld_mortality_multipliers", {}))

    # Location adjustment — center-code only (#293: 22-city fallback retired;
    # no code -> neutral 1.0, surfaced via data_quality provenance)
    city_mult = 1.0
    if center_code:
        city_mult = _center_adjustment(center_code, organ).get("mortality_factor", 1.0)

    return urg_mult * meld_mult * city_mult


def get_annual_mortality_hazard(
    organ: str,
    city: str = "",
    urgency: int = 2,
    meld: int | None = None,
    center_code: str = "",
) -> float:
    """Annual waitlist-mortality HAZARD for this patient at this center (#259).

    The multipliers are applied here rather than to the probability, because a
    mortality "multiplier" is a hazard ratio in the literature these values
    come from. Multiplying probabilities instead produced 1.1734 for liver at
    MELD 40 / urgency 4 — not a probability at all.

    This is what the simulation should consume: an exponential draw needs a
    rate, and `rate_to_exponential_scale` divides 12 by whatever it is handed.
    """
    _ensure_loaded()
    organ_data = _RISKS.get(organ)
    if organ_data is None:
        return _probability_to_hazard(0.08)  # fallback, as a hazard
    lam0 = _probability_to_hazard(organ_data["annual_mortality_rate"])
    return lam0 * _mortality_multiplier(organ_data, organ, urgency, meld, center_code)


def get_annual_delisting_hazard(organ: str, city: str = "", center_code: str = "") -> float:
    """Annual delisting HAZARD for this center (#259). See the mortality twin."""
    _ensure_loaded()
    organ_data = _RISKS.get(organ)
    if organ_data is None:
        return _probability_to_hazard(0.05)
    lam0 = _probability_to_hazard(organ_data["annual_delisting_rate"])
    city_mult = 1.0
    if center_code:
        city_mult = _center_adjustment(center_code, organ).get("delisting_factor", 1.0)
    return lam0 * city_mult


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

    return _hazard_to_probability(
        _probability_to_hazard(base) * urg_mult * meld_mult * city_mult)


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

    return _hazard_to_probability(_probability_to_hazard(base) * city_mult)


def get_organ_risks(organ: str) -> dict | None:
    """Return raw risk parameters for an organ (for inspection/testing)."""
    _ensure_loaded()
    return _RISKS.get(organ)

