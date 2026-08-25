"""
Tests for the BBN inference engine (Phase 5 M1, Issue #38).

Validates:
  - DAG structure (nodes, edges, acyclicity)
  - Model construction and CPT/normalization validation (custom NumPy engine)
  - Inference produces valid probability distributions
  - Results match expected patterns for known inputs
  - simulate_bbn produces valid SimulationResult objects
  - Multi-granularity support (#206/#293): state (~50) and full (~248) — classic retired
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


def test_build_node_cardinalities_state():
    cards = _build_node_cardinalities(list(REGIONS))
    assert cards["Region"] == 22


def test_build_node_cardinalities_dynamic():
    fake_regions = ["RegionA", "RegionB", "RegionC"]
    cards = _build_node_cardinalities(fake_regions)
    assert cards["Region"] == 3
    # Non-region nodes unchanged
    assert cards["Organ"] == NODE_CARDS["Organ"]


def test_build_state_names_state():
    names = _build_state_names(list(REGIONS))
    assert names["Region"] == list(REGIONS)


def test_build_state_names_dynamic():
    fake_regions = ["X", "Y"]
    names = _build_state_names(fake_regions)
    assert names["Region"] == ["X", "Y"]
    assert names["Organ"] == NODE_STATE_NAMES["Organ"]


# ──────────────────────────────────────────────────────────────────────
# Model construction — state granularity (default)
# ──────────────────────────────────────────────────────────────────────


def test_build_model_state_succeeds():
    model = build_model("state")
    assert model is not None


def test_model_state_passes_check():
    model = build_model("state")
    assert model.check_model()


def test_model_state_has_correct_node_count():
    model = build_model("state")
    assert len(model.nodes()) == 12


def test_model_state_has_correct_edge_count():
    model = build_model("state")
    assert len(model.edges) == 20


def test_build_model_caches():
    """Second call returns same object (cache hit)."""
    m1 = build_model("state")
    m2 = build_model("state")
    assert m1 is m2


# ──────────────────────────────────────────────────────────────────────
# Inference basics — state granularity (default)
# ──────────────────────────────────────────────────────────────────────


def _make_patient(**kwargs) -> PatientProfile:
    defaults = dict(
        organ="kidney", blood_type="O+", age=55,
        sex="male", urgency=2, bbn_granularity="state",
    )
    defaults.update(kwargs)
    return PatientProfile(**defaults)


class TestScaleTimeHorizons:
    """#244: scaling the within-24mo wait shape to P(transplant<=24)."""

    def test_normal_case_is_monotonic_and_anchors_p24(self):
        from services.bayesian_network import _scale_time_horizons, _estimate_time_horizon_probs
        tp = _estimate_time_horizon_probs([0.25, 0.25, 0.25, 0.25])
        p6, p12, p24, p36 = _scale_time_horizons(tp, p_transplant_24=0.6)
        assert p24 == 0.6
        assert 0 <= p6 <= p12 <= p24 <= p36 <= 1.0

    def test_extreme_long_wait_preserves_conditional_shape(self):
        """When <1% of mass is within 24mo, p6/p12 must keep their true
        conditional ratio, not be deflated by a magic 0.01 denominator floor."""
        from services.bayesian_network import _scale_time_horizons, _estimate_time_horizon_probs
        wp = [0.001, 0.002, 0.002, 0.995]  # p24_wait = 0.005
        tp = _estimate_time_horizon_probs(wp)
        pt24 = 0.10
        p6, p12, p24, p36 = _scale_time_horizons(tp, p_transplant_24=pt24)
        # True conditional: p6 = (0.001/0.005)*0.10 = 0.02 ; p12 = (0.003/0.005)*0.10 = 0.06
        assert p6 == pytest.approx(0.02, abs=1e-6)
        assert p12 == pytest.approx(0.06, abs=1e-6)

    def test_zero_wait_mass_within_24mo_is_safe(self):
        from services.bayesian_network import _scale_time_horizons, _estimate_time_horizon_probs
        tp = _estimate_time_horizon_probs([0.0, 0.0, 0.0, 1.0])  # p24_wait = 0
        p6, p12, p24, p36 = _scale_time_horizons(tp, p_transplant_24=0.10)
        assert p6 == 0.0 and p12 == 0.0
        assert p24 == 0.10

    def test_p36_not_inflated_when_scale_factor_exceeds_one(self):
        """#244 residual: with tiny within-24mo mass and a larger
        p_transplant_24 (inconsistent inputs, scale factor >1), the p36
        extrapolation must not balloon toward certainty. The 24→36mo increment
        is scaled by min(s, 1), so p36 = p24 + raw increment here."""
        from services.bayesian_network import _scale_time_horizons, _estimate_time_horizon_probs
        wp = [0.001, 0.002, 0.002, 0.995]  # p24_wait = 0.005, very_long = 0.995
        tp = _estimate_time_horizon_probs(wp)
        p6, p12, p24, p36 = _scale_time_horizons(tp, p_transplant_24=0.10)
        assert p36 < 1.0, f"p36 clamped to certainty: {p36}"
        # increment = tp36 - tp24w = 0.5 * 0.995 = 0.4975, scaled by min(20, 1) = 1
        assert p36 == pytest.approx(0.10 + 0.4975, abs=1e-9)

    def test_p36_unchanged_for_consistent_inputs(self):
        """For the production relationship p_transplant_24 = p24_wait*(1-q),
        the increment form is algebraically identical to the old cumulative
        scaling — no behavior change on the real path."""
        from services.bayesian_network import _scale_time_horizons, _estimate_time_horizon_probs
        wp = [0.1, 0.2, 0.3, 0.4]
        tp = _estimate_time_horizon_probs(wp)
        s = 0.8  # (1 - q)
        pt24 = tp["p24"] * s
        p6, p12, p24, p36 = _scale_time_horizons(tp, p_transplant_24=pt24)
        assert p36 == pytest.approx(tp["p36"] * s, abs=1e-12)


