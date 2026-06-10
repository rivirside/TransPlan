"""Tests for services/equity.py — demographic equity analysis."""
import pytest
import numpy as np
from unittest.mock import patch

from models.schemas import EquityAnalysisResult, CityEquity, PatientProfile
from services.equity import compute_equity_analysis, _gini


# -- Fixtures --

@pytest.fixture
def kidney_patient() -> PatientProfile:
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2, cpra=50)


@pytest.fixture
def liver_patient() -> PatientProfile:
    return PatientProfile(organ="liver", blood_type="A+", age=52, sex="female", urgency=2, meld=20)


@pytest.fixture
def kidney_equity(kidney_patient, data) -> EquityAnalysisResult:
    """Pre-computed equity result to avoid repeated slow computation.

    Depends on the session `data` fixture so center data is always loaded —
    otherwise the result silently falls back to 22 cities and the center
    count depends on which test modules ran first.
    """
    return compute_equity_analysis(kidney_patient, n_iterations=200)


# -- Gini coefficient unit tests --

class TestGiniComputation:
    def test_perfect_equality(self):
        """All equal values → Gini = 0."""
        assert _gini(np.ones(10)) == 0.0

    def test_near_perfect_inequality(self):
        """One group has everything → Gini approaches 1."""
        vals = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
        assert _gini(vals) > 0.8

    def test_moderate_inequality(self):
        """Moderate spread → Gini between 0 and 1."""
        vals = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        g = _gini(vals)
        assert 0.0 < g < 1.0

    def test_empty_or_zero(self):
        """Edge cases: empty array or all zeros → Gini = 0."""
        assert _gini(np.array([])) == 0.0
        assert _gini(np.zeros(5)) == 0.0

    def test_single_value(self):
        """Single value → Gini = 0."""
        assert _gini(np.array([0.5])) == 0.0

    def test_negative_values_rejected(self):
        """Gini is undefined for negative inputs — must raise (#225)."""
        with pytest.raises(ValueError, match="non-negative"):
            _gini(np.array([0.5, -0.1, 0.3]))

    def test_nan_rejected(self):
        """NaN/inf inputs indicate an upstream bug — must raise (#225)."""
        with pytest.raises(ValueError, match="finite"):
            _gini(np.array([0.5, np.nan]))
        with pytest.raises(ValueError, match="finite"):
            _gini(np.array([0.5, np.inf]))


# -- Result structure --

class TestEquityResultStructure:
    def test_returns_equity_result(self, kidney_equity):
        assert isinstance(kidney_equity, EquityAnalysisResult)

    def test_full_center_coverage_by_default(self, kidney_equity):
        # #216: analytic p24 makes the FULL center set feasible — no silent
        # 30-cap. Kidney has 230+ centers; assert we analyze them all.
        assert len(kidney_equity.cities) > 200

    def test_analytic_method_flagged(self, kidney_equity):
        # iterations_per_profile == 0 signals the closed-form (no-MC) method.
        assert kidney_equity.iterations_per_profile == 0

    def test_48_profiles_simulated(self, kidney_equity):
        # 8 blood types × 3 age brackets × 2 sexes = 48
        assert kidney_equity.profiles_simulated == 48

    def test_organ_preserved(self, kidney_equity):
        assert kidney_equity.organ == "kidney"

    def test_elapsed_positive(self, kidney_equity):
        assert kidney_equity.elapsed_seconds > 0

    def test_disclaimers_present(self, kidney_equity):
        assert len(kidney_equity.disclaimers) >= 4
        # Check that key topics are covered
        all_text = " ".join(kidney_equity.disclaimers).lower()
        assert "race" in all_text
        assert "insurance" in all_text
        assert "mortality" in all_text


# -- City equity metrics --

class TestCityEquityMetrics:
    def test_gini_in_valid_range(self, kidney_equity):
        for city in kidney_equity.cities:
            assert 0 <= city.gini_coefficient <= 1, f"{city.city}: gini={city.gini_coefficient}"

    def test_overall_gini_in_valid_range(self, kidney_equity):
        assert 0 <= kidney_equity.overall_gini <= 1

    def test_p24_range_valid(self, kidney_equity):
        for city in kidney_equity.cities:
            lo, hi = city.p24_range
            assert 0 <= lo <= hi <= 1, f"{city.city}: p24_range={city.p24_range}"

    def test_median_wait_range_positive(self, kidney_equity):
        for city in kidney_equity.cities:
            lo, hi = city.median_wait_range
            assert lo > 0 and hi > 0, f"{city.city}: wait_range={city.median_wait_range}"

    def test_sorted_by_gini_ascending(self, kidney_equity):
        ginis = [c.gini_coefficient for c in kidney_equity.cities]
        assert ginis == sorted(ginis), "Cities should be sorted by Gini ascending"


# -- Dimension disparities --

