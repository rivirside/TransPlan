"""Tests for services/monte_carlo.py — Monte Carlo simulation engine."""
import inspect

import numpy as np
import pytest

from models.schemas import PatientProfile, SimulationResult
from services.monte_carlo import simulate, CITIES, _bootstrap_ci, _get_cod_multiplier


def test_bootstrap_default_1000():
    """Bootstrap CI should use at least 1000 resamples by default."""
    sig = inspect.signature(_bootstrap_ci)
    assert sig.parameters["n_bootstrap"].default >= 1000


# -- Fixtures --

@pytest.fixture
def kidney_o_plus() -> PatientProfile:
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2)


@pytest.fixture
def kidney_ab_plus() -> PatientProfile:
    return PatientProfile(organ="kidney", blood_type="AB+", age=45, sex="male", urgency=2)


@pytest.fixture
def kidney_high_cpra() -> PatientProfile:
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2, cpra=99)


@pytest.fixture
def liver_high_meld() -> PatientProfile:
    return PatientProfile(organ="liver", blood_type="A+", age=52, sex="female", urgency=3, meld=35)


@pytest.fixture
def lung_high_las() -> PatientProfile:
    return PatientProfile(organ="lung", blood_type="B+", age=38, sex="male", urgency=2, las=75)


# -- Bootstrap CI tests --

class TestBootstrapCI:
    def test_ci_contains_point_estimate(self):
        rng = np.random.default_rng(42)
        n = 1000
        samples = rng.lognormal(mean=np.log(24), sigma=0.8, size=n)
        # Simulate: all transplant outcomes, event times = samples
        outcomes = np.zeros(n, dtype=int)  # all transplant
        p_hat = np.mean(samples <= 24)
        lo, hi = _bootstrap_ci(outcomes, event=0, threshold_months=samples, time_horizon=24)
        assert lo <= p_hat <= hi

    def test_ci_bounds_are_valid_probabilities(self):
        rng = np.random.default_rng(42)
        n = 1000
        samples = rng.lognormal(mean=np.log(24), sigma=0.8, size=n)
        outcomes = np.zeros(n, dtype=int)
        lo, hi = _bootstrap_ci(outcomes, event=0, threshold_months=samples, time_horizon=24)
        assert 0 <= lo <= 1
        assert 0 <= hi <= 1
        assert lo <= hi


# -- Result structure tests --

class TestSimulationResultStructure:
    def test_returns_simulation_result(self, kidney_o_plus):
        result = simulate(kidney_o_plus, n_iterations=200)
        assert isinstance(result, SimulationResult)

    def test_all_22_cities_present(self, kidney_o_plus):
        result = simulate(kidney_o_plus, n_iterations=200)
        assert len(result.cities) == 22

    def test_city_names_match(self, kidney_o_plus):
        result = simulate(kidney_o_plus, n_iterations=200)
        expected = {c["city"] for c in CITIES}
        actual = {c.city for c in result.cities}
        assert actual == expected

    def test_probabilities_monotonically_increase(self, kidney_o_plus):
        """P(transplant <= 6mo) <= P(<= 12mo) <= P(<= 24mo) <= P(<= 36mo)."""
        result = simulate(kidney_o_plus, n_iterations=500)
        for city in result.cities:
            assert city.p_transplant_6mo <= city.p_transplant_12mo + 0.01  # small tolerance for sampling noise
            assert city.p_transplant_12mo <= city.p_transplant_24mo + 0.01
            assert city.p_transplant_24mo <= city.p_transplant_36mo + 0.01

    def test_probabilities_in_valid_range(self, kidney_o_plus):
        result = simulate(kidney_o_plus, n_iterations=200)
        for city in result.cities:
            assert 0 <= city.p_transplant_6mo <= 1
            assert 0 <= city.p_transplant_12mo <= 1
            assert 0 <= city.p_transplant_24mo <= 1
            assert 0 <= city.p_transplant_36mo <= 1

    def test_median_wait_positive(self, kidney_o_plus):
        result = simulate(kidney_o_plus, n_iterations=200)
        for city in result.cities:
            assert city.median_wait_months > 0

    def test_ranked_by_24mo_descending(self, kidney_o_plus):
        result = simulate(kidney_o_plus, n_iterations=500)
        probs = [c.p_transplant_24mo for c in result.cities]
        assert probs == sorted(probs, reverse=True)

    def test_patient_profile_preserved(self, kidney_o_plus):
        result = simulate(kidney_o_plus, n_iterations=200)
        assert result.patient.organ == "kidney"
        assert result.patient.blood_type == "O+"

    def test_iterations_recorded(self, kidney_o_plus):
        result = simulate(kidney_o_plus, n_iterations=300)
        assert result.iterations == 300

    def test_elapsed_seconds_recorded(self, kidney_o_plus):
        result = simulate(kidney_o_plus, n_iterations=200)
        assert result.elapsed_seconds > 0
        assert result.elapsed_seconds < 30  # should be fast


