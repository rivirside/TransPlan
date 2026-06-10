"""
Tests for the BBN inference engine (Phase 5 M1, Issue #38).

Validates:
  - DAG structure (nodes, edges, acyclicity)
  - Model construction and pgmpy validation
  - Inference produces valid probability distributions
  - Results match expected patterns for known inputs
  - simulate_bbn produces valid SimulationResult objects
  - Multi-granularity support (#206): classic (22 cities), state (~50), full (~248)
  - Edge cases and error handling
"""
import pytest

from models.schemas import PatientProfile
from services.bayesian_network import (
    DAG_EDGES,
    NODE_CARDS,
    NODE_STATE_NAMES,
    REGIONS,
    _build_node_cardinalities,
    _build_state_names,
    _estimate_median_wait,
    _estimate_time_horizon_probs,
    build_model,
    reset_model,
    simulate_bbn,
)
from services.bbn_parameterizer import get_regions
from services.data_loader import get_data, load_all


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True, scope="module")
def _ensure_data_loaded():
    """Load data once for the entire test module."""
    try:
        get_data()
    except RuntimeError:
        load_all()


@pytest.fixture(autouse=True)
def _reset():
    """Reset model cache between tests for isolation."""
    reset_model()
    yield
    reset_model()


# ──────────────────────────────────────────────────────────────────────
# DAG structure
# ──────────────────────────────────────────────────────────────────────


def test_dag_has_20_edges():
    # 20 after #211: CompetingOutcome's 3 latent parents (WaitCategory,
    # MortalityRisk, DelistingRisk) were replaced by 2 (Organ, Region).
    assert len(DAG_EDGES) == 20


def test_dag_has_12_nodes():
    all_nodes = set()
    for src, dst in DAG_EDGES:
        all_nodes.add(src)
        all_nodes.add(dst)
    assert len(all_nodes) == 12


def test_dag_evidence_nodes_have_no_parents():
    evidence_nodes = {"Organ", "BloodType", "AgeGroup", "Urgency", "Region"}
    child_nodes = {dst for _, dst in DAG_EDGES}
    for node in evidence_nodes:
        assert node not in child_nodes, f"Evidence node {node} should not be a child"


def test_node_cards_match_state_names():
    for node, card in NODE_CARDS.items():
        assert len(NODE_STATE_NAMES[node]) == card, (
            f"{node}: card={card} but {len(NODE_STATE_NAMES[node])} state names"
        )


# ──────────────────────────────────────────────────────────────────────
# Dynamic cardinalities / state names (#206)
# ──────────────────────────────────────────────────────────────────────


def test_build_node_cardinalities_classic():
    cards = _build_node_cardinalities(list(REGIONS))
    assert cards["Region"] == 22


def test_build_node_cardinalities_dynamic():
    fake_regions = ["RegionA", "RegionB", "RegionC"]
    cards = _build_node_cardinalities(fake_regions)
    assert cards["Region"] == 3
    # Non-region nodes unchanged
    assert cards["Organ"] == NODE_CARDS["Organ"]


def test_build_state_names_classic():
    names = _build_state_names(list(REGIONS))
    assert names["Region"] == list(REGIONS)


def test_build_state_names_dynamic():
    fake_regions = ["X", "Y"]
    names = _build_state_names(fake_regions)
    assert names["Region"] == ["X", "Y"]
    assert names["Organ"] == NODE_STATE_NAMES["Organ"]


# ──────────────────────────────────────────────────────────────────────
# Model construction — classic granularity
# ──────────────────────────────────────────────────────────────────────


def test_build_model_classic_succeeds():
    model = build_model("classic")
    assert model is not None


def test_model_classic_passes_check():
    model = build_model("classic")
    assert model.check_model()


def test_model_classic_has_correct_node_count():
    model = build_model("classic")
    assert len(model.nodes()) == 12


def test_model_classic_has_correct_edge_count():
    model = build_model("classic")
    assert len(model.edges) == 20


def test_build_model_caches():
    """Second call returns same object (cache hit)."""
    m1 = build_model("classic")
    m2 = build_model("classic")
    assert m1 is m2


# ──────────────────────────────────────────────────────────────────────
# Inference basics — classic granularity
# ──────────────────────────────────────────────────────────────────────


