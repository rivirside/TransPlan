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
    def test_returns_valid_probability(self, data):
        p = _analytical_p_transplant_12mo("kidney", "O+", "Nashville")
        assert 0 < p < 1

    def test_kidney_o_plus_plausible_range(self, data):
        """Kidney O+ 12-month transplant prob should be modest (10-40%)."""
        p = _analytical_p_transplant_12mo("kidney", "O+", "Nashville")
        assert 0.05 < p < 0.50, f"Kidney O+ Nashville p12={p:.3f} out of plausible range"

    def test_liver_higher_than_kidney(self, data):
        """Liver waits are much shorter; 12mo transplant prob should be higher."""
        p_kidney = _analytical_p_transplant_12mo("kidney", "O+", "Nashville")
        p_liver = _analytical_p_transplant_12mo("liver", "A+", "Nashville", meld=20)
        assert p_liver > p_kidney

    def test_high_cpra_lowers_probability(self, data):
        p_low = _analytical_p_transplant_12mo("kidney", "O+", "Nashville", cpra=10)
        p_high = _analytical_p_transplant_12mo("kidney", "O+", "Nashville", cpra=99)
        assert p_high < p_low * 0.5, "High cPRA should cut probability drastically"

    def test_high_meld_raises_probability(self, data):
        """High MELD → shorter wait → higher transplant probability."""
        p_low = _analytical_p_transplant_12mo("liver", "A+", "Nashville", meld=10)
        p_high = _analytical_p_transplant_12mo("liver", "A+", "Nashville", meld=35)
        assert p_high > p_low

    def test_short_wait_city_higher_probability(self, data):
        """Low city factor (St. Louis 0.57) should beat high city factor (San Francisco 2.12)."""
        p_stl = _analytical_p_transplant_12mo("kidney", "O+", "St. Louis")
        p_sf = _analytical_p_transplant_12mo("kidney", "O+", "San Francisco")
        assert p_stl > p_sf


# -- Brier score structure tests --

class TestBrierScoreStructure:
    def test_returns_brier_result(self, data):
        result = compute_brier_score("kidney", "O+", n_iterations=300)
        assert isinstance(result, BrierResult)

    def test_all_cities_present(self, data):
        result = compute_brier_score("kidney", "O+", n_iterations=300)
        assert result.n_cities >= 1
        assert len(result.cities) >= 1

    def test_city_validations_have_required_fields(self, data):
        result = compute_brier_score("kidney", "O+", n_iterations=300)
        for cv in result.cities:
            assert isinstance(cv, CityValidation)
            assert 0 <= cv.p_predicted <= 1
            assert 0 <= cv.p_analytical <= 1
            assert cv.squared_error >= 0

    def test_brier_score_is_mean_of_squared_errors(self, data):
        result = compute_brier_score("kidney", "O+", n_iterations=300)
        import numpy as np
        expected = np.mean([cv.squared_error for cv in result.cities])
        assert abs(result.brier_score - expected) < 1e-4

    def test_cities_sorted_by_error_descending(self, data):
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
    def test_brier_under_threshold(self, organ, blood_type, kwargs, data):
        """Monte Carlo should reproduce analytical expectations (relaxed for 248 centers)."""
        result = compute_brier_score(organ, blood_type, urgency=2, n_iterations=2000, **kwargs)
        # Threshold relaxed from 0.02 to 0.08 for 248-center mode:
        # small-volume centers have noisier calibration
        assert result.brier_score < 0.08, (
            f"{organ} {blood_type} Brier={result.brier_score:.4f} exceeds threshold 0.08"
        )

    def test_kidney_no_city_exceeds_large_error(self, data):
        """No single center should have squared error > 0.15."""
        result = compute_brier_score("kidney", "O+", n_iterations=2000, cpra=30)
        for cv in result.cities:
            assert cv.squared_error < 0.15, (
                f"{cv.city}: SE={cv.squared_error:.4f}, pred={cv.p_predicted}, analytical={cv.p_analytical}"
            )


# -- All organs validation --

class TestValidateAllOrgans:
    def test_all_organs_pass(self, data):
        """Comprehensive validation across all 6 organs."""
        results = validate_all_organs(n_iterations=1000)
        assert len(results) == 6
        for organ, result in results.items():
            assert result.brier_score < 0.08, (
                f"{organ}: Brier={result.brier_score:.4f} exceeds threshold"
            )


# -- Center-code threading (#287) --

class TestCenterCodeThreading:
    """The analytical benchmark must use the same center-level factors as the
    MC side. Before #287 it passed a display name as `city` and never passed
    center_code, so every center factor silently defaulted to 1.0 and the
    analytical baseline was effectively national."""

    def test_analytical_uses_center_code(self, data, monkeypatch):
        from services import brier_score as bs

        seen = {}
        real_dist = bs.get_wait_time_distribution
        real_mort = bs.get_annual_mortality_rate
        real_delist = bs.get_annual_delisting_rate

        def spy_dist(*a, **kw):
            seen["dist"] = kw.get("center_code", "")
            return real_dist(*a, **kw)

        def spy_mort(*a, **kw):
            seen["mort"] = kw.get("center_code", "")
            return real_mort(*a, **kw)

        def spy_delist(*a, **kw):
            seen["delist"] = kw.get("center_code", "")
            return real_delist(*a, **kw)

        monkeypatch.setattr(bs, "get_wait_time_distribution", spy_dist)
        monkeypatch.setattr(bs, "get_annual_mortality_rate", spy_mort)
        monkeypatch.setattr(bs, "get_annual_delisting_rate", spy_delist)

        _analytical_p_transplant_12mo(
            "kidney", "O+", "Children's of Alabama", center_code="ALCH",
        )
        assert seen == {"dist": "ALCH", "mort": "ALCH", "delist": "ALCH"}

    def test_compute_brier_threads_center_codes(self, data, monkeypatch):
        """compute_brier_score must pass each simulated center's code through
        to the analytical benchmark, not just its display name."""
        from services import brier_score as bs

        codes_seen = []
        real = bs._analytical_p_transplant_12mo

        def spy(*a, **kw):
            codes_seen.append(kw.get("center_code", ""))
            return real(*a, **kw)

        monkeypatch.setattr(bs, "_analytical_p_transplant_12mo", spy)

        result = bs.compute_brier_score("intestine", "A+", n_iterations=200)
        assert result.n_cities >= 1
        assert codes_seen, "analytical benchmark never called"
        # In 248-center mode every simulated row carries a center code
        assert all(c for c in codes_seen), f"empty center_code in {codes_seen[:5]}"

    def test_center_factors_change_analytical_value(self, data):
        """Two centers with different center-level factors must give different
        analytical probabilities — identical values would mean the factors are
        being dropped again."""
        from services.data_loader import get_data

        wt = get_data().center_wait_times.get("center_wait_time_factors", {})
        # pick two kidney centers with clearly different wait factors
        kidney = {
            code: f.get("kidney") for code, f in wt.items()
            if isinstance(f, dict) and isinstance(f.get("kidney"), (int, float))
        }
        assert len(kidney) > 2, "need center wait factors for this test"
        lo = min(kidney, key=kidney.get)
        hi = max(kidney, key=kidney.get)
        p_lo = _analytical_p_transplant_12mo("kidney", "O+", "x", center_code=lo)
        p_hi = _analytical_p_transplant_12mo("kidney", "O+", "x", center_code=hi)
        assert p_lo != p_hi
        assert p_lo > p_hi, (
            f"lower wait factor should mean higher p12: {lo}={p_lo}, {hi}={p_hi}"
        )