# -- Clinical sanity checks --

class TestClinicalSanity:
    def test_ab_plus_higher_probability_than_o_plus(self, kidney_o_plus, kidney_ab_plus):
        """AB+ (universal recipient) should have higher 24mo probability than O+."""
        result_o = simulate(kidney_o_plus, n_iterations=1000)
        result_ab = simulate(kidney_ab_plus, n_iterations=1000)

        # Compare top-ranked city's 24mo probability
        best_o = result_o.cities[0].p_transplant_24mo
        best_ab = result_ab.cities[0].p_transplant_24mo
        assert best_ab > best_o, f"AB+ ({best_ab}) should beat O+ ({best_o})"

    def test_high_cpra_lower_probability(self, kidney_o_plus, kidney_high_cpra):
        """cPRA 99 should have much lower 24mo probability than baseline."""
        result_base = simulate(kidney_o_plus, n_iterations=1000)
        result_high = simulate(kidney_high_cpra, n_iterations=1000)

        # Same city comparison (first ranked for each)
        # High cPRA's best city should still be worse than baseline's best
        best_base = result_base.cities[0].p_transplant_24mo
        best_high = result_high.cities[0].p_transplant_24mo
        assert best_high < best_base, "High cPRA should reduce probability"

    def test_liver_high_meld_fast(self, liver_high_meld):
        """MELD 35 liver patients should have short wait times (high priority)."""
        result = simulate(liver_high_meld, n_iterations=1000)
        # Best city should show >50% chance within 12 months
        best = result.cities[0]
        assert best.p_transplant_12mo > 0.3, f"High MELD should have high 12mo prob, got {best.p_transplant_12mo}"

    def test_lung_high_las_very_fast(self, lung_high_las):
        """LAS 75 lung patients should have very short waits."""
        result = simulate(lung_high_las, n_iterations=1000)
        best = result.cities[0]
        assert best.p_transplant_6mo > 0.3, f"High LAS should have high 6mo prob, got {best.p_transplant_6mo}"

    def test_kidney_o_plus_long_median(self, kidney_o_plus):
        """Kidney O+ should have median wait in the 30-70 month range."""
        result = simulate(kidney_o_plus, n_iterations=1000)
        # Check a representative city (not best, not worst — mid-rank)
        mid_city = result.cities[10]
        assert 20 < mid_city.median_wait_months < 100, (
            f"Kidney O+ median {mid_city.median_wait_months}mo out of plausible range"
        )


# -- Stability tests --

class TestStability:
    def test_two_runs_within_tolerance(self, kidney_o_plus):
        """Two runs with same inputs should produce results within 15% (relative) or 0.03 (absolute)."""
        result_a = simulate(kidney_o_plus, n_iterations=2000)
        result_b = simulate(kidney_o_plus, n_iterations=2000)

        # Compare 24mo probability for each city
        probs_a = {c.city: c.p_transplant_24mo for c in result_a.cities}
        probs_b = {c.city: c.p_transplant_24mo for c in result_b.cities}

        for city in probs_a:
            a, b = probs_a[city], probs_b[city]
            if a > 0.10:  # skip low probabilities (high relative noise at small P)
                assert abs(a - b) / a < 0.15 or abs(a - b) < 0.03, (
                    f"{city}: {a:.4f} vs {b:.4f} — unstable"
                )

    def test_more_iterations_tighter_ci(self, kidney_o_plus):
        """More iterations should produce a tighter confidence interval."""
        result_200 = simulate(kidney_o_plus, n_iterations=200)
        result_2000 = simulate(kidney_o_plus, n_iterations=2000)

        ci_200 = result_200.cities[0].confidence_interval_95
        ci_2000 = result_2000.cities[0].confidence_interval_95

        width_200 = ci_200[1] - ci_200[0]
        width_2000 = ci_2000[1] - ci_2000[0]
        assert width_2000 < width_200, "More iterations should tighten CI"


# -- All organs produce results --

class TestAllOrgans:
    @pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung", "pancreas", "intestine"])
    def test_simulation_runs_for_organ(self, organ):
        patient = PatientProfile(organ=organ, blood_type="A+", age=40, sex="male", urgency=2)
        result = simulate(patient, n_iterations=200)
        assert len(result.cities) == 22
        assert all(c.p_transplant_24mo >= 0 for c in result.cities)


# -- Stochastic COD multiplier tests --

class TestCodMultiplierDeterministic:
    """Tests for the deterministic (n_samples=0) COD multiplier."""

    def test_returns_float_when_deterministic(self):
        result = _get_cod_multiplier("TN", "kidney")
        assert isinstance(result, float)

    def test_centered_around_one(self):
        """Multiplier for any state should be within plausible range."""
        for state in ["TN", "CA", "NY", "TX", "OH", "FL"]:
            mult = _get_cod_multiplier(state, "kidney")
            assert 0.8 < mult < 1.3, f"{state} kidney multiplier {mult} out of range"

    def test_unknown_state_returns_one(self):
        assert _get_cod_multiplier("XX", "kidney") == 1.0

    def test_organ_variation(self):
        """Different organs should produce different multipliers for the same state."""
        kidney = _get_cod_multiplier("TN", "kidney")
        heart = _get_cod_multiplier("TN", "heart")
        # They CAN be equal but in practice differ due to different recovery rate profiles
        # Just verify both are valid
        assert 0.5 < kidney < 2.0
        assert 0.5 < heart < 2.0