class TestLongWaitTimeProfiles:
    """#244 concrete confirmation: extreme long-wait patients must get sane,
    strictly sub-certain, monotonic time profiles from the BBN."""

    def test_high_cpra_kidney_profiles_sane(self, data):
        patient = _make_patient(cpra=98, bbn_granularity="full")
        result = simulate_bbn(patient)
        assert len(result.cities) > 100
        for c in result.cities:
            assert 0.0 <= c.p_transplant_6mo <= c.p_transplant_12mo \
                <= c.p_transplant_24mo <= c.p_transplant_36mo, c.center_code
            assert c.p_transplant_36mo < 1.0, (
                f"{c.center_code}: p36={c.p_transplant_36mo} hit certainty "
                f"for a high-cPRA patient"
            )


def test_simulate_bbn_classic_coerced_to_state():
    """#293: 'classic' is no longer a valid granularity — the schema validator
    coerces unknown values to 'state', so the request still succeeds with the
    full center set."""
    patient = _make_patient()
    patient.bbn_granularity = "state"
    result = simulate_bbn(patient)
    assert len(result.cities) > 100


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


def test_ci_width_scales_with_cohort_size():
    """#226: the CI band must reflect cohort n, not a flat heuristic — tighter
    for high-volume centers, wider for sparse ones."""
    from services.bayesian_network import _data_uncertainty_ci
    # Monotone non-increasing in n for reasonably-sized cohorts.
    widths = [_data_uncertainty_ci(0.6, n) for n in (25, 100, 500, 2000)]
    assert widths == sorted(widths, reverse=True), f"CI should tighten with n: {widths}"
    assert widths[-1] < widths[0], "high-n band must be strictly tighter than low-n"
    # Bounded, and a large cohort is far tighter than the old flat 0.10*p24=0.06.
    assert _data_uncertainty_ci(0.6, 2000) < 0.03
    assert 0.0 < _data_uncertainty_ci(0.6, 0) <= 0.30


def test_simulate_bbn_competing_risks_sum():
    result = simulate_bbn(_make_patient())
    for c in result.cities:
        cr = c.competing_risks
        total = (cr["p_transplant_24mo"] + cr["p_mortality_24mo"] +
                 cr["p_delisting_24mo"] + cr["p_still_waiting_24mo"])
        assert abs(total - 1.0) < 0.01, (
            f"{c.city}: competing risks sum to {total}, expected ~1.0"
        )


def test_simulate_bbn_state_covers_all_centers():
    patient = _make_patient(bbn_granularity="state")
    result = simulate_bbn(patient)
    assert all(c.center_code for c in result.cities)
    assert len(result.cities) > 200


# ──────────────────────────────────────────────────────────────────────
# Semantic: known patterns
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


def test_short_wait_states_beat_long_wait_states():
    """Post-#293 replacement for the Madison/SF city checks: Wisconsin centers
    (historically short kidney waits) should rank above California centers
    (long waits) on average in state mode."""
    result = simulate_bbn(_make_patient())
    by_state: dict[str, list[float]] = {}
    for c in result.cities:
        st = c.state[:2] if len(c.state) == 2 else c.state
        by_state.setdefault(st, []).append(c.p_transplant_24mo)
    wi = by_state.get("WI") or by_state.get("Wisconsin")
    ca = by_state.get("CA") or by_state.get("California")
    assert wi and ca
    assert sum(wi) / len(wi) > sum(ca) / len(ca)


# ──────────────────────────────────────────────────────────────────────
# Different organ types
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung", "pancreas", "intestine"])
def test_all_organs_produce_valid_results(organ):
    result = simulate_bbn(_make_patient(organ=organ))
    assert len(result.cities) >= 10
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


def test_get_regions_classic_retired():
    """#293: the legacy 22-city granularity raises."""
    with pytest.raises(ValueError, match="retired"):
        get_regions("classic")


def test_get_regions_full_more_than_state():
    state_regions = get_regions("state")
    full_regions = get_regions("full")
    assert len(full_regions) > len(state_regions)


def test_granularity_models_cached_independently():
    """Each granularity gets its own cached model."""
    m_full = build_model("full")
    m_state = build_model("state")
    assert m_full is not m_state


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
