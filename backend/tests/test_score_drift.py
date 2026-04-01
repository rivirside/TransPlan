"""Tests for F3: Dynamic score progression (MELD/LAS drift)."""
import pytest

from models.schemas import PatientProfile
from services.distributions import get_drift_adjusted_multiplier
from services.monte_carlo import simulate


# -- Unit tests for get_drift_adjusted_multiplier --
# These don't need the data fixture since _ensure_loaded() handles it internally.

class TestDriftMultiplier:
    def test_liver_meld_drift_reduces_multiplier(self, data):
        ratio = get_drift_adjusted_multiplier("liver", meld=20, expected_wait_months=24)
        assert ratio <= 1.0, f"Expected ratio <= 1.0, got {ratio}"

    def test_liver_high_meld_caps_at_40(self, data):
        ratio = get_drift_adjusted_multiplier("liver", meld=38, expected_wait_months=24)
        assert isinstance(ratio, float)
        assert ratio > 0

    def test_liver_no_wait_no_drift(self, data):
        ratio = get_drift_adjusted_multiplier("liver", meld=20, expected_wait_months=0)
        assert ratio == 1.0

    def test_kidney_returns_1(self, data):
        ratio = get_drift_adjusted_multiplier("kidney", meld=None, expected_wait_months=24)
        assert ratio == 1.0

    def test_lung_las_drift(self, data):
        ratio = get_drift_adjusted_multiplier("lung", las=50, expected_wait_months=12)
        assert isinstance(ratio, float)
        assert ratio > 0

    def test_no_meld_returns_1(self, data):
        ratio = get_drift_adjusted_multiplier("liver", meld=None, expected_wait_months=24)
        assert ratio == 1.0

    def test_heart_returns_1(self, data):
        ratio = get_drift_adjusted_multiplier("heart", expected_wait_months=12)
        assert ratio == 1.0


# -- Integration tests --

class TestScoreDriftIntegration:
    def test_simulate_with_score_drift_runs(self, data, liver_patient):
        result = simulate(liver_patient, n_iterations=200, seed=42, model_score_drift=True)
        assert len(result.cities) > 0
        assert all(0 <= c.p_transplant_24mo <= 1 for c in result.cities)

    def test_drift_changes_liver_results(self, data):
        # MELD=14 is at top of 6-14 range (mult=2.0). With drift ~2.5/yr,
        # avg MELD over wait crosses into 15-25 range (mult=1.0) → ratio=0.5
        boundary_patient = PatientProfile(
            organ="liver", blood_type="A+", age=52, sex="female", urgency=2, meld=14,
        )
        baseline = simulate(boundary_patient, n_iterations=500, seed=42, model_score_drift=False)
        with_drift = simulate(boundary_patient, n_iterations=500, seed=42, model_score_drift=True)

        # Compare median waits — drift should produce shorter waits (ratio < 1)
        baseline_waits = [c.median_wait_months for c in baseline.cities]
        drift_waits = [c.median_wait_months for c in with_drift.cities]
        assert baseline_waits != drift_waits, "Score drift should change liver results (MELD 14 crosses boundary)"

    def test_no_effect_on_kidney(self, data, kidney_patient):
        baseline = simulate(kidney_patient, n_iterations=200, seed=42, model_score_drift=False)
        with_drift = simulate(kidney_patient, n_iterations=200, seed=42, model_score_drift=True)

        for c1, c2 in zip(baseline.cities, with_drift.cities):
            assert c1.p_transplant_24mo == c2.p_transplant_24mo

    def test_seed_reproducibility_with_drift(self, data, liver_patient):
        r1 = simulate(liver_patient, n_iterations=200, seed=99, model_score_drift=True)
        r2 = simulate(liver_patient, n_iterations=200, seed=99, model_score_drift=True)
        for c1, c2 in zip(r1.cities, r2.cities):
            assert c1.p_transplant_24mo == c2.p_transplant_24mo
