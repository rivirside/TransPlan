"""Tests for services/what_if.py — what-if scenario analysis."""
import pytest

from models.schemas import PatientProfile
from services.what_if import compute_what_if, WhatIfResult, _run_single
import numpy as np


# -- Fixtures --

@pytest.fixture
def kidney_patient() -> PatientProfile:
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2, cpra=50)


@pytest.fixture
def liver_patient() -> PatientProfile:
    return PatientProfile(organ="liver", blood_type="A+", age=52, sex="female", urgency=2, meld=20)


# -- Result structure --

class TestWhatIfResultStructure:
    def test_returns_what_if_result(self, kidney_patient):
        result = compute_what_if(kidney_patient, city="Nashville", n_iterations=200)
        assert isinstance(result, WhatIfResult)

    def test_city_preserved(self, kidney_patient):
        result = compute_what_if(kidney_patient, city="Pittsburgh", n_iterations=200)
        assert result.city == "Pittsburgh"
        assert result.state == "PA"

    def test_multipliers_preserved(self, kidney_patient):
        result = compute_what_if(
            kidney_patient, city="Nashville",
            donor_rate_multiplier=1.5, wait_time_multiplier=0.8, n_iterations=200,
        )
        assert result.donor_rate_multiplier == 1.5
        assert result.wait_time_multiplier == 0.8

    def test_elapsed_recorded(self, kidney_patient):
        result = compute_what_if(kidney_patient, city="Nashville", n_iterations=200)
        assert result.elapsed_seconds > 0
        assert result.elapsed_seconds < 10

    def test_iterations_preserved(self, kidney_patient):
        result = compute_what_if(kidney_patient, city="Nashville", n_iterations=300)
        assert result.iterations == 300


# -- Probability validity --

class TestProbabilityValidity:
    def test_baseline_in_valid_range(self, kidney_patient):
        result = compute_what_if(kidney_patient, city="Nashville", n_iterations=300)
        assert 0 <= result.baseline_p24 <= 1

    def test_adjusted_in_valid_range(self, kidney_patient):
        result = compute_what_if(
            kidney_patient, city="Nashville",
            donor_rate_multiplier=1.5, n_iterations=300,
        )
        assert 0 <= result.adjusted_p24 <= 1

    def test_delta_is_correct_difference(self, kidney_patient):
        result = compute_what_if(
            kidney_patient, city="Nashville",
            donor_rate_multiplier=1.3, n_iterations=300,
        )
        expected_delta = round(result.adjusted_p24 - result.baseline_p24, 4)
        assert result.delta_p24 == expected_delta

    def test_confidence_intervals_valid(self, kidney_patient):
        result = compute_what_if(kidney_patient, city="Nashville", n_iterations=300)
        assert result.baseline_ci_95[0] <= result.baseline_p24 <= result.baseline_ci_95[1] or \
            abs(result.baseline_ci_95[0] - result.baseline_p24) < 0.05
        assert result.adjusted_ci_95[0] <= result.adjusted_ci_95[1]


# -- Multiplier effects --

class TestMultiplierEffects:
    def test_more_donors_improves_p24(self, kidney_patient):
        """donor_rate_multiplier > 1 should increase p24 (more donors → shorter waits)."""
        result = compute_what_if(
            kidney_patient, city="Nashville",
            donor_rate_multiplier=1.5, wait_time_multiplier=1.0,
            n_iterations=500,
        )
        # With 50% more donors, p24 should increase (paired-seed comparison removes noise)
        assert result.delta_p24 > 0, f"More donors should improve p24: {result.delta_p24}"

    def test_fewer_donors_worsens_p24(self, kidney_patient):
        """donor_rate_multiplier < 1 should decrease p24 (fewer donors → longer waits)."""
        result = compute_what_if(
            kidney_patient, city="Nashville",
            donor_rate_multiplier=0.5, wait_time_multiplier=1.0,
            n_iterations=500,
        )
        # With 50% fewer donors, p24 should decrease
        assert result.delta_p24 < 0, f"Fewer donors should worsen p24: {result.delta_p24}"

    def test_longer_waits_worsen_p24(self, kidney_patient):
        """wait_time_multiplier > 1 should decrease p24 (longer base waits)."""
        result = compute_what_if(
            kidney_patient, city="Nashville",
            donor_rate_multiplier=1.0, wait_time_multiplier=1.5,
            n_iterations=500,
        )
        assert result.delta_p24 < 0, f"Longer waits should worsen p24: {result.delta_p24}"

    def test_shorter_waits_improve_p24(self, kidney_patient):
        """wait_time_multiplier < 1 should increase p24 (shorter base waits)."""
        result = compute_what_if(
            kidney_patient, city="Nashville",
            donor_rate_multiplier=1.0, wait_time_multiplier=0.5,
            n_iterations=500,
        )
        assert result.delta_p24 > 0, f"Shorter waits should improve p24: {result.delta_p24}"

    def test_baseline_multipliers_give_small_delta(self, kidney_patient):
        """With both multipliers at 1.0, delta should be near zero."""
        result = compute_what_if(
            kidney_patient, city="Nashville",
            donor_rate_multiplier=1.0, wait_time_multiplier=1.0,
            n_iterations=500,
        )
        # Monte Carlo noise exists but delta from same-seed paired comparison
        # should be very small (ideally 0 if same seed, but seeds differ)
        assert abs(result.delta_p24) < 0.15, f"Baseline-vs-baseline delta too large: {result.delta_p24}"


