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


def _gamma_poisson_eb(events: list[float], exposure: list[float]) -> list[float]:
    """Gamma-Poisson empirical-Bayes shrinkage of per-unit rates.

    Model: events_i ~ Poisson(mu_i * E_i), with the unknown true rates drawn
    from a shared prior mu_i ~ Gamma(alpha, beta). The Gamma prior's mean
    m = alpha/beta and variance sigma2 = alpha/beta**2 are estimated from the
    data by method of moments (DerSimonian-Laird):

        m      = sum(events) / sum(E)                      # pooled rate
        sigma2 = max(0, (Q - N*m) / sum(E)),  Q = sum_i E_i*(events_i/E_i - m)^2

    (Q's expectation under no between-unit variance is N*m, since the Poisson
    sampling variance of r_i = events_i/E_i is ~ m/E_i and E_i * m/E_i = m.)

    Returns the posterior-mean RATE RATIO mu_i / m for each unit:
        ratio_i = (events_i + alpha) / (E_i + beta) / m
    High-exposure units keep their observed ratio; low-information units (small
    E_i, few/zero events) shrink toward 1.0. If there is no detectable
    between-unit variance (sigma2 == 0) every unit collapses to 1.0.
    """
    tot_E = sum(exposure)
    tot_ev = sum(events)
    N = len(events)
    if tot_E <= 0 or tot_ev <= 0 or N == 0:
        return [1.0] * N
    m = tot_ev / tot_E
    Q = sum(e * ((ev / e) - m) ** 2 for ev, e in zip(events, exposure) if e > 0)
    sigma2 = max(0.0, (Q - N * m) / tot_E)
    if sigma2 <= 1e-12:
        return [1.0] * N  # no real between-center signal → full pooling
    beta = m / sigma2
    alpha = m * m / sigma2
    return [((ev + alpha) / (e + beta)) / m for ev, e in zip(events, exposure)]


@lru_cache(maxsize=16)
def _eb_factor_table(organ: str) -> dict[str, dict[str, float]]:
    """Per-center EB-shrunk mortality/delisting factors for an organ, computed
    from the RAW observed rates + cohort size (data_loader.observed_outcome) —
    NOT the clamped ratios in competing-risks-centers.json (#268).

    Exposure E_i = n_i / 100 (cohort as a patient-time proxy); reconstructed
    events_i = rate_i * E_i. Shrinkage strength is derived entirely from the
    data via _gamma_poisson_eb. This dissolves the artificial pile-ups the old
    [0.3, 3.0] clamp produced (e.g. zero-death small centers, which now shrink
    to ~1.0 instead of the 0.3 floor)."""
    from services.data_loader import get_data
    d = get_data()
    rows = []
    for code in d.center_competing_risks.get("center_adjustments", {}):
        rec = d.observed_outcome(organ, code)
        if rec and rec.get("n") and int(rec["n"]) > 0:
            rows.append((
                code,
                int(rec["n"]) / 100.0,                       # exposure
                float(rec.get("waitlist_death_rate") or 0.0),
                float(rec.get("delisting_rate") or 0.0),
            ))
    if not rows:
        return {}
    exposure = [r[1] for r in rows]
    mort_ratio = _gamma_poisson_eb([r[2] * r[1] for r in rows], exposure)
    delist_ratio = _gamma_poisson_eb([r[3] * r[1] for r in rows], exposure)
    return {
        r[0]: {"mortality_factor": mort_ratio[i], "delisting_factor": delist_ratio[i]}
        for i, r in enumerate(rows)
    }


def _center_adjustment(center_code: str, organ: str) -> dict[str, float]:
    """Per-organ mortality/delisting factors for a center. Uses the empirical-
    Bayes estimate (from raw rates) where observed data exists (#268), falling
    back to the stored clamped ratio for centers without observed outcomes."""
    table = _eb_factor_table(organ)
    if center_code in table:
        return table[center_code]
    return _raw_center_adjustment(center_code, organ)


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
