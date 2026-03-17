"""Tests for services/outcomes.py — post-transplant outcomes service.

Uses the session-scoped `data` fixture from conftest.py which calls load_all().
Tests that hit _get_outcomes_data() require data to be loaded first.
"""
import pytest
from services.data_loader import TransPlanData
from services.outcomes import (
    get_city_outcomes,
    get_national_baselines,
    get_graft_survival_1yr,
    get_patient_survival_1yr,
    compute_compound_success,
    build_outcomes_dict,
    VALID_ORGANS,
    MIN_SURVIVAL_PCT,
)


# ---------------------------------------------------------------------------
# National baselines (requires loaded data)
# ---------------------------------------------------------------------------

class TestNationalBaselines:
    @pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung", "intestine"])
    def test_baselines_present_for_organs_with_graft_data(self, data, organ):
        baselines = get_national_baselines(organ)
        assert baselines is not None
        assert baselines["national_graft_survival_1yr"] is not None
        assert baselines["national_patient_survival_1yr"] is not None

    def test_pancreas_has_patient_but_no_graft_survival(self, data):
        baselines = get_national_baselines("pancreas")
        assert baselines is not None
        assert baselines["national_graft_survival_1yr"] is None
        assert baselines["national_patient_survival_1yr"] == pytest.approx(96.6, abs=0.1)

    def test_invalid_organ_returns_none(self):
        assert get_national_baselines("spleen") is None

    def test_baseline_values_in_reasonable_range(self, data):
        for organ in VALID_ORGANS:
            baselines = get_national_baselines(organ)
            assert baselines is not None
            ps = baselines["national_patient_survival_1yr"]
            assert ps is not None
            assert 50.0 <= ps <= 100.0


# ---------------------------------------------------------------------------
# City outcomes (requires loaded data)
# ---------------------------------------------------------------------------

class TestCityOutcomes:
    def test_known_city_has_kidney_outcomes(self, data):
        outcomes = get_city_outcomes("kidney", "Cleveland")
        assert outcomes is not None
        assert "graft_survival_1yr" in outcomes
        assert "patient_survival_1yr" in outcomes
        assert "performance_rating" in outcomes

    def test_performance_rating_valid_values(self, data):
        outcomes = get_city_outcomes("kidney", "Cleveland")
        assert outcomes["performance_rating"] in (
            "better_than_expected", "as_expected", "worse_than_expected"
        )

    def test_unknown_city_returns_none(self, data):
        assert get_city_outcomes("kidney", "Atlantis") is None

    def test_invalid_organ_returns_none(self):
        assert get_city_outcomes("spleen", "Cleveland") is None

    def test_hazard_ratio_and_ci_present(self, data):
        outcomes = get_city_outcomes("kidney", "Pittsburgh")
        assert outcomes is not None
        assert outcomes["graft_hr_1yr"] > 0
        ci = outcomes["graft_hr_1yr_ci"]
        assert len(ci) == 2
        assert ci[0] < ci[1]

    def test_n_1yr_present_and_positive(self, data):
        outcomes = get_city_outcomes("kidney", "Pittsburgh")
        assert outcomes["n_1yr"] > 0


# ---------------------------------------------------------------------------
# Graft / patient survival helpers (requires loaded data)
# ---------------------------------------------------------------------------

class TestSurvivalHelpers:
    def test_graft_survival_returns_center_value(self, data):
        gs = get_graft_survival_1yr("kidney", "Cleveland")
        assert gs is not None
        assert 80.0 <= gs <= 100.0

    def test_graft_survival_falls_back_to_national(self, data):
        """Unknown city should fall back to national baseline."""
        gs = get_graft_survival_1yr("kidney", "Atlantis")
        national = get_national_baselines("kidney")["national_graft_survival_1yr"]
        assert gs == national

    def test_patient_survival_returns_center_value(self, data):
        ps = get_patient_survival_1yr("kidney", "Cleveland")
        assert ps is not None
        assert 80.0 <= ps <= 100.0

    def test_patient_survival_falls_back_to_national(self, data):
        ps = get_patient_survival_1yr("kidney", "Atlantis")
        national = get_national_baselines("kidney")["national_patient_survival_1yr"]
        assert ps == national

    def test_pancreas_graft_survival_falls_back_to_national_none(self, data):
        """Pancreas has no national graft survival; center data may also be None."""
        gs = get_graft_survival_1yr("pancreas", "Atlantis")
        # National graft is None for pancreas, so should return None
        assert gs is None


