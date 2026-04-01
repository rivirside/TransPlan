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

from config import COPULA_THETA, ORGAN_COPULA_THETA, SIMULATION_ITERATIONS, SUPPLY_WAIT_ELASTICITY
from models.schemas import CityProbability, PatientProfile, SimulationResult
from services.competing_risks import get_annual_mortality_rate, get_annual_delisting_rate
from services.copula import draw_correlated_competing_risks
from services.data_loader import get_data
from services.distributions import get_wait_time_distribution
from services.outcomes import build_outcomes_dict
from services.trends import get_city_trends

logger = logging.getLogger(__name__)

# Fallback 22 cities — used only when data_loader hasn't loaded yet (e.g. tests)
_FALLBACK_CITIES = [
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

# Fallback state abbreviation to full name
_FALLBACK_STATE_NAMES = {
    "PA": "Pennsylvania", "MD": "Maryland", "NY": "New York",
    "MN": "Minnesota", "WI": "Wisconsin", "IL": "Illinois",
    "OH": "Ohio", "MO": "Missouri", "IN": "Indiana",
    "NE": "Nebraska", "TN": "Tennessee", "NC": "North Carolina",
    "FL": "Florida", "TX": "Texas", "OR": "Oregon",
    "WA": "Washington", "CA": "California",
}


def _get_cities() -> list[dict[str, str]]:
    """Get city list from data_loader, falling back to hardcoded list."""
    try:
        cities = get_data().cities
        return cities if cities else _FALLBACK_CITIES
    except RuntimeError:
        return _FALLBACK_CITIES


def _get_centers(organ: str) -> list[dict]:
    """Get all SRTR centers that perform *organ*, falling back to 22 cities."""
    try:
        centers = get_data().centers_for_organ(organ)
        return centers if centers else _FALLBACK_CITIES
    except RuntimeError:
        return _FALLBACK_CITIES


# Module-level CITIES kept for backward compat (tests, imports).
# Production code uses _get_centers(organ) which loads from data files.
CITIES = _FALLBACK_CITIES


def _get_state_full_name(state_abbrev: str) -> str | None:
    """Get full state name from data_loader, falling back to hardcoded map."""
    try:
        names = get_data().state_full_names
        return names.get(state_abbrev) or _FALLBACK_STATE_NAMES.get(state_abbrev)
    except RuntimeError:
        return _FALLBACK_STATE_NAMES.get(state_abbrev)


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
    state_name = _get_state_full_name(state_abbrev)
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


def _bootstrap_ci(outcomes: np.ndarray, event: int, threshold_months: np.ndarray, time_horizon: float, confidence: float = 0.95, n_bootstrap: int = 1000, rng: np.random.Generator | None = None) -> tuple[float, float]:
    """
    Compute a bootstrap confidence interval for P(event occurs first AND within time_horizon).

    Parameters
    ----------
    outcomes : array of int (0=transplant, 1=death, 2=delisted)
    event : which event to compute CI for (0, 1, or 2)
    threshold_months : array of event times (min of the three draws)
    time_horizon : months cutoff
    rng : numpy random generator (if None, creates unseeded one)
    """
    if rng is None:
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


def _get_acceptance_rate(organ: str, center_code: str) -> float:
    """Return center-level effective acceptance rate (0 < rate <= 1.0).

    Computed as national_rate * center_factor. Centers with higher volume
    relative to median are assumed to accept more offers.
    """
    data = get_data()
    ar = data.acceptance_rates
    national = ar.get("national_acceptance_rates", {}).get(organ, 0.25)
    factor = ar.get("center_acceptance_factors", {}).get(center_code, {}).get(organ, 1.0)
    return min(national * factor, 1.0)


def simulate(
    patient: PatientProfile,
    n_iterations: int | None = None,
    copula_theta_override: float | None = None,
    elasticity_override: float | None = None,
    seed: int | None = None,
    model_acceptance: bool = False,
    model_score_drift: bool = False,
    trend_years: float = 0.0,
) -> SimulationResult:
    """
    Run Monte Carlo simulation with competing risks for all SRTR centers
    that perform the requested organ.

    For each center and iteration:
      1. Draw transplant_time from log-normal (center-level wait-time factor)
      2. Draw mortality_time from exponential (center-level mortality factor)
      3. Draw delisting_time from exponential (center-level delisting factor)
      4. Outcome = whichever event occurs first

    Returns ranked centers with transplant probabilities, CIs, and
    competing risks breakdown at 24 months.

    Parameters
    ----------
    seed : optional RNG seed for reproducibility. If None, a random seed is
        generated and returned in the result so the run can be replicated.
    """
    if n_iterations is None:
        n_iterations = SIMULATION_ITERATIONS

    eff_elasticity = elasticity_override if elasticity_override is not None else SUPPLY_WAIT_ELASTICITY

    start = time.perf_counter()
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 2**31))
    rng = np.random.default_rng(seed)
    city_results: list[CityProbability] = []

    # --- F2: Pre-compute trend projections for 22 cities ---
    trend_projections: dict[str, dict[str, float]] = {}
    center_to_trend_city: dict[str, str] = {}
    if trend_years > 0:
        from services.trends import get_trend_projection
        data = get_data()
        mapping = data.center_mapping.get("cities", {})
        # Build reverse map: center_code → city_name
        for city_name, info in mapping.items():
            primary = info.get("primary", "")
            if primary:
                center_to_trend_city[primary] = city_name
            for alt in info.get("alternates", []):
                center_to_trend_city[alt] = city_name
        # Pre-compute projections for each city
        for city_name in mapping:
            trend_projections[city_name] = get_trend_projection(
                patient.organ, city_name, years_forward=trend_years,
            )

    for center in _get_centers(patient.organ):
        # Center records have {code, name, state, state_abbr, lat, lon, ...}
        # Fallback records (22-city mode) have {city, state}
        code = center.get("code", "")
        name = center.get("name", center.get("city", ""))
        state_abbr = center.get("state_abbr", center.get("state", ""))
        state_full = center.get("state", _get_state_full_name(state_abbr) or state_abbr)
        lat = center.get("lat")
        lon = center.get("lon")
        # Display label: use city name for fallback, center name for full mode
        display_city = center.get("city", name)

        # --- Draw transplant times from log-normal ---
        dist = get_wait_time_distribution(
            organ=patient.organ,
            blood_type=patient.blood_type,
            center_code=code,
            city=display_city,
            cpra=patient.cpra,
            meld=patient.meld,
            las=patient.las,
        )
        transplant_times = dist.rvs(size=n_iterations, random_state=rng)

        # --- F1: Acceptance rate thinning ---
        # If center accepts fraction a of offers, effective wait = T/a
        if model_acceptance:
            a_rate = _get_acceptance_rate(patient.organ, code)
            if a_rate > 0 and a_rate < 1.0:
                transplant_times = transplant_times / a_rate

        # --- F3: Dynamic score drift (MELD/LAS progression) ---
        if model_score_drift:
            from services.distributions import get_drift_adjusted_multiplier
            drift_ratio = get_drift_adjusted_multiplier(
                patient.organ, meld=patient.meld, las=patient.las,
                expected_wait_months=float(dist.median()),
            )
            if drift_ratio != 1.0:
                transplant_times = transplant_times * drift_ratio

        # --- Apply organ-specific cause-of-death multiplier (M2) ---
        # Sublinear elasticity: wait_adj = multiplier ^ elasticity (L-056)
        if patient.adjust_for_cause_of_death:
            cod_mult = _get_cod_multiplier(
                state_abbr, patient.organ,
                n_samples=n_iterations, rng=rng,
            )
            safe_mult = np.where(cod_mult > 0, cod_mult, 1.0)
            effective_mult = np.power(safe_mult, eff_elasticity)
            transplant_times = transplant_times / effective_mult

        # --- Draw mortality & delisting times ---
        annual_mort = get_annual_mortality_rate(
            organ=patient.organ, center_code=code, city=display_city,
            urgency=patient.urgency, meld=patient.meld,
        )

        annual_delist = get_annual_delisting_rate(
            organ=patient.organ, center_code=code, city=display_city,
        )

        # --- F3: Adjust mortality for score drift (higher MELD → higher mortality) ---
        if model_score_drift and patient.organ == "liver" and patient.meld is not None:
            from config import SCORE_DRIFT_RATES, SCORE_DRIFT_CAPS
            drift_rate = SCORE_DRIFT_RATES.get("liver", {}).get("meld", 0)
            if drift_rate > 0:
                eff_meld = min(
                    patient.meld + drift_rate * float(dist.median()) / 12.0,
                    SCORE_DRIFT_CAPS.get("meld", 40),
                )
                avg_meld = (patient.meld + eff_meld) / 2.0
                mort_at_drift = get_annual_mortality_rate(
                    organ="liver", center_code=code, city=display_city,
                    urgency=patient.urgency, meld=int(avg_meld),
                )
                if mort_at_drift > 0:
                    annual_mort = mort_at_drift

        # --- F2: Apply trend projections to rates ---
        if trend_years > 0:
            tc = center_to_trend_city.get(code)
            if tc and tc in trend_projections:
                tp = trend_projections[tc]
                transplant_times = transplant_times * tp["wait_time_factor"]
                annual_mort = annual_mort * tp["mortality_factor"]
                annual_delist = annual_delist * tp["delisting_factor"]

        mort_scale = 12.0 / annual_mort if annual_mort > 0 else 1e6
        delist_scale = 12.0 / annual_delist if annual_delist > 0 else 1e6

        if patient.use_copula:
            mortality_times, delisting_times = draw_correlated_competing_risks(
                mort_scale=mort_scale,
                delist_scale=delist_scale,
                n=n_iterations,
                theta=copula_theta_override if copula_theta_override is not None else ORGAN_COPULA_THETA.get(patient.organ, COPULA_THETA),
                rng=rng,
            )
        else:
            mortality_times = rng.exponential(scale=mort_scale, size=n_iterations)
            delisting_times = rng.exponential(scale=delist_scale, size=n_iterations)

        # --- Determine outcome: which event occurs first ---
        all_times = np.stack([transplant_times, mortality_times, delisting_times], axis=1)
        event_times = np.min(all_times, axis=1)
        outcomes = np.argmin(all_times, axis=1)

        # --- Compute transplant probabilities ---
        def p_transplant_within(horizon: float) -> float:
            return float(np.mean((outcomes == 0) & (event_times <= horizon)))

        p_6 = p_transplant_within(6)
        p_12 = p_transplant_within(12)
        p_24 = p_transplant_within(24)
        p_36 = p_transplant_within(36)

        ci_95 = _bootstrap_ci(outcomes, event=0, threshold_months=event_times, time_horizon=24, rng=rng)

        transplanted_mask = outcomes == 0
        if np.any(transplanted_mask):
            median_wait = float(np.median(transplant_times[transplanted_mask]))
        else:
            median_wait = float(np.median(transplant_times))

        competing_risks_24 = {
            "p_transplant_24mo": round(p_24, 4),
            "p_mortality_24mo": round(float(np.mean((outcomes == 1) & (event_times <= 24))), 4),
            "p_delisting_24mo": round(float(np.mean((outcomes == 2) & (event_times <= 24))), 4),
            "p_still_waiting_24mo": round(float(np.mean(event_times > 24)), 4),
        }

        # Post-transplant outcomes (center-level if available)
        outcomes_data = None
        try:
            outcomes_data = build_outcomes_dict(
                patient.organ, city=display_city, p_transplant_24mo=p_24, center_code=code,
            )
        except (KeyError, FileNotFoundError, ValueError) as e:
            logger.warning("Outcomes data unavailable for %s/%s: %s", patient.organ, code or display_city, e)

        # Historical trends (city-level — center-level trends not yet available)
        trends_data = None
        try:
            trends_data = get_city_trends(patient.organ, display_city)
        except (KeyError, FileNotFoundError, ValueError):
            pass

        city_results.append(CityProbability(
            city=display_city,
            state=state_full,
            center_code=code,
            center_name=name,
            lat=lat,
            lon=lon,
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

    city_results.sort(key=lambda c: c.p_transplant_24mo, reverse=True)

    elapsed = time.perf_counter() - start
    n_centers = len(city_results)
    logger.info(
        "Simulation complete: %s %s, %d centers, %d iterations, %.2fs",
        patient.organ, patient.blood_type, n_centers, n_iterations, elapsed,
    )

    return SimulationResult(
        patient=patient,
        cities=city_results,
        iterations=n_iterations,
        elapsed_seconds=round(elapsed, 3),
        seed_used=seed,
    )
