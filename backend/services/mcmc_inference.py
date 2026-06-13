"""
MCMC inference service — Phase 5 M3 + Phase 7 #207.

At query time, loads a cached posterior trace (fitted offline) and runs
forward Monte Carlo simulation using parameter draws from the posterior.
This produces results with data-derived credible intervals instead of
the fixed point estimates used by the standard Monte Carlo engine.

Query-time flow:
  1. Load cached ArviZ trace for the requested organ (with auto-fallback)
  2. Draw N parameter sets from the posterior (one per iteration group)
  3. For each center, map to trace city via explicit center->region mapping
  4. Apply center-level adjustment factors post-inference
  5. Assemble into SimulationResult (same schema as monte_carlo.simulate)

Granularity modes (#207):
  - "classic": Iterate over 22 trace cities only (original behavior)
  - "state" / "full": Iterate over all ~248 centers, applying center-level
    adjustment factors relative to the parent trace city's parameters.
"""

import json
import logging
import time
from pathlib import Path

import numpy as np
import scipy.stats

from config import COPULA_THETA, DATA_DIR, ORGAN_COPULA_THETA, SIMULATION_ITERATIONS, SUPPLY_WAIT_ELASTICITY
from models.schemas import CityProbability, PatientProfile, SimulationResult
from services.copula import draw_correlated_competing_risks
from services.mcmc_survival import (
    BLOOD_TYPES,
    URGENCY_LEVELS,
    load_trace,
    sample_params_from_trace,
    trace_exists,
)
from services.monte_carlo import CITIES, _get_centers, _get_cities, _get_cod_multiplier
from services.stats_utils import rate_to_exponential_scale

# Lazy import to avoid circular dependency
_outcomes_builder = None
_trends_getter = None

logger = logging.getLogger(__name__)

# Cache loaded traces in memory (loaded once at first query)
_trace_cache: dict = {}


# ---------------------------------------------------------------------------
# Trace loading with auto-fallback (#207)
# ---------------------------------------------------------------------------

def _trace_path(organ: str, granularity: str = "classic") -> Path:
    """Return the expected trace file path for a given organ and granularity."""
    if granularity == "classic":
        return Path(DATA_DIR) / "mcmc-traces" / f"{organ}.nc"
    return Path(DATA_DIR) / "mcmc-traces" / f"{organ}-{granularity}.nc"


def _select_trace(organ: str, granularity: str) -> tuple[Path | None, str | None]:
    """Find best available trace, falling back to coarser granularity.

    Tries the requested granularity first, then falls back through
    state -> classic. Returns (path, actual_granularity) or (None, None).
    """
    for g in [granularity, "state", "classic"]:
        p = _trace_path(organ, g)
        if p.exists():
            return p, g
    return None, None


def _get_trace(organ: str, granularity: str = "classic"):
    """Load trace from cache or disk, with auto-fallback to coarser granularity."""
    cache_key = f"{organ}:{granularity}"
    if cache_key in _trace_cache:
        return _trace_cache[cache_key]

    # Try auto-fallback
    path, actual_g = _select_trace(organ, granularity)
    if path is None:
        # Last resort: try the default classic path (backward compat)
        classic_key = f"{organ}:classic"
        if classic_key in _trace_cache:
            return _trace_cache[classic_key]
        trace = load_trace(organ)
        if trace is not None:
            _trace_cache[classic_key] = trace
        return trace

    if actual_g != granularity:
        logger.info(
            "Trace fallback: %s requested %s, using %s trace at %s",
            organ, granularity, actual_g, path,
        )

    # Load the trace
    import arviz as az
    trace = az.from_netcdf(str(path))
    _trace_cache[cache_key] = trace
    return trace


def is_available(organ: str) -> bool:
    """Check if MCMC inference is available for the given organ."""
    return trace_exists(organ)


def _get_age_bracket(age: int) -> str:
    """Map age to bracket key."""
    if age < 35:
        return "18-34"
    elif age < 50:
        return "35-49"
    elif age < 65:
        return "50-64"
    else:
        return "65+"


