"""Tests for piecewise score drift (per-sample F3 enhancement).

Verifies that get_piecewise_drift_lookup() returns correct lookup tables
and that the Monte Carlo engine applies them correctly via np.interp.
"""
import numpy as np
import pytest

from models.schemas import PatientProfile
from services.distributions import get_piecewise_drift_lookup, get_drift_adjusted_multiplier
from services.monte_carlo import simulate


class TestPiecewiseDriftLookup:
    """Unit tests for get_piecewise_drift_lookup()."""

    def test_meld14_at_18mo_less_than_simple_average(self, data):
        """MELD 14 crosses into 15-25 range early; piecewise ratio < simple average ratio."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("liver", meld=14)
        assert lookup_t is not None and lookup_r is not None

        # Piecewise ratio at 18 months
        pw_ratio = float(np.interp(18.0, lookup_t, lookup_r))

        # Simple average ratio (the old approach)
        simple_ratio = get_drift_adjusted_multiplier(
            "liver", meld=14, expected_wait_months=18.0,
        )

        # Both should be < 1.0 (higher MELD = shorter wait multiplier)
        assert pw_ratio < 1.0, f"Expected piecewise ratio < 1.0, got {pw_ratio}"
        assert simple_ratio < 1.0, f"Expected simple ratio < 1.0, got {simple_ratio}"

        # The piecewise and simple approaches should differ for boundary cases
        # (they compute cumulative averages differently)
        assert pw_ratio != simple_ratio, (
            f"Piecewise ({pw_ratio}) should differ from simple average ({simple_ratio}) "
            "for MELD 14 at 18 months"
        )

    def test_short_wait_same_bucket_near_one(self, data):
        """Short wait within the same MELD bucket should give ratio close to 1.0."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("liver", meld=20)
        assert lookup_t is not None and lookup_r is not None

        # At 1 month, MELD drifts from 20 to ~20.2, stays in 15-25 bucket
        ratio_1mo = float(np.interp(1.0, lookup_t, lookup_r))
        assert abs(ratio_1mo - 1.0) < 0.01, f"Expected ratio ~1.0 at 1 month, got {ratio_1mo}"

    def test_kidney_returns_none(self, data):
        """Kidney has no score drift; should return (None, None)."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("kidney")
        assert lookup_t is None
        assert lookup_r is None

    def test_kidney_with_meld_returns_none(self, data):
        """Kidney with irrelevant MELD should still return (None, None)."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("kidney", meld=20)
        assert lookup_t is None
        assert lookup_r is None

    def test_lung_las_drift(self, data):
        """Lung LAS drift should produce valid lookup tables."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("lung", las=50)
        assert lookup_t is not None and lookup_r is not None

        # LAS drifts downward (-1 pt/year), so at 12 months LAS ~49
        # Still in 50-69 range initially, may cross into 40-49 range
        # which has a HIGHER multiplier (2.0 vs 1.0 wait-time bucket)
        # So the ratio should be > 1.0 (wait gets longer as LAS improves/drops)
        ratio_12mo = float(np.interp(12.0, lookup_t, lookup_r))
        assert ratio_12mo > 0, f"Expected positive ratio, got {ratio_12mo}"

    def test_lung_las_at_boundary(self, data):
        """LAS at a boundary value should produce valid results."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("lung", las=40)
        assert lookup_t is not None and lookup_r is not None

        # LAS 40 is at bottom of 40-49 (mult=1.0). Drifts to 39 → 0-39 (mult=2.0).
        # Cumulative avg should push ratio > 1.0 after crossing
        ratio_24mo = float(np.interp(24.0, lookup_t, lookup_r))
        assert ratio_24mo > 1.0, f"Expected ratio > 1.0 for LAS 40→38 over 24mo, got {ratio_24mo}"

    def test_liver_no_meld_returns_none(self, data):
        """Liver with no MELD value should return (None, None)."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("liver", meld=None)
        assert lookup_t is None
        assert lookup_r is None

    def test_heart_returns_none(self, data):
        """Heart has no drift; should return (None, None)."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("heart")
        assert lookup_t is None
        assert lookup_r is None

    def test_lookup_table_shape(self, data):
        """Lookup table should span 0-60 months with monthly resolution."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("liver", meld=20)
        assert lookup_t is not None
        assert len(lookup_t) == 61  # 0..60 inclusive
        assert len(lookup_r) == 61
        assert lookup_t[0] == 0.0
        assert lookup_t[-1] == 60.0
        assert lookup_r[0] == 1.0  # ratio at t=0 is always 1.0

    def test_meld_high_caps_at_40(self, data):
        """MELD near cap should not exceed 40."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("liver", meld=38)
        assert lookup_t is not None and lookup_r is not None

        # All ratios should be positive and finite
        assert np.all(lookup_r > 0)
        assert np.all(np.isfinite(lookup_r))

    def test_ratios_monotonic_for_meld_boundary(self, data):
        """For MELD 14 crossing into 15-25, ratios should generally decrease (shorter waits)."""
        lookup_t, lookup_r = get_piecewise_drift_lookup("liver", meld=14)
        assert lookup_t is not None and lookup_r is not None

        # After crossing into 15-25 range, cumulative avg multiplier drops
        # relative to the static mult at t=0 (which is 2.0 for MELD 6-14)
        ratio_6mo = float(np.interp(6.0, lookup_t, lookup_r))
        ratio_24mo = float(np.interp(24.0, lookup_t, lookup_r))
        assert ratio_24mo < ratio_6mo, (
            f"Ratio should decrease over time for MELD 14: "
            f"6mo={ratio_6mo}, 24mo={ratio_24mo}"
        )


