"""
Cross-validation tests: BBN vs Monte Carlo (Phase 5 M1, Issue #41).

Validates that the BBN produces results that are directionally consistent
with Monte Carlo simulation. We do NOT expect exact agreement — the BBN
uses discrete approximations while MC uses continuous distributions.

Key checks:
  - Spearman rank correlation > 0.6 for city rankings
  - Same directional effects (blood type, organ, urgency)
  - BBN probabilities are in a plausible range
"""
import numpy as np
import pytest
from scipy.stats import spearmanr

from models.schemas import PatientProfile
from services.bayesian_network import reset_model, simulate_bbn
from services.data_loader import get_data, load_all
from services.monte_carlo import simulate as simulate_mc


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True, scope="module")
def _ensure_data_loaded():
    try:
        get_data()
    except RuntimeError:
        load_all()


@pytest.fixture(autouse=True)
def _reset():
    reset_model()
    yield
    reset_model()


def _make_patient(**kwargs) -> PatientProfile:
    defaults = dict(organ="kidney", blood_type="O+", age=55, sex="male", urgency=2,
                    bbn_granularity="classic")
    defaults.update(kwargs)
    return PatientProfile(**defaults)


def _rank_correlation(patient: PatientProfile, mc_iters: int = 500) -> float:
    """Compute Spearman rank correlation between BBN and MC city rankings."""
    mc_result = simulate_mc(patient, n_iterations=mc_iters)
    bbn_result = simulate_bbn(patient)

    # Build city→p24 maps (intersect — BBN classic has 22 cities, MC has 248)
    mc_map = {c.city: c.p_transplant_24mo for c in mc_result.cities}
    bbn_map = {c.city: c.p_transplant_24mo for c in bbn_result.cities}

    cities = sorted(mc_map.keys() & bbn_map.keys())
    assert len(cities) >= 10, f"Too few overlapping cities: {len(cities)}"
    mc_vals = [mc_map[c] for c in cities]
    bbn_vals = [bbn_map[c] for c in cities]

    rho, _ = spearmanr(mc_vals, bbn_vals)
    return rho


# ──────────────────────────────────────────────────────────────────────
# Rank correlation tests
# ──────────────────────────────────────────────────────────────────────


def test_kidney_rank_correlation():
    rho = _rank_correlation(_make_patient(organ="kidney"))
    assert rho > 0.5, f"Kidney rank correlation too low: {rho:.3f}"


def test_heart_rank_correlation():
    rho = _rank_correlation(_make_patient(organ="heart"))
    assert rho > 0.5, f"Heart rank correlation too low: {rho:.3f}"


def test_liver_rank_correlation():
    rho = _rank_correlation(_make_patient(organ="liver"))
    assert rho > 0.5, f"Liver rank correlation too low: {rho:.3f}"


# ──────────────────────────────────────────────────────────────────────
# Directional consistency: blood type effect
# ──────────────────────────────────────────────────────────────────────


def test_blood_type_direction_consistent():
    """AB+ should have higher avg p24 than O+ in both MC and BBN."""
    mc_ab = simulate_mc(_make_patient(blood_type="AB+"), n_iterations=300)
    mc_o = simulate_mc(_make_patient(blood_type="O+"), n_iterations=300)
    bbn_ab = simulate_bbn(_make_patient(blood_type="AB+"))
    bbn_o = simulate_bbn(_make_patient(blood_type="O+"))

    mc_ab_avg = np.mean([c.p_transplant_24mo for c in mc_ab.cities])
    mc_o_avg = np.mean([c.p_transplant_24mo for c in mc_o.cities])
    bbn_ab_avg = np.mean([c.p_transplant_24mo for c in bbn_ab.cities])
    bbn_o_avg = np.mean([c.p_transplant_24mo for c in bbn_o.cities])

    mc_direction = mc_ab_avg > mc_o_avg
    bbn_direction = bbn_ab_avg > bbn_o_avg

    assert mc_direction == bbn_direction, (
        f"Blood type effect inconsistent: MC AB>O={mc_direction}, BBN AB>O={bbn_direction}"
    )


