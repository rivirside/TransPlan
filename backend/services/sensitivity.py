"""
Input parameter sensitivity analysis for transplant probability.

Measures how much p_transplant_24mo changes when clinical input parameters
are varied from their most favorable to least favorable values.

Parameters tested (organ-specific):
  - urgency (all organs): 1 → 4
  - cpra (kidney): 0 → 98
  - meld (liver): 7 → 38
  - las (lung): 20 → 85

Used to generate tornado charts for M7 validation.
"""
import logging
import time

import numpy as np

from config import COPULA_THETA, ORGAN_COPULA_THETA
from models.schemas import ParameterImpact, PatientProfile, SensitivityResult
from services.competing_risks import get_annual_delisting_rate, get_annual_mortality_rate
from services.copula import draw_correlated_competing_risks
from services.distributions import get_wait_time_distribution

logger = logging.getLogger(__name__)


def _p24_single_city(
    patient: PatientProfile,
    city: str,
    n_iterations: int,
    rng: np.random.Generator,
    center_code: str = "",
) -> float:
    """Run Monte Carlo for a single center/city and return p_transplant_24mo."""
    dist = get_wait_time_distribution(
        organ=patient.organ,
        blood_type=patient.blood_type,
        city=city,
        center_code=center_code,
        cpra=patient.cpra,
        meld=patient.meld,
        las=patient.las,
    )
    transplant_times = dist.rvs(size=n_iterations)

    annual_mort = get_annual_mortality_rate(
        organ=patient.organ,
        city=city,
        center_code=center_code,
        urgency=patient.urgency,
        meld=patient.meld,
    )
    mort_scale = 12.0 / annual_mort if annual_mort > 0 else 1e6

    annual_delist = get_annual_delisting_rate(organ=patient.organ, city=city, center_code=center_code)
    delist_scale = 12.0 / annual_delist if annual_delist > 0 else 1e6

    if patient.use_copula:
        mortality_times, delisting_times = draw_correlated_competing_risks(
            mort_scale=mort_scale,
            delist_scale=delist_scale,
            n=n_iterations,
            theta=ORGAN_COPULA_THETA.get(patient.organ, COPULA_THETA),
            rng=rng,
        )
    else:
        mortality_times = rng.exponential(scale=mort_scale, size=n_iterations)
        delisting_times = rng.exponential(scale=delist_scale, size=n_iterations)

    all_times = np.stack([transplant_times, mortality_times, delisting_times], axis=1)
    event_times = np.min(all_times, axis=1)
    outcomes = np.argmin(all_times, axis=1)

    return float(np.mean((outcomes == 0) & (event_times <= 24)))


def compute_sensitivity(
    patient: PatientProfile,
    city: str = "Nashville",
    n_iterations: int = 1000,
    center_code: str = "",
) -> SensitivityResult:
    """
    Compute input sensitivity for p_transplant_24mo for a single center/city.

    For each wired parameter, runs the simulation at the most favorable
    and least favorable extreme values and records the resulting p_transplant_24mo.
    Returns impacts sorted by magnitude (largest swing first).
    """
    start = time.perf_counter()

    # Validate center_code or city name
    from services.monte_carlo import _get_centers, _get_cities
    if center_code:
        from services.data_loader import get_data
        all_centers = get_data().all_centers.get("centers", {})
        if center_code not in all_centers:
            raise ValueError(f"Unknown center code: '{center_code}'")
        # Use center name as display label
        city = all_centers[center_code].get("name", city)
    else:
        valid_cities = {c["city"] for c in _get_cities()}
        if city not in valid_cities:
            # Also check center names
            pass  # Allow any city name through for backward compat

    rng = np.random.default_rng()
    baseline_p24 = _p24_single_city(patient, city, n_iterations, rng, center_code=center_code)
    impacts: list[ParameterImpact] = []
    organ = patient.organ

    # --- Urgency (all organs): higher urgency → higher mortality → lower p24 ---
    urg_low_patient = patient.model_copy(update={"urgency": 1})
    urg_high_patient = patient.model_copy(update={"urgency": 4})
    impacts.append(ParameterImpact(
        parameter="urgency",
        label="Medical Urgency",
        baseline_value=float(patient.urgency),
        low_value=1.0,
        high_value=4.0,
        p24_baseline=round(baseline_p24, 4),
        p24_at_low=round(_p24_single_city(urg_low_patient, city, n_iterations, rng, center_code=center_code), 4),
        p24_at_high=round(_p24_single_city(urg_high_patient, city, n_iterations, rng, center_code=center_code), 4),
    ))

    # --- Organ-specific clinical parameters ---
    if organ == "kidney":
        # High cPRA → longer wait (rare compatible donor) → lower p24
        cpra_low_patient = patient.model_copy(update={"cpra": 0})
        cpra_high_patient = patient.model_copy(update={"cpra": 98})
        impacts.append(ParameterImpact(
            parameter="cpra",
            label="Kidney Sensitization (cPRA %)",
            baseline_value=float(patient.cpra or 0),
            low_value=0.0,
            high_value=98.0,
            p24_baseline=round(baseline_p24, 4),
            p24_at_low=round(_p24_single_city(cpra_low_patient, city, n_iterations, rng, center_code=center_code), 4),
            p24_at_high=round(_p24_single_city(cpra_high_patient, city, n_iterations, rng, center_code=center_code), 4),
        ))

    elif organ == "liver":
        # High MELD → higher allocation priority (shorter wait) but also higher mortality
        # Net effect on p24 depends on balance; typically high MELD improves p24
        meld_low_patient = patient.model_copy(update={"meld": 7})
        meld_high_patient = patient.model_copy(update={"meld": 38})
        impacts.append(ParameterImpact(
            parameter="meld",
            label="Liver Disease Severity (MELD)",
            baseline_value=float(patient.meld or 15),
            low_value=7.0,
            high_value=38.0,
            p24_baseline=round(baseline_p24, 4),
            p24_at_low=round(_p24_single_city(meld_low_patient, city, n_iterations, rng, center_code=center_code), 4),
            p24_at_high=round(_p24_single_city(meld_high_patient, city, n_iterations, rng, center_code=center_code), 4),
        ))

    elif organ == "lung":
        # High LAS → higher allocation priority → shorter wait → higher p24
        las_low_patient = patient.model_copy(update={"las": 20.0})
        las_high_patient = patient.model_copy(update={"las": 85.0})
        impacts.append(ParameterImpact(
            parameter="las",
            label="Lung Allocation Score (LAS)",
            baseline_value=float(patient.las or 40.0),
            low_value=20.0,
            high_value=85.0,
            p24_baseline=round(baseline_p24, 4),
            p24_at_low=round(_p24_single_city(las_low_patient, city, n_iterations, rng, center_code=center_code), 4),
            p24_at_high=round(_p24_single_city(las_high_patient, city, n_iterations, rng, center_code=center_code), 4),
        ))

    # Sort by magnitude (largest swing first)
    impacts.sort(key=lambda x: abs(x.p24_at_high - x.p24_at_low), reverse=True)

    elapsed = time.perf_counter() - start
    logger.info(
        "Sensitivity complete: %s %s city=%s, %d impacts, %.2fs",
        patient.organ, patient.blood_type, city, len(impacts), elapsed,
    )

    return SensitivityResult(
        patient=patient,
        city=city,
        center_code=center_code,
        impacts=impacts,
        iterations=n_iterations,
        elapsed_seconds=round(elapsed, 3),
    )