def _get_clinical_multiplier(organ: str, params: dict, patient: PatientProfile) -> float:
    """
    Compute clinical multiplier from patient-specific scores.

    Uses the same range-based lookups as the standard Monte Carlo engine.
    Clinical multipliers are NOT in the hierarchical model (too few data
    points for Bayesian estimation), so we use the deterministic values.
    """
    from services.distributions import get_wait_time_distribution

    # We use the distribution service to get the clinical multiplier
    # by computing the ratio of clinical-adjusted vs unadjusted median
    dist_base = get_wait_time_distribution(organ=organ, blood_type="A+", city="Nashville")
    dist_patient = get_wait_time_distribution(
        organ=organ, blood_type="A+", city="Nashville",
        cpra=patient.cpra, meld=patient.meld, las=patient.las,
    )
    base_median = dist_base.median()
    patient_median = dist_patient.median()
    if base_median > 0:
        return patient_median / base_median
    return 1.0


# ---------------------------------------------------------------------------
# Center-level adjustment factors (#207)
# ---------------------------------------------------------------------------

def _load_center_adjustments(organ: str) -> dict:
    """Load center-level wait time and competing risk adjustment data.

    Returns a dict with:
      - wait_factors: {center_code: organ_factor}
      - mort_factors: {center_code: mortality_factor}
      - delist_factors: {center_code: delisting_factor}
      - city_wait_factors: {city: factor} (from city-level data, for ratio computation)
      - city_mort_factors: {city: factor}
      - city_delist_factors: {city: factor}
    """
    from services.data_loader import get_data
    data = get_data()

    # Center-level factors
    cwt = data.center_wait_times.get("center_wait_time_factors", {})
    center_wait = {code: info.get(organ, 1.0) for code, info in cwt.items()}

    ccr = data.center_competing_risks.get("center_adjustments", {})
    center_mort = {
        code: info.get(organ, {}).get("mortality_factor", 1.0)
        for code, info in ccr.items()
    }
    center_delist = {
        code: info.get(organ, {}).get("delisting_factor", 1.0)
        for code, info in ccr.items()
    }

    # City-level factors (for computing center/city ratio)
    city_wait = data.wait_time_distributions.get("city_wait_time_factors", {})
    city_wait = {k: v for k, v in city_wait.items() if not k.startswith("_")}

    city_adj = data.competing_risks.get("city_adjustments", {})
    city_mort = {}
    city_delist = {}
    for city_name, adj in city_adj.items():
        if city_name.startswith("_"):
            continue
        mf = adj.get("mortality_factor", 1.0)
        df = adj.get("delisting_factor", 1.0)
        city_mort[city_name] = mf if not isinstance(mf, str) else 1.0
        city_delist[city_name] = df if not isinstance(df, str) else 1.0

    return {
        "wait_factors": center_wait,
        "mort_factors": center_mort,
        "delist_factors": center_delist,
        "city_wait_factors": city_wait,
        "city_mort_factors": city_mort,
        "city_delist_factors": city_delist,
    }


def _compute_center_adjustment(center_factor: float, city_factor: float) -> float:
    """Compute center-level adjustment ratio relative to parent city.

    If a center's factor is 0.5 and its parent city's factor is 1.0,
    the center should have half the wait time (ratio = 0.5).
    """
    if city_factor <= 0:
        return 1.0
    return center_factor / city_factor


