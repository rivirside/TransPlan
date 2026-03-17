"""
Monte Carlo simulation engine for transplant wait time forecasting.

Samples from per-city log-normal wait time distributions (M2) with
competing risks (M4) to produce:
  - P(transplant <= X months) at 6, 12, 24, 36 month horizons
  - Competing risks breakdown: P(transplant), P(mortality), P(delisting), P(still waiting)
  - 95% confidence intervals for the 24-month transplant probability
  - Median wait time per city
  - Rankings by 24-month transplant probability (descending)

For each iteration, three competing events are drawn independently:
  1. Transplant time ~ LogNormal (from M2 distributions)
  2. Mortality time ~ Exponential (from M4 competing risks)
  3. Delisting time ~ Exponential (from M4 competing risks)
The event that occurs first determines the outcome.
"""
import logging
import time

import numpy as np

from config import SIMULATION_ITERATIONS, SUPPLY_WAIT_ELASTICITY
from models.schemas import CityProbability, PatientProfile, SimulationResult
from services.competing_risks import get_annual_mortality_rate, get_annual_delisting_rate
from services.data_loader import get_data
from services.distributions import get_wait_time_distribution
from services.outcomes import build_outcomes_dict
from services.trends import get_city_trends

logger = logging.getLogger(__name__)

# 22 cities with state abbreviations — mirrors scripts/utils.js CITIES
CITIES = [
    {"city": "Pittsburgh", "state": "PA"},
    {"city": "Baltimore", "state": "MD"},
    {"city": "Philadelphia", "state": "PA"},
    {"city": "New York", "state": "NY"},
    {"city": "Minneapolis", "state": "MN"},
    {"city": "Madison", "state": "WI"},
    {"city": "Chicago", "state": "IL"},
    {"city": "Cleveland", "state": "OH"},
    {"city": "St. Louis", "state": "MO"},
    {"city": "Indianapolis", "state": "IN"},
    {"city": "Omaha", "state": "NE"},
    {"city": "Rochester", "state": "MN"},
    {"city": "Nashville", "state": "TN"},
    {"city": "Durham", "state": "NC"},
    {"city": "Miami", "state": "FL"},
    {"city": "Dallas", "state": "TX"},
    {"city": "Houston", "state": "TX"},
    {"city": "Portland", "state": "OR"},
    {"city": "Seattle", "state": "WA"},
    {"city": "San Francisco", "state": "CA"},
    {"city": "Los Angeles", "state": "CA"},
    {"city": "Palo Alto", "state": "CA"},
]

# State abbreviation to full name for cause-of-death data lookup
_STATE_FULL_NAMES = {
    "PA": "Pennsylvania", "MD": "Maryland", "NY": "New York",
    "MN": "Minnesota", "WI": "Wisconsin", "IL": "Illinois",
    "OH": "Ohio", "MO": "Missouri", "IN": "Indiana",
    "NE": "Nebraska", "TN": "Tennessee", "NC": "North Carolina",
    "FL": "Florida", "TX": "Texas", "OR": "Oregon",
    "WA": "Washington", "CA": "California",
}


