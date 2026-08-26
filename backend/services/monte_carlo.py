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
import zlib

import numpy as np

from config import COPULA_THETA, ORGAN_COPULA_THETA, SIMULATION_ITERATIONS, SUPPLY_WAIT_ELASTICITY
from models.schemas import CityProbability, PatientProfile, SimulationResult
from services.competing_risks import get_annual_mortality_rate, get_annual_delisting_rate
from services.copula import draw_correlated_competing_risks
from services.data_loader import get_data
from services.distributions import get_lognorm_params, get_wait_time_distribution
from services.outcomes import build_outcomes_dict
from services.stats_utils import rate_to_exponential_scale
from services.trends import get_city_trends

logger = logging.getLogger(__name__)

# Pediatric shrinkage strength, in person-years: a center with this
# much pediatric exposure gets 50% weight on its own rate, the rest
# on the national pediatric baseline (#335).
_PEDS_SHRINK_PY = 10.0

# (#293: the 22-city _FALLBACK_CITIES list was retired — the data files
# must be loaded via load_all() before simulation.)

# Fallback state abbreviation to full name
_FALLBACK_STATE_NAMES = {
    "PA": "Pennsylvania", "MD": "Maryland", "NY": "New York",
    "MN": "Minnesota", "WI": "Wisconsin", "IL": "Illinois",
    "OH": "Ohio", "MO": "Missouri", "IN": "Indiana",
    "NE": "Nebraska", "TN": "Tennessee", "NC": "North Carolina",
    "FL": "Florida", "TX": "Texas", "OR": "Oregon",
    "WA": "Washington", "CA": "California",
}


def _get_centers(organ: str) -> list[dict]:
    """Get all SRTR centers that perform *organ*.

    (#293: the 22-city fallback was retired — an empty result means the data
    files are not loaded, which is an error worth surfacing, not papering over.)
    """
    try:
        centers = get_data().centers_for_organ(organ)
    except RuntimeError as e:
        # #220: an empty 200 response would misreport a server-side problem
        raise RuntimeError(
            "Center data not loaded — call load_all() before simulating"
        ) from e
    if not centers:
        raise RuntimeError(f"No centers found for organ {organ} — data files missing?")
    return centers


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
    # Resample from an isolated child generator so the bootstrap does not
    # consume the caller's RNG stream. Otherwise each center's simulation
    # draws would depend on the CI computation of every prior center (#243).
    boot_rng = rng.spawn(1)[0]
    n = len(outcomes)
    proportions = np.empty(n_bootstrap)
    mask = (outcomes == event) & (threshold_months <= time_horizon)
    for i in range(n_bootstrap):
        idx = boot_rng.integers(0, n, size=n)
        proportions[i] = np.mean(mask[idx])

    alpha = (1 - confidence) / 2
    lo = float(np.percentile(proportions, alpha * 100))
    hi = float(np.percentile(proportions, (1 - alpha) * 100))
    return (lo, hi)


# Panel-measured persistence of OARR deviations (raw random-effects ANOVA
# over the 15-release panel, data/offer-acceptance-panel.json): the share of
# a center's OARR deviation from 1.0 that is persistent behavior rather than
# release noise. Used to shrink the single-release OARR before F1 thinning.
_OARR_SIGNAL_FRACTION = {"kidney": 0.62, "liver": 0.60, "heart": 0.58,
                         "lung": 0.51, "pancreas": 0.55, "intestine": 0.55}


def _get_acceptance_rate(organ: str, center_code: str) -> float:
    """Return center-level effective acceptance rate (0 < rate <= 1.0).

    Computed as national_rate * center_factor. Centers with higher volume
    relative to median are assumed to accept more offers.
    """
    data = get_data()
    ar = data.acceptance_rates
    if not ar.get("national_acceptance_rates"):
        # #219: with the acceptance file missing, the old 0.25 default silently
        # QUADRUPLED every modeled wait. No data → no thinning.
        logger.warning("acceptance-rates data missing — acceptance thinning disabled")
        return 1.0
    national = ar.get("national_acceptance_rates", {}).get(organ, 0.25)
    # #320: prefer the OBSERVED risk-adjusted Offer Acceptance Rate Ratio
    # (SRTR Table B11) over the volume-proxy composite — the direct
    # measurement of the discretion SURV-28 inferred. The single-release
    # OARR is SHRUNK toward neutral by the panel-measured signal fraction
    # (offer-acceptance-panel.json ANOVA: ~50-62% of OARR deviation is
    # persistent center behavior, the rest release noise) — the same
    # empirical-Bayes logic as the #317 priors. Clamped to [0.3, 3.0].
    oar = (data.offer_acceptance.get(organ, {}).get("centers", {})
           .get(center_code, {}).get("oar"))
    if isinstance(oar, (int, float)) and oar > 0:
        frac = _OARR_SIGNAL_FRACTION.get(organ, 0.55)
        shrunk = 1.0 + frac * (float(oar) - 1.0)
        factor = max(0.3, min(shrunk, 3.0))
    else:
        factor = ar.get("center_acceptance_factors", {}).get(center_code, {}).get(organ, 1.0)
    return min(national * factor, 1.0)


