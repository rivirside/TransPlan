"""
Bayesian Belief Network inference engine for transplant probability estimation.

Alternative to Monte Carlo simulation (Phase 5 M1, ADR-024).
Uses the in-house bbn_lite engine (variable_elimination) for exact inference on
a 12-node DAG — NOT pgmpy (which pulled in torch at ~2GB). See bbn_lite.py.

The BBN is constructed and cached per granularity level. For each patient query,
evidence is set on the 5 observable nodes and marginal probabilities are computed
for all outcome nodes across all regions (Region iterated as evidence).

Granularity levels (#206):
  - "classic": 22 representative cities (original model)
  - "state":   ~50 US states
  - "full":    all ~248 SRTR centers

Typical query time: < 100ms for classic (vs ~2s for Monte Carlo).
"""
import logging
import time

import numpy as np

from models.schemas import CityProbability, PatientProfile, SimulationResult
from services.bbn_lite import BayesianNet, Factor, variable_elimination
from services.bbn_parameterizer import (
    AGE_GROUPS,
    BLOOD_TYPES,
    COMPETING_OUTCOME_STATES,
    COMPOUND_SUCCESS_STATES,
    DELISTING_RISK_STATES,
    DONOR_SUPPLY_STATES,
    GRAFT_SURVIVAL_STATES,
    MORTALITY_RISK_STATES,
    ORGANS,
    REGIONS,
    URGENCY_LEVELS,
    WAIT_CATEGORY_STATES,
    age_to_group,
    build_all_cpts,
    get_center_to_region_map,
    get_regions,
)
from services.outcomes import build_outcomes_dict

logger = logging.getLogger(__name__)

# City → state abbreviation (mirrors monte_carlo.py)
# (#293: the legacy 22-city region maps — _CITY_STATES, _STATE_TO_REGION,
# _get_center_region_map — were removed with the classic granularity.)

# ──────────────────────────────────────────────────────────────────────
# DAG edges (19 edges, 12 nodes)
# ──────────────────────────────────────────────────────────────────────

DAG_EDGES = [
    # Evidence → DonorSupply
    ("Organ", "DonorSupply"),
    ("BloodType", "DonorSupply"),
    ("Region", "DonorSupply"),
    # Evidence + DonorSupply → WaitCategory
    ("Organ", "WaitCategory"),
    ("BloodType", "WaitCategory"),
    ("Region", "WaitCategory"),
    ("DonorSupply", "WaitCategory"),
    # Evidence → MortalityRisk
    ("Organ", "MortalityRisk"),
    ("AgeGroup", "MortalityRisk"),
    ("Urgency", "MortalityRisk"),
    ("Region", "MortalityRisk"),
    # Organ + Region + WaitCategory → DelistingRisk
    ("Organ", "DelistingRisk"),
    ("Region", "DelistingRisk"),
    ("WaitCategory", "DelistingRisk"),
    # Organ + Region → CompetingOutcome (#206/#211, option A).
    # CompetingOutcome is now grounded directly in the center's OBSERVED 24-month
    # competing-risk outcomes (SRTR Table B7), not derived from the latent
    # WaitCategory/MortalityRisk/DelistingRisk states. Parent order here must match
    # the CPT axis order (Organ, Region) in build_competing_outcome_cpt.
    # MortalityRisk/DelistingRisk remain in the graph (queryable risk summaries)
    # but no longer feed CompetingOutcome.
    ("Organ", "CompetingOutcome"),
    ("Region", "CompetingOutcome"),
    # Organ + Region → GraftSurvival1yr
    ("Organ", "GraftSurvival1yr"),
    ("Region", "GraftSurvival1yr"),
    # CompetingOutcome + GraftSurvival1yr → CompoundSuccess
    ("CompetingOutcome", "CompoundSuccess"),
    ("GraftSurvival1yr", "CompoundSuccess"),
]

# ──────────────────────────────────────────────────────────────────────
# Node cardinalities and state names
# ──────────────────────────────────────────────────────────────────────

