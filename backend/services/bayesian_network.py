"""
Bayesian Belief Network inference engine for transplant probability estimation.

Alternative to Monte Carlo simulation (Phase 5 M1, ADR-024).
Uses pgmpy's VariableElimination for exact inference on a 12-node DAG.

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
from services.trends import get_city_trends

logger = logging.getLogger(__name__)

# City → state abbreviation (mirrors monte_carlo.py)
_CITY_STATES = {
    "Pittsburgh": "PA", "Baltimore": "MD", "Philadelphia": "PA",
    "New York": "NY", "Minneapolis": "MN", "Madison": "WI",
    "Chicago": "IL", "Cleveland": "OH", "St. Louis": "MO",
    "Indianapolis": "IN", "Omaha": "NE", "Rochester": "MN",
    "Nashville": "TN", "Durham": "NC", "Miami": "FL",
    "Dallas": "TX", "Houston": "TX", "Portland": "OR",
    "Seattle": "WA", "San Francisco": "CA", "Los Angeles": "CA",
    "Palo Alto": "CA",
}

# Inverted: state abbreviation → first BBN region in that state
_STATE_TO_REGION = {}
for _city, _st in _CITY_STATES.items():
    _STATE_TO_REGION.setdefault(_st, _city)

# Center code → BBN region cache (built lazily)
_CENTER_REGION_MAP: dict[str, str] | None = None


def _get_center_region_map() -> dict[str, str]:
    """Build center_code -> BBN region (one of 22 cities) mapping."""
    global _CENTER_REGION_MAP
    if _CENTER_REGION_MAP is not None:
        return _CENTER_REGION_MAP

    from services.data_loader import get_data
    data = get_data()

    # 1) Direct mapping from srtr-center-mapping.json
    mapping = data.center_mapping.get("cities", {})
    code_to_region: dict[str, str] = {}
    for city_name, info in mapping.items():
        primary = info.get("primary", "")
        if primary:
            code_to_region[primary] = city_name
        for alt in info.get("alternates", []):
            code_to_region[alt] = city_name

    # 2) State-based fallback for unmapped centers
    all_centers = data.all_centers.get("centers", {})
    for code, info in all_centers.items():
        if code not in code_to_region:
            st = info.get("state_abbr", "")
            code_to_region[code] = _STATE_TO_REGION.get(st, "Nashville")

    _CENTER_REGION_MAP = code_to_region
    return code_to_region

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
    # WaitCategory + MortalityRisk + DelistingRisk → CompetingOutcome
    ("WaitCategory", "CompetingOutcome"),
    ("MortalityRisk", "CompetingOutcome"),
    ("DelistingRisk", "CompetingOutcome"),
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

# Legacy module-level dicts (classic 22-city model) — kept for backward
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
        # Fallback: first region in list (safe default)
        city = valid_regions[0]

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


# ──────────────────────────────────────────────────────────────────────
# Main entry point: simulate_bbn (parallel to monte_carlo.simulate)
# ──────────────────────────────────────────────────────────────────────

def simulate_bbn(patient: PatientProfile) -> SimulationResult:
    """
    Run Bayesian Belief Network inference for all SRTR centers
    that perform the patient's organ.

    The BBN Region node size adapts to ``patient.bbn_granularity``:
      - "classic": 22 cities — only centers mapped to those 22 BBN cities
      - "state":   ~50 states — all centers
      - "full":    ~248 centers — all centers

    Centers sharing a region receive the same BBN probabilities but
    different post-transplant outcomes (center-level data).
    """
    start = time.perf_counter()

    granularity = getattr(patient, "bbn_granularity", "state")

    model = build_model(granularity)

    # Use dynamic region functions from bbn_parameterizer
    regions = get_regions(granularity)
    center_region_map = get_center_to_region_map(granularity)

    # Keep legacy map for backward-compatible trend lookups
    legacy_center_region_map = _get_center_region_map()

    # Build state name mapping for index lookups
    state_names = _build_state_names(regions)

    organ = patient.organ
    blood_type = patient.blood_type
    age_group = age_to_group(patient.age)
    urgency = str(patient.urgency)

    # Cache BBN results by region (many centers share a region)
    region_cache: dict[str, dict] = {}

    city_results: list[CityProbability] = []

    if granularity == "classic":
        # Classic mode: one result per BBN region (22 cities).
        # Use the region name as the display city and look up representative
        # center info for lat/lon/state from the legacy _CITY_STATES mapping.
        for region_name in regions:
            query_result = _query_city(
                model, organ, blood_type, age_group, urgency, region_name,
                regions=regions, node_state_names=state_names,
            )
            region_cache[region_name] = query_result

            state_abbr = _CITY_STATES.get(region_name, "")

            co_probs = query_result["competing_outcome"]
            p_transplant_24 = co_probs[0]
            p_mortality_24 = co_probs[1]
            p_delisting_24 = co_probs[2]
            p_waiting_24 = co_probs[3]

            wait_probs = query_result["wait_category"]
            time_probs = _estimate_time_horizon_probs(wait_probs)
            p_6 = time_probs["p6"] * p_transplant_24 / max(time_probs["p24"], 0.01)
            p_12 = time_probs["p12"] * p_transplant_24 / max(time_probs["p24"], 0.01)
            p_24 = p_transplant_24
            p_36 = min(1.0, time_probs["p36"] * p_transplant_24 / max(time_probs["p24"], 0.01))

            p_6 = max(0.0, min(p_6, p_24))
            p_12 = max(p_6, min(p_12, p_24))
            p_36 = max(p_24, min(p_36, 1.0))

            median_wait = _estimate_median_wait(wait_probs)

            ci_half = max(0.03, p_24 * 0.10)
            ci_lo = max(0.0, p_24 - ci_half)
            ci_hi = min(1.0, p_24 + ci_half)

            competing_risks_24 = {
                "p_transplant_24mo": round(p_24, 4),
                "p_mortality_24mo": round(p_mortality_24, 4),
                "p_delisting_24mo": round(p_delisting_24, 4),
                "p_still_waiting_24mo": round(p_waiting_24, 4),
            }

            outcomes_data = None
            try:
                outcomes_data = build_outcomes_dict(patient.organ, city=region_name, p_transplant_24mo=p_24)
            except (KeyError, FileNotFoundError, ValueError):
                pass

            trends_data = None
            try:
                trends_data = get_city_trends(patient.organ, region_name)
            except (KeyError, FileNotFoundError, ValueError):
                pass

            city_results.append(CityProbability(
                city=region_name,
                state=state_abbr,
                center_code="",
                center_name=region_name,
                lat=None,
                lon=None,
                p_transplant_6mo=round(p_6, 4),
                p_transplant_12mo=round(p_12, 4),
                p_transplant_24mo=round(p_24, 4),
                p_transplant_36mo=round(p_36, 4),
                confidence_interval_95=(round(ci_lo, 4), round(ci_hi, 4)),
                median_wait_months=round(max(median_wait, 0.1), 2),
                competing_risks=competing_risks_24,
                outcomes=outcomes_data,
                trends=trends_data,
            ))
    else:
        # State / full mode: one result per SRTR center.
        from services.monte_carlo import _get_centers
        centers = _get_centers(organ)

        for center in centers:
            code = center.get("code", "")
            name = center.get("name", center.get("city", ""))
            state_full = center.get("state", center.get("state_abbr", ""))
            lat = center.get("lat")
            lon = center.get("lon")

            # Map center to BBN region using the granularity-aware map
            region = center_region_map.get(code, regions[0] if regions else "Nashville")
            if region not in regions:
                region = regions[0] if regions else "Nashville"

            # Run BBN inference (cached per region)
            if region not in region_cache:
                region_cache[region] = _query_city(
                    model, organ, blood_type, age_group, urgency, region,
                    regions=regions, node_state_names=state_names,
                )
            query_result = region_cache[region]

            co_probs = query_result["competing_outcome"]
            p_transplant_24 = co_probs[0]
            p_mortality_24 = co_probs[1]
            p_delisting_24 = co_probs[2]
            p_waiting_24 = co_probs[3]

            wait_probs = query_result["wait_category"]
            time_probs = _estimate_time_horizon_probs(wait_probs)
            p_6 = time_probs["p6"] * p_transplant_24 / max(time_probs["p24"], 0.01)
            p_12 = time_probs["p12"] * p_transplant_24 / max(time_probs["p24"], 0.01)
            p_24 = p_transplant_24
            p_36 = min(1.0, time_probs["p36"] * p_transplant_24 / max(time_probs["p24"], 0.01))

            p_6 = max(0.0, min(p_6, p_24))
            p_12 = max(p_6, min(p_12, p_24))
            p_36 = max(p_24, min(p_36, 1.0))

            median_wait = _estimate_median_wait(wait_probs)

            ci_half = max(0.03, p_24 * 0.10)
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

            # Trends use the legacy 22-city region for lookup
            legacy_region = legacy_center_region_map.get(code, center.get("city", "Nashville"))
            trends_data = None
            try:
                trends_data = get_city_trends(patient.organ, legacy_region)
            except (KeyError, FileNotFoundError, ValueError):
                pass

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
            ))

    city_results.sort(key=lambda c: c.p_transplant_24mo, reverse=True)

    elapsed = time.perf_counter() - start
    logger.info(
        "BBN inference complete: %s %s (granularity=%s), %.3fs for %d centers (%d unique regions)",
        patient.organ, patient.blood_type, granularity, elapsed, len(city_results), len(region_cache),
    )

    return SimulationResult(
        patient=patient,
        cities=city_results,
        iterations=0,
        elapsed_seconds=round(elapsed, 3),
        inference_mode="bayesian",
    )
