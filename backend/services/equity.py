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
from services.monte_carlo import CITIES, _get_centers, _get_cities
from services.sensitivity import _p24_single_city
from services.competing_risks import get_annual_mortality_rate, get_annual_delisting_rate
from services.stats_utils import rate_to_exponential_scale

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
    (
        "Transplant probabilities are computed in closed form (the competing-"
        "risks integral over the wait-time distribution), so all centers are "
        "analyzed with no sampling. Mortality–delisting correlation (the optional "
        "copula) is omitted; it shifts centers near-uniformly and does not "
        "materially affect the Gini disparity metric."
    ),
]


# Issue #64: Use shared implementation from stats_utils
from services.stats_utils import gini as _gini


def _simulate_profile_center(
    patient: PatientProfile,
    city: str,
    n_iterations: int,
    rng: np.random.Generator,
    center_code: str = "",
) -> tuple[float, float]:
    """
    Run lightweight Monte Carlo for one profile + one center/city.

    Returns (p_transplant_24mo, median_wait_months).
    Reuses _p24_single_city for p24 and computes median wait from
    the distribution directly (faster than re-simulating).
    """
    from services.distributions import get_wait_time_distribution

    p24 = _p24_single_city(patient, city, n_iterations, rng, center_code=center_code)

    dist = get_wait_time_distribution(
        organ=patient.organ,
        blood_type=patient.blood_type,
        city=city,
        center_code=center_code,
        cpra=patient.cpra,
        meld=patient.meld,
        las=patient.las,
        age=patient.age,
        sex=patient.sex,
    )
    median_wait = float(dist.median())

    return p24, median_wait


# Fixed integration grid over [0, 24] months for the closed-form p24 (#216).
# 241 points (~0.1-month spacing) integrated by the trapezoid rule — the
# log-normal × exponential integrand is smooth, so this matches adaptive quad
# to ~1e-4 while being a single vectorized pdf evaluation.
_P24_GRID = np.linspace(0.0, 24.0, 241)


def _grid_p24(dist, inv_total: float) -> float:
    """∫₀²⁴ f_T(t)·exp(-(λ_M+λ_D)·t) dt by vectorized trapezoid integration.

    f_T = wait-time pdf; exp(-inv_total·t) = joint survival of the two
    (independent, exponential) competing risks. Probability that transplant
    occurs first AND within 24 months.
    """
    integrand = dist.pdf(_P24_GRID) * np.exp(-inv_total * _P24_GRID)
    # np.trapezoid (numpy>=2) with np.trapz fallback (numpy<2).
    _trapz = getattr(np, "trapezoid", None) or np.trapz
    return float(np.clip(_trapz(integrand, _P24_GRID), 0.0, 1.0))


