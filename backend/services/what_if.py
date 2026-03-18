"""
What-if scenario analysis: re-run Monte Carlo with adjusted model assumptions.

Unlike sensitivity analysis (which varies patient parameters at extremes),
what-if analysis varies *model assumptions* — things like donor availability
and base wait time — using continuous multipliers.

Both baseline and adjusted runs use the SAME random seed for paired comparison,
reducing noise and making the delta attributable to the multiplier change alone.
"""
import logging
import time

import numpy as np
from pydantic import BaseModel, Field

from models.schemas import PatientProfile
from services.competing_risks import get_annual_delisting_rate, get_annual_mortality_rate
from services.copula import draw_correlated_competing_risks
from services.distributions import get_wait_time_distribution
from config import COPULA_THETA, SUPPLY_WAIT_ELASTICITY
from services.monte_carlo import CITIES, _get_cod_multiplier

logger = logging.getLogger(__name__)


class WhatIfResult(BaseModel):
    city: str
    state: str
    donor_rate_multiplier: float
    wait_time_multiplier: float
    baseline_p24: float = Field(ge=0, le=1)
    adjusted_p24: float = Field(ge=0, le=1)
    delta_p24: float = Field(description="adjusted_p24 - baseline_p24")
    baseline_ci_95: tuple[float, float]
    adjusted_ci_95: tuple[float, float]
    baseline_median_wait: float
    adjusted_median_wait: float
    iterations: int
    elapsed_seconds: float


def _run_single(
    patient: PatientProfile,
    city: str,
    state: str,
    n_iterations: int,
    rng: np.random.Generator,
    donor_rate_multiplier: float = 1.0,
    wait_time_multiplier: float = 1.0,
) -> dict:
    """
    Run Monte Carlo for a single city with optional multipliers.

    Returns dict with p24, ci_95, median_wait.

    Multiplier mechanics (same as main simulate engine):
      - donor_rate_multiplier divides transplant_times: >1 = more donors = shorter waits
      - wait_time_multiplier multiplies the log-normal mu (location) parameter:
        >1 = longer base waits, <1 = shorter base waits
    """
    dist = get_wait_time_distribution(
        organ=patient.organ,
        blood_type=patient.blood_type,
        city=city,
        cpra=patient.cpra,
        meld=patient.meld,
        las=patient.las,
    )

    # Apply wait_time_multiplier by scaling the distribution's scale parameter.
    # distributions.py returns scipy.stats.lognorm(s=sigma, scale=adjusted_median).
    # For lognorm, scale IS the median. Multiplying scale by k shifts the entire
    # distribution proportionally — a 1.2× multiplier makes median 20% longer.
    if wait_time_multiplier != 1.0:
        import scipy.stats
        # Frozen lognorm: when created with keyword args, both s and scale are in kwds
        s = dist.args[0] if dist.args else dist.kwds.get('s', 1.0)
        loc = dist.kwds.get('loc', 0)
        scale = dist.kwds.get('scale', 1.0)
        dist = scipy.stats.lognorm(s=s, loc=loc, scale=scale * wait_time_multiplier)

    transplant_times = dist.rvs(size=n_iterations, random_state=rng)

    # Apply COD multiplier if enabled (same as main engine — stochastic Beta)
    # Sublinear elasticity: wait_adj = multiplier ^ elasticity (L-056)
    if patient.adjust_for_cause_of_death:
        cod_mult = _get_cod_multiplier(
            state, patient.organ,
            n_samples=n_iterations, rng=rng,
        )
        safe_mult = np.where(cod_mult > 0, cod_mult, 1.0)
        effective_mult = np.power(safe_mult, SUPPLY_WAIT_ELASTICITY)
        transplant_times = transplant_times / effective_mult

    # Apply donor rate multiplier: more donors → shorter waits
    # Same sublinear elasticity applies (L-056)
    if donor_rate_multiplier != 1.0 and donor_rate_multiplier > 0:
        effective_donor = donor_rate_multiplier ** SUPPLY_WAIT_ELASTICITY
        transplant_times = transplant_times / effective_donor

    # Draw mortality & delisting times
    annual_mort = get_annual_mortality_rate(
        organ=patient.organ, city=city, urgency=patient.urgency, meld=patient.meld,
    )
    mort_scale = 12.0 / annual_mort if annual_mort > 0 else 1e6

    annual_delist = get_annual_delisting_rate(organ=patient.organ, city=city)
    delist_scale = 12.0 / annual_delist if annual_delist > 0 else 1e6

    if patient.use_copula:
        mortality_times, delisting_times = draw_correlated_competing_risks(
            mort_scale=mort_scale,
            delist_scale=delist_scale,
            n=n_iterations,
            theta=COPULA_THETA,
            rng=rng,
        )
    else:
        mortality_times = rng.exponential(scale=mort_scale, size=n_iterations)
        delisting_times = rng.exponential(scale=delist_scale, size=n_iterations)

    # Competing risks: which event occurs first
    all_times = np.stack([transplant_times, mortality_times, delisting_times], axis=1)
    event_times = np.min(all_times, axis=1)
    outcomes = np.argmin(all_times, axis=1)

    # p_transplant_24mo
    p24 = float(np.mean((outcomes == 0) & (event_times <= 24)))

    # Bootstrap CI for p24
    mask = (outcomes == 0) & (event_times <= 24)
    boot_rng = np.random.default_rng()
    n = len(outcomes)
    proportions = np.empty(200)
    for i in range(200):
        idx = boot_rng.integers(0, n, size=n)
        proportions[i] = np.mean(mask[idx])
    ci_lo = float(np.percentile(proportions, 2.5))
    ci_hi = float(np.percentile(proportions, 97.5))

    # Median wait among transplanted
    transplanted_mask = outcomes == 0
    if np.any(transplanted_mask):
        median_wait = float(np.median(transplant_times[transplanted_mask]))
    else:
        median_wait = float(np.median(transplant_times))

    return {
        "p24": round(p24, 4),
        "ci_95": (round(ci_lo, 4), round(ci_hi, 4)),
        "median_wait": round(median_wait, 2),
    }


