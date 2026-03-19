"""Tests for MCMC inference service (Phase 5 M3)."""

import json

import numpy as np
import pytest

from models.schemas import PatientProfile, SimulationResult
from services.mcmc_survival import BLOOD_TYPES, build_organ_model, load_organ_data


# ---------------------------------------------------------------------------
# Shared fixture: quick-fit kidney trace saved to disk
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def _fit_kidney_trace():
    """Fit a quick kidney trace and save to disk for inference tests."""
    import pymc as pm
    from services.mcmc_survival import save_trace

    data = load_organ_data("kidney")
    model = build_organ_model(data)
    with model:
        trace = pm.sample(
            draws=100, chains=1, tune=50, random_seed=42,
            target_accept=0.85, return_inferencedata=True,
            progressbar=False,
        )
    trace.attrs["organ"] = "kidney"
    trace.attrs["cities"] = json.dumps(data["cities"])
    trace.attrs["blood_types"] = json.dumps(BLOOD_TYPES)
    save_trace("kidney", trace)
    yield
    # Cleanup: remove trace file after tests
    from services.mcmc_survival import TRACE_DIR
    trace_path = TRACE_DIR / "kidney.nc"
    if trace_path.exists():
        trace_path.unlink()


# ---------------------------------------------------------------------------
# Availability tests
# ---------------------------------------------------------------------------

class TestAvailability:
    def test_kidney_available(self):
        from services.mcmc_inference import is_available
        assert is_available("kidney") is True

    def test_liver_not_available(self):
        from services.mcmc_inference import is_available
        # Only kidney was fitted in the fixture
        assert is_available("liver") is False


# ---------------------------------------------------------------------------
# Simulation result structure tests
# ---------------------------------------------------------------------------

@pytest.fixture
def kidney_patient():
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2)


class TestSimulationResultStructure:
    def test_returns_simulation_result(self, kidney_patient):
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=200)
        assert isinstance(result, SimulationResult)

    def test_inference_mode_is_mcmc(self, kidney_patient):
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=200)
        assert result.inference_mode == "mcmc"

    def test_22_cities_present(self, kidney_patient):
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=200)
        assert len(result.cities) == 22

    def test_probabilities_valid(self, kidney_patient):
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=200)
        for city in result.cities:
            assert 0 <= city.p_transplant_6mo <= 1
            assert 0 <= city.p_transplant_12mo <= 1
            assert 0 <= city.p_transplant_24mo <= 1
            assert 0 <= city.p_transplant_36mo <= 1

    def test_probabilities_monotonic(self, kidney_patient):
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=500)
        for city in result.cities:
            assert city.p_transplant_6mo <= city.p_transplant_12mo + 0.02
            assert city.p_transplant_12mo <= city.p_transplant_24mo + 0.02
            assert city.p_transplant_24mo <= city.p_transplant_36mo + 0.02

    def test_median_wait_positive(self, kidney_patient):
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=200)
        for city in result.cities:
            assert city.median_wait_months > 0

    def test_ranked_by_p24_descending(self, kidney_patient):
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=500)
        probs = [c.p_transplant_24mo for c in result.cities]
        assert probs == sorted(probs, reverse=True)

    def test_competing_risks_present(self, kidney_patient):
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=200)
        for city in result.cities:
            cr = city.competing_risks
            assert cr is not None
            assert "p_transplant_24mo" in cr
            assert "p_mortality_24mo" in cr
            assert "p_delisting_24mo" in cr
            assert "p_still_waiting_24mo" in cr

    def test_confidence_intervals(self, kidney_patient):
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=200)
        for city in result.cities:
            lo, hi = city.confidence_interval_95
            assert 0 <= lo <= 1
            assert 0 <= hi <= 1
            assert lo <= hi

    def test_elapsed_seconds(self, kidney_patient):
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=200)
        assert result.elapsed_seconds > 0
        assert result.elapsed_seconds < 30


# ---------------------------------------------------------------------------
# Clinical parameter tests
# ---------------------------------------------------------------------------

class TestClinicalParameters:
    def test_blood_type_ab_better_than_o(self):
        """AB+ (universal recipient) should have higher p24 than O+."""
        from services.mcmc_inference import simulate_mcmc
        patient_o = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2)
        patient_ab = PatientProfile(organ="kidney", blood_type="AB+", age=45, sex="male", urgency=2)
        result_o = simulate_mcmc(patient_o, n_iterations=500)
        result_ab = simulate_mcmc(patient_ab, n_iterations=500)
        best_o = result_o.cities[0].p_transplant_24mo
        best_ab = result_ab.cities[0].p_transplant_24mo
        assert best_ab > best_o, f"AB+ ({best_ab}) should beat O+ ({best_o})"

    def test_copula_works_with_mcmc(self):
        """MCMC inference should work with copula enabled."""
        from services.mcmc_inference import simulate_mcmc
        patient = PatientProfile(
            organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
            use_copula=True,
        )
        result = simulate_mcmc(patient, n_iterations=200)
        assert len(result.cities) == 22
        for city in result.cities:
            assert 0 <= city.p_transplant_24mo <= 1


# ---------------------------------------------------------------------------
# Bayesian HDI tests
# ---------------------------------------------------------------------------

class TestBayesianHDI:
    def test_ci_width_positive(self, kidney_patient):
        """Bayesian credible interval should have non-zero width for top cities."""
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=500)
        widths = [c.confidence_interval_95[1] - c.confidence_interval_95[0]
                  for c in result.cities]
        # At least one city should have CI width > 0.01
        assert max(widths) > 0.01, f"Max CI width {max(widths)} too narrow"

    def test_ci_contains_point_estimate(self, kidney_patient):
        """The point estimate p24 should be within or near the CI."""
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=500)
        top = result.cities[0]
        lo, hi = top.confidence_interval_95
        # Allow tolerance for MC noise
        assert lo <= top.p_transplant_24mo + 0.05
        assert hi >= top.p_transplant_24mo - 0.05


# ---------------------------------------------------------------------------
# Shared frailty tests
# ---------------------------------------------------------------------------

class TestSharedFrailty:
    def test_mcmc_without_copula_flag(self, kidney_patient):
        """MCMC with shared frailty should work without external copula."""
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=200)
        assert len(result.cities) == 22
        for city in result.cities:
            assert 0 <= city.p_transplant_24mo <= 1

    def test_competing_risks_sum_to_one(self, kidney_patient):
        """Competing risks should sum to ~1.0 with shared frailty."""
        from services.mcmc_inference import simulate_mcmc
        result = simulate_mcmc(kidney_patient, n_iterations=300)
        for city in result.cities:
            cr = city.competing_risks
            total = (cr["p_transplant_24mo"] + cr["p_mortality_24mo"] +
                     cr["p_delisting_24mo"] + cr["p_still_waiting_24mo"])
            assert 0.95 <= total <= 1.05, f"{city.city}: total={total}"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_missing_trace_raises(self):
        from services.mcmc_inference import simulate_mcmc
        patient = PatientProfile(organ="liver", blood_type="A+", age=40, sex="male", urgency=2)
        with pytest.raises(RuntimeError, match="No MCMC trace"):
            simulate_mcmc(patient, n_iterations=200)