def compute_equity_analysis(
    patient: PatientProfile,
    n_iterations: int = 200,
    seed: int | None = None,
    max_centers: int | None = None,
) -> EquityAnalysisResult:
    """
    Run equity analysis across 48 demographic profiles × centers
    for the patient's organ.

    Varies blood_type (8), age (3 brackets), sex (2) while preserving
    the patient's organ, urgency, cpra/meld/las, and COD toggle.

    p_transplant_24mo is computed in CLOSED FORM (#216) — the competing-risks
    integral, not Monte Carlo — so the FULL center set (up to 248) is feasible
    with no sampling and no noise. The old MC approach forced a 30-center cap
    (248×48×1000 ≈ 11.9M draws), which silently analyzed a sample while
    presenting as comprehensive. `n_iterations` is now ignored (kept for API
    compatibility); `max_centers=None` means all centers (set an int only to
    cap deliberately).
    """
    start = time.perf_counter()
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 2**31))

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

    centers = _get_centers(patient.organ)

    # Optional deliberate cap (default: analyze ALL centers — analytic p24 makes
    # this feasible, so no silent sampling).
    if max_centers is not None and len(centers) > max_centers:
        sorted_centers = sorted(centers, key=lambda c: c.get("wait_time_factor", 1.0))
        centers = sorted_centers[:max_centers]

    logger.info(
        "Equity analysis (analytic): %s, %d profiles x %d centers",
        patient.organ, len(profiles), len(centers),
    )

    # --- Evaluate all profiles × all centers (closed form) ---
    center_results: dict[str, list] = defaultdict(list)
    all_p24_values = []

    from services.distributions import get_wait_time_distribution, _age_sex_multiplier

    for center in centers:
        code = center.get("code", "")
        display = center.get("name", center.get("city", ""))

        # Mortality/delisting depend on (organ, center, urgency, meld) — all FIXED
        # across the 48 profiles — so the combined competing hazard is computed
        # ONCE per center.
        rep = profiles[0]["patient"]
        annual_mort = get_annual_mortality_rate(
            organ=rep.organ, city=display, center_code=code,
            urgency=rep.urgency, meld=rep.meld,
        )
        annual_delist = get_annual_delisting_rate(
            organ=rep.organ, city=display, center_code=code,
        )
        mort_scale = rate_to_exponential_scale(annual_mort, "mortality", code or display)
        delist_scale = rate_to_exponential_scale(annual_delist, "delisting", code or display)
        inv_total = 1.0 / mort_scale + 1.0 / delist_scale

        # p24 and base median depend only on blood type (age/sex enter median via a
        # scalar multiplier; the current model does not vary p24 by age/sex). So
        # compute 8 distributions per center, not 48 — then map the 48 profiles.
        bt_p24: dict[str, float] = {}
        bt_median: dict[str, float] = {}
        for bt in BLOOD_TYPES:
            dist = get_wait_time_distribution(
                organ=rep.organ, blood_type=bt, city=display, center_code=code,
                cpra=rep.cpra, meld=rep.meld, las=rep.las,
            )
            bt_p24[bt] = _grid_p24(dist, inv_total)
            bt_median[bt] = float(dist.median())

        for profile in profiles:
            bt = profile["blood_type"]
            p24 = bt_p24[bt]
            median_wait = bt_median[bt] * _age_sex_multiplier(
                rep.organ, profile["patient"].age, profile["sex"])
            center_results[code or display].append({
                "p24": p24,
                "median_wait": median_wait,
                "blood_type": bt,
                "age_bracket": profile["age_bracket"],
                "sex": profile["sex"],
            })
            all_p24_values.append(p24)

    # --- Compute per-center equity metrics ---
    city_equities = []
    for center in centers:
        code = center.get("code", "")
        key = code or center.get("name", center.get("city", ""))
        display = center.get("name", center.get("city", ""))
        state = center.get("state", center.get("state_abbr", ""))
        results = center_results[key]

        p24_vals = np.array([r["p24"] for r in results])
        wait_vals = np.array([r["median_wait"] for r in results])

        gini = _gini(p24_vals)
        p24_range = (float(np.min(p24_vals)), float(np.max(p24_vals)))
        wait_range = (float(np.min(wait_vals)), float(np.max(wait_vals)))

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
            city=display,
            state=state,
            center_code=code,
            center_name=display,
            gini_coefficient=round(gini, 4),
            p24_range=(round(p24_range[0], 4), round(p24_range[1], 4)),
            median_wait_range=(round(wait_range[0], 1), round(wait_range[1], 1)),
            dimension_disparities=dim_disparities,
        ))

    city_equities.sort(key=lambda c: c.gini_coefficient)
    overall_gini = _gini(np.array(all_p24_values))

    elapsed = time.perf_counter() - start
    logger.info(
        "Equity analysis complete: %s, %d profiles x %d centers, overall Gini=%.4f, %.2fs",
        patient.organ, len(profiles), len(centers), overall_gini, elapsed,
    )

    return EquityAnalysisResult(
        organ=patient.organ,
        cities=city_equities,
        overall_gini=round(overall_gini, 4),
        profiles_simulated=len(profiles),
        iterations_per_profile=0,  # 0 = analytic (closed-form, no Monte Carlo sampling)
        elapsed_seconds=round(elapsed, 3),
        disclaimers=EQUITY_DISCLAIMERS,
        seed_used=seed,
    )
