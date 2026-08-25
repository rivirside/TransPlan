"""Tests for center-code-based what-if analysis (#286).

The scenarios page offers all 248 centers, so /what-if must accept a
center_code and thread it through to the center-level data getters instead
of validating display names against the legacy 22-city list.
"""
import pytest

from models.schemas import PatientProfile
from services import what_if as what_if_mod
from services.what_if import compute_what_if, WhatIfResult


@pytest.fixture(autouse=True)
def _load_data(data):
    """Center-code resolution needs the real data files loaded."""


@pytest.fixture
def kidney_patient() -> PatientProfile:
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2, cpra=50)


class TestCenterCodePath:
    def test_center_code_accepted(self, kidney_patient):
        """A center outside the 22 focus cities must not raise Unknown city."""
        result = compute_what_if(kidney_patient, center_code="ALCH", n_iterations=200)
        assert isinstance(result, WhatIfResult)
        assert result.center_code == "ALCH"
        assert result.city == "Children's of Alabama"
        assert result.state == "AL"

    def test_unknown_center_code_raises(self, kidney_patient):
        with pytest.raises(ValueError, match="Unknown center"):
            compute_what_if(kidney_patient, center_code="ZZZZ", n_iterations=200)

    def test_organ_not_offered_raises(self, kidney_patient):
        """ALCH does not perform lung transplants."""
        lung_patient = PatientProfile(
            organ="lung", blood_type="O+", age=45, sex="male", urgency=2, las=50,
        )
        with pytest.raises(ValueError, match="does not perform"):
            compute_what_if(lung_patient, center_code="ALCH", n_iterations=200)

    def test_center_code_threaded_to_getters(self, kidney_patient, monkeypatch):
        """The center-level factors must actually be used, not silently dropped
        (regression guard for the brier_score-style bug)."""
        seen = {}

        real_mort = what_if_mod.get_annual_mortality_rate
        real_dist = what_if_mod.get_wait_time_distribution
        real_delist = what_if_mod.get_annual_delisting_rate

        def spy_mort(*args, **kwargs):
            seen["mort_center"] = kwargs.get("center_code", "")
            return real_mort(*args, **kwargs)

        def spy_dist(*args, **kwargs):
            seen["dist_center"] = kwargs.get("center_code", "")
            return real_dist(*args, **kwargs)

        def spy_delist(*args, **kwargs):
            seen["delist_center"] = kwargs.get("center_code", "")
            return real_delist(*args, **kwargs)

        monkeypatch.setattr(what_if_mod, "get_annual_mortality_rate", spy_mort)
        monkeypatch.setattr(what_if_mod, "get_wait_time_distribution", spy_dist)
        monkeypatch.setattr(what_if_mod, "get_annual_delisting_rate", spy_delist)

        compute_what_if(kidney_patient, center_code="ALCH", n_iterations=200)
        assert seen["mort_center"] == "ALCH"
        assert seen["dist_center"] == "ALCH"
        assert seen["delist_center"] == "ALCH"

    def test_city_path_still_works(self, kidney_patient):
        """Legacy 22-city path stays intact until #285 retires it."""
        result = compute_what_if(kidney_patient, city="Nashville", n_iterations=200)
        assert result.city == "Nashville"
        assert result.center_code == ""

    def test_center_code_takes_precedence_over_city(self, kidney_patient):
        """When both are sent (the frontend sends a display label as city),
        the center code wins and no city validation happens."""
        result = compute_what_if(
            kidney_patient, city="Children's of Alabama", center_code="ALCH",
            n_iterations=200,
        )
        assert result.center_code == "ALCH"

    def test_seed_reproducible_for_center(self, kidney_patient):
        r1 = compute_what_if(kidney_patient, center_code="ALCH", n_iterations=200, seed=42)
        r2 = compute_what_if(kidney_patient, center_code="ALCH", n_iterations=200, seed=42)
        assert r1.baseline_p24 == r2.baseline_p24
        assert r1.adjusted_p24 == r2.adjusted_p24
