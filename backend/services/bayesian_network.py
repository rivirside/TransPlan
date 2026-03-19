"""
Bayesian Belief Network inference engine for transplant probability estimation.

Alternative to Monte Carlo simulation (Phase 5 M1, ADR-024).
Uses pgmpy's VariableElimination for exact inference on a 12-node DAG.

The BBN is constructed once and cached. For each patient query, evidence is set
on the 5 observable nodes and marginal probabilities are computed for all
outcome nodes across all 22 cities (Region iterated as evidence).

Typical query time: < 100ms for all 22 cities (vs ~2s for Monte Carlo).
"""
import logging
import time

import numpy as np
from pgmpy.factors.discrete import TabularCPD
from pgmpy.inference import VariableElimination
from pgmpy.models import DiscreteBayesianNetwork as PgmpyBN

from models.schemas import CityProbability, PatientProfile, SimulationResult
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

# ──────────────────────────────────────────────────────────────────────
# Cached BBN model
# ──────────────────────────────────────────────────────────────────────

_model: PgmpyBN | None = None
_inference: VariableElimination | None = None


def _build_cpd(name: str, cpt: np.ndarray, parents: list[str]) -> TabularCPD:
    """
    Construct a pgmpy TabularCPD from our numpy CPT array.

    For a node with k states and parents with cardinalities [c1, c2, ...],
    pgmpy expects a (k, c1*c2*...) 2D array where columns enumerate
    all parent state combinations in row-major order.
    """
    card = NODE_CARDS[name]
    state_names = {name: NODE_STATE_NAMES[name]}

    if not parents:
        # Root node — 1D prior
        values = cpt.reshape(card, 1)
        return TabularCPD(
            variable=name,
            variable_card=card,
            values=values,
            state_names=state_names,
        )

    parent_cards = [NODE_CARDS[p] for p in parents]
    for p in parents:
        state_names[p] = NODE_STATE_NAMES[p]

    # Reshape CPT to 2D: (node_card, product_of_parent_cards)
    # Our CPT arrays have shape (node_card, parent1_card, parent2_card, ...)
    # pgmpy wants (node_card, parent1_card * parent2_card * ...) in C-order
    total_parent_configs = int(np.prod(parent_cards))
    values = cpt.reshape(card, total_parent_configs)

    return TabularCPD(
        variable=name,
        variable_card=card,
        values=values,
        evidence=parents,
        evidence_card=parent_cards,
        state_names=state_names,
    )


def _get_parents(node: str) -> list[str]:
    """Get parent nodes from DAG_EDGES."""
    return [src for src, dst in DAG_EDGES if dst == node]


def build_model() -> tuple[PgmpyBN, VariableElimination]:
    """
    Construct the pgmpy BayesianNetwork and VariableElimination engine.
    Cached after first call.
    """
    global _model, _inference

    if _model is not None and _inference is not None:
        return _model, _inference

    start = time.perf_counter()

    # Build CPTs from data
    cpts = build_all_cpts()

    # Construct pgmpy model
    model = PgmpyBN(DAG_EDGES)

    # Add CPDs
    cpd_list = []
    for name, cpt_array in cpts.items():
        parents = _get_parents(name)
        cpd = _build_cpd(name, cpt_array, parents)
        cpd_list.append(cpd)

    model.add_cpds(*cpd_list)

    # Validate
    if not model.check_model():
        raise RuntimeError("BBN model validation failed — CPDs are inconsistent with DAG")

    inference = VariableElimination(model)

    elapsed = time.perf_counter() - start
    logger.info("BBN model built in %.3fs: %d nodes, %d edges",
                elapsed, len(model.nodes()), len(model.edges()))

    _model = model
    _inference = inference
    return model, inference


def reset_model() -> None:
    """Reset cached model (for testing)."""
    global _model, _inference
    _model = None
    _inference = None


# ──────────────────────────────────────────────────────────────────────
# Inference: query outcome probabilities for a patient × city
# ──────────────────────────────────────────────────────────────────────