class TestDimensionDisparities:
    def test_blood_type_has_8_entries(self, kidney_equity):
        for city in kidney_equity.cities:
            bt = city.dimension_disparities.get("blood_type", [])
            assert len(bt) == 8, f"{city.city}: blood_type has {len(bt)} entries"

    def test_age_bracket_has_3_entries(self, kidney_equity):
        for city in kidney_equity.cities:
            ab = city.dimension_disparities.get("age_bracket", [])
            assert len(ab) == 3, f"{city.city}: age_bracket has {len(ab)} entries"

    def test_sex_has_2_entries(self, kidney_equity):
        for city in kidney_equity.cities:
            sx = city.dimension_disparities.get("sex", [])
            assert len(sx) == 2, f"{city.city}: sex has {len(sx)} entries"

    def test_dimension_p24_values_valid(self, kidney_equity):
        for city in kidney_equity.cities:
            for dim_key, entries in city.dimension_disparities.items():
                for entry in entries:
                    assert 0 <= entry["p24"] <= 1, f"{city.city}/{dim_key}/{entry['value']}: p24={entry['p24']}"
                    assert entry["median_wait"] > 0, f"{city.city}/{dim_key}/{entry['value']}: wait={entry['median_wait']}"


# -- Clinical sanity checks --

class TestClinicalSanity:
    def test_blood_type_o_disadvantaged(self, kidney_equity):
        """Type O (universal donor, restricted recipient) should have lower p24 than AB."""
        # Check across all cities: on average, O should be worse than AB
        o_avg = []
        ab_avg = []
        for city in kidney_equity.cities:
            bt = {e["value"]: e["p24"] for e in city.dimension_disparities["blood_type"]}
            o_avg.append((bt.get("O+", 0) + bt.get("O-", 0)) / 2)
            ab_avg.append((bt.get("AB+", 0) + bt.get("AB-", 0)) / 2)
        # O should have lower average p24 than AB (longer wait for common type)
        assert np.mean(o_avg) < np.mean(ab_avg), "Type O should wait longer than AB on average"

    def test_disparity_exists(self, kidney_equity):
        """p24_range should show real variation (min < max for at least some cities)."""
        has_variation = any(c.p24_range[0] < c.p24_range[1] for c in kidney_equity.cities)
        assert has_variation, "At least one city should show demographic variation"


# -- All organs --

@pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung", "pancreas", "intestine"])
def test_equity_runs_for_all_organs(organ, data):
    """Equity analysis should complete without error for all 6 organ types."""
    patient = PatientProfile(organ=organ, blood_type="A+", age=40, sex="female", urgency=2)
    result = compute_equity_analysis(patient)
    assert isinstance(result, EquityAnalysisResult)
    assert result.organ == organ
    # #216: no default cap — every center for the organ is analyzed (analytic).
    assert 0 < len(result.cities) <= 260


# -- max_centers parameter (#216: opt-in cap; default None = all centers) --

class TestMaxCenters:
    """The cap is now opt-in. Default None analyzes ALL centers (feasible because
    p24 is closed-form, #216); an int caps deliberately."""

    def test_default_max_centers_is_none(self):
        import inspect
        sig = inspect.signature(compute_equity_analysis)
        assert sig.parameters["max_centers"].default is None

    def test_explicit_cap_truncates(self, data):
        patient = PatientProfile(
            organ="kidney", blood_type="A+", age=45, sex="male", urgency=2, cpra=50,
        )
        result = compute_equity_analysis(patient, max_centers=10)
        assert len(result.cities) == 10

    def test_no_cap_analyzes_all(self, data):
        patient = PatientProfile(
            organ="kidney", blood_type="O+", age=45, sex="male", urgency=2, cpra=50,
        )
        capped = compute_equity_analysis(patient, max_centers=10)
        full = compute_equity_analysis(patient)
        assert len(full.cities) > len(capped.cities) > 0

    def test_capped_results_still_valid(self, data):
        patient = PatientProfile(
            organ="kidney", blood_type="B+", age=50, sex="female", urgency=2, cpra=30,
        )
        result = compute_equity_analysis(patient, max_centers=15)
        assert len(result.cities) == 15
        assert result.profiles_simulated == 48
        assert 0 <= result.overall_gini <= 1
        for city in result.cities:
            assert 0 <= city.gini_coefficient <= 1
            lo, hi = city.p24_range
            assert 0 <= lo <= hi <= 1

    def test_cap_selects_lowest_wait_factor_centers(self):
        """When capping, the cap deterministically keeps the lowest-wait-factor
        centers (no random sampling, #216)."""
        fake_centers = [
            {"city": f"City{i}", "state": "CA", "code": f"C{i:03d}",
             "name": f"Center {i}", "wait_time_factor": float(i)}
            for i in range(20)
        ]
        patient = PatientProfile(
            organ="kidney", blood_type="A+", age=40, sex="male", urgency=2, cpra=50,
        )
        with patch("services.equity._get_centers", return_value=fake_centers):
            result = compute_equity_analysis(patient, max_centers=10)

        # Exactly the 10 lowest wait_time_factor codes (C000..C009).
        result_codes = {c.center_code for c in result.cities}
        assert result_codes == {f"C{i:03d}" for i in range(10)}
