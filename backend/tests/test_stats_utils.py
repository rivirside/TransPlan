"""Tests for shared statistical utilities (stats_utils.py)."""

import logging

import numpy as np
import pytest

from services.stats_utils import (
    ZERO_RATE_SCALE_MONTHS,
    get_range_multiplier,
    gini,
    rate_to_exponential_scale,
)


class TestRateToExponentialScale:
    def test_positive_rate(self):
        """Annual rate of 0.12 → mean time-to-event of 100 months."""
        assert rate_to_exponential_scale(0.12, "mortality") == pytest.approx(100.0)

    def test_annual_rate_of_one(self):
        assert rate_to_exponential_scale(1.0, "delisting") == pytest.approx(12.0)

    def test_zero_rate_falls_back_and_warns(self, caplog):
        """Zero rate → near-zero risk fallback, logged as a data problem (#229)."""
        with caplog.at_level(logging.WARNING, logger="services.stats_utils"):
            scale = rate_to_exponential_scale(0.0, "mortality", "TESTCTR")
        assert scale == ZERO_RATE_SCALE_MONTHS
        assert "TESTCTR" in caplog.text
        assert "mortality" in caplog.text

    def test_negative_rate_falls_back_and_warns(self, caplog):
        with caplog.at_level(logging.WARNING, logger="services.stats_utils"):
            scale = rate_to_exponential_scale(-0.01, "delisting")
        assert scale == ZERO_RATE_SCALE_MONTHS
        assert "delisting" in caplog.text


class TestGiniValidation:
    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            gini(np.array([1.0, -2.0]))

    def test_nan_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            gini(np.array([1.0, np.nan]))

    def test_valid_input_unchanged(self):
        assert gini(np.ones(10)) == 0.0
        assert 0.0 < gini(np.array([0.1, 0.2, 0.3, 0.4, 0.5])) < 1.0


class TestGetRangeMultiplier:
    def test_match(self):
        assert get_range_multiplier(50, {"0-20": 0.5, "21-80": 1.5}) == 1.5

    def test_no_match_returns_one(self):
        assert get_range_multiplier(200, {"0-20": 0.5}) == 1.0


# -- Weighted Gini (#254) --

class TestWeightedGini:
    def test_equal_weights_match_unweighted(self):
        from services.stats_utils import gini, gini_weighted
        vals = np.array([0.1, 0.2, 0.3, 0.4, 0.9])
        w = np.ones(5)
        assert abs(gini_weighted(vals, w) - gini(vals)) < 1e-12

    def test_zero_weight_cells_ignored(self):
        from services.stats_utils import gini, gini_weighted
        vals = np.array([0.1, 0.2, 0.3, 5.0])
        w = np.array([1.0, 1.0, 1.0, 0.0])
        assert abs(gini_weighted(vals, w) - gini(vals[:3])) < 1e-12

    def test_perfect_equality_zero(self):
        from services.stats_utils import gini_weighted
        assert gini_weighted(np.array([0.4, 0.4, 0.4]), np.array([0.2, 0.5, 0.3])) == 0.0

    def test_weight_scaling_invariant(self):
        from services.stats_utils import gini_weighted
        vals = np.array([0.1, 0.5, 0.9])
        w = np.array([0.2, 0.3, 0.5])
        g1 = gini_weighted(vals, w)
        g2 = gini_weighted(vals, w * 100)
        assert abs(g1 - g2) < 1e-12

    def test_rejects_negative_values(self):
        from services.stats_utils import gini_weighted
        with pytest.raises(ValueError):
            gini_weighted(np.array([-0.1, 0.5]), np.array([1.0, 1.0]))

    def test_known_two_point_case(self):
        """Two cells, one holds everything: weighted Gini = weight share of
        the zero cell. With w=(0.75, 0.25) and values (0, x): G = 0.75."""
        from services.stats_utils import gini_weighted
        g = gini_weighted(np.array([0.0, 1.0]), np.array([0.75, 0.25]))
        assert abs(g - 0.75) < 1e-9