def _get_cod_multiplier(state_abbrev: str, organ: str, *, n_samples: int = 0, rng: np.random.Generator | None = None) -> float | np.ndarray:
    """
    Compute organ-specific cause-of-death multiplier for Monte Carlo.

    Returns a value centered around 1.0. Values > 1.0 mean more donors
    available for this organ in this state → shorter waits (divide times).

    Uses PMC10329409 recovery rates × CDC state mortality proportions.
    Returns 1.0 (no adjustment) if data is unavailable.

    Parameters
    ----------
    state_abbrev : two-letter state code
    organ : organ name (e.g. "kidney")
    n_samples : if > 0, return an array of stochastic multiplier draws
        using Beta-distributed recovery rates. If 0, return deterministic float.
    rng : numpy random generator (required when n_samples > 0)
    """
    try:
        cod = get_data().cause_of_death
    except RuntimeError:
        return np.ones(n_samples) if n_samples > 0 else 1.0
    if not cod:
        return np.ones(n_samples) if n_samples > 0 else 1.0

    recovery_rates = cod.get("organRecoveryRates", {}).get(organ)
    state_name = _STATE_FULL_NAMES.get(state_abbrev)
    if not recovery_rates or not state_name:
        return np.ones(n_samples) if n_samples > 0 else 1.0

    proportions = cod.get("stateCauseOfDeathProportions", {}).get(state_name)
    if not proportions:
        return np.ones(n_samples) if n_samples > 0 else 1.0

    categories = ["trauma", "cardiovascular", "drug_intox", "stroke", "anoxia"]

    all_states = cod.get("stateCauseOfDeathProportions", {})
    if not all_states:
        return np.ones(n_samples) if n_samples > 0 else 1.0

    # Compute deterministic national average (used as normalizer in both modes)
    nat_total = sum(
        sum(sp.get(c, 0) * recovery_rates.get(c, 0) for c in categories)
        for sp in all_states.values()
    )
    nat_avg = nat_total / len(all_states)
    if nat_avg == 0:
        return np.ones(n_samples) if n_samples > 0 else 1.0

    if n_samples > 0 and rng is not None:
        # Stochastic mode: draw recovery rates from Beta distributions.
        # Beta(a, b) where a = rate * kappa, b = (1-rate) * kappa.
        # kappa (concentration) controls variance. Higher = tighter.
        # kappa=50 gives ~5-10% relative std dev for typical rates.
        KAPPA = 50.0
        state_scores = np.zeros(n_samples)

        for c in categories:
            rate = recovery_rates.get(c, 0)
            if rate <= 0 or rate >= 1:
                sampled = np.full(n_samples, rate)
            else:
                a = rate * KAPPA
                b = (1.0 - rate) * KAPPA
                sampled = rng.beta(a, b, size=n_samples)

            p_state = proportions.get(c, 0)
            state_scores += p_state * sampled

        # Normalize against deterministic national average so stochastic
        # variation in recovery rates propagates to the multiplier
        return state_scores / nat_avg
    else:
        # Deterministic mode (original behavior)
        state_score = sum(proportions.get(c, 0) * recovery_rates.get(c, 0) for c in categories)
        return state_score / nat_avg


def _bootstrap_ci(outcomes: np.ndarray, event: int, threshold_months: np.ndarray, time_horizon: float, confidence: float = 0.95, n_bootstrap: int = 200) -> tuple[float, float]:
    """
    Compute a bootstrap confidence interval for P(event occurs first AND within time_horizon).

    Parameters
    ----------
    outcomes : array of int (0=transplant, 1=death, 2=delisted)
    event : which event to compute CI for (0, 1, or 2)
    threshold_months : array of event times (min of the three draws)
    time_horizon : months cutoff
    """
    rng = np.random.default_rng()
    n = len(outcomes)
    proportions = np.empty(n_bootstrap)
    mask = (outcomes == event) & (threshold_months <= time_horizon)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        proportions[i] = np.mean(mask[idx])

    alpha = (1 - confidence) / 2
    lo = float(np.percentile(proportions, alpha * 100))
    hi = float(np.percentile(proportions, (1 - alpha) * 100))
    return (lo, hi)