# compatibility with code that imports NODE_CARDS / NODE_STATE_NAMES directly.
NODE_CARDS = {
    "Organ": len(ORGANS),
    "BloodType": len(BLOOD_TYPES),
    "AgeGroup": len(AGE_GROUPS),
    "Urgency": len(URGENCY_LEVELS),
    "Region": len(REGIONS),
    "DonorSupply": len(DONOR_SUPPLY_STATES),
    "WaitCategory": len(WAIT_CATEGORY_STATES),
    "MortalityRisk": len(MORTALITY_RISK_STATES),
    "DelistingRisk": len(DELISTING_RISK_STATES),
    "CompetingOutcome": len(COMPETING_OUTCOME_STATES),
    "GraftSurvival1yr": len(GRAFT_SURVIVAL_STATES),
    "CompoundSuccess": len(COMPOUND_SUCCESS_STATES),
}

NODE_STATE_NAMES = {
    "Organ": ORGANS,
    "BloodType": BLOOD_TYPES,
    "AgeGroup": AGE_GROUPS,
    "Urgency": [str(u) for u in URGENCY_LEVELS],
    "Region": REGIONS,
    "DonorSupply": DONOR_SUPPLY_STATES,
    "WaitCategory": WAIT_CATEGORY_STATES,
    "MortalityRisk": MORTALITY_RISK_STATES,
    "DelistingRisk": DELISTING_RISK_STATES,
    "CompetingOutcome": COMPETING_OUTCOME_STATES,
    "GraftSurvival1yr": GRAFT_SURVIVAL_STATES,
    "CompoundSuccess": COMPOUND_SUCCESS_STATES,
}


def _build_node_cardinalities(regions: list[str]) -> dict[str, int]:
    """Build node cardinality dict for a dynamic region list."""
    return {
        "Organ": len(ORGANS),
        "BloodType": len(BLOOD_TYPES),
        "AgeGroup": len(AGE_GROUPS),
        "Urgency": len(URGENCY_LEVELS),
        "Region": len(regions),
        "DonorSupply": len(DONOR_SUPPLY_STATES),
        "WaitCategory": len(WAIT_CATEGORY_STATES),
        "MortalityRisk": len(MORTALITY_RISK_STATES),
        "DelistingRisk": len(DELISTING_RISK_STATES),
        "CompetingOutcome": len(COMPETING_OUTCOME_STATES),
        "GraftSurvival1yr": len(GRAFT_SURVIVAL_STATES),
        "CompoundSuccess": len(COMPOUND_SUCCESS_STATES),
    }


def _build_state_names(regions: list[str]) -> dict[str, list[str]]:
    """Build node state-name dict for a dynamic region list."""
    return {
        "Organ": ORGANS,
        "BloodType": BLOOD_TYPES,
        "AgeGroup": AGE_GROUPS,
        "Urgency": [str(u) for u in URGENCY_LEVELS],
        "Region": regions,
        "DonorSupply": DONOR_SUPPLY_STATES,
        "WaitCategory": WAIT_CATEGORY_STATES,
        "MortalityRisk": MORTALITY_RISK_STATES,
        "DelistingRisk": DELISTING_RISK_STATES,
        "CompetingOutcome": COMPETING_OUTCOME_STATES,
        "GraftSurvival1yr": GRAFT_SURVIVAL_STATES,
        "CompoundSuccess": COMPOUND_SUCCESS_STATES,
    }

# ──────────────────────────────────────────────────────────────────────
# Cached BBN models — keyed by granularity level
# ──────────────────────────────────────────────────────────────────────

_MODEL_CACHE: dict[str, tuple[BayesianNet, list[str]]] = {}


def _build_factor(
    name: str,
    cpt: np.ndarray,
    parents: list[str],
    node_cards: dict[str, int],
) -> Factor:
    """
    Construct a bbn_lite Factor from our numpy CPT array.

    Our CPT arrays have shape (node_card, parent1_card, parent2_card, ...).
    Factor expects variables=[node, parent1, parent2, ...] with matching
    cardinalities.
    """
    if not parents:
        # Root node — 1D prior
        return Factor([name], [node_cards[name]], cpt.flatten())

    variables = [name] + parents
    cardinalities = [node_cards[v] for v in variables]
    return Factor(variables, cardinalities, cpt)


def _get_parents(node: str) -> list[str]:
    """Get parent nodes from DAG_EDGES."""
    return [src for src, dst in DAG_EDGES if dst == node]


