"""Tests for services/trends.py — historical trends & center trajectory analysis.

Uses the session-scoped `data` fixture from conftest.py which calls load_all().
Tests that hit _get_historical_data() require data to be loaded first.
"""
import pytest
import numpy as np
from services.trends import (
    get_city_trends,
    get_all_trends,
    _compute_metric_trend,
    _classify_trend,
    _overall_direction,
    VALID_ORGANS,
    MIN_POINTS,
    P_VALUE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Unit tests: _compute_metric_trend (pure function, no data dependency)
# ---------------------------------------------------------------------------

class TestComputeMetricTrend:
    def test_clearly_decreasing_wait_time_is_improving(self):
        years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        values = [48.0, 46.0, 44.0, 42.0, 40.0, 38.0, 36.0]
        result = _compute_metric_trend(years, values, "median_wait_months")
        assert result["direction"] == "improving"
        assert result["slope"] < 0
        assert result["p_value"] is not None
        assert result["p_value"] < P_VALUE_THRESHOLD

    def test_clearly_increasing_wait_time_is_declining(self):
        years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        values = [30.0, 32.0, 34.0, 36.0, 38.0, 40.0, 42.0]
        result = _compute_metric_trend(years, values, "median_wait_months")
        assert result["direction"] == "declining"
        assert result["slope"] > 0

    def test_increasing_volume_is_improving(self):
        years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        values = [200, 210, 220, 230, 240, 250, 260]
        result = _compute_metric_trend(years, values, "volume")
        assert result["direction"] == "improving"
        assert result["slope"] > 0

    def test_decreasing_volume_is_declining(self):
        years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        values = [300, 280, 260, 240, 220, 200, 180]
        result = _compute_metric_trend(years, values, "volume")
        assert result["direction"] == "declining"

    def test_increasing_graft_survival_is_improving(self):
        years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        values = [90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0]
        result = _compute_metric_trend(years, values, "graft_survival_1yr")
        assert result["direction"] == "improving"
        assert result["slope"] > 0

    def test_decreasing_mortality_rate_is_improving(self):
        years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        values = [0.05, 0.045, 0.040, 0.035, 0.030, 0.025, 0.020]
        result = _compute_metric_trend(years, values, "mortality_rate")
        assert result["direction"] == "improving"
        assert result["slope"] < 0  # lower is better

    def test_flat_series_is_stable(self):
        years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        values = [40.0, 40.1, 39.9, 40.0, 40.1, 39.9, 40.0]
        result = _compute_metric_trend(years, values, "median_wait_months")
        assert result["direction"] == "stable"

    def test_all_identical_values_is_stable(self):
        years = [2019, 2020, 2021, 2022, 2023]
        values = [35.0, 35.0, 35.0, 35.0, 35.0]
        result = _compute_metric_trend(years, values, "median_wait_months")
        assert result["direction"] == "stable"

    def test_only_two_points_is_insufficient(self):
        years = [2023, 2024]
        values = [40.0, 35.0]
        result = _compute_metric_trend(years, values, "median_wait_months")
        assert result["direction"] == "insufficient_data"
        assert result["slope"] is None
        assert result["p_value"] is None

    def test_only_one_point_is_insufficient(self):
        result = _compute_metric_trend([2025], [36.0], "median_wait_months")
        assert result["direction"] == "insufficient_data"

    def test_empty_data_is_insufficient(self):
        result = _compute_metric_trend([], [], "median_wait_months")
        assert result["direction"] == "insufficient_data"

    def test_null_values_filtered_before_regression(self):
        years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        values = [48.0, None, 44.0, None, 40.0, None, 36.0]
        result = _compute_metric_trend(years, values, "median_wait_months")
        # 4 valid points — enough for regression
        assert result["direction"] in ("improving", "stable", "declining")
        assert result["slope"] is not None

    def test_all_null_values_is_insufficient(self):
        years = [2019, 2020, 2021]
        values = [None, None, None]
        result = _compute_metric_trend(years, values, "median_wait_months")
        assert result["direction"] == "insufficient_data"

    def test_years_and_values_preserved_in_result(self):
        years = [2019, 2020, 2021, 2022]
        values = [40.0, 38.0, 36.0, 34.0]
        result = _compute_metric_trend(years, values, "median_wait_months")
        assert result["years"] == years
        assert result["values"] == values

    def test_change_per_year_is_rounded(self):
        years = [2019, 2020, 2021, 2022, 2023]
        values = [40.0, 38.0, 36.0, 34.0, 32.0]
        result = _compute_metric_trend(years, values, "median_wait_months")
        assert result["change_per_year"] is not None
        # Should be exactly -2.0 per year
        assert result["change_per_year"] == pytest.approx(-2.0, abs=0.01)


# ---------------------------------------------------------------------------
# Unit tests: _classify_trend
# ---------------------------------------------------------------------------

class TestClassifyTrend:
    def test_non_significant_is_stable(self):
        assert _classify_trend(-5.0, 0.50, "median_wait_months", 0.5) == "stable"

    def test_small_slope_is_stable(self):
        assert _classify_trend(-0.01, 0.05, "median_wait_months", 0.5) == "stable"

    def test_negative_wait_time_slope_is_improving(self):
        assert _classify_trend(-2.0, 0.01, "median_wait_months", 0.5) == "improving"

    def test_positive_wait_time_slope_is_declining(self):
        assert _classify_trend(2.0, 0.01, "median_wait_months", 0.5) == "declining"

    def test_positive_volume_slope_is_improving(self):
        assert _classify_trend(10.0, 0.01, "volume", 3.0) == "improving"

    def test_negative_volume_slope_is_declining(self):
        assert _classify_trend(-10.0, 0.01, "volume", 3.0) == "declining"


# ---------------------------------------------------------------------------
# Unit tests: _overall_direction
# ---------------------------------------------------------------------------

class TestOverallDirection:
    def test_all_improving(self):
        trends = {
            "wait_time_trend": {"direction": "improving"},
            "volume_trend": {"direction": "improving"},
            "graft_survival_trend": {"direction": "improving"},
            "mortality_rate_trend": {"direction": "improving"},
        }
        assert _overall_direction(trends) == "improving"

    def test_all_declining(self):
        trends = {
            "wait_time_trend": {"direction": "declining"},
            "volume_trend": {"direction": "declining"},
            "graft_survival_trend": {"direction": "declining"},
            "mortality_rate_trend": {"direction": "declining"},
        }
        assert _overall_direction(trends) == "declining"

    def test_mixed_biased_improving(self):
        trends = {
            "wait_time_trend": {"direction": "improving"},  # weight 3
            "volume_trend": {"direction": "improving"},      # weight 2
            "graft_survival_trend": {"direction": "stable"},  # weight 2
            "mortality_rate_trend": {"direction": "stable"},  # weight 1
        }
        assert _overall_direction(trends) == "improving"

    def test_all_stable(self):
        trends = {
            "wait_time_trend": {"direction": "stable"},
            "volume_trend": {"direction": "stable"},
            "graft_survival_trend": {"direction": "stable"},
            "mortality_rate_trend": {"direction": "stable"},
        }
        assert _overall_direction(trends) == "stable"

    def test_all_insufficient_data(self):
        trends = {
            "wait_time_trend": {"direction": "insufficient_data"},
            "volume_trend": {"direction": "insufficient_data"},
            "graft_survival_trend": {"direction": "insufficient_data"},
            "mortality_rate_trend": {"direction": "insufficient_data"},
        }
        assert _overall_direction(trends) == "insufficient_data"

    def test_empty_trends(self):
        assert _overall_direction({}) == "insufficient_data"


# ---------------------------------------------------------------------------
# Integration tests: get_city_trends (requires loaded data)
# ---------------------------------------------------------------------------

class TestGetCityTrends:
    def test_known_city_returns_trend_data(self, data):
        trend = get_city_trends("kidney", "Cleveland")
        assert trend is not None
        assert "wait_time_trend" in trend
        assert "volume_trend" in trend
        assert "graft_survival_trend" in trend
        assert "overall_direction" in trend
        assert "sparklines" in trend
        assert trend["city"] == "Cleveland"
        assert trend["organ"] == "kidney"

    def test_overall_direction_is_valid(self, data):
        trend = get_city_trends("kidney", "Cleveland")
        assert trend is not None
        assert trend["overall_direction"] in ("improving", "stable", "declining", "insufficient_data")

    def test_sparklines_have_years_and_data(self, data):
        trend = get_city_trends("kidney", "Cleveland")
        assert trend is not None
        sparklines = trend["sparklines"]
        assert "years" in sparklines
        assert "wait_time" in sparklines
        assert "volume" in sparklines
        assert "graft_survival" in sparklines
        assert len(sparklines["years"]) > 0
        assert len(sparklines["wait_time"]) == len(sparklines["years"])

    def test_national_data_included(self, data):
        trend = get_city_trends("kidney", "Pittsburgh")
        assert trend is not None
        assert "national" in trend
        assert "years" in trend["national"]
        assert "wait_time" in trend["national"]

    def test_all_metric_trends_have_required_fields(self, data):
        trend = get_city_trends("kidney", "Cleveland")
        assert trend is not None
        for key in ["wait_time_trend", "volume_trend", "graft_survival_trend", "mortality_rate_trend"]:
            mt = trend[key]
            assert "years" in mt
            assert "values" in mt
            assert "direction" in mt
            assert mt["direction"] in ("improving", "stable", "declining", "insufficient_data")

    def test_slope_sign_matches_direction(self, data):
        """For metrics with a clear direction, verify slope sign is consistent."""
        trend = get_city_trends("kidney", "Cleveland")
        assert trend is not None
        wt = trend["wait_time_trend"]
        if wt["direction"] == "improving" and wt["slope"] is not None:
            assert wt["slope"] < 0  # shorter waits = negative slope
        elif wt["direction"] == "declining" and wt["slope"] is not None:
            assert wt["slope"] > 0

    def test_invalid_organ_returns_none(self, data):
        assert get_city_trends("spleen", "Cleveland") is None

    def test_unknown_city_returns_none(self, data):
        assert get_city_trends("kidney", "Atlantis") is None

    @pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung"])
    def test_major_organs_have_trend_data(self, data, organ):
        trend = get_city_trends(organ, "Pittsburgh")
        assert trend is not None
        assert trend["overall_direction"] in ("improving", "stable", "declining", "insufficient_data")

    def test_pancreas_may_have_null_values(self, data):
        """Pancreas programs are smaller; some cities may have sparse data."""
        trend = get_city_trends("pancreas", "Cleveland")
        # Should return a trend (or None if no data), but shouldn't crash
        if trend:
            wt = trend["wait_time_trend"]
            assert wt["direction"] in ("improving", "stable", "declining", "insufficient_data")


# ---------------------------------------------------------------------------
# Integration tests: get_all_trends (requires loaded data)
# ---------------------------------------------------------------------------

class TestGetAllTrends:
    def test_returns_dict_of_trends(self, data):
        trends = get_all_trends("kidney")
        assert isinstance(trends, dict)
        assert len(trends) > 0
        for city, trend in trends.items():
            assert "overall_direction" in trend
            assert trend["organ"] == "kidney"

    def test_all_22_cities_have_kidney_trends(self, data):
        trends = get_all_trends("kidney")
        assert len(trends) >= 20  # Allow for a few cities without data

    def test_invalid_organ_returns_empty(self, data):
        trends = get_all_trends("spleen")
        assert trends == {}

    @pytest.mark.parametrize("organ", list(VALID_ORGANS))
    def test_all_organs_return_trends(self, data, organ):
        trends = get_all_trends(organ)
        assert isinstance(trends, dict)
        # All major organs should have at least some city trends
        if organ in ("kidney", "liver", "heart", "lung"):
            assert len(trends) >= 15


# ---------------------------------------------------------------------------
# Schema integration: CityProbability.trends field
# ---------------------------------------------------------------------------

class TestCityProbabilityTrendsField:
    def test_trends_field_accepts_dict(self):
        from models.schemas import CityProbability
        cp = CityProbability(
            city="Cleveland",
            state="OH",
            p_transplant_6mo=0.1,
            p_transplant_12mo=0.3,
            p_transplant_24mo=0.6,
            p_transplant_36mo=0.8,
            confidence_interval_95=(0.55, 0.65),
            median_wait_months=18.0,
            trends={"overall_direction": "improving", "wait_time_trend": {"direction": "improving"}},
        )
        assert cp.trends is not None
        assert cp.trends["overall_direction"] == "improving"

    def test_trends_field_defaults_to_none(self):
        from models.schemas import CityProbability
        cp = CityProbability(
            city="Cleveland",
            state="OH",
            p_transplant_6mo=0.1,
            p_transplant_12mo=0.3,
            p_transplant_24mo=0.6,
            p_transplant_36mo=0.8,
            confidence_interval_95=(0.55, 0.65),
            median_wait_months=18.0,
        )
        assert cp.trends is None
