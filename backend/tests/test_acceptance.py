"""Tests for F1: Organ acceptance rate modeling."""
import pytest

from services.monte_carlo import _get_acceptance_rate, simulate


# -- Unit tests for _get_acceptance_rate --

class TestGetAcceptanceRate:
    def test_known_organ_returns_positive(self, data):
        rate = _get_acceptance_rate("kidney", "PAPT")
        assert 0 < rate <= 1.0

    def test_unknown_center_returns_national_average(self, data):
        rate = _get_acceptance_rate("kidney", "ZZZZ")
        assert 0.15 <= rate <= 0.30

    def test_all_organs_have_national_rates(self, data):
        for organ in ("kidney", "liver", "heart", "lung", "pancreas", "intestine"):
            rate = _get_acceptance_rate(organ, "")
            assert rate > 0, f"No acceptance rate for {organ}"

    def test_rate_capped_at_one(self, data):
        for organ in ("kidney", "liver", "heart", "lung"):
            rate = _get_acceptance_rate(organ, "PAPT")
            assert rate <= 1.0


# -- Integration tests --

class TestAcceptanceIntegration:
    def test_simulate_with_acceptance_runs(self, data, kidney_patient):
        result = simulate(kidney_patient, n_iterations=200, seed=42, model_acceptance=True)
        assert len(result.cities) > 0
        assert all(0 <= c.p_transplant_24mo <= 1 for c in result.cities)

    def test_acceptance_reduces_transplant_probability(self, data, kidney_patient):
        baseline = simulate(kidney_patient, n_iterations=500, seed=42, model_acceptance=False)
        with_acceptance = simulate(kidney_patient, n_iterations=500, seed=42, model_acceptance=True)

        avg_baseline = sum(c.p_transplant_24mo for c in baseline.cities) / len(baseline.cities)
        avg_accept = sum(c.p_transplant_24mo for c in with_acceptance.cities) / len(with_acceptance.cities)

        assert avg_accept < avg_baseline, (
            f"Expected acceptance to reduce avg p24: baseline={avg_baseline:.4f}, "
            f"with_acceptance={avg_accept:.4f}"
        )

    def test_seed_reproducibility_with_acceptance(self, data, kidney_patient):
        r1 = simulate(kidney_patient, n_iterations=200, seed=123, model_acceptance=True)
        r2 = simulate(kidney_patient, n_iterations=200, seed=123, model_acceptance=True)
        for c1, c2 in zip(r1.cities, r2.cities):
            assert c1.p_transplant_24mo == c2.p_transplant_24mo

    def test_default_off_matches_baseline(self, data, kidney_patient):
        r1 = simulate(kidney_patient, n_iterations=200, seed=42, model_acceptance=False)
        r2 = simulate(kidney_patient, n_iterations=200, seed=42)
        for c1, c2 in zip(r1.cities, r2.cities):
            assert c1.p_transplant_24mo == c2.p_transplant_24mo
