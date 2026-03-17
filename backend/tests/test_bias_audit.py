"""Tests for the bias audit service (Phase 4 M5)."""
import pytest
import numpy as np

from services.bias_audit import (
    _cohens_d,
    _compute_dimension_disparity,
    _gini,
    run_bias_audit,
    BiasAuditResult,
    DisparityMetrics,
)


# --- Cohen's d ---

class TestCohensD:
    def test_identical_groups(self):
        d = _cohens_d([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
        assert d == 0.0

    def test_different_groups(self):
        d = _cohens_d([0.8, 0.9, 0.85], [0.2, 0.3, 0.25])
        assert d > 2.0  # Large effect

    def test_moderate_difference(self):
        d = _cohens_d([0.50, 0.51, 0.52], [0.49, 0.50, 0.51])
        assert 0.0 < abs(d) < 2.0  # Moderate effect (groups overlap)

    def test_empty_group(self):
        d = _cohens_d([], [0.5, 0.6])
        assert d == 0.0

    def test_single_element(self):
        d = _cohens_d([0.5], [0.5])
        assert d == 0.0


# --- Gini ---

class TestGini:
    def test_perfect_equality(self):
        g = _gini([0.5, 0.5, 0.5, 0.5])
        assert g == 0.0

    def test_some_inequality(self):
        g = _gini([0.1, 0.2, 0.3, 0.9])
        assert 0.0 < g < 1.0

    def test_empty(self):
        g = _gini([])
        assert g == 0.0

    def test_single(self):
        g = _gini([0.5])
        assert g == 0.0


# --- Dimension Disparity ---

class TestDimensionDisparity:
    def test_basic(self):
        groups = {"O+": [0.3, 0.35], "AB+": [0.6, 0.65]}
        result = _compute_dimension_disparity(groups, "blood_type")
        assert result.dimension == "blood_type"
        assert result.max_group == "AB+"
        assert result.min_group == "O+"
        assert result.disparity_ratio > 1.0
        assert result.absolute_gap > 0.0

    def test_identical_groups(self):
        groups = {"male": [0.5, 0.5], "female": [0.5, 0.5]}
        result = _compute_dimension_disparity(groups, "sex")
        assert result.disparity_ratio == 1.0
        assert result.absolute_gap == 0.0

    def test_empty(self):
        result = _compute_dimension_disparity({}, "age")
        assert result.disparity_ratio == 1.0


# --- Full Bias Audit ---

class TestBiasAudit:
    @pytest.fixture
    def mock_equity_result(self):
        """Create a minimal mock equity analysis result."""
        profiles = []
        for bt in ["O+", "A+", "AB+"]:
            for age in ["18-34", "35-54"]:
                for sex in ["male", "female"]:
                    # AB+ gets higher probability, O+ lower
                    base = 0.5
                    if bt == "O+":
                        base = 0.3
                    elif bt == "AB+":
                        base = 0.7
                    profiles.append({
                        "blood_type": bt,
                        "age_bracket": age,
                        "sex": sex,
                        "p_transplant_24mo": base + np.random.default_rng(42).uniform(-0.02, 0.02),
                    })

        return {
            "cities": [
                {"city": "Chicago", "gini": 0.12, "profiles": profiles},
                {"city": "New York", "gini": 0.15, "profiles": profiles},
            ]
        }

    def test_returns_result(self, mock_equity_result):
        result = run_bias_audit(mock_equity_result)
        assert isinstance(result, BiasAuditResult)
        assert result.n_cities == 2
        assert result.n_profiles == 48

    def test_city_profiles(self, mock_equity_result):
        result = run_bias_audit(mock_equity_result)
        assert len(result.city_profiles) == 2
        assert result.city_profiles[0].city == "Chicago"

    def test_national_disparities(self, mock_equity_result):
        result = run_bias_audit(mock_equity_result)
        assert result.national_blood_type_disparity is not None
        assert result.national_blood_type_disparity.dimension == "blood_type"
        assert result.national_blood_type_disparity.disparity_ratio > 1.0

    def test_national_gini(self, mock_equity_result):
        result = run_bias_audit(mock_equity_result)
        assert 0.0 <= result.national_gini <= 1.0

    def test_blood_type_is_dominant_disparity(self, mock_equity_result):
        """Blood type should be the largest disparity driver."""
        result = run_bias_audit(mock_equity_result)
        bt_gap = result.national_blood_type_disparity.absolute_gap
        sex_gap = result.national_sex_disparity.absolute_gap
        assert bt_gap > sex_gap

    def test_empty_input(self):
        result = run_bias_audit({"cities": []})
        assert result.n_cities == 0
        assert result.national_gini == 0.0

    def test_warnings_for_large_disparity(self, mock_equity_result):
        result = run_bias_audit(mock_equity_result)
        # Our mock has O+ (0.3) vs AB+ (0.7) → ratio > 2.0
        assert any("Blood type disparity" in w for w in result.warnings)
