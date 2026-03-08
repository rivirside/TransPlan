"""Tests for services/sensitivity.py — input parameter sensitivity analysis."""
import pytest

from models.schemas import PatientProfile, SensitivityResult, ParameterImpact
from services.sensitivity import compute_sensitivity, _p24_single_city
import numpy as np


# -- Fixtures --

@pytest.fixture
def kidney_patient() -> PatientProfile:
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2, cpra=50)


@pytest.fixture
def liver_patient() -> PatientProfile:
    return PatientProfile(organ="liver", blood_type="A+", age=52, sex="female", urgency=2, meld=20)


@pytest.fixture
def lung_patient() -> PatientProfile:
    return PatientProfile(organ="lung", blood_type="B+", age=38, sex="male", urgency=2, las=50.0)


@pytest.fixture
def heart_patient() -> PatientProfile:
    return PatientProfile(organ="heart", blood_type="A+", age=55, sex="male", urgency=3)


# -- Single-city helper --

class TestP24SingleCity:
    def test_returns_valid_probability(self, kidney_patient):
        rng = np.random.default_rng(42)
        p24 = _p24_single_city(kidney_patient, "Nashville", 500, rng)
        assert 0 <= p24 <= 1

    def test_different_cities_give_different_results(self, kidney_patient):
        rng = np.random.default_rng(42)
        p_omaha = _p24_single_city(kidney_patient, "Omaha", 1000, rng)
        p_ny = _p24_single_city(kidney_patient, "New York", 1000, rng)
        # Omaha (low city factor) should generally beat New York (high city factor)
        assert p_omaha != p_ny


# -- Result structure --

class TestSensitivityResultStructure:
    def test_returns_sensitivity_result(self, kidney_patient):
        result = compute_sensitivity(kidney_patient, city="Nashville", n_iterations=200)
        assert isinstance(result, SensitivityResult)

    def test_patient_preserved(self, kidney_patient):
        result = compute_sensitivity(kidney_patient, city="Nashville", n_iterations=200)
        assert result.patient.organ == "kidney"
        assert result.patient.blood_type == "O+"

    def test_city_preserved(self, kidney_patient):
        result = compute_sensitivity(kidney_patient, city="Pittsburgh", n_iterations=200)
        assert result.city == "Pittsburgh"

    def test_elapsed_recorded(self, kidney_patient):
        result = compute_sensitivity(kidney_patient, city="Nashville", n_iterations=200)
        assert result.elapsed_seconds > 0
        assert result.elapsed_seconds < 10

    def test_impacts_are_parameter_impact(self, kidney_patient):
        result = compute_sensitivity(kidney_patient, city="Nashville", n_iterations=200)
        for imp in result.impacts:
            assert isinstance(imp, ParameterImpact)


# -- Organ-specific parameter coverage --

class TestOrganCoverage:
    def test_kidney_has_cpra_and_urgency(self, kidney_patient):
        result = compute_sensitivity(kidney_patient, city="Nashville", n_iterations=200)
        params = {imp.parameter for imp in result.impacts}
        assert "cpra" in params
        assert "urgency" in params
        assert len(result.impacts) == 2

    def test_liver_has_meld_and_urgency(self, liver_patient):
        result = compute_sensitivity(liver_patient, city="Nashville", n_iterations=200)
        params = {imp.parameter for imp in result.impacts}
        assert "meld" in params
        assert "urgency" in params
        assert len(result.impacts) == 2

    def test_lung_has_las_and_urgency(self, lung_patient):
        result = compute_sensitivity(lung_patient, city="Nashville", n_iterations=200)
        params = {imp.parameter for imp in result.impacts}
        assert "las" in params
        assert "urgency" in params
        assert len(result.impacts) == 2

    def test_heart_has_urgency_only(self, heart_patient):
        result = compute_sensitivity(heart_patient, city="Nashville", n_iterations=200)
        params = {imp.parameter for imp in result.impacts}
        assert params == {"urgency"}
        assert len(result.impacts) == 1


# -- Sorting --

class TestImpactSorting:
    def test_sorted_by_magnitude_descending(self, kidney_patient):
        """Impacts should be sorted by abs(p24_at_high - p24_at_low) descending."""
        result = compute_sensitivity(kidney_patient, city="Nashville", n_iterations=500)
        swings = [abs(imp.p24_at_high - imp.p24_at_low) for imp in result.impacts]
        assert swings == sorted(swings, reverse=True)


# -- Clinical sanity --

class TestClinicalSanity:
    def test_cpra_has_large_impact_on_kidney(self, kidney_patient):
        """cPRA range (0 → 98) should cause a large swing in kidney p24."""
        result = compute_sensitivity(kidney_patient, city="Nashville", n_iterations=500)
        cpra_imp = next(imp for imp in result.impacts if imp.parameter == "cpra")
        swing = abs(cpra_imp.p24_at_high - cpra_imp.p24_at_low)
        assert swing > 0.05, f"cPRA swing {swing:.4f} too small"

    def test_low_cpra_better_than_high_cpra(self, kidney_patient):
        """cPRA 0 (unsensitized) should give higher p24 than cPRA 98 (highly sensitized)."""
        result = compute_sensitivity(kidney_patient, city="Nashville", n_iterations=500)
        cpra_imp = next(imp for imp in result.impacts if imp.parameter == "cpra")
        assert cpra_imp.p24_at_low > cpra_imp.p24_at_high, "Low cPRA should have higher p24"

    def test_probabilities_in_valid_range(self, kidney_patient):
        result = compute_sensitivity(kidney_patient, city="Nashville", n_iterations=300)
        for imp in result.impacts:
            assert 0 <= imp.p24_baseline <= 1
            assert 0 <= imp.p24_at_low <= 1
            assert 0 <= imp.p24_at_high <= 1

    def test_baseline_consistent_across_impacts(self, kidney_patient):
        """All impacts should share the same p24_baseline value."""
        result = compute_sensitivity(kidney_patient, city="Nashville", n_iterations=300)
        baselines = {imp.p24_baseline for imp in result.impacts}
        assert len(baselines) == 1, f"Inconsistent baselines: {baselines}"


# -- All organs produce results --

class TestAllOrgans:
    @pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung", "pancreas", "intestine"])
    def test_sensitivity_runs_for_organ(self, organ):
        patient = PatientProfile(organ=organ, blood_type="A+", age=40, sex="male", urgency=2)
        result = compute_sensitivity(patient, city="Nashville", n_iterations=200)
        assert len(result.impacts) >= 1  # at least urgency
        assert all(0 <= imp.p24_baseline <= 1 for imp in result.impacts)