def build_model(granularity: str = "state") -> BayesianNet:
    """
    Construct the BayesianNet with CPDs.

    Cached per granularity level ("classic", "state", "full").
    Returns the BayesianNet model (inference is done via variable_elimination()).
    """
    if granularity in _MODEL_CACHE:
        model, _ = _MODEL_CACHE[granularity]
        return model

    start = time.perf_counter()

    # Get regions for this granularity level
    regions = get_regions(granularity)
    node_cards = _build_node_cardinalities(regions)

    # Build CPTs from data for this granularity
    cpts = build_all_cpts(granularity)

    # Construct lightweight model
    model = BayesianNet(DAG_EDGES)

    # Add CPDs
    for name, cpt_array in cpts.items():
        parents = _get_parents(name)
        factor = _build_factor(name, cpt_array, parents, node_cards)
        model.add_cpd(name, factor)

    # Validate
    if not model.check_model():
        raise RuntimeError(
            f"BBN model validation failed for granularity '{granularity}' "
            f"— CPDs are inconsistent with DAG"
        )

    elapsed = time.perf_counter() - start
    logger.info(
        "BBN model built in %.3fs (granularity=%s, %d regions): %d nodes, %d edges",
        elapsed, granularity, len(regions), len(model.nodes()), len(model.edges),
    )

    _MODEL_CACHE[granularity] = (model, regions)
    return model


def reset_model() -> None:
    """Reset all cached models (for testing)."""
    _MODEL_CACHE.clear()


# ──────────────────────────────────────────────────────────────────────
# Inference: query outcome probabilities for a patient × city
# ──────────────────────────────────────────────────────────────────────

def _query_city(
    model: BayesianNet,
    organ: str,
    blood_type: str,
    age_group: str,
    urgency: str,
    city: str,
    regions: list[str] | None = None,
    node_state_names: dict[str, list[str]] | None = None,
) -> dict:
    """
    Query the BBN for a single city (region).

    Parameters
    ----------
    regions : list[str] | None
        Valid region names for this model's granularity. If provided, the
        *city* argument is validated against this list. Falls back to the
        legacy REGIONS constant when None.
    node_state_names : dict[str, list[str]] | None
        Mapping from node name to state name list, used to convert
        string evidence values to integer indices.

    Returns dict with:
      - competing_outcome: P(transplant|mortality|delisting|still_waiting)
      - graft_survival: P(good|moderate|poor)
      - compound_success: P(success|partial|failure)
      - wait_category: P(short|moderate|long|very_long)
    """
    valid_regions = regions if regions is not None else REGIONS
    if city not in valid_regions:
        # #220: never answer for a different region than the one requested
        raise ValueError(f"Unknown BBN region: '{city}'")

    # Use module-level state names as fallback
    state_names = node_state_names if node_state_names is not None else NODE_STATE_NAMES

    # Convert string evidence to integer indices
    evidence = {
        "Organ": state_names["Organ"].index(organ),
        "BloodType": state_names["BloodType"].index(blood_type),
        "AgeGroup": state_names["AgeGroup"].index(age_group),
        "Urgency": state_names["Urgency"].index(urgency),
        "Region": state_names["Region"].index(city),
    }

    # Query each outcome node independently (matches pgmpy behavior)
    results = {}

    co = variable_elimination(model, ["CompetingOutcome"], evidence)
    results["competing_outcome"] = co["CompetingOutcome"].tolist()

    gs = variable_elimination(model, ["GraftSurvival1yr"], evidence)
    results["graft_survival"] = gs["GraftSurvival1yr"].tolist()

    cs = variable_elimination(model, ["CompoundSuccess"], evidence)
    results["compound_success"] = cs["CompoundSuccess"].tolist()

    wc = variable_elimination(model, ["WaitCategory"], evidence)
    results["wait_category"] = wc["WaitCategory"].tolist()

    return results


def _estimate_median_wait(wait_probs: list[float]) -> float:
    """
    Estimate median wait time from wait category probabilities.

    Maps discrete categories to representative months:
      short=3, moderate=9, long=18, very_long=36
    Returns expected value (probability-weighted average).
    """
    representative_months = [3.0, 9.0, 18.0, 36.0]
    return sum(p * m for p, m in zip(wait_probs, representative_months))


def _estimate_time_horizon_probs(wait_probs: list[float]) -> dict[str, float]:
    """
    Estimate P(transplant <= X months) from wait category distribution.

    Uses CDF interpolation from category boundaries:
      short covers [0, 6], moderate [6, 12], long [12, 24], very_long [24+]
    """
    # Cumulative: P(wait <= 6), P(wait <= 12), P(wait <= 24)
    p_6 = wait_probs[0]
    p_12 = wait_probs[0] + wait_probs[1]
    p_24 = wait_probs[0] + wait_probs[1] + wait_probs[2]
    p_36 = min(1.0, p_24 + wait_probs[3] * 0.5)  # Half of very_long by 36mo

    return {"p6": p_6, "p12": p_12, "p24": p_24, "p36": p_36}