def simulate_mcmc(
    patient: PatientProfile,
    n_iterations: int | None = None,
    seed: int | None = None,
) -> SimulationResult:
    """
    Run simulation using posterior parameter draws from the MCMC trace.

    For each iteration batch (grouped by posterior draw):
      1. Sample a parameter set from the posterior
      2. For each city/center, construct log-normal wait time distribution
      3. Draw competing risk times (with optional copula)
      4. Determine outcomes

    The key difference from standard MC: parameters themselves vary across
    draws, producing wider credible intervals that honestly reflect
    parameter uncertainty.

    Granularity modes (#207):
      - "classic": Iterate over 22 trace cities (one result per city)
      - "state"/"full": Iterate over all ~248 centers with center-level
        adjustment factors applied post-inference
    """
    if n_iterations is None:
        n_iterations = SIMULATION_ITERATIONS

    granularity = getattr(patient, "bbn_granularity", "classic")

    trace = _get_trace(patient.organ, granularity)
    if trace is None:
        raise RuntimeError(
            f"No MCMC trace available for {patient.organ}. "
            f"Run scripts/fit-mcmc-model.py --organ {patient.organ} first."
        )

    start = time.perf_counter()
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 2**31))
    rng = np.random.default_rng(seed)

    # Draw multiple parameter sets from the posterior.
    # We use N_PARAM_DRAWS independent draws; each draw produces
    # n_iterations // N_PARAM_DRAWS simulations.
    N_PARAM_DRAWS = min(50, n_iterations)
    iters_per_draw = max(1, n_iterations // N_PARAM_DRAWS)
    actual_iterations = N_PARAM_DRAWS * iters_per_draw

    # Pre-sample all parameter sets
    param_draws = sample_params_from_trace(trace, n_draws=N_PARAM_DRAWS, rng=rng)

    # Build city name -> index mapping from trace metadata
    trace_cities = json.loads(str(trace.attrs.get("cities", "[]")))
    if not trace_cities:
        # Fall back to sorted city names from wait time data
        with open(DATA_DIR / "wait-time-distributions.json") as f:
            wt = json.load(f)
        cf = wt.get("city_wait_time_factors", {})
        trace_cities = sorted(k for k in cf if not k.startswith("_"))
    city_to_idx = {c: i for i, c in enumerate(trace_cities)}

    # Build explicit center -> trace city mapping (#207)
    try:
        from services.bbn_parameterizer import get_center_to_region_map
        center_city_map = get_center_to_region_map("classic")
    except (RuntimeError, ImportError):
        # Fallback: empty map (Nashville fallback will be used for all centers)
        center_city_map = {}

    # Map blood type and urgency to indices
    bt_idx = BLOOD_TYPES.index(patient.blood_type) if patient.blood_type in BLOOD_TYPES else 2  # A+ fallback
    urg_idx = URGENCY_LEVELS.index(patient.urgency) if patient.urgency in URGENCY_LEVELS else 1  # urgency 2 fallback

    # Clinical multiplier (deterministic, not in hierarchical model)
    clinical_mult = _get_clinical_multiplier(patient.organ, {}, patient)

    # Age mortality multiplier (from competing-risks.json, not in trace)
    age_bracket = _get_age_bracket(patient.age)
    with open(DATA_DIR / "competing-risks.json") as f:
        cr_data = json.load(f)
    age_mults = cr_data.get("age_mortality_multipliers", {})
    age_mort_mult = age_mults.get(age_bracket, 1.0)
    if isinstance(age_mort_mult, str):
        age_mort_mult = 1.0

    # Load center-level adjustment data (for state/full granularity) (#207)
    center_adj = None
    if granularity in ("state", "full"):
        try:
            center_adj = _load_center_adjustments(patient.organ)
        except Exception as e:
            logger.warning("Could not load center adjustments: %s — proceeding without", e)

    # Determine iteration targets based on granularity (#207)
    if granularity == "classic":
        # Classic mode: iterate over trace cities only
        iteration_targets = [
            {
                "code": "",
                "city": city_name,
                "state": "",
                "lat": None,
                "lon": None,
                "name": city_name,
                "cidx": idx,
                "center_wait_adj": 1.0,
                "center_mort_adj": 1.0,
                "center_delist_adj": 1.0,
            }
            for city_name, idx in city_to_idx.items()
        ]
    else:
        # State/full mode: iterate over all centers with center-level adjustments
        iteration_targets = []
        for center in _get_centers(patient.organ):
            code = center.get("code", "")
            city = center.get("name", center.get("city", ""))
            state = center.get("state", center.get("state_abbr", ""))
            lat = center.get("lat")
            lon = center.get("lon")

            # Use explicit center->city mapping (#207)
            region = center_city_map.get(code, "Nashville")
            cidx = city_to_idx.get(region)
            if cidx is None:
                cidx = city_to_idx.get("Nashville", 0)

            # Compute center-level adjustment ratios (#207)
            center_wait_adj = 1.0
            center_mort_adj = 1.0
            center_delist_adj = 1.0
            if center_adj is not None and code:
                # Wait time: center_factor / city_factor for the parent city
                c_wait = center_adj["wait_factors"].get(code, 1.0)
                city_wait = center_adj["city_wait_factors"].get(region, 1.0)
                center_wait_adj = _compute_center_adjustment(c_wait, city_wait)

                # Mortality: center_factor / city_factor
                c_mort = center_adj["mort_factors"].get(code, 1.0)
                city_mort = center_adj["city_mort_factors"].get(region, 1.0)
                center_mort_adj = _compute_center_adjustment(c_mort, city_mort)

                # Delisting: center_factor / city_factor
                c_delist = center_adj["delist_factors"].get(code, 1.0)
                city_delist = center_adj["city_delist_factors"].get(region, 1.0)
                center_delist_adj = _compute_center_adjustment(c_delist, city_delist)

            iteration_targets.append({
                "code": code,
                "city": city,
                "state": state,
                "lat": lat,
                "lon": lon,
                "name": center.get("name", city),
                "cidx": cidx,
                "center_wait_adj": center_wait_adj,
                "center_mort_adj": center_mort_adj,
                "center_delist_adj": center_delist_adj,
            })

    city_results: list[CityProbability] = []

    for target in iteration_targets:
        code = target["code"]
        city = target["city"]
        state = target["state"]
        lat = target["lat"]
        lon = target["lon"]
        cidx = target["cidx"]
        center_wait_adj = target["center_wait_adj"]
        center_mort_adj = target["center_mort_adj"]
        center_delist_adj = target["center_delist_adj"]

        # Accumulate simulation results across parameter draws
        all_outcomes = np.empty(actual_iterations, dtype=int)
        all_event_times = np.empty(actual_iterations)
        all_transplant_times = np.empty(actual_iterations)
        # Per-draw p24 for Bayesian HDI (one value per posterior draw)
        per_draw_p24 = np.empty(N_PARAM_DRAWS)

        for draw_i in range(N_PARAM_DRAWS):
            params = param_draws[draw_i]
            offset = draw_i * iters_per_draw

            # --- Construct wait time distribution from posterior params ---
            national_median = params["national_median"]
            log_sigma = params["log_sigma"]

            # City wait factor from posterior (or fallback to 1.0)
            city_wait_factor = 1.0
            if cidx is not None and cidx < len(params["city_wait_factors"]):
                city_wait_factor = params["city_wait_factors"][cidx]

            # Blood type multiplier from posterior
            bt_mult = params["bt_multipliers"][bt_idx]

            # Compose adjusted median with center-level adjustment (#207)
            adjusted_median = (
                national_median * bt_mult * city_wait_factor
                * clinical_mult * center_wait_adj
            )

            # Draw transplant times from log-normal
            dist = scipy.stats.lognorm(s=log_sigma, scale=adjusted_median)
            transplant_times = dist.rvs(size=iters_per_draw, random_state=rng)

            # --- Apply COD multiplier (same as standard MC) ---
            if patient.adjust_for_cause_of_death:
                cod_state = state if len(state) == 2 else ""
                cod_mult = _get_cod_multiplier(cod_state, patient.organ, n_samples=iters_per_draw, rng=rng)
                safe_mult = np.where(cod_mult > 0, cod_mult, 1.0)
                effective_mult = np.power(safe_mult, SUPPLY_WAIT_ELASTICITY)
                transplant_times = transplant_times / effective_mult

            # --- Mortality and delisting from posterior ---
            national_mort = params["national_mort_rate"]
            national_delist = params["national_delist_rate"]

            # City adjustments from posterior offsets
            if cidx is not None and cidx < len(params["city_mort_offsets"]):
                city_mort_factor = np.exp(params["city_mort_offsets"][cidx])
                city_delist_factor = np.exp(params["city_delist_offsets"][cidx])
            else:
                city_mort_factor = 1.0
                city_delist_factor = 1.0

            # Urgency multiplier from posterior
            urg_mult = params["urg_multipliers"][urg_idx]

            # Compose annual rates with center-level adjustments (#207)
            annual_mort = (
                national_mort * city_mort_factor * urg_mult
                * age_mort_mult * center_mort_adj
            )
            annual_delist = (
                national_delist * city_delist_factor * center_delist_adj
            )

            mort_scale = rate_to_exponential_scale(annual_mort, "mortality", code or city)
            delist_scale = rate_to_exponential_scale(annual_delist, "delisting", code or city)

            # Draw competing risk times.
            # The MCMC model learns mort<->delist correlation via shared
            # frailty (LKJ prior).  The posterior draws already carry
            # correlated city offsets, so the external Clayton copula is
            # redundant for MCMC mode.  We still honor use_copula as an
            # extra layer if requested AND the trace lacks learned corr.
            learned_corr = params.get("mort_delist_corr", 0.0)
            use_external_copula = patient.use_copula and abs(learned_corr) < 0.01

            if use_external_copula:
                mortality_times, delisting_times = draw_correlated_competing_risks(
                    mort_scale=mort_scale,
                    delist_scale=delist_scale,
                    n=iters_per_draw,
                    theta=ORGAN_COPULA_THETA.get(patient.organ, COPULA_THETA),
                    rng=rng,
                )
            else:
                mortality_times = rng.exponential(scale=mort_scale, size=iters_per_draw)
                delisting_times = rng.exponential(scale=delist_scale, size=iters_per_draw)

            # Determine outcomes
            times_3 = np.stack([transplant_times, mortality_times, delisting_times], axis=1)
            event_times = np.min(times_3, axis=1)
            outcomes = np.argmin(times_3, axis=1)

            # Store in aggregated arrays
            all_outcomes[offset:offset + iters_per_draw] = outcomes
            all_event_times[offset:offset + iters_per_draw] = event_times
            all_transplant_times[offset:offset + iters_per_draw] = transplant_times

            # Per-draw p24 for Bayesian credible interval
            per_draw_p24[draw_i] = float(np.mean(
                (outcomes == 0) & (event_times <= 24)
            ))

        # --- Compute probabilities from aggregated results ---
        def p_transplant_within(horizon: float) -> float:
            return float(np.mean((all_outcomes == 0) & (all_event_times <= horizon)))

        p_6 = p_transplant_within(6)
        p_12 = p_transplant_within(12)
        p_24 = p_transplant_within(24)
        p_36 = p_transplant_within(36)

        # 95% Bayesian credible interval from posterior-predictive p24 draws.
        # Each draw's p24 reflects a different posterior parameter set, so the
        # spread captures parameter uncertainty (not just sampling noise).
        ci_lo = float(np.percentile(per_draw_p24, 2.5))
        ci_hi = float(np.percentile(per_draw_p24, 97.5))
        ci_95 = (ci_lo, ci_hi)

        # Median wait to transplant
        transplanted_mask = all_outcomes == 0
        if np.any(transplanted_mask):
            median_wait = float(np.median(all_transplant_times[transplanted_mask]))
        else:
            median_wait = float(np.median(all_transplant_times))

        # Competing risks at 24 months
        p_mort_24 = float(np.mean((all_outcomes == 1) & (all_event_times <= 24)))
        p_delist_24 = float(np.mean((all_outcomes == 2) & (all_event_times <= 24)))
        p_waiting_24 = float(np.mean(all_event_times > 24))

        competing_risks_24 = {
            "p_transplant_24mo": round(p_24, 4),
            "p_mortality_24mo": round(p_mort_24, 4),
            "p_delisting_24mo": round(p_delist_24, 4),
            "p_still_waiting_24mo": round(p_waiting_24, 4),
        }

        # Post-transplant outcomes (same as standard MC)
        outcomes_data = None
        try:
            from services.outcomes import build_outcomes_dict
            outcomes_data = build_outcomes_dict(patient.organ, city, p_24)
        except Exception:
            pass

        # Historical trends (same as standard MC)
        trends_data = None
        try:
            from services.trends import get_city_trends
            trends_data = get_city_trends(patient.organ, city)
        except Exception:
            pass

        city_results.append(CityProbability(
            city=city,
            state=state,
            center_code=code,
            center_name=target.get("name", city),
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

    # Sort by p_transplant_24mo descending
    city_results.sort(key=lambda c: c.p_transplant_24mo, reverse=True)

    elapsed = time.perf_counter() - start
    n_targets = len(city_results)
    logger.info(
        "MCMC inference: %s %s, %d %s, %d iterations (%d param draws x %d each), %.2fs",
        patient.organ, patient.blood_type, n_targets,
        "cities" if granularity == "classic" else "centers",
        actual_iterations, N_PARAM_DRAWS, iters_per_draw, elapsed,
    )

    return SimulationResult(
        patient=patient,
        cities=city_results,
        iterations=actual_iterations,
        elapsed_seconds=round(elapsed, 3),
        inference_mode="mcmc",
        seed_used=seed,
    )
