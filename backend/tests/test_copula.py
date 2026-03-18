"""Tests for services/copula.py — Clayton copula for correlated competing risks."""
import numpy as np
import pytest
from scipy import stats

from services.copula import (
    draw_correlated_competing_risks,
    kendall_tau,
    sample_clayton_bivariate,
    theta_from_tau,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
RNG = np.random.default_rng(42)
N = 50_000  # large sample for statistical tests


class TestSampleClaytonBivariate:
    """Tests for the raw copula sampler."""

    def test_output_shape(self):
        u1, u2 = sample_clayton_bivariate(100, theta=1.0, rng=RNG)
        assert u1.shape == (100,)
        assert u2.shape == (100,)

    def test_marginals_uniform(self):
        """Both marginals should be approximately Uniform(0, 1)."""
        u1, u2 = sample_clayton_bivariate(N, theta=1.0, rng=np.random.default_rng(0))
        # Kolmogorov-Smirnov test against U(0,1)
        _, p1 = stats.kstest(u1, "uniform")
        _, p2 = stats.kstest(u2, "uniform")
        assert p1 > 0.001, f"u1 not uniform: KS p={p1}"
        assert p2 > 0.001, f"u2 not uniform: KS p={p2}"

    def test_positive_dependence(self):
        """Clayton copula should produce positive Kendall's tau."""
        u1, u2 = sample_clayton_bivariate(N, theta=2.0, rng=np.random.default_rng(1))
        tau_empirical, _ = stats.kendalltau(u1, u2)
        # Theoretical tau for theta=2 is 2/(2+2) = 0.5
        assert tau_empirical > 0.4, f"Expected strong positive tau, got {tau_empirical}"
        assert tau_empirical < 0.6

    def test_weak_dependence_small_theta(self):
        """Near-zero theta should give near-zero dependence."""
        u1, u2 = sample_clayton_bivariate(N, theta=0.01, rng=np.random.default_rng(2))
        tau_empirical, _ = stats.kendalltau(u1, u2)
        assert abs(tau_empirical) < 0.05, f"Expected near-zero tau, got {tau_empirical}"

    def test_strong_dependence_large_theta(self):
        """Large theta should give tau approaching 1."""
        u1, u2 = sample_clayton_bivariate(N, theta=20.0, rng=np.random.default_rng(3))
        tau_empirical, _ = stats.kendalltau(u1, u2)
        assert tau_empirical > 0.85, f"Expected tau > 0.85, got {tau_empirical}"

    def test_values_in_unit_interval(self):
        """All values must be in (0, 1)."""
        u1, u2 = sample_clayton_bivariate(N, theta=1.0, rng=np.random.default_rng(4))
        assert np.all(u1 > 0) and np.all(u1 < 1)
        assert np.all(u2 > 0) and np.all(u2 < 1)

    def test_no_nans_or_infs(self):
        """No NaN or Inf in output."""
        u1, u2 = sample_clayton_bivariate(N, theta=1.0, rng=np.random.default_rng(5))
        assert not np.any(np.isnan(u1)) and not np.any(np.isinf(u1))
        assert not np.any(np.isnan(u2)) and not np.any(np.isinf(u2))

    def test_theta_zero_raises(self):
        with pytest.raises(ValueError, match="must be > 0"):
            sample_clayton_bivariate(100, theta=0, rng=RNG)

    def test_negative_theta_raises(self):
        with pytest.raises(ValueError, match="must be > 0"):
            sample_clayton_bivariate(100, theta=-1.0, rng=RNG)

    def test_n_zero_raises(self):
        with pytest.raises(ValueError, match="n must be > 0"):
            sample_clayton_bivariate(0, theta=1.0, rng=RNG)

    def test_reproducible_with_same_seed(self):
        """Same seed → same output."""
        u1a, u2a = sample_clayton_bivariate(100, theta=1.0, rng=np.random.default_rng(99))
        u1b, u2b = sample_clayton_bivariate(100, theta=1.0, rng=np.random.default_rng(99))
        np.testing.assert_array_equal(u1a, u1b)
        np.testing.assert_array_equal(u2a, u2b)

    def test_empirical_tau_matches_theoretical(self):
        """Empirical Kendall's tau should match θ/(θ+2) within tolerance."""
        for theta in (0.5, 1.0, 2.0, 5.0):
            u1, u2 = sample_clayton_bivariate(N, theta=theta, rng=np.random.default_rng(int(theta * 10)))
            tau_emp, _ = stats.kendalltau(u1, u2)
            tau_theo = theta / (theta + 2.0)
            assert abs(tau_emp - tau_theo) < 0.03, (
                f"theta={theta}: empirical tau={tau_emp:.4f} vs theoretical={tau_theo:.4f}"
            )


class TestDrawCorrelatedCompetingRisks:
    """Tests for the exponential-mapped convenience function."""

    def test_output_shape(self):
        mort, delist = draw_correlated_competing_risks(
            mort_scale=120.0, delist_scale=180.0, n=500, theta=1.0, rng=RNG,
        )
        assert mort.shape == (500,)
        assert delist.shape == (500,)

    def test_positive_times(self):
        """All event times must be > 0."""
        mort, delist = draw_correlated_competing_risks(
            mort_scale=120.0, delist_scale=180.0, n=N, theta=1.0,
            rng=np.random.default_rng(10),
        )
        assert np.all(mort > 0)
        assert np.all(delist > 0)

    def test_mean_close_to_scale(self):
        """Mean of exponential should be close to the scale parameter."""
        mort, delist = draw_correlated_competing_risks(
            mort_scale=120.0, delist_scale=180.0, n=N, theta=1.0,
            rng=np.random.default_rng(11),
        )
        # Copula preserves marginals, so means should match scales
        assert abs(np.mean(mort) - 120.0) < 5.0, f"Mortality mean: {np.mean(mort):.1f}"
        assert abs(np.mean(delist) - 180.0) < 5.0, f"Delisting mean: {np.mean(delist):.1f}"

    def test_correlated_times(self):
        """With theta > 0, short mortality should correlate with short delisting."""
        mort, delist = draw_correlated_competing_risks(
            mort_scale=120.0, delist_scale=180.0, n=N, theta=2.0,
            rng=np.random.default_rng(12),
        )
        # Spearman rank correlation should be positive
        rho, _ = stats.spearmanr(mort, delist)
        assert rho > 0.3, f"Expected positive Spearman rho, got {rho}"

    def test_no_nans(self):
        mort, delist = draw_correlated_competing_risks(
            mort_scale=120.0, delist_scale=180.0, n=N, theta=1.0,
            rng=np.random.default_rng(13),
        )
        assert not np.any(np.isnan(mort))
        assert not np.any(np.isnan(delist))

    def test_extreme_scales(self):
        """Very large scale (near-zero rate) should not produce NaN/Inf."""
        mort, delist = draw_correlated_competing_risks(
            mort_scale=1e6, delist_scale=1e6, n=1000, theta=1.0,
            rng=np.random.default_rng(14),
        )
        assert np.all(np.isfinite(mort))
        assert np.all(np.isfinite(delist))


class TestKendallTau:
    def test_known_values(self):
        assert kendall_tau(1.0) == pytest.approx(1.0 / 3.0)
        assert kendall_tau(2.0) == pytest.approx(0.5)
        assert kendall_tau(0.5) == pytest.approx(0.2)

    def test_invalid_theta(self):
        with pytest.raises(ValueError):
            kendall_tau(0)
        with pytest.raises(ValueError):
            kendall_tau(-1.0)


class TestThetaFromTau:
    def test_round_trip(self):
        for theta in (0.5, 1.0, 2.0, 5.0, 10.0):
            tau = kendall_tau(theta)
            theta_back = theta_from_tau(tau)
            assert theta_back == pytest.approx(theta, rel=1e-10)

    def test_invalid_tau(self):
        with pytest.raises(ValueError):
            theta_from_tau(0.0)
        with pytest.raises(ValueError):
            theta_from_tau(1.0)
        with pytest.raises(ValueError):
            theta_from_tau(-0.5)