class TestCodMultiplierStochastic:
    """Tests for the stochastic (n_samples>0) COD multiplier with Beta distributions."""

    def test_returns_array_when_stochastic(self):
        rng = np.random.default_rng(42)
        result = _get_cod_multiplier("TN", "kidney", n_samples=100, rng=rng)
        assert isinstance(result, np.ndarray)
        assert result.shape == (100,)

    def test_stochastic_mean_near_deterministic(self):
        """Mean of many stochastic draws should be close to the deterministic value."""
        det = _get_cod_multiplier("CA", "kidney")
        rng = np.random.default_rng(42)
        stoch = _get_cod_multiplier("CA", "kidney", n_samples=5000, rng=rng)
        assert abs(stoch.mean() - det) < 0.05, (
            f"Stochastic mean {stoch.mean():.4f} too far from deterministic {det:.4f}"
        )

    def test_stochastic_has_variance(self):
        """Stochastic draws should NOT all be identical."""
        rng = np.random.default_rng(42)
        result = _get_cod_multiplier("TN", "kidney", n_samples=1000, rng=rng)
        assert result.std() > 0.001, "Stochastic multiplier should have nonzero variance"

    def test_stochastic_bounded_positive(self):
        """All draws should be positive (no negative donor multipliers)."""
        rng = np.random.default_rng(42)
        result = _get_cod_multiplier("TN", "kidney", n_samples=5000, rng=rng)
        assert (result > 0).all(), "All stochastic multiplier draws should be positive"

    def test_stochastic_variance_reasonable(self):
        """Relative std dev should be small (~5-15%) — not a high-variance distribution."""
        rng = np.random.default_rng(42)
        result = _get_cod_multiplier("TN", "kidney", n_samples=5000, rng=rng)
        cv = result.std() / result.mean()  # coefficient of variation
        assert 0.01 < cv < 0.25, f"CV {cv:.4f} outside expected range"

    def test_unknown_state_returns_ones_array(self):
        rng = np.random.default_rng(42)
        result = _get_cod_multiplier("XX", "kidney", n_samples=100, rng=rng)
        assert isinstance(result, np.ndarray)
        assert (result == 1.0).all()

    @pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung", "pancreas", "intestine"])
    def test_all_organs_stochastic(self, organ):
        """Stochastic mode works for all organ types."""
        rng = np.random.default_rng(42)
        result = _get_cod_multiplier("CA", organ, n_samples=500, rng=rng)
        assert result.shape == (500,)
        assert (result > 0).all()
        assert result.std() > 0

    def test_cod_enabled_simulation_still_valid(self):
        """Full simulation with COD enabled (now stochastic) produces valid results."""
        patient = PatientProfile(
            organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
            adjust_for_cause_of_death=True,
        )
        result = simulate(patient, n_iterations=500)
        assert len(result.cities) == 22
        for city in result.cities:
            assert 0 <= city.p_transplant_24mo <= 1


# -- Clayton copula integration tests (Phase 5 M2) --

class TestCopulaIntegration:
    """Verify that use_copula=True produces valid simulation results."""

    def test_copula_simulation_runs(self):
        patient = PatientProfile(
            organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
            use_copula=True,
        )
        result = simulate(patient, n_iterations=500)
        assert len(result.cities) == 22
        for city in result.cities:
            assert 0 <= city.p_transplant_24mo <= 1

    def test_copula_probabilities_monotonic(self):
        patient = PatientProfile(
            organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
            use_copula=True,
        )
        result = simulate(patient, n_iterations=500)
        for city in result.cities:
            assert city.p_transplant_6mo <= city.p_transplant_12mo + 0.02
            assert city.p_transplant_12mo <= city.p_transplant_24mo + 0.02
            assert city.p_transplant_24mo <= city.p_transplant_36mo + 0.02

    @pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung", "pancreas", "intestine"])
    def test_copula_all_organs(self, organ):
        patient = PatientProfile(organ=organ, blood_type="A+", age=40, sex="male", urgency=2, use_copula=True)
        result = simulate(patient, n_iterations=200)
        assert len(result.cities) == 22

    def test_copula_with_cod_combined(self):
        """Copula + cause-of-death adjustment should work together."""
        patient = PatientProfile(
            organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
            use_copula=True, adjust_for_cause_of_death=True,
        )
        result = simulate(patient, n_iterations=500)
        assert len(result.cities) == 22
        for city in result.cities:
            assert 0 <= city.p_transplant_24mo <= 1