def _query_city(
    inference: VariableElimination,
    organ: str,
    blood_type: str,
    age_group: str,
    urgency: str,
    city: str,
) -> dict:
    """
    Query the BBN for a single city (region).

    Returns dict with:
      - competing_outcome: P(transplant|mortality|delisting|still_waiting)
      - graft_survival: P(good|moderate|poor)
      - compound_success: P(success|partial|failure)
      - wait_category: P(short|moderate|long|very_long)
    """
    evidence = {
        "Organ": organ,
        "BloodType": blood_type,
        "AgeGroup": age_group,
        "Urgency": urgency,
        "Region": city,
    }

    results = {}

    # Query CompetingOutcome
    co_result = inference.query(["CompetingOutcome"], evidence=evidence)
    results["competing_outcome"] = co_result.values.tolist()

    # Query GraftSurvival1yr
    gs_result = inference.query(["GraftSurvival1yr"], evidence=evidence)
    results["graft_survival"] = gs_result.values.tolist()

    # Query CompoundSuccess
    cs_result = inference.query(["CompoundSuccess"], evidence=evidence)
    results["compound_success"] = cs_result.values.tolist()

    # Query WaitCategory (useful for median wait estimation)
    wc_result = inference.query(["WaitCategory"], evidence=evidence)
    results["wait_category"] = wc_result.values.tolist()

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
    Run Bayesian Belief Network inference for all 22 cities.

    Returns a SimulationResult with the same structure as Monte Carlo,
    enabling direct comparison and seamless frontend rendering.
    """
    start = time.perf_counter()

    _, inference = build_model()

    # Map patient profile to evidence state names
    organ = patient.organ
    blood_type = patient.blood_type
    age_group = age_to_group(patient.age)
    urgency = str(patient.urgency)

    city_results: list[CityProbability] = []

    for city in REGIONS:
        state = _CITY_STATES.get(city, "")

        # Run BBN inference for this city
        query_result = _query_city(inference, organ, blood_type, age_group, urgency, city)

        # Extract competing outcome probabilities
        co_probs = query_result["competing_outcome"]
        p_transplant_24 = co_probs[0]  # P(transplant wins at 24mo)
        p_mortality_24 = co_probs[1]
        p_delisting_24 = co_probs[2]
        p_waiting_24 = co_probs[3]

        # Estimate time-horizon probabilities from wait category distribution
        wait_probs = query_result["wait_category"]
        # Scale by P(transplant wins) to get conditional transplant probabilities
        time_probs = _estimate_time_horizon_probs(wait_probs)
        p_6 = time_probs["p6"] * p_transplant_24 / max(time_probs["p24"], 0.01)
        p_12 = time_probs["p12"] * p_transplant_24 / max(time_probs["p24"], 0.01)
        p_24 = p_transplant_24
        p_36 = min(1.0, time_probs["p36"] * p_transplant_24 / max(time_probs["p24"], 0.01))

        # Clamp to [0, 1] and ensure monotonicity
        p_6 = max(0.0, min(p_6, p_24))
        p_12 = max(p_6, min(p_12, p_24))
        p_36 = max(p_24, min(p_36, 1.0))

        # Estimate median wait
        median_wait = _estimate_median_wait(wait_probs)

        # Uncertainty band: BBN inference is deterministic (exact Variable Elimination),
        # so this is NOT a sampling confidence interval. The ±10% band represents
        # epistemic uncertainty from CPT discretization (continuous → tercile categories)
        # and conditional independence assumptions. See issue #54.
        ci_half = max(0.03, p_24 * 0.10)
        ci_lo = max(0.0, p_24 - ci_half)
        ci_hi = min(1.0, p_24 + ci_half)

        competing_risks_24 = {
            "p_transplant_24mo": round(p_24, 4),
            "p_mortality_24mo": round(p_mortality_24, 4),
            "p_delisting_24mo": round(p_delisting_24, 4),
            "p_still_waiting_24mo": round(p_waiting_24, 4),
        }

        # Post-transplant outcomes (reuse existing service)
        outcomes_data = None
        try:
            outcomes_data = build_outcomes_dict(patient.organ, city, p_24)
        except (KeyError, FileNotFoundError, ValueError) as e:
            logger.warning("Outcomes data unavailable for %s/%s: %s", patient.organ, city, e)

        # Historical trends (reuse existing service)
        trends_data = None
        try:
            trends_data = get_city_trends(patient.organ, city)
        except (KeyError, FileNotFoundError, ValueError) as e:
            logger.warning("Trends data unavailable for %s/%s: %s", patient.organ, city, e)

        city_results.append(CityProbability(
            city=city,
            state=state,
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

    # Rank by 24-month transplant probability, descending
    city_results.sort(key=lambda c: c.p_transplant_24mo, reverse=True)

    elapsed = time.perf_counter() - start
    logger.info(
        "BBN inference complete: %s %s, %.3fs for %d cities",
        patient.organ, patient.blood_type, elapsed, len(city_results),
    )

    return SimulationResult(
        patient=patient,
        cities=city_results,
        iterations=0,  # BBN is exact inference, not iterative
        elapsed_seconds=round(elapsed, 3),
        inference_mode="bayesian",
    )
