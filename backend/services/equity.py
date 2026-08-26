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
from services.monte_carlo import _get_centers
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

# #335: SRTR's own pediatric age bands (Tables B8-B9). A pediatric candidate
# swept over the ADULT brackets above would be silently aged into a 26-, 45-
# and 62-year-old and scored against the adult center set — the equity result
# would describe a population the patient is not in.
PEDIATRIC_AGE_BRACKETS = [
    {"label": "0-1", "representative_age": 1},
    {"label": "2-11", "representative_age": 6},
    {"label": "12-17", "representative_age": 15},
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
        "analyzed with no sampling and the reported metrics carry no Monte "
        "Carlo uncertainty. Mortality–delisting correlation (the optional "
        "copula) is omitted; it shifts centers near-uniformly and does not "
        "materially affect the Gini disparity metric."
    ),
    (
        "The unweighted Gini treats all 48 demographic cells equally, which "
        "overstates rare groups (AB- is 0.6% of the population). Weighted "
        "metrics use US blood-type prevalence and an approximate OPTN waitlist "
        "age/sex mix; centers are equal-weighted because per-center waitlist "
        "volume is not yet modeled."
    ),
    (
        "Much of the blood-type disparity reflects ABO-matching biology, not "
        "systemic bias. The between/within blood-type decomposition separates "
        "the ABO component (gini_between_blood_type) from geographic and "
        "age/sex variation (gini_within_blood_type)."
    ),
]


# Issue #64: Use shared implementation from stats_utils
from services.stats_utils import gini as _gini
from services.stats_utils import gini_weighted as _gini_weighted

# --- Population weights for equity cells (#254) ---
# Equal-weighting the 48 cells overstates rare groups (AB- is 0.6% of the US
# population but got 1/8 of the blood-type weight). Weighted metrics use:
#
# Blood type: US population prevalence (American Red Cross / Stanford Blood
# Center distribution). Register: EQSP-32.
BLOOD_TYPE_PREVALENCE = {
    "O+": 0.374, "A+": 0.357, "B+": 0.085, "AB+": 0.034,
    "O-": 0.066, "A-": 0.063, "B-": 0.015, "AB-": 0.006,
}
# Age brackets / sex: approximate adult OPTN waitlist composition (OPTN/SRTR
# Annual Data Report; the waitlist skews older and male). These are rough,
# documented approximations — not per-organ. Register: EQSP-31.
AGE_BRACKET_WEIGHTS = {"18-34": 0.11, "35-54": 0.38, "55-70": 0.51}
SEX_WEIGHTS = {"male": 0.60, "female": 0.40}

# Fallback only. The real pediatric mix is per-organ and differs enormously
# (liver is 41% under-2, kidney 4.6%), so it is read from the data below and
# this uniform split is used only if that lookup fails. Register: EQSP-33.
_PEDIATRIC_WEIGHTS_FALLBACK = {"0-1": 1 / 3, "2-11": 1 / 3, "12-17": 1 / 3}


def pediatric_age_weights(organ: str) -> dict[str, float]:
    """Observed national pediatric waitlist age mix for *organ* (#335).

    Source: SRTR Tables B8-B9 national counts, parsed into
    data/pediatric-centers.json by scripts/parse-srtr-pediatric.py.
    """
    from services.data_loader import get_data

    try:
        mix = get_data().pediatric.get(organ, {}).get("national_age_mix") or {}
    except RuntimeError:
        return dict(_PEDIATRIC_WEIGHTS_FALLBACK)
    weights = mix.get("weights") or {}
    total = sum(weights.values())
    if not weights or not 0.98 <= total <= 1.02:
        return dict(_PEDIATRIC_WEIGHTS_FALLBACK)
    return dict(weights)


def _profile_weight(blood_type: str, age_bracket: str, sex: str,
                    age_weights: dict[str, float] | None = None) -> float:
    """Joint population weight for one demographic cell (independence assumed)."""
    ages = AGE_BRACKET_WEIGHTS if age_weights is None else age_weights
    return (
        BLOOD_TYPE_PREVALENCE.get(blood_type, 0.0)
        * ages.get(age_bracket, 0.0)
        * SEX_WEIGHTS.get(sex, 0.0)
    )