def compute_what_if(
    patient: PatientProfile,
    city: str = "Nashville",
    donor_rate_multiplier: float = 1.0,
    wait_time_multiplier: float = 1.0,
    n_iterations: int = 500,
) -> WhatIfResult:
    """
    Run what-if analysis: baseline vs adjusted Monte Carlo for a single city.

    Uses paired random seeds so the only difference between baseline and adjusted
    results is the multiplier — this minimizes Monte Carlo noise in the delta.
    """
    start = time.perf_counter()

    # Look up state for this city
    state = "TN"  # default
    for c in CITIES:
        if c["city"] == city:
            state = c["state"]
            break

    # Use paired seeds for baseline vs adjusted comparison
    seed = np.random.SeedSequence()
    seed_baseline, seed_adjusted = seed.spawn(2)

    # Baseline run (multipliers = 1.0)
    baseline = _run_single(
        patient=patient,
        city=city,
        state=state,
        n_iterations=n_iterations,
        rng=np.random.default_rng(seed_baseline),
        donor_rate_multiplier=1.0,
        wait_time_multiplier=1.0,
    )

    # Adjusted run (with user's multipliers)
    adjusted = _run_single(
        patient=patient,
        city=city,
        state=state,
        n_iterations=n_iterations,
        rng=np.random.default_rng(seed_adjusted),
        donor_rate_multiplier=donor_rate_multiplier,
        wait_time_multiplier=wait_time_multiplier,
    )

    elapsed = time.perf_counter() - start
    logger.info(
        "What-if complete: %s %s city=%s donor=%.2f wait=%.2f → Δp24=%.4f (%.2fs)",
        patient.organ, patient.blood_type, city,
        donor_rate_multiplier, wait_time_multiplier,
        adjusted["p24"] - baseline["p24"], elapsed,
    )

    return WhatIfResult(
        city=city,
        state=state,
        donor_rate_multiplier=donor_rate_multiplier,
        wait_time_multiplier=wait_time_multiplier,
        baseline_p24=baseline["p24"],
        adjusted_p24=adjusted["p24"],
        delta_p24=round(adjusted["p24"] - baseline["p24"], 4),
        baseline_ci_95=baseline["ci_95"],
        adjusted_ci_95=adjusted["ci_95"],
        baseline_median_wait=baseline["median_wait"],
        adjusted_median_wait=adjusted["median_wait"],
        iterations=n_iterations,
        elapsed_seconds=round(elapsed, 3),
    )
