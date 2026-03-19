"""
Demographic equity analysis for transplant probability.

Runs Monte Carlo simulations across a matrix of demographic profiles
(blood type × age bracket × sex) to surface disparities in model-predicted
outcomes. Computes Gini coefficient as inequality metric per city and overall.

Design decisions:
  - No race/ethnicity: simulate underlying clinical drivers instead.
  - No insurance: field exists on PatientProfile but is unused by Monte Carlo.
  - Gini over Theil for MVP: simpler, widely understood.
  - Mandatory disclaimers on every response.
"""
import logging
import time
from collections import defaultdict

import numpy as np

from models.schemas import CityEquity, EquityAnalysisResult, PatientProfile
from services.monte_carlo import CITIES
from services.sensitivity import _p24_single_city

logger = logging.getLogger(__name__)

# --- Stratification dimensions ---

AGE_BRACKETS = [
    {"label": "18-34", "representative_age": 26},
    {"label": "35-54", "representative_age": 45},
    {"label": "55-70", "representative_age": 62},
]

BLOOD_TYPES = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]

SEXES = ["male", "female"]

# --- Mandatory disclaimers ---

EQUITY_DISCLAIMERS = [
    (
        "This equity simulation varies blood type, age, and sex while holding "
        "clinical parameters fixed. It does not model race, ethnicity, "
        "socioeconomic status, or insurance type."
    ),
    (
        "Competing risks (waitlist mortality and delisting) are not stratified "
        "by demographics in the current model. Older patients face higher actual "
        "mortality that is not captured in these disparity estimates."
    ),
    (
        "Insurance type is not currently modeled. Medicaid vs. private insurance "
        "access differences are a known driver of transplant disparities not "
        "reflected here."
    ),
    (
        "These results show how the simulation model responds to demographic "
        "inputs, not observed real-world disparities. Actual disparities may be "
        "larger due to factors outside this model (referral bias, evaluation "
        "criteria, social determinants of health)."
    ),
]


def _gini(values: np.ndarray) -> float:
    """Compute Gini coefficient. 0 = perfect equality, 1 = total inequality."""
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or np.sum(values) == 0:
        return 0.0
    s = np.sort(values)
    n = len(s)
    idx = np.arange(1, n + 1)
    return float((2 * np.sum(idx * s) - (n + 1) * np.sum(s)) / (n * np.sum(s)))


def _simulate_profile_city(
    patient: PatientProfile,
    city: str,
    n_iterations: int,
    rng: np.random.Generator,
) -> tuple[float, float]:
    """
    Run lightweight Monte Carlo for one profile + one city.

    Returns (p_transplant_24mo, median_wait_months).
    Reuses _p24_single_city for p24 and computes median wait from
    the distribution directly (faster than re-simulating).
    """
    from services.distributions import get_wait_time_distribution

    p24 = _p24_single_city(patient, city, n_iterations, rng)

    # Compute median wait from the distribution (log-normal median = exp(mu))
    # Issue #48: pass age/sex so demographic multipliers affect the distribution
    dist = get_wait_time_distribution(
        organ=patient.organ,
        blood_type=patient.blood_type,
        city=city,
        cpra=patient.cpra,
        meld=patient.meld,
        las=patient.las,
        age=patient.age,
        sex=patient.sex,
    )
    median_wait = float(dist.median())

    return p24, median_wait


def compute_equity_analysis(
    patient: PatientProfile,
    n_iterations: int = 300,
) -> EquityAnalysisResult:
    """
    Run equity analysis across 48 demographic profiles × 22 cities.

    Varies blood_type (8), age (3 brackets), sex (2) while preserving
    the patient's organ, urgency, cpra/meld/las, and COD toggle.
    """
    start = time.perf_counter()
    rng = np.random.default_rng(42)  # Fixed seed for reproducibility

    # --- Generate profile variants ---
    profiles = []
    for bt in BLOOD_TYPES:
        for ab in AGE_BRACKETS:
            for sex in SEXES:
                variant = patient.model_copy(update={
                    "blood_type": bt,
                    "age": ab["representative_age"],
                    "sex": sex,
                })
                profiles.append({
                    "patient": variant,
                    "blood_type": bt,
                    "age_bracket": ab["label"],
                    "sex": sex,
                })

    logger.info(
        "Equity analysis: %s, %d profiles × %d cities × %d iter",
        patient.organ, len(profiles), len(CITIES), n_iterations,
    )

    # --- Simulate all profiles × all cities ---
    # Structure: city_results[city] = list of (p24, median_wait, profile_info)
    city_results: dict[str, list] = defaultdict(list)
    all_p24_values = []

    for city_info in CITIES:
        city = city_info["city"]
        for profile in profiles:
            p24, median_wait = _simulate_profile_city(
                profile["patient"], city, n_iterations, rng,
            )
            city_results[city].append({
                "p24": p24,
                "median_wait": median_wait,
                "blood_type": profile["blood_type"],
                "age_bracket": profile["age_bracket"],
                "sex": profile["sex"],
            })
            all_p24_values.append(p24)

    # --- Compute per-city equity metrics ---
    city_equities = []
    for city_info in CITIES:
        city = city_info["city"]
        state = city_info["state"]
        results = city_results[city]

        p24_vals = np.array([r["p24"] for r in results])
        wait_vals = np.array([r["median_wait"] for r in results])

        # Gini coefficient
        gini = _gini(p24_vals)

        # Ranges
        p24_range = (float(np.min(p24_vals)), float(np.max(p24_vals)))
        wait_range = (float(np.min(wait_vals)), float(np.max(wait_vals)))

        # Per-dimension averages
        dim_disparities: dict[str, list[dict]] = {}
        for dim_key in ["blood_type", "age_bracket", "sex"]:
            groups: dict[str, list] = defaultdict(list)
            wait_groups: dict[str, list] = defaultdict(list)
            for r in results:
                groups[r[dim_key]].append(r["p24"])
                wait_groups[r[dim_key]].append(r["median_wait"])

            dim_disparities[dim_key] = [
                {
                    "value": val,
                    "p24": round(float(np.mean(p24s)), 4),
                    "median_wait": round(float(np.mean(wait_groups[val])), 1),
                }
                for val, p24s in sorted(groups.items())
            ]

        city_equities.append(CityEquity(
            city=city,
            state=state,
            gini_coefficient=round(gini, 4),
            p24_range=(round(p24_range[0], 4), round(p24_range[1], 4)),
            median_wait_range=(round(wait_range[0], 1), round(wait_range[1], 1)),
            dimension_disparities=dim_disparities,
        ))

    # Sort by Gini ascending (most equitable first)
    city_equities.sort(key=lambda c: c.gini_coefficient)

    # Overall Gini
    overall_gini = _gini(np.array(all_p24_values))

    elapsed = time.perf_counter() - start
    logger.info(
        "Equity analysis complete: %s, %d profiles, overall Gini=%.4f, %.2fs",
        patient.organ, len(profiles), overall_gini, elapsed,
    )

    return EquityAnalysisResult(
        organ=patient.organ,
        cities=city_equities,
        overall_gini=round(overall_gini, 4),
        profiles_simulated=len(profiles),
        iterations_per_profile=n_iterations,
        elapsed_seconds=round(elapsed, 3),
        disclaimers=EQUITY_DISCLAIMERS,
    )