def _abo_decomposition(results: list[dict]) -> tuple[float, float]:
    """Split inequality into ABO-biology vs non-ABO components (#254).

    between = weighted Gini of the blood-type weighted-mean p24s (what ABO
    matching alone produces); within = prevalence-weighted mean of the
    weighted Gini across cells inside each blood type (everything else).
    """
    by_bt: dict[str, tuple[list, list]] = defaultdict(lambda: ([], []))
    for r in results:
        vals, wts = by_bt[r["blood_type"]]
        vals.append(r["p24"])
        wts.append(r["weight"])

    bt_means, bt_weights, within_ginis = [], [], []
    for bt, (vals, wts) in by_bt.items():
        vals, wts = np.array(vals), np.array(wts)
        prevalence = BLOOD_TYPE_PREVALENCE.get(bt, 0.0)
        if np.sum(wts) > 0:
            bt_means.append(float(np.average(vals, weights=wts)))
            bt_weights.append(prevalence)
            within_ginis.append((_gini_weighted(vals, wts), prevalence))

    between = _gini_weighted(np.array(bt_means), np.array(bt_weights)) if len(bt_means) > 1 else 0.0
    total_prev = sum(p for _, p in within_ginis)
    within = sum(g * p for g, p in within_ginis) / total_prev if total_prev > 0 else 0.0
    return between, within


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


def compute_bias_audit(
    patient: PatientProfile,
    seed: int | None = None,
    max_centers: int | None = None,
):
    """Run the equity analysis and feed its per-profile results to the bias
    audit (effect sizes, disparity ratios) — wiring for #254; bias_audit.py
    was previously unreachable from any endpoint."""
    from services.bias_audit import run_bias_audit

    result, per_center_profiles = _compute_equity_core(
        patient, seed=seed, max_centers=max_centers,
    )
    payload = {
        "cities": [
            {
                "city": ce.center_name or ce.city,
                "gini": ce.gini_coefficient,
                "profiles": per_center_profiles[ce.center_code or ce.city],
            }
            for ce in result.cities
        ]
    }
    return run_bias_audit(payload)


def compute_equity_analysis(
    patient: PatientProfile,
    n_iterations: int = 200,
    seed: int | None = None,
    max_centers: int | None = None,
) -> EquityAnalysisResult:
    """Public entry point — see _compute_equity_core for the full docstring."""
    result, _ = _compute_equity_core(
        patient, n_iterations=n_iterations, seed=seed, max_centers=max_centers,
    )
    return result