def _scale_time_horizons(
    time_probs: dict[str, float], p_transplant_24: float
) -> tuple[float, float, float, float]:
    """Scale the within-24mo wait-category CDF to a given P(transplant<=24).

    Divides the 6/12/36mo cumulative by the TRUE 24mo cumulative (not a magic
    0.01 floor) to preserve the conditional shape: since p6<=p12<=p24_wait, the
    ratios are bounded in [0, 1], so results never exceed p_transplant_24. Only
    the exact-zero case is guarded. Fixes the old max(p24,0.01) denominator,
    which deflated p6/p12 by up to ~2x when <1% of mass fell within 24mo (#244).
    """
    p24w = time_probs["p24"]
    p24 = p_transplant_24
    if p24w <= 0:
        p6 = p12 = 0.0
        p36 = p24
    else:
        s = p_transplant_24 / p24w
        p6 = time_probs["p6"] * s
        p12 = time_probs["p12"] * s
        # p36 scales the 24→36mo INCREMENT with the conversion factor capped
        # at 1. On the production path s = (1-q) <= 1 and this is algebraically
        # identical to scaling the cumulative; but if a caller ever passes
        # p_transplant_24 > p24w (s > 1), cumulative scaling extrapolates the
        # excess into the 24-36mo window and clamps p36 to certainty for
        # exactly the long-wait cases this function exists to protect (#244).
        p36 = p24 + (time_probs["p36"] - p24w) * min(s, 1.0)
    p6 = max(0.0, min(p6, p24))
    p12 = max(p6, min(p12, p24))
    p36 = max(p24, min(p36, 1.0))
    return p6, p12, p24, p36


def _combine_outcomes(query_result: dict, mortality_modulation: float = 1.0) -> dict:
    """Combine WaitCategory timing with the observed CompetingOutcome (#206/#211).

    WaitCategory drives transplant *timing* (sensitive to blood type / region /
    donor supply, so the headline probability varies by patient). The
    empirically-grounded CompetingOutcome (the center's OBSERVED outcomes)
    supplies the competing-loss drain q — the share of terminal outcomes lost to
    death/delisting rather than transplant — and the split of the non-transplant
    mass into death / delisting / still-waiting. Returns transplant probabilities
    at 6/12/24/36 months plus the 24-month competing-risk breakdown (which sums
    to 1 with p_24).

    Option B (#238, closes the L-072 v1 trade-off): mortality_modulation
    scales the observed death hazard to the patient (age x urgency x MELD via
    competing_risks.get_patient_mortality_multiplier). Transplant hazard is
    never modulated (double-counting guard, plan Q4); delisting modulation is
    deferred until sourced patient-level delisting multipliers exist.
    """
    obs_tx, obs_death, obs_delist, obs_wait = query_result["competing_outcome"]

    # Option B (#238): modulate the observed vector by the patient's
    # mortality multiplier on the CAUSE-SPECIFIC HAZARD scale. Only the
    # death hazard is scaled — never the transplant hazard (double-counting
    # guard: WaitCategory already carries the patient's wait signal) and not
    # delisting (v1; no sourced patient-level delisting modulators). At the
    # reference multiplier 1.0 this is a bit-exact no-op, so the reference
    # patient recovers the center's observed vector exactly (the anchor).
    if mortality_modulation != 1.0:
        import math
        p_evt = min(obs_tx + obs_death + obs_delist, 1.0 - 1e-12)
        if p_evt > 1e-12:
            h_total = -math.log(1.0 - p_evt)
            h_tx = h_total * obs_tx / p_evt
            h_death = h_total * obs_death / p_evt * mortality_modulation
            h_delist = h_total * obs_delist / p_evt
            h_new = h_tx + h_death + h_delist
            p_evt_new = 1.0 - math.exp(-h_new)
            obs_tx = p_evt_new * h_tx / h_new
            obs_death = p_evt_new * h_death / h_new
            obs_delist = p_evt_new * h_delist / h_new
            obs_wait = max(0.0, 1.0 - p_evt_new)

    time_probs = _estimate_time_horizon_probs(query_result["wait_category"])

    terminal = obs_tx + obs_death + obs_delist
    q = (obs_death + obs_delist) / terminal if terminal > 1e-9 else 0.0
    p_24 = time_probs["p24"] * (1.0 - q)

    # Scale 6/12/36mo to p_24 using the true conditional denominator (#244).
    p_6, p_12, _, p_36 = _scale_time_horizons(time_probs, p_24)

    nt = obs_death + obs_delist + obs_wait
    rem = max(0.0, 1.0 - p_24)
    if nt > 1e-9:
        p_m, p_d, p_w = rem * obs_death / nt, rem * obs_delist / nt, rem * obs_wait / nt
    else:
        p_m = p_d = 0.0
        p_w = rem

    return {"p_6": p_6, "p_12": p_12, "p_24": p_24, "p_36": p_36,
            "p_mortality_24": p_m, "p_delisting_24": p_d, "p_waiting_24": p_w}


