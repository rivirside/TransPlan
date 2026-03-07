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

from config import SIMULATION_ITERATIONS
from models.schemas import CityProbability, PatientProfile, SimulationResult
from services.competing_risks import get_annual_mortality_rate, get_annual_delisting_rate
from services.distributions import get_wait_time_distribution

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
