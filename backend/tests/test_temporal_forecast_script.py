"""Unit tests for scripts/run-temporal-forecast.py core functions (#237).

The script is standalone (parses archived SRTR zips), but its model core —
sigma fit, wait factor, closed-form p12 — must mirror the production
derivations, so we pin their behavior here.
"""
import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "run-temporal-forecast.py"
_spec = importlib.util.spec_from_file_location("temporal_forecast", _SCRIPT)
tf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tf)


class TestWaitFactor:
    def test_median_ratio(self):
        f = tf.wait_factor({"p50": 20.0, "p25": 8.0}, {"p50": 10.0, "p25": 5.0})
        assert f == 2.0

    def test_clamped_to_parser_range(self):
        assert tf.wait_factor({"p50": 100.0}, {"p50": 10.0}) == 3.0
        assert tf.wait_factor({"p50": 1.0}, {"p50": 10.0}) == 0.3

    def test_censored_median_uses_p25(self):
        f = tf.wait_factor({"p50": tf.CENSORED, "p25": 10.0}, {"p50": 12.0, "p25": 5.0})
        assert f == 2.0

    def test_both_censored_conservative(self):
        f = tf.wait_factor({"p50": tf.CENSORED, "p25": tf.CENSORED}, {"p50": 12.0, "p25": 5.0})
        assert f == 2.5

    def test_no_data_returns_none(self):
        assert tf.wait_factor({"p50": None, "p25": None}, {"p50": None, "p25": None}) is None


class TestFitSigma:
    def test_clamped_range(self):
        assert 0.3 <= tf.fit_sigma(1.0, 1.01, 5.0, 6.0) <= 1.2
        assert 0.3 <= tf.fit_sigma(0.1, 50.0, 60.0, 70.0) <= 1.2

    def test_fallback(self):
        assert tf.fit_sigma(None, None, None, None) == 0.8


class TestPredictP12:
    def test_probability_bounds(self):
        p = tf.predict_p12(12.0, 0.8, 0.08, 0.04)
        assert 0.0 < p < 1.0

    def test_longer_wait_lower_p12(self):
        p_short = tf.predict_p12(6.0, 0.8, 0.08, 0.04)
        p_long = tf.predict_p12(30.0, 0.8, 0.08, 0.04)
        assert p_short > p_long

    def test_higher_mortality_lower_p12(self):
        p_low = tf.predict_p12(12.0, 0.8, 0.05, 0.04)
        p_high = tf.predict_p12(12.0, 0.8, 0.50, 0.04)
        assert p_low > p_high

    def test_ranking_driven_by_wait_factor(self):
        """The core property the forecast test relies on: centers with lower
        wait factors rank higher, monotonically."""
        medians = [6.0, 9.0, 12.0, 18.0, 24.0, 36.0]
        preds = [tf.predict_p12(m, 0.8, 0.08, 0.04) for m in medians]
        assert preds == sorted(preds, reverse=True)


class TestLagMonths:
    def test_same_year(self):
        assert tf._lag_months("1905", "1911") == 6

    def test_across_years(self):
        assert tf._lag_months("1811", "2511") == 84