def _compute_equity_core(
    patient: PatientProfile,
    n_iterations: int = 200,
    seed: int | None = None,
    max_centers: int | None = None,
) -> tuple[EquityAnalysisResult, dict[str, list[dict]]]:
    """
    Run equity analysis across 48 demographic profiles × centers
    for the patient's organ.

    Returns (result, per_center_profiles) where per_center_profiles maps
    center key → per-profile rows for the bias audit (#254).

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
    pediatric = bool(getattr(patient, "is_pediatric", False))
    brackets = PEDIATRIC_AGE_BRACKETS if pediatric else AGE_BRACKETS
    age_weights = pediatric_age_weights(patient.organ) if pediatric else None
    for bt in BLOOD_TYPES:
        for ab in brackets:
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
        # #219: the old key c.get("wait_time_factor") never existed on center
        # records, so the cap silently truncated by input order while claiming
        # wait-factor ordering. Sort by the real per-organ wait factor.
        from services.data_loader import get_data
        cwt = get_data().center_wait_times.get("center_wait_time_factors", {})
        centers = sorted(
            centers,
            key=lambda c: cwt.get(c.get("code", ""), {}).get(patient.organ, 1.0),
        )[:max_centers]

    logger.info(
        "Equity analysis (analytic): %s, %d profiles x %d centers",
        patient.organ, len(profiles), len(centers),
    )

    # --- Evaluate all profiles × all centers (closed form) ---
    center_results: dict[str, list] = defaultdict(list)
    all_p24_values = []
    all_weights = []
    all_results = []

    import scipy.stats

    from services.distributions import get_wait_time_params

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

        # p24 depends on blood type AND age/sex: the age/sex multiplier scales
        # the whole wait distribution, which moves the competing-risks integral.
        # Computing p24 per blood type only (and letting age/sex touch just the
        # displayed median) was the #254 defect — the Gini never saw age/sex.
        #
        # Vectorized over the 48 profiles (2026-08 review): only the lognorm
        # parameters vary per profile, so all 48 pdfs evaluate as one
        # (48, 241) expression + one trapezoid pass instead of 48 frozen-dist
        # integrations (~100x less CPU per request on the web tier).
        params = np.array([
            get_wait_time_params(
                rep.organ, p["patient"].blood_type, center_code=code,
                cpra=rep.cpra, meld=rep.meld, las=rep.las,
                age=p["patient"].age, sex=p["patient"].sex,
            )
            for p in profiles
        ])  # columns: (sigma, adjusted_median)
        pdfs = scipy.stats.lognorm.pdf(
            _P24_GRID[None, :], s=params[:, [0]], scale=params[:, [1]],
        )
        survival = np.exp(-inv_total * _P24_GRID)
        _trapz = getattr(np, "trapezoid", None) or np.trapz
        p24s = np.clip(_trapz(pdfs * survival[None, :], _P24_GRID, axis=1),
                       0.0, 1.0)
        # Lognorm median = scale (ppf(0.5) of the standard lognorm is exactly
        # 1) — matches dist.median() without 48 frozen dists + ppf calls.
        medians = params[:, 1]

        for profile, p24, median_wait in zip(profiles, p24s, medians):
            weight = _profile_weight(
                profile["blood_type"], profile["age_bracket"], profile["sex"],
                age_weights)
            row = {
                "p24": float(p24),
                "median_wait": float(median_wait),
                "blood_type": profile["blood_type"],
                "age_bracket": profile["age_bracket"],
                "sex": profile["sex"],
                "weight": weight,
            }
            center_results[code or display].append(row)
            all_results.append(row)
            all_p24_values.append(float(p24))
            all_weights.append(weight)

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
        weights = np.array([r["weight"] for r in results])

        gini = _gini(p24_vals)
        gini_w = _gini_weighted(p24_vals, weights)
        gini_between_bt, gini_within_bt = _abo_decomposition(results)
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
            gini_weighted=round(gini_w, 4),
            gini_between_blood_type=round(gini_between_bt, 4),
            gini_within_blood_type=round(gini_within_bt, 4),
            p24_range=(round(p24_range[0], 4), round(p24_range[1], 4)),
            median_wait_range=(round(wait_range[0], 1), round(wait_range[1], 1)),
            dimension_disparities=dim_disparities,
        ))

    city_equities.sort(key=lambda c: c.gini_coefficient)
    overall_gini = _gini(np.array(all_p24_values))
    # Centers are equal-weighted in the overall metrics (per-center waitlist
    # volume is not yet available — #275); cells are population-weighted.
    overall_gini_w = _gini_weighted(np.array(all_p24_values), np.array(all_weights))
    overall_between_bt, overall_within_bt = _abo_decomposition(all_results)

    elapsed = time.perf_counter() - start
    logger.info(
        "Equity analysis complete: %s, %d profiles x %d centers, overall Gini=%.4f, %.2fs",
        patient.organ, len(profiles), len(centers), overall_gini, elapsed,
    )

    result = EquityAnalysisResult(
        organ=patient.organ,
        cities=city_equities,
        overall_gini=round(overall_gini, 4),
        overall_gini_weighted=round(overall_gini_w, 4),
        overall_gini_between_blood_type=round(overall_between_bt, 4),
        overall_gini_within_blood_type=round(overall_within_bt, 4),
        profiles_simulated=len(profiles),
        iterations_per_profile=0,  # 0 = analytic (closed-form, no Monte Carlo sampling)
        elapsed_seconds=round(elapsed, 3),
        disclaimers=EQUITY_DISCLAIMERS,
        seed_used=seed,
    )

    per_center_profiles = {
        key: [
            {
                "blood_type": r["blood_type"],
                "age_bracket": r["age_bracket"],
                "sex": r["sex"],
                "p_transplant_24mo": r["p24"],
            }
            for r in rows
        ]
        for key, rows in center_results.items()
    }
    return result, per_center_profiles