# ---------------------------------------------------------------------------
# Compound success metric (pure computation — no data loading needed)
# ---------------------------------------------------------------------------

class TestCompoundSuccess:
    def test_basic_computation(self):
        # P(tx 24mo) = 0.5, graft survival = 95% → 0.5 * 0.95 = 0.475
        result = compute_compound_success(0.5, 95.0)
        assert result == pytest.approx(0.475)

    def test_perfect_probability(self):
        result = compute_compound_success(1.0, 100.0)
        assert result == pytest.approx(1.0)

    def test_none_graft_returns_none(self):
        assert compute_compound_success(0.5, None) is None

    def test_below_minimum_survival_returns_none(self):
        assert compute_compound_success(0.5, MIN_SURVIVAL_PCT - 1) is None

    def test_at_minimum_survival_returns_value(self):
        result = compute_compound_success(0.5, MIN_SURVIVAL_PCT)
        assert result is not None
        assert result == pytest.approx(0.5 * MIN_SURVIVAL_PCT / 100.0)

    def test_zero_probability(self):
        result = compute_compound_success(0.0, 95.0)
        assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# build_outcomes_dict (integration — requires loaded data)
# ---------------------------------------------------------------------------

class TestBuildOutcomesDict:
    def test_returns_dict_for_known_city(self, data):
        result = build_outcomes_dict("kidney", "Cleveland", 0.6)
        assert result is not None
        assert "graft_survival_1yr" in result
        assert "patient_survival_1yr" in result
        assert "compound_success" in result

    def test_survival_values_are_decimals(self, data):
        """build_outcomes_dict converts percentages to 0-1 decimals."""
        result = build_outcomes_dict("kidney", "Cleveland", 0.6)
        assert 0.0 < result["graft_survival_1yr"] <= 1.0
        assert 0.0 < result["patient_survival_1yr"] <= 1.0

    def test_compound_success_bounded(self, data):
        result = build_outcomes_dict("kidney", "Cleveland", 0.6)
        assert 0.0 < result["compound_success"] <= 1.0

    def test_national_baselines_included(self, data):
        result = build_outcomes_dict("kidney", "Cleveland", 0.6)
        assert "national_graft_survival_1yr" in result
        assert "national_patient_survival_1yr" in result

    def test_hazard_ratio_included(self, data):
        result = build_outcomes_dict("kidney", "Pittsburgh", 0.5)
        assert "graft_hr_1yr" in result
        assert "graft_hr_1yr_ci" in result

    def test_performance_rating_included(self, data):
        result = build_outcomes_dict("kidney", "Pittsburgh", 0.5)
        assert "performance_rating" in result

    def test_unknown_city_uses_national_baselines(self, data):
        result = build_outcomes_dict("kidney", "Atlantis", 0.5)
        # Should still get national data
        assert result is not None
        assert "national_graft_survival_1yr" in result
        assert "graft_survival_1yr" in result  # Falls back to national

    def test_no_data_returns_none(self, data):
        result = build_outcomes_dict("spleen", "Cleveland", 0.5)
        assert result is None

    def test_pancreas_uses_patient_survival_fallback(self, data):
        """Pancreas lacks graft survival; compound success should use patient survival."""
        result = build_outcomes_dict("pancreas", "Pittsburgh", 0.5)
        if result is not None:
            if "compound_success" in result:
                assert "compound_success_note" in result
                assert "patient survival" in result["compound_success_note"].lower()

    def test_all_organs_produce_valid_output(self, data):
        """Every valid organ should produce output for a known city."""
        for organ in VALID_ORGANS:
            result = build_outcomes_dict(organ, "Cleveland", 0.5)
            # At minimum, national baselines should be available
            assert result is not None, f"No outcomes for {organ} in Cleveland"
            assert "patient_survival_1yr" in result or "graft_survival_1yr" in result