def pediatric_programs(organ: str) -> dict:
    """Centers with a pediatric program for *organ* (#335).

    Shared by all three engines so a child never gets a different center set
    depending on inference_mode — the engine-parity lesson from the 2026-08
    review. Empty dict means no pediatric data for the organ.
    """
    return get_data().pediatric.get(organ, {}).get("centers", {})


def restrict_to_pediatric(centers: list, organ: str) -> list:
    """Filter a center list to pediatric programs, raising with an explicit
    reason rather than silently returning adult centers."""
    programs = pediatric_programs(organ)
    if not programs:
        raise ValueError(
            f"No pediatric {organ} program data is available, so pediatric "
            f"results cannot be produced for this organ."
        )
    out = [c for c in centers if c.get("code") in programs]
    if not out:
        raise ValueError(
            f"No center with a pediatric {organ} program could be matched to "
            f"the center registry."
        )
    return out


def _pediatric_dist(patient, code: str, peds_block: dict, adult_dist):
    """Rescale the wait distribution so its 12-month transplant probability
    matches the center's observed PEDIATRIC rate (#335).

    Uses the adult-fitted exposure calibration k (see
    scripts/parse-srtr-pediatric.py): P12 = 1 - exp(-k * rate). Centers with
    thin exposure are shrunk toward the national pediatric rate in proportion
    to their person-years, so a 2-person-year program does not masquerade as
    a precise estimate. Falls back to the adult distribution untouched if the
    center has no usable pediatric record.
    """
    import math

    import scipy.stats

    rec = peds_block.get("centers", {}).get(code)
    cal = peds_block.get("calibration") or {}
    k = cal.get("k")
    if not rec or not k:
        # No adult-fitted conversion for this organ (pancreas and intestine
        # have too few adult centers carrying both a rate and a published
        # median to fit one). The center set is still pediatric, but the wait
        # numbers fall back to adult — surfaced via TAG_PEDIATRIC_UNCALIBRATED
        # rather than presented as a pediatric estimate.
        return adult_dist
    rate = rec.get("transplant_rate")
    if rate is None:
        return adult_dist
    if rate < 0:
        return adult_dist
    # NOTE: rate == 0.0 deliberately continues. A center that genuinely
    # performed no pediatric transplants is an OBSERVATION, not missing data,
    # and treating it as missing handed it the unshrunk adult curve — the
    # opposite of the shrinkage rule this function documents, and the same
    # defect class as the closed #229. With shrinkage, a 2-person-year center
    # observing zero lands near the national pediatric baseline instead of
    # inheriting an adult probability it has no evidence for.

    # Empirical-Bayes shrinkage on exposure: weight = py / (py + PRIOR_PY)
    nat_rate = (peds_block.get("national") or {}).get("transplant_rate", rate)
    py = float(rec.get("person_years") or 0.0)
    w = py / (py + _PEDS_SHRINK_PY)
    eff_rate = w * rate + (1.0 - w) * nat_rate

    p12 = 1.0 - math.exp(-k * eff_rate)
    p12 = min(max(p12, 1e-4), 0.999)

    # Solve for the lognormal median reproducing p12 at 12 months, holding
    # the organ's sigma. P(T<=12) = Phi((ln12 - ln median)/sigma) = p12
    s, loc, _ = get_lognorm_params(adult_dist)
    z = scipy.stats.norm.ppf(p12)
    median = math.exp(math.log(12.0) - z * s)
    return scipy.stats.lognorm(s=s, loc=loc, scale=median)


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
    city_results: list[CityProbability] = []

    # --- F2: Trend projections — per-center (#288), covering every center
    # with archived SRTR history instead of the 52 reachable via the legacy
    # 22-city mapping. The city path survives only for code-less fallback rows.
    if trend_years > 0:
        from services.trends import get_center_trend_projection, get_trend_projection

    # #335: pediatric candidates are restricted to centers that actually run
    # a pediatric program for this organ. Scoring a child against an adult-only
    # program is the silent wrongness pediatric mode exists to end, so the
    # exclusion is explicit and the reason is reportable.
    centers_to_run = _get_centers(patient.organ)
    pediatric = patient.is_pediatric
    peds_block = {}
    if pediatric:
        peds_block = get_data().pediatric.get(patient.organ, {})
        centers_to_run = restrict_to_pediatric(centers_to_run, patient.organ)

    # L-067 (#304): optional user-defined center set
    if patient.center_codes:
        wanted = set(patient.center_codes)
        centers_to_run = [c for c in centers_to_run if c.get("code") in wanted]
        if not centers_to_run:
            raise ValueError(
                f"None of the requested center_codes perform {patient.organ} "
                f"transplants (or the codes are unknown)."
            )

    for center in centers_to_run:
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

        # Per-center RNG stream keyed on (seed, code) — NOT a stream shared
        # across the loop, whose draws would depend on which other centers
        # run. Guarantees shortlist isolation: filtering to a center subset
        # reproduces exactly the full run's values for those centers
        # (caught by the #312 property suite).
        rng = np.random.default_rng([seed, zlib.crc32(code.encode() or b"national")])

        # --- Data-provenance tags (#300): make silent fallbacks visible.
        from services.provenance import center_data_quality
        degraded = center_data_quality(patient.organ, code, pediatric=pediatric)

        # --- Draw transplant times from log-normal ---
        dist = get_wait_time_distribution(
            organ=patient.organ,
            blood_type=patient.blood_type,
            center_code=code,
            city=display_city,
            cpra=patient.cpra,
            meld=patient.meld,
            las=patient.las,
            age=patient.age,
            sex=patient.sex,
        )
        # --- F1: Acceptance rate thinning ---
        # If center accepts fraction a of offers, effective wait = T/a.
        # Resolved BEFORE drawing so accrued-time conditioning (#329) can
        # truncate the EFFECTIVE distribution (time served counts against
        # the thinned wait, not the raw one).
        a_rate = 1.0
        if model_acceptance and not pediatric:
            a = _get_acceptance_rate(patient.organ, code)
            if a > 0 and a < 1.0:
                a_rate = a
        # #335: acceptance thinning is DELIBERATELY skipped on the pediatric
        # path. The pediatric anchor below is the center's OBSERVED pediatric
        # transplant rate, which already reflects how readily that program
        # accepts offers — thinning it again applies the same effect twice.
        # Measured before this guard, with model_acceptance=True:
        #     FLFH p12 0.806 -> 0.235   MOCH 0.739 -> 0.136
        # i.e. a 3-5x deflation of an anchored probability that should not
        # have moved at all. The adult path is unaffected: its distribution
        # comes from wait-time percentiles, which do NOT embed acceptance.

        # #335: for pediatric runs the center's OBSERVED pediatric transplant
        # rate is the anchor (the inversion gate showed the derived median
        # recovers order far better than magnitude, so the rate drives the
        # probability directly). Convert rate/person-year -> 12-month
        # probability with the adult-fitted calibration, shrink small cohorts
        # toward the national pediatric baseline, then scale the wait
        # distribution's median to reproduce that probability.
        if pediatric:
            dist = _pediatric_dist(patient, code, peds_block, dist)

        t0 = float(patient.months_waiting or 0.0)
        if t0 > 0:
            # Left-truncate at t0: T_remaining ~ (T_eff - t0 | T_eff > t0),
            # sampling the effective (scale / a_rate) lognormal directly.
            # Competing-risk clocks restart (memoryless exponentials).
            # NOTE the inspection paradox is real and intended: with a
            # heavy-tailed lognormal, long time served can RAISE the
            # remaining-wait median (evidence of being in the long tail).
            from services.distributions import get_lognorm_params
            from services.stats_utils import truncated_wait_times
            import scipy.stats as _ss
            s_, loc_, scale_ = get_lognorm_params(dist)
            eff_dist = _ss.lognorm(s=s_, loc=loc_, scale=scale_ / a_rate)
            transplant_times = truncated_wait_times(
                eff_dist, t0, size=n_iterations, rng=rng)
        else:
            transplant_times = dist.rvs(size=n_iterations, random_state=rng)
            if a_rate < 1.0:
                transplant_times = transplant_times / a_rate

        # --- F3: Dynamic score drift (MELD/LAS progression) ---
        # Per-sample piecewise drift: each sample's wait time maps to a
        # time-varying ratio via np.interp over a monthly lookup table.
        if model_score_drift:
            from services.distributions import get_piecewise_drift_lookup
            lookup_t, lookup_r = get_piecewise_drift_lookup(
                patient.organ, meld=patient.meld, las=patient.las,
            )
            if lookup_r is not None:
                transplant_times = transplant_times * np.interp(
                    transplant_times, lookup_t, lookup_r,
                )

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
            if code:
                tp = get_center_trend_projection(
                    patient.organ, code, years_forward=trend_years,
                )
            else:
                tp = get_trend_projection(
                    patient.organ, display_city, years_forward=trend_years,
                )
            transplant_times = transplant_times * tp["wait_time_factor"]
            annual_mort = annual_mort * tp["mortality_factor"]
            annual_delist = annual_delist * tp["delisting_factor"]

        mort_scale = rate_to_exponential_scale(annual_mort, "mortality", code or display_city)
        delist_scale = rate_to_exponential_scale(annual_delist, "delisting", code or display_city)

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

        # Historical trends — per-center when a code exists (#288), city fallback
        trends_data = None
        try:
            if code:
                from services.trends import get_center_trends
                trends_data = get_center_trends(patient.organ, code)
            if trends_data is None:
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
            data_quality=degraded or None,
        ))

    city_results.sort(key=lambda c: c.p_transplant_24mo, reverse=True)

    # Response-level provenance summary (#300)
    from services.provenance import summarize_cities
    dq_summary = summarize_cities(city_results)
    vintage = get_data().srtr_vintage()

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
        data_quality=dq_summary,
        data_vintage=vintage,
    )
