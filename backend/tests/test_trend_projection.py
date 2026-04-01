"""Tests for F2: Population trend projection."""
import pytest

from services.monte_carlo import simulate
from services.trends import get_trend_projection


# -- Unit tests for get_trend_projection --

class TestGetTrendProjection:
    def test_returns_dict_with_three_factors(self, data):
        result = get_trend_projection("kidney", "Pittsburgh", years_forward=1.0)
        assert "wait_time_factor" in result
        assert "mortality_factor" in result
        assert "delisting_factor" in result

    def test_zero_years_returns_all_ones(self, data):
        result = get_trend_projection("kidney", "Pittsburgh", years_forward=0.0)
        assert result["wait_time_factor"] == 1.0
        assert result["mortality_factor"] == 1.0
        assert result["delisting_factor"] == 1.0

    def test_unknown_city_returns_all_ones(self, data):
        result = get_trend_projection("kidney", "Nonexistent City", years_forward=2.0)
        assert result["wait_time_factor"] == 1.0
        assert result["mortality_factor"] == 1.0
        assert result["delisting_factor"] == 1.0

    def test_invalid_organ_returns_all_ones(self, data):
        result = get_trend_projection("unicorn", "Pittsburgh", years_forward=1.0)
        assert result["wait_time_factor"] == 1.0

    def test_factors_clamped_to_valid_range(self, data):
        for organ in ("kidney", "liver", "heart", "lung"):
            result = get_trend_projection(organ, "Pittsburgh", years_forward=5.0)
            for key in ("wait_time_factor", "mortality_factor", "delisting_factor"):
                assert 0.5 <= result[key] <= 2.0, f"{organ}/{key}={result[key]} out of range"


# -- Integration tests --

class TestTrendProjectionIntegration:
    def test_simulate_with_trends_runs(self, data, kidney_patient):
        result = simulate(kidney_patient, n_iterations=200, seed=42, trend_years=1.0)
        assert len(result.cities) > 0
        assert all(0 <= c.p_transplant_24mo <= 1 for c in result.cities)

    def test_trend_zero_matches_baseline(self, data, kidney_patient):
        r1 = simulate(kidney_patient, n_iterations=200, seed=42, trend_years=0.0)
        r2 = simulate(kidney_patient, n_iterations=200, seed=42)
        for c1, c2 in zip(r1.cities, r2.cities):
            assert c1.p_transplant_24mo == c2.p_transplant_24mo

    def test_seed_reproducibility_with_trends(self, data, kidney_patient):
        r1 = simulate(kidney_patient, n_iterations=200, seed=77, trend_years=2.0)
        r2 = simulate(kidney_patient, n_iterations=200, seed=77, trend_years=2.0)
        for c1, c2 in zip(r1.cities, r2.cities):
            assert c1.p_transplant_24mo == c2.p_transplant_24mo

    def test_trends_change_results_for_mapped_centers(self, data, kidney_patient):
        baseline = simulate(kidney_patient, n_iterations=300, seed=42, trend_years=0.0)
        with_trends = simulate(kidney_patient, n_iterations=300, seed=42, trend_years=2.0)

        diffs = [
            abs(c1.p_transplant_24mo - c2.p_transplant_24mo)
            for c1, c2 in zip(baseline.cities, with_trends.cities)
        ]
        assert max(diffs) > 0, "Trend projection should change at least some center results"