def simulate(patient: PatientProfile, n_iterations: int | None = None) -> SimulationResult:
    """
    Run Monte Carlo simulation with competing risks for all 22 cities.

    For each city and iteration:
      1. Draw transplant_time from log-normal (M2)
      2. Draw mortality_time from exponential (annual rate → monthly scale)
      3. Draw delisting_time from exponential (annual rate → monthly scale)
      4. Outcome = whichever event occurs first

    Returns ranked cities with transplant probabilities, CIs, and
    competing risks breakdown at 24 months.
    """
    if n_iterations is None:
        n_iterations = SIMULATION_ITERATIONS

    start = time.perf_counter()
    rng = np.random.default_rng()
    city_results: list[CityProbability] = []

    for city_info in CITIES:
        city = city_info["city"]
        state = city_info["state"]

        # --- Draw transplant times from log-normal ---
        dist = get_wait_time_distribution(
            organ=patient.organ,
            blood_type=patient.blood_type,
            city=city,
            cpra=patient.cpra,
            meld=patient.meld,
            las=patient.las,
        )
        transplant_times = dist.rvs(size=n_iterations)

        # --- Apply organ-specific cause-of-death multiplier (M2) ---
        # Sublinear elasticity: wait_adj = multiplier ^ elasticity (L-056)
        if patient.adjust_for_cause_of_death:
            cod_mult = _get_cod_multiplier(
                state, patient.organ,
                n_samples=n_iterations, rng=rng,
            )
            # cod_mult is an array of per-iteration multipliers (stochastic)
            safe_mult = np.where(cod_mult > 0, cod_mult, 1.0)
            effective_mult = np.power(safe_mult, SUPPLY_WAIT_ELASTICITY)
            transplant_times = transplant_times / effective_mult

        # --- Draw mortality times from exponential ---
        annual_mort = get_annual_mortality_rate(
            organ=patient.organ, city=city, urgency=patient.urgency, meld=patient.meld,
        )
        # Convert annual rate to monthly: monthly_rate = annual_rate / 12
        # Exponential scale = 1/rate = 12/annual_rate (mean time in months)
        mort_scale = 12.0 / annual_mort if annual_mort > 0 else 1e6
        mortality_times = rng.exponential(scale=mort_scale, size=n_iterations)

        # --- Draw delisting times from exponential ---
        annual_delist = get_annual_delisting_rate(organ=patient.organ, city=city)
        delist_scale = 12.0 / annual_delist if annual_delist > 0 else 1e6
        delisting_times = rng.exponential(scale=delist_scale, size=n_iterations)

        # --- Determine outcome: which event occurs first ---
        all_times = np.stack([transplant_times, mortality_times, delisting_times], axis=1)
        event_times = np.min(all_times, axis=1)      # time of first event
        outcomes = np.argmin(all_times, axis=1)       # 0=transplant, 1=death, 2=delisted

        # --- Compute transplant probabilities (transplant occurs first AND within horizon) ---
        def p_transplant_within(horizon: float) -> float:
            return float(np.mean((outcomes == 0) & (event_times <= horizon)))

        p_6 = p_transplant_within(6)
        p_12 = p_transplant_within(12)
        p_24 = p_transplant_within(24)
        p_36 = p_transplant_within(36)

        # --- 95% CI for 24-month transplant probability ---
        ci_95 = _bootstrap_ci(outcomes, event=0, threshold_months=event_times, time_horizon=24)

        # --- Median wait to transplant (among those who got transplanted) ---
        transplanted_mask = outcomes == 0
        if np.any(transplanted_mask):
            median_wait = float(np.median(transplant_times[transplanted_mask]))
        else:
            median_wait = float(np.median(transplant_times))  # fallback

        # --- Competing risks breakdown at 24 months ---
        p_mort_24 = float(np.mean((outcomes == 1) & (event_times <= 24)))
        p_delist_24 = float(np.mean((outcomes == 2) & (event_times <= 24)))
        p_waiting_24 = float(np.mean(event_times > 24))

        competing_risks_24 = {
            "p_transplant_24mo": round(p_24, 4),
            "p_mortality_24mo": round(p_mort_24, 4),
            "p_delisting_24mo": round(p_delist_24, 4),
            "p_still_waiting_24mo": round(p_waiting_24, 4),
        }

        # Phase 4 M2: Attach post-transplant outcomes if available
        outcomes_data = None
        try:
            outcomes_data = build_outcomes_dict(organ, city, p_24)
        except Exception:
            pass  # Graceful degradation if outcomes data unavailable

        # Phase 4 M3: Attach historical trends if available
        trends_data = None
        try:
            trends_data = get_city_trends(organ, city)
        except Exception:
            pass  # Graceful degradation if trends data unavailable

        city_results.append(CityProbability(
            city=city,
            state=state,
            p_transplant_6mo=round(p_6, 4),
            p_transplant_12mo=round(p_12, 4),
            p_transplant_24mo=round(p_24, 4),
            p_transplant_36mo=round(p_36, 4),
            confidence_interval_95=(round(ci_95[0], 4), round(ci_95[1], 4)),
            median_wait_months=round(median_wait, 2),
            competing_risks=competing_risks_24,
            outcomes=outcomes_data,
            trends=trends_data,
        ))

    # Rank by 24-month transplant probability, descending
    city_results.sort(key=lambda c: c.p_transplant_24mo, reverse=True)

    elapsed = time.perf_counter() - start
    logger.info(
        "Simulation complete: %s %s, %d iterations, %.2fs",
        patient.organ, patient.blood_type, n_iterations, elapsed,
    )

    return SimulationResult(
        patient=patient,
        cities=city_results,
        iterations=n_iterations,
        elapsed_seconds=round(elapsed, 3),
    )
