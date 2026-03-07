"""
Monte Carlo simulation engine for transplant wait time forecasting.

Samples from per-city log-normal wait time distributions (from M2) to produce:
  - P(transplant <= X months) at 6, 12, 24, 36 month horizons
  - 95% confidence intervals for the 24-month probability
  - Median wait time per city
  - Rankings by 24-month transplant probability (descending)
"""
import logging
import time

import numpy as np

from config import SIMULATION_ITERATIONS
from models.schemas import CityProbability, PatientProfile, SimulationResult
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


def _bootstrap_ci(samples: np.ndarray, threshold: float, confidence: float = 0.95, n_bootstrap: int = 200) -> tuple[float, float]:
    """
    Compute a bootstrap confidence interval for P(sample <= threshold).

    Uses percentile method with n_bootstrap resamples for speed.
    """
    rng = np.random.default_rng()
    n = len(samples)
    proportions = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        resample = rng.choice(samples, size=n, replace=True)
        proportions[i] = np.mean(resample <= threshold)

    alpha = (1 - confidence) / 2
    lo = float(np.percentile(proportions, alpha * 100))
    hi = float(np.percentile(proportions, (1 - alpha) * 100))
    return (lo, hi)


def simulate(patient: PatientProfile, n_iterations: int | None = None) -> SimulationResult:
    """
    Run Monte Carlo simulation for all 22 cities.

    For each city, draws n_iterations wait time samples from the city's
    log-normal distribution (parameterized by organ, blood type, city factor,
    and clinical score). Computes P(transplant <= X months) at four time
    horizons and ranks cities by 24-month probability.

    Parameters
    ----------
    patient : PatientProfile
        Patient clinical profile.
    n_iterations : int, optional
        Number of Monte Carlo iterations per city. Defaults to config value (1000).

    Returns
    -------
    SimulationResult
        Ranked list of cities with transplant probabilities and CIs.
    """
    if n_iterations is None:
        n_iterations = SIMULATION_ITERATIONS

    start = time.perf_counter()
    city_results: list[CityProbability] = []

    for city_info in CITIES:
        city = city_info["city"]
        state = city_info["state"]

        dist = get_wait_time_distribution(
            organ=patient.organ,
            blood_type=patient.blood_type,
            city=city,
            cpra=patient.cpra,
            meld=patient.meld,
            las=patient.las,
        )

        # Vectorized sampling — fast
        samples = dist.rvs(size=n_iterations)

        # Compute probabilities at time horizons
        p_6 = float(np.mean(samples <= 6))
        p_12 = float(np.mean(samples <= 12))
        p_24 = float(np.mean(samples <= 24))
        p_36 = float(np.mean(samples <= 36))

        # 95% CI for 24-month probability via bootstrap
        ci_95 = _bootstrap_ci(samples, threshold=24)

        median_wait = float(np.median(samples))

        city_results.append(CityProbability(
            city=city,
            state=state,
            p_transplant_6mo=round(p_6, 4),
            p_transplant_12mo=round(p_12, 4),
            p_transplant_24mo=round(p_24, 4),
            p_transplant_36mo=round(p_36, 4),
            confidence_interval_95=(round(ci_95[0], 4), round(ci_95[1], 4)),
            median_wait_months=round(median_wait, 2),
            competing_risks=None,  # FIXME (Milestone 4): integrate competing risks
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