def _make_patient(**kwargs) -> PatientProfile:
    defaults = dict(
        organ="kidney", blood_type="O+", age=55,
        sex="male", urgency=2, bbn_granularity="classic",
    )
    defaults.update(kwargs)
    return PatientProfile(**defaults)


def test_simulate_bbn_classic_returns_22():
    patient = _make_patient(bbn_granularity="classic")
    result = simulate_bbn(patient)
    # Classic mode should only return results for the 22 BBN cities
    assert len(result.cities) <= 22


def test_simulate_bbn_inference_mode():
    result = simulate_bbn(_make_patient())
    assert result.inference_mode == "bayesian"


def test_simulate_bbn_iterations_zero():
    """BBN is exact inference — iterations should be 0."""
    result = simulate_bbn(_make_patient())
    assert result.iterations == 0


def test_simulate_bbn_elapsed_positive():
    result = simulate_bbn(_make_patient())
    assert result.elapsed_seconds > 0


def test_simulate_bbn_cities_ranked_descending():
    result = simulate_bbn(_make_patient())
    p24s = [c.p_transplant_24mo for c in result.cities]
    for i in range(len(p24s) - 1):
        assert p24s[i] >= p24s[i + 1], (
            f"Cities not sorted: {result.cities[i].city}={p24s[i]} < "
            f"{result.cities[i+1].city}={p24s[i+1]}"
        )


def test_simulate_bbn_probabilities_in_range():
    result = simulate_bbn(_make_patient())
    for c in result.cities:
        assert 0 <= c.p_transplant_6mo <= 1
        assert 0 <= c.p_transplant_12mo <= 1
        assert 0 <= c.p_transplant_24mo <= 1
        assert 0 <= c.p_transplant_36mo <= 1


def test_simulate_bbn_probabilities_monotonic():
    """P(transplant <= t) should be non-decreasing in t."""
    result = simulate_bbn(_make_patient())
    for c in result.cities:
        assert c.p_transplant_6mo <= c.p_transplant_12mo + 0.001
        assert c.p_transplant_12mo <= c.p_transplant_24mo + 0.001
        assert c.p_transplant_24mo <= c.p_transplant_36mo + 0.001


def test_simulate_bbn_median_wait_positive():
    result = simulate_bbn(_make_patient())
    for c in result.cities:
        assert c.median_wait_months > 0


def test_simulate_bbn_ci_contains_point_estimate():
    result = simulate_bbn(_make_patient())
    for c in result.cities:
        lo, hi = c.confidence_interval_95
        assert lo <= c.p_transplant_24mo <= hi, (
            f"{c.city}: p24={c.p_transplant_24mo} not in CI [{lo}, {hi}]"
        )


def test_simulate_bbn_competing_risks_sum():
    result = simulate_bbn(_make_patient())
    for c in result.cities:
        cr = c.competing_risks
        total = (cr["p_transplant_24mo"] + cr["p_mortality_24mo"] +
                 cr["p_delisting_24mo"] + cr["p_still_waiting_24mo"])
        assert abs(total - 1.0) < 0.01, (
            f"{c.city}: competing risks sum to {total}, expected ~1.0"
        )


def test_simulate_bbn_classic_all_22_cities_present():
    patient = _make_patient(bbn_granularity="classic")
    result = simulate_bbn(patient)
    result_cities = {c.city for c in result.cities}
    expected_cities = set(REGIONS)
    assert result_cities == expected_cities


# ──────────────────────────────────────────────────────────────────────
# Semantic: known patterns (classic mode)
# ──────────────────────────────────────────────────────────────────────


def test_heart_higher_p24_than_kidney():
    """Heart has 2.2mo median vs kidney 27.4mo -> much higher transplant prob."""
    heart = simulate_bbn(_make_patient(organ="heart"))
    kidney = simulate_bbn(_make_patient(organ="kidney"))

    heart_avg = sum(c.p_transplant_24mo for c in heart.cities) / max(len(heart.cities), 1)
    kidney_avg = sum(c.p_transplant_24mo for c in kidney.cities) / max(len(kidney.cities), 1)

    assert heart_avg > kidney_avg, (
        f"Heart avg p24={heart_avg:.3f} should exceed kidney avg={kidney_avg:.3f}"
    )