def _region_observed_n(organ: str, region: str, center_map: dict) -> int:
    """Total observed cohort size (SRTR Table B7 n) across a region's centers."""
    if not center_map:
        return 0
    from services.data_loader import get_data
    data = get_data()
    total = 0
    for c, r in center_map.items():
        if r != region:
            continue
        rec = data.observed_outcome(organ, c)
        if rec and rec.get("n"):
            total += int(rec["n"])
    return total


def _data_uncertainty_ci(p24: float, n: int) -> float:
    """Half-width of the data-sampling interval on p24 (#226).

    Replaces the old heuristic `max(0.03, 0.10*p24)`, which ignored cohort size
    (and imposed a 3-point floor at low probabilities). Uses the binomial
    standard error of the observed transplant proportion at the center's cohort
    n, so the band TIGHTENS for high-volume centers and WIDENS for sparse ones.

    Scope (honest labeling, plan D5): this is the *data-sampling* uncertainty in
    the observed rates — the source #226 flagged. It is NOT the full credible
    interval on p24, which would also propagate the WaitCategory-timing
    uncertainty; that requires the CPT-parameter Monte Carlo deferred to a
    follow-up. n=0 (no observed data for the region) → a wide, honest band.
    """
    import math
    if n >= 1:
        se = math.sqrt(max(p24 * (1.0 - p24), 1e-6) / n)
        return min(0.30, max(0.01, 1.96 * se))
    return 0.20


# ──────────────────────────────────────────────────────────────────────
# Main entry point: simulate_bbn (parallel to monte_carlo.simulate)
# ──────────────────────────────────────────────────────────────────────