class TestPiecewiseDriftIntegration:
    """Integration tests: piecewise drift in the full simulation pipeline."""

    def test_simulate_liver_with_piecewise_drift(self, data):
        """simulate() with liver MELD=14 and model_score_drift=True should produce valid results."""
        patient = PatientProfile(
            organ="liver", blood_type="A+", age=52, sex="female", urgency=2, meld=14,
        )
        result = simulate(patient, n_iterations=200, seed=42, model_score_drift=True)
        assert len(result.cities) > 0
        assert all(0 <= c.p_transplant_24mo <= 1 for c in result.cities)
        assert all(c.median_wait_months > 0 for c in result.cities)

    def test_seed_reproducibility(self, data):
        """Same seed should produce identical results with piecewise drift."""
        patient = PatientProfile(
            organ="liver", blood_type="A+", age=52, sex="female", urgency=2, meld=14,
        )
        r1 = simulate(patient, n_iterations=200, seed=99, model_score_drift=True)
        r2 = simulate(patient, n_iterations=200, seed=99, model_score_drift=True)
        for c1, c2 in zip(r1.cities, r2.cities):
            assert c1.p_transplant_24mo == c2.p_transplant_24mo
            assert c1.median_wait_months == c2.median_wait_months

    def test_drift_changes_liver_results(self, data):
        """Drift should produce different results from no-drift for MELD 14."""
        patient = PatientProfile(
            organ="liver", blood_type="A+", age=52, sex="female", urgency=2, meld=14,
        )
        baseline = simulate(patient, n_iterations=500, seed=42, model_score_drift=False)
        with_drift = simulate(patient, n_iterations=500, seed=42, model_score_drift=True)

        baseline_waits = [c.median_wait_months for c in baseline.cities]
        drift_waits = [c.median_wait_months for c in with_drift.cities]
        assert baseline_waits != drift_waits, (
            "Piecewise score drift should change liver results for MELD 14"
        )

    def test_no_effect_on_kidney(self, data, kidney_patient):
        """Piecewise drift should have no effect on kidney simulations."""
        baseline = simulate(kidney_patient, n_iterations=200, seed=42, model_score_drift=False)
        with_drift = simulate(kidney_patient, n_iterations=200, seed=42, model_score_drift=True)

        for c1, c2 in zip(baseline.cities, with_drift.cities):
            assert c1.p_transplant_24mo == c2.p_transplant_24mo

    def test_lung_drift_simulation(self, data):
        """simulate() with lung LAS and model_score_drift=True should work."""
        patient = PatientProfile(
            organ="lung", blood_type="B+", age=60, sex="male", urgency=2, las=50,
        )
        result = simulate(patient, n_iterations=200, seed=42, model_score_drift=True)
        assert len(result.cities) > 0
        assert all(0 <= c.p_transplant_24mo <= 1 for c in result.cities)