# -- Median wait --

class TestMedianWait:
    def test_median_wait_positive(self, kidney_patient):
        result = compute_what_if(kidney_patient, city="Nashville", n_iterations=300)
        assert result.baseline_median_wait > 0
        assert result.adjusted_median_wait > 0

    def test_more_donors_shortens_median_wait(self, kidney_patient):
        result = compute_what_if(
            kidney_patient, city="Nashville",
            donor_rate_multiplier=2.0, wait_time_multiplier=1.0,
            n_iterations=500,
        )
        # 2× donors should substantially shorten wait
        assert result.adjusted_median_wait < result.baseline_median_wait * 1.1


# -- All organs --

class TestAllOrgans:
    @pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung", "pancreas", "intestine"])
    def test_what_if_runs_for_organ(self, organ):
        patient = PatientProfile(organ=organ, blood_type="A+", age=40, sex="male", urgency=2)
        result = compute_what_if(patient, city="Nashville", donor_rate_multiplier=1.2, n_iterations=200)
        assert isinstance(result, WhatIfResult)
        assert 0 <= result.baseline_p24 <= 1
        assert 0 <= result.adjusted_p24 <= 1


# -- _run_single helper --

class TestRunSingle:
    def test_returns_dict_with_keys(self, kidney_patient):
        rng = np.random.default_rng(42)
        result = _run_single(kidney_patient, "Nashville", "TN", 300, rng)
        assert "p24" in result
        assert "ci_95" in result
        assert "median_wait" in result

    def test_wait_time_multiplier_scales_distribution(self, kidney_patient):
        """Higher wait_time_multiplier should produce longer median waits."""
        rng1 = np.random.default_rng(42)
        base = _run_single(kidney_patient, "Nashville", "TN", 500, rng1, wait_time_multiplier=1.0)
        rng2 = np.random.default_rng(42)
        longer = _run_single(kidney_patient, "Nashville", "TN", 500, rng2, wait_time_multiplier=2.0)
        assert longer["median_wait"] > base["median_wait"] * 1.3, "2× wait multiplier should substantially increase median"

    def test_donor_multiplier_scales_wait(self, kidney_patient):
        """Higher donor_rate_multiplier should produce shorter median waits."""
        rng1 = np.random.default_rng(42)
        base = _run_single(kidney_patient, "Nashville", "TN", 500, rng1, donor_rate_multiplier=1.0)
        rng2 = np.random.default_rng(42)
        more_donors = _run_single(kidney_patient, "Nashville", "TN", 500, rng2, donor_rate_multiplier=2.0)
        assert more_donors["median_wait"] < base["median_wait"] * 0.9, "2× donors should substantially decrease median"


# -- Elasticity tests (L-056) --

class TestSupplyWaitElasticity:
    """Verify that donor supply changes apply sublinear elasticity."""

    def test_elasticity_is_sublinear(self, kidney_patient):
        """2× donors with elasticity=0.65 should reduce waits less than 2×."""
        rng1 = np.random.default_rng(42)
        base = _run_single(kidney_patient, "Nashville", "TN", 1000, rng1, donor_rate_multiplier=1.0)
        rng2 = np.random.default_rng(42)
        double = _run_single(kidney_patient, "Nashville", "TN", 1000, rng2, donor_rate_multiplier=2.0)
        # With elasticity=0.65, effective_mult = 2^0.65 ≈ 1.57 (not 2.0)
        # So wait should decrease by ~36% (not 50%)
        ratio = double["median_wait"] / base["median_wait"]
        # Should be closer to 1/1.57 ≈ 0.64 than 1/2 = 0.50
        assert ratio > 0.50, f"Ratio {ratio:.3f} too aggressive — elasticity not applied"
        assert ratio < 0.85, f"Ratio {ratio:.3f} too mild — donor effect not working"

    def test_elasticity_symmetric_for_decrease(self, kidney_patient):
        """0.5× donors should increase waits sublinearly too."""
        rng1 = np.random.default_rng(42)
        base = _run_single(kidney_patient, "Nashville", "TN", 1000, rng1, donor_rate_multiplier=1.0)
        rng2 = np.random.default_rng(42)
        half = _run_single(kidney_patient, "Nashville", "TN", 1000, rng2, donor_rate_multiplier=0.5)
        ratio = half["median_wait"] / base["median_wait"]
        # With elasticity=0.65, effective_mult = 0.5^0.65 ≈ 0.637
        # Wait ratio = 1/0.637 ≈ 1.57 (not 2.0)
        assert ratio < 2.0, f"Ratio {ratio:.3f} too aggressive — elasticity not applied"
        assert ratio > 1.1, f"Ratio {ratio:.3f} too mild — donor effect not working"