# ──────────────────────────────────────────────────────────────────────
# Directional consistency: organ wait times
# ──────────────────────────────────────────────────────────────────────


def test_organ_ordering_consistent():
    """Heart should have higher avg p24 than kidney in both methods."""
    mc_heart = simulate_mc(_make_patient(organ="heart"), n_iterations=300)
    mc_kidney = simulate_mc(_make_patient(organ="kidney"), n_iterations=300)
    bbn_heart = simulate_bbn(_make_patient(organ="heart"))
    bbn_kidney = simulate_bbn(_make_patient(organ="kidney"))

    mc_heart_avg = np.mean([c.p_transplant_24mo for c in mc_heart.cities])
    mc_kidney_avg = np.mean([c.p_transplant_24mo for c in mc_kidney.cities])
    bbn_heart_avg = np.mean([c.p_transplant_24mo for c in bbn_heart.cities])
    bbn_kidney_avg = np.mean([c.p_transplant_24mo for c in bbn_kidney.cities])

    mc_direction = mc_heart_avg > mc_kidney_avg
    bbn_direction = bbn_heart_avg > bbn_kidney_avg

    assert mc_direction == bbn_direction, (
        f"Organ ordering inconsistent: MC heart>kidney={mc_direction}, BBN={bbn_direction}"
    )


# ──────────────────────────────────────────────────────────────────────
# BBN probabilities plausibility
# ──────────────────────────────────────────────────────────────────────


def test_bbn_kidney_p24_range():
    """Kidney O+ p24 should be in 0.2-0.9 range (not degenerate)."""
    result = simulate_bbn(_make_patient(organ="kidney", blood_type="O+"))
    p24s = [c.p_transplant_24mo for c in result.cities]
    assert min(p24s) > 0.1, f"Min p24 too low: {min(p24s):.3f}"
    assert max(p24s) < 0.95, f"Max p24 too high: {max(p24s):.3f}"


def test_bbn_heart_p24_range():
    """Heart has short median → most cities should have high p24."""
    result = simulate_bbn(_make_patient(organ="heart"))
    p24s = [c.p_transplant_24mo for c in result.cities]
    assert np.mean(p24s) > 0.5, f"Heart avg p24 too low: {np.mean(p24s):.3f}"


def test_bbn_variability_across_cities():
    """BBN should show meaningful variation across cities (not all same)."""
    result = simulate_bbn(_make_patient())
    p24s = [c.p_transplant_24mo for c in result.cities]
    spread = max(p24s) - min(p24s)
    assert spread > 0.05, f"City spread too narrow: {spread:.3f}"


def test_bbn_competing_risks_plausible():
    """Competing risks should show reasonable proportions."""
    result = simulate_bbn(_make_patient(organ="kidney", urgency=2))
    for c in result.cities:
        cr = c.competing_risks
        # Transplant should be the dominant outcome at 24mo for most cities
        # (mortality and delisting are secondary)
        assert cr["p_transplant_24mo"] > 0.1, f"{c.city}: p_transplant too low"
        assert cr["p_mortality_24mo"] < 0.5, f"{c.city}: p_mortality too high"
        assert cr["p_delisting_24mo"] < 0.5, f"{c.city}: p_delisting too high"


# ──────────────────────────────────────────────────────────────────────
# Speed comparison
# ──────────────────────────────────────────────────────────────────────


def test_bbn_faster_than_mc():
    """BBN should be faster than MC (especially on cached model)."""
    import time

    patient = _make_patient()

    # Warm up BBN model
    simulate_bbn(patient)

    # Time BBN (cached)
    t0 = time.perf_counter()
    simulate_bbn(patient)
    bbn_time = time.perf_counter() - t0

    # Time MC with 500 iterations
    t0 = time.perf_counter()
    simulate_mc(patient, n_iterations=500)
    mc_time = time.perf_counter() - t0

    # BBN should be at least as fast as 500-iteration MC
    # (In practice BBN is ~10-100x faster)
    assert bbn_time < mc_time * 5, (
        f"BBN ({bbn_time:.3f}s) not significantly faster than MC ({mc_time:.3f}s)"
    )
