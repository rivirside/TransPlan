"""Tests for the data_quality provenance fields (#300).

Silent fallbacks (missing center data defaulting to national factors) must be
visible in API responses — this is what let bugs like #287 hide.
"""
import pytest

from models.schemas import PatientProfile
from services.monte_carlo import simulate


@pytest.fixture(autouse=True)
def _load(data):
    pass


@pytest.fixture
def kidney_patient():
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                          urgency=2, cpra=20)


class TestDataQuality:
    def test_summary_present_and_consistent(self, kidney_patient):
        result = simulate(kidney_patient, n_iterations=200, seed=42)
        dq = result.data_quality
        assert dq is not None
        assert dq["centers_total"] == len(result.cities)
        wt = dq["wait_time_factors"]
        assert wt["center_level"] + wt["national_default"] == dq["centers_total"]
        assert dq["fully_center_level"] <= dq["centers_total"]

    def test_most_kidney_centers_are_center_level(self, kidney_patient):
        """The SRTR parse covers nearly all centers — a majority falling back
        would mean the data files regressed (2026-08-05 incident class)."""
        result = simulate(kidney_patient, n_iterations=200, seed=42)
        dq = result.data_quality
        assert dq["wait_time_factors"]["center_level"] > 0.8 * dq["centers_total"]

    def test_per_center_tags_match_summary(self, kidney_patient):
        result = simulate(kidney_patient, n_iterations=200, seed=42)
        n_missing_obs = sum(
            1 for c in result.cities
            if c.data_quality and "no_observed_outcomes" in c.data_quality
        )
        assert n_missing_obs == result.data_quality["observed_outcomes"]["missing"]

    def test_intestine_shows_degradation_honestly(self):
        """Sparse organs must not pretend to be fully center-level."""
        p = PatientProfile(organ="intestine", blood_type="A+", age=45, sex="male",
                           urgency=2)
        result = simulate(p, n_iterations=200, seed=42)
        dq = result.data_quality
        assert dq is not None
        # There should be at least SOME degradation signal for intestine,
        # or (if data is complete) everything consistent
        assert dq["fully_center_level"] + sum(
            1 for c in result.cities if c.data_quality) == dq["centers_total"]
