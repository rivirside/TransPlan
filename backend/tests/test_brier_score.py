"""Tests for services/brier_score.py — calibration Brier score validation."""
import pytest

from services.brier_score import (
    _analytical_p_transplant_12mo,
    compute_brier_score,
    validate_all_organs,
    BrierResult,
    CityValidation,
)


# -- Analytical probability tests --

class TestAnalyticalProbability:
    def test_returns_valid_probability(self):
        p = _analytical_p_transplant_12mo("kidney", "O+", "Nashville")
        assert 0 < p < 1

    def test_kidney_o_plus_plausible_range(self):
        """Kidney O+ 12-month transplant prob should be modest (10-40%)."""
        p = _analytical_p_transplant_12mo("kidney", "O+", "Nashville")
        assert 0.05 < p < 0.50, f"Kidney O+ Nashville p12={p:.3f} out of plausible range"

    def test_liver_higher_than_kidney(self):
        """Liver waits are much shorter; 12mo transplant prob should be higher."""
        p_kidney = _analytical_p_transplant_12mo("kidney", "O+", "Nashville")
        p_liver = _analytical_p_transplant_12mo("liver", "A+", "Nashville", meld=20)
        assert p_liver > p_kidney

    def test_high_cpra_lowers_probability(self):
        p_low = _analytical_p_transplant_12mo("kidney", "O+", "Nashville", cpra=10)
        p_high = _analytical_p_transplant_12mo("kidney", "O+", "Nashville", cpra=99)
        assert p_high < p_low * 0.5, "High cPRA should cut probability drastically"

    def test_high_meld_raises_probability(self):
        """High MELD → shorter wait → higher transplant probability."""
        p_low = _analytical_p_transplant_12mo("liver", "A+", "Nashville", meld=10)
        p_high = _analytical_p_transplant_12mo("liver", "A+", "Nashville", meld=35)
        assert p_high > p_low

    def test_short_wait_city_higher_probability(self):
        """Low city factor (St. Louis 0.57) should beat high city factor (San Francisco 2.12)."""
        p_stl = _analytical_p_transplant_12mo("kidney", "O+", "St. Louis")
        p_sf = _analytical_p_transplant_12mo("kidney", "O+", "San Francisco")
        assert p_stl > p_sf


# -- Brier score structure tests --

class TestBrierScoreStructure:
    def test_returns_brier_result(self):
        result = compute_brier_score("kidney", "O+", n_iterations=300)
        assert isinstance(result, BrierResult)

    def test_all_22_cities_present(self):
        result = compute_brier_score("kidney", "O+", n_iterations=300)
        assert result.n_cities == 22
        assert len(result.cities) == 22

    def test_city_validations_have_required_fields(self):
        result = compute_brier_score("kidney", "O+", n_iterations=300)
        for cv in result.cities:
            assert isinstance(cv, CityValidation)
            assert 0 <= cv.p_predicted <= 1
            assert 0 <= cv.p_analytical <= 1
            assert cv.squared_error >= 0

    def test_brier_score_is_mean_of_squared_errors(self):
        result = compute_brier_score("kidney", "O+", n_iterations=300)
        import numpy as np
        expected = np.mean([cv.squared_error for cv in result.cities])
        assert abs(result.brier_score - expected) < 1e-4

    def test_cities_sorted_by_error_descending(self):
        result = compute_brier_score("kidney", "O+", n_iterations=300)
        errors = [cv.squared_error for cv in result.cities]
        assert errors == sorted(errors, reverse=True)


# -- Calibration quality: Brier < 0.20 (roadmap target) --

class TestCalibrationQuality:
    @pytest.mark.parametrize("organ,blood_type,kwargs", [
        ("kidney", "O+", {"cpra": 30}),
        ("liver", "A+", {"meld": 20}),
        ("heart", "O+", {}),
        ("lung", "B+", {"las": 50.0}),
        ("pancreas", "A+", {}),
        ("intestine", "A+", {}),
    ])
    def test_brier_under_threshold(self, organ, blood_type, kwargs):
        """Monte Carlo should reproduce analytical expectations with BS < 0.02."""
        result = compute_brier_score(organ, blood_type, urgency=2, n_iterations=2000, **kwargs)
        assert result.brier_score < 0.02, (
            f"{organ} {blood_type} Brier={result.brier_score:.4f} exceeds threshold 0.02"
        )

    def test_kidney_no_city_exceeds_large_error(self):
        """No single city should have squared error > 0.05."""
        result = compute_brier_score("kidney", "O+", n_iterations=2000, cpra=30)
        for cv in result.cities:
            assert cv.squared_error < 0.05, (
                f"{cv.city}: SE={cv.squared_error:.4f}, pred={cv.p_predicted}, analytical={cv.p_analytical}"
            )


# -- All organs validation --

class TestValidateAllOrgans:
    def test_all_organs_pass(self):
        """Comprehensive validation across all 6 organs."""
        results = validate_all_organs(n_iterations=1000)
        assert len(results) == 6
        for organ, result in results.items():
            assert result.brier_score < 0.05, (
                f"{organ}: Brier={result.brier_score:.4f} exceeds threshold"
            )