def test_ab_favorable_over_o():
    """AB+ blood type has lower wait multiplier -> higher p24."""
    ab = simulate_bbn(_make_patient(blood_type="AB+"))
    o = simulate_bbn(_make_patient(blood_type="O+"))

    ab_avg = sum(c.p_transplant_24mo for c in ab.cities) / max(len(ab.cities), 1)
    o_avg = sum(c.p_transplant_24mo for c in o.cities) / max(len(o.cities), 1)

    assert ab_avg > o_avg, (
        f"AB+ avg p24={ab_avg:.3f} should exceed O+ avg={o_avg:.3f}"
    )


def test_madison_near_top():
    """Madison has lowest city wait factor (0.51) -> should rank highly."""
    result = simulate_bbn(_make_patient())
    top_5_cities = [c.city for c in result.cities[:5]]
    assert "Madison" in top_5_cities, (
        f"Madison should be in top 5, got: {top_5_cities}"
    )


def test_sf_near_bottom():
    """San Francisco has highest city wait factor (2.12) -> should rank low."""
    result = simulate_bbn(_make_patient())
    bottom_5_cities = [c.city for c in result.cities[-5:]]
    assert "San Francisco" in bottom_5_cities, (
        f"San Francisco should be in bottom 5, got: {bottom_5_cities}"
    )


# ──────────────────────────────────────────────────────────────────────
# Different organ types (classic mode)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung", "pancreas", "intestine"])
def test_all_organs_produce_valid_results(organ):
    result = simulate_bbn(_make_patient(organ=organ))
    assert len(result.cities) <= 22
    for c in result.cities:
        assert 0 <= c.p_transplant_24mo <= 1


# ──────────────────────────────────────────────────────────────────────
# Multi-granularity tests (#206)
# ──────────────────────────────────────────────────────────────────────


def test_simulate_bbn_state_granularity():
    patient = _make_patient(bbn_granularity="state")
    result = simulate_bbn(patient)
    # State mode should return all centers for the organ (>>22)
    assert len(result.cities) >= 100


def test_simulate_bbn_full_granularity():
    patient = _make_patient(bbn_granularity="full")
    result = simulate_bbn(patient)
    # Full mode should also return all centers
    assert len(result.cities) >= 100


def test_build_model_state_granularity():
    model = build_model("state")
    assert model is not None
    assert model.check_model()
    assert len(model.nodes()) == 12


def test_build_model_full_granularity():
    model = build_model("full")
    assert model is not None
    assert model.check_model()
    assert len(model.nodes()) == 12


def test_get_regions_classic_has_22():
    regions = get_regions("classic")
    assert len(regions) == 22
    assert set(regions) == set(REGIONS)


def test_get_regions_state_more_than_classic():
    classic_regions = get_regions("classic")
    state_regions = get_regions("state")
    assert len(state_regions) > len(classic_regions)


def test_granularity_models_cached_independently():
    """Each granularity gets its own cached model."""
    m_classic = build_model("classic")
    m_state = build_model("state")
    assert m_classic is not m_state


# ──────────────────────────────────────────────────────────────────────
# Helper function tests
# ──────────────────────────────────────────────────────────────────────


def test_estimate_median_wait():
    # All probability on "short" (3 months)
    assert abs(_estimate_median_wait([1.0, 0.0, 0.0, 0.0]) - 3.0) < 0.01
    # All probability on "very_long" (36 months)
    assert abs(_estimate_median_wait([0.0, 0.0, 0.0, 1.0]) - 36.0) < 0.01
    # Uniform -> (3+9+18+36)/4 = 16.5
    assert abs(_estimate_median_wait([0.25, 0.25, 0.25, 0.25]) - 16.5) < 0.01


def test_estimate_time_horizon_probs():
    probs = _estimate_time_horizon_probs([0.3, 0.2, 0.3, 0.2])
    assert abs(probs["p6"] - 0.3) < 0.01
    assert abs(probs["p12"] - 0.5) < 0.01
    assert abs(probs["p24"] - 0.8) < 0.01
    assert probs["p36"] >= probs["p24"]


def test_estimate_time_horizon_monotonic():
    probs = _estimate_time_horizon_probs([0.1, 0.2, 0.3, 0.4])
    assert probs["p6"] <= probs["p12"] <= probs["p24"] <= probs["p36"]