def simulate_bbn(patient: PatientProfile) -> SimulationResult:
    """
    Run Bayesian Belief Network inference for all SRTR centers
    that perform the patient's organ.

    The BBN Region node size adapts to ``patient.bbn_granularity``:
      - "state": ~50 states — all centers
      - "full":  ~248 centers — all centers
    (The legacy 22-city "classic" mode was retired — #285/#293.)

    Centers sharing a region receive the same BBN probabilities but
    different post-transplant outcomes (center-level data).
    """
    start = time.perf_counter()

    granularity = getattr(patient, "bbn_granularity", "state")

    model = build_model(granularity)

    # Use dynamic region functions from bbn_parameterizer
    regions = get_regions(granularity)
    center_region_map = get_center_to_region_map(granularity)

    # Build state name mapping for index lookups
    state_names = _build_state_names(regions)

    organ = patient.organ
    blood_type = patient.blood_type
    age_group = age_to_group(patient.age)
    urgency = str(patient.urgency)

    # Option B (#238): patient-level mortality modulation for the observed
    # competing-risk vector (age x urgency x MELD; 1.0 for the reference
    # patient). Computed once — constant across centers for one patient.
    from services.competing_risks import get_patient_mortality_multiplier
    mort_modulation = get_patient_mortality_multiplier(
        organ, age=patient.age, urgency=patient.urgency, meld=patient.meld,
    )

    # Cache BBN results by region (many centers share a region)
    region_cache: dict[str, dict] = {}

    city_results: list[CityProbability] = []

    # One result per SRTR center (state / full granularity).
    from services.monte_carlo import _get_centers
    centers = _get_centers(organ)

    for center in centers:
        code = center.get("code", "")
        name = center.get("name", center.get("city", ""))
        state_full = center.get("state", center.get("state_abbr", ""))
        lat = center.get("lat")
        lon = center.get("lon")

        # Map center to BBN region using the granularity-aware map.
        # #220: a center with no region is SKIPPED with a log — the old
        # code silently answered with the alphabetically-first region.
        region = center_region_map.get(code)
        if region is None or region not in regions:
            logger.warning("No BBN region for center %s (region=%s) — skipped", code, region)
            continue

        # Run BBN inference (cached per region)
        if region not in region_cache:
            region_cache[region] = _query_city(
                model, organ, blood_type, age_group, urgency, region,
                regions=regions, node_state_names=state_names,
            )
        query_result = region_cache[region]

        oc = _combine_outcomes(query_result, mortality_modulation=mort_modulation)
        p_6, p_12, p_24, p_36 = oc["p_6"], oc["p_12"], oc["p_24"], oc["p_36"]
        p_mortality_24, p_delisting_24, p_waiting_24 = (
            oc["p_mortality_24"], oc["p_delisting_24"], oc["p_waiting_24"])

        median_wait = _estimate_median_wait(query_result["wait_category"])

        n_obs = _region_observed_n(organ, region, center_region_map)
        ci_half = _data_uncertainty_ci(p_24, n_obs)
        ci_lo = max(0.0, p_24 - ci_half)
        ci_hi = min(1.0, p_24 + ci_half)

        competing_risks_24 = {
            "p_transplant_24mo": round(p_24, 4),
            "p_mortality_24mo": round(p_mortality_24, 4),
            "p_delisting_24mo": round(p_delisting_24, 4),
            "p_still_waiting_24mo": round(p_waiting_24, 4),
        }

        # Center-level outcomes
        outcomes_data = None
        try:
            outcomes_data = build_outcomes_dict(patient.organ, city=name, p_transplant_24mo=p_24, center_code=code)
        except (KeyError, FileNotFoundError, ValueError):
            pass

        # Per-center historical trends (#288)
        trends_data = None
        try:
            from services.trends import get_center_trends
            trends_data = get_center_trends(patient.organ, code)
        except (KeyError, FileNotFoundError, ValueError):
            pass

        # Data-provenance tags (#300/#219 — previously null for BBN runs,
        # which read as "no degraded inputs" instead of "not measured")
        from services.provenance import center_data_quality
        degraded = center_data_quality(patient.organ, code)

        city_results.append(CityProbability(
            city=name,
            state=state_full,
            center_code=code,
            center_name=name,
            lat=lat,
            lon=lon,
            p_transplant_6mo=round(p_6, 4),
            p_transplant_12mo=round(p_12, 4),
            p_transplant_24mo=round(p_24, 4),
            p_transplant_36mo=round(p_36, 4),
            confidence_interval_95=(round(ci_lo, 4), round(ci_hi, 4)),
            median_wait_months=round(max(median_wait, 0.1), 2),
            competing_risks=competing_risks_24,
            outcomes=outcomes_data,
            trends=trends_data,
            data_quality=degraded or None,
        ))

    # L-067 (#304): optional user-defined center set (post-filter — the BBN
    # computes per-region, so restricting output is the meaningful operation).
    # An all-unknown shortlist raises, matching the MC engine's contract.
    if patient.center_codes:
        wanted = set(patient.center_codes)
        city_results = [c for c in city_results if c.center_code in wanted]
        if not city_results:
            raise ValueError(
                f"None of the requested center_codes perform {patient.organ} "
                f"transplants (or the codes are unknown)."
            )

    city_results.sort(key=lambda c: c.p_transplant_24mo, reverse=True)

    elapsed = time.perf_counter() - start
    logger.info(
        "BBN inference complete: %s %s (granularity=%s), %.3fs for %d centers (%d unique regions)",
        patient.organ, patient.blood_type, granularity, elapsed, len(city_results), len(region_cache),
    )

    dq_summary = None
    if city_results:
        from services.provenance import summarize
        dq_summary = summarize([c.data_quality or [] for c in city_results])
    from services.data_loader import get_data as _get_data
    vintage = _get_data().srtr_vintage()

    return SimulationResult(
        patient=patient,
        cities=city_results,
        iterations=0,
        elapsed_seconds=round(elapsed, 3),
        inference_mode="bayesian",
        data_quality=dq_summary,
        data_vintage=vintage,
    )
