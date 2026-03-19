"""Tests for services/posterior_checks.py — posterior predictive checks.

These tests mock the MCMC trace since fitting is expensive and traces may
not exist in CI.  We verify the check logic, aggregation, and edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock

import numpy as np

try:
    from services.posterior_checks import (
        CheckResult,
        PosteriorCheckReport,
        _ci_90,
        run_posterior_checks,
    )
    HAS_MCMC_DEPS = True
except ImportError:
    HAS_MCMC_DEPS = False

pytestmark = pytest.mark.skipif(
    not HAS_MCMC_DEPS,
    reason="MCMC dependencies (arviz, pymc) not installed",
)


# -- _ci_90 --

class TestCi90:
    def test_symmetric_distribution(self):
        vals = np.linspace(0, 100, 10000)
        lo, hi = _ci_90(vals)
        assert lo == pytest.approx(5.0, abs=0.5)
        assert hi == pytest.approx(95.0, abs=0.5)

    def test_narrow_distribution(self):
        vals = np.full(100, 5.0)
        lo, hi = _ci_90(vals)
        assert lo == 5.0
        assert hi == 5.0


# -- Mock posterior draws factory --

def _make_mock_draws(n_draws, obs_data, noise=0.05):
    """Create mock posterior draws that are close to observed values."""
    rng = np.random.default_rng(42)
    draws = []
    for _ in range(n_draws):
        draws.append({
            "national_median": obs_data["national_median"] * (1 + rng.normal(0, noise)),
            "log_sigma": obs_data["log_sigma"] * (1 + rng.normal(0, noise)),
            "city_wait_factors": obs_data["city_wait_factors"] * (1 + rng.normal(0, noise, size=obs_data["n_cities"])),
            "bt_multipliers": obs_data["bt_mults"] * (1 + rng.normal(0, noise, size=len(obs_data["bt_mults"]))),
            "national_mort_rate": obs_data["national_mort_rate"] * (1 + rng.normal(0, noise)),
            "national_delist_rate": obs_data["national_delist_rate"] * (1 + rng.normal(0, noise)),
            "urg_multipliers": obs_data["urg_mults"] * (1 + rng.normal(0, noise, size=len(obs_data["urg_mults"]))),
            "city_mort_offsets": rng.normal(0, 0.1, size=obs_data["n_cities"]),
            "city_delist_offsets": rng.normal(0, 0.1, size=obs_data["n_cities"]),
            "mort_delist_corr": rng.uniform(-0.3, 0.3),
        })
    return draws


def _make_obs_data():
    """Create mock observed data matching load_organ_data structure."""
    return {
        "organ": "kidney",
        "cities": ["Baltimore", "Chicago", "Cleveland", "Dallas", "Durham",
                    "Houston", "Indianapolis", "Los Angeles", "Madison",
                    "Miami", "Minneapolis", "Nashville", "New York", "Omaha",
                    "Palo Alto", "Philadelphia", "Pittsburgh", "Portland",
                    "Rochester", "San Francisco", "Seattle", "St. Louis"],
        "n_cities": 22,
        "national_median": 27.4,
        "log_sigma": 1.2,
        "city_wait_factors": np.array([1.1, 0.9, 1.0, 0.95, 1.05,
                                        0.88, 1.02, 0.92, 1.08, 0.97,
                                        1.03, 1.0, 1.15, 0.93, 0.85,
                                        1.12, 1.06, 0.91, 1.01, 0.89,
                                        0.94, 0.98]),
        "city_mort_factors": np.ones(22),
        "city_delist_factors": np.ones(22),
        "national_mort_rate": 0.08,
        "national_delist_rate": 0.05,
        "bt_mults": np.array([1.3, 1.4, 0.9, 1.0, 1.15, 1.25, 0.55, 0.65]),
        "urg_mults": np.array([0.5, 1.0, 1.5, 2.5]),
        "age_mults": {"18-34": 0.4, "35-49": 0.7, "50-64": 1.0, "65+": 1.9},
    }


# -- run_posterior_checks (with mocks) --

class TestRunPosteriorChecks:
    """Test the check runner with mocked trace and data."""

    @patch("services.posterior_checks.sample_params_from_trace")
    @patch("services.posterior_checks.load_trace")
    @patch("services.posterior_checks.load_organ_data")
    @patch("services.posterior_checks.trace_exists", return_value=True)
    def test_returns_report(self, mock_exists, mock_load_data, mock_load_trace, mock_sample):
        obs = _make_obs_data()
        mock_load_data.return_value = obs
        mock_load_trace.return_value = MagicMock()
        mock_sample.return_value = _make_mock_draws(200, obs, noise=0.05)

        report = run_posterior_checks("kidney")
        assert isinstance(report, PosteriorCheckReport)
        assert report.organ == "kidney"
        assert report.n_draws == 200
        assert len(report.checks) >= 6  # at least 6 check types

    @patch("services.posterior_checks.sample_params_from_trace")
    @patch("services.posterior_checks.load_trace")
    @patch("services.posterior_checks.load_organ_data")
    @patch("services.posterior_checks.trace_exists", return_value=True)
    def test_well_calibrated_model_passes(self, mock_exists, mock_load_data, mock_load_trace, mock_sample):
        """When posterior draws are close to observed, most checks should pass."""
        obs = _make_obs_data()
        mock_load_data.return_value = obs
        mock_load_trace.return_value = MagicMock()
        mock_sample.return_value = _make_mock_draws(200, obs, noise=0.03)

        report = run_posterior_checks("kidney")
        n_passed = sum(1 for c in report.checks if c.passed)
        # With 3% noise, nearly all checks should pass
        assert n_passed >= len(report.checks) * 0.7, (
            f"Only {n_passed}/{len(report.checks)} passed with 3% noise: "
            f"{[c.name for c in report.checks if not c.passed]}"
        )
        assert report.overall_passed is True

    @patch("services.posterior_checks.sample_params_from_trace")
    @patch("services.posterior_checks.load_trace")
    @patch("services.posterior_checks.load_organ_data")
    @patch("services.posterior_checks.trace_exists", return_value=True)
    def test_poorly_calibrated_model_flags_issues(self, mock_exists, mock_load_data, mock_load_trace, mock_sample):
        """When posterior draws are far from observed, checks should fail."""
        obs = _make_obs_data()
        mock_load_data.return_value = obs
        mock_load_trace.return_value = MagicMock()
        # Use high noise and shift means way off
        bad_draws = _make_mock_draws(200, obs, noise=0.5)
        # Shift national median way off
        for d in bad_draws:
            d["national_median"] *= 3.0
        mock_sample.return_value = bad_draws

        report = run_posterior_checks("kidney")
        # National median check should fail
        median_check = next(c for c in report.checks if c.name == "national_median_wait")
        assert median_check.passed is False
        assert median_check.discrepancy > 0.2

    @patch("services.posterior_checks.trace_exists", return_value=False)
    def test_no_trace_raises_error(self, mock_exists):
        with pytest.raises(RuntimeError, match="No MCMC trace"):
            run_posterior_checks("kidney")

    @patch("services.posterior_checks.sample_params_from_trace")
    @patch("services.posterior_checks.load_trace")
    @patch("services.posterior_checks.load_organ_data")
    @patch("services.posterior_checks.trace_exists", return_value=True)
    def test_calibration_fraction_computed(self, mock_exists, mock_load_data, mock_load_trace, mock_sample):
        obs = _make_obs_data()
        mock_load_data.return_value = obs
        mock_load_trace.return_value = MagicMock()
        mock_sample.return_value = _make_mock_draws(200, obs, noise=0.03)

        report = run_posterior_checks("kidney")
        assert 0.0 <= report.calibration_fraction <= 1.0

    @patch("services.posterior_checks.sample_params_from_trace")
    @patch("services.posterior_checks.load_trace")
    @patch("services.posterior_checks.load_organ_data")
    @patch("services.posterior_checks.trace_exists", return_value=True)
    def test_urgency_monotonicity_checked(self, mock_exists, mock_load_data, mock_load_trace, mock_sample):
        obs = _make_obs_data()
        mock_load_data.return_value = obs
        mock_load_trace.return_value = MagicMock()
        mock_sample.return_value = _make_mock_draws(200, obs, noise=0.01)

        report = run_posterior_checks("kidney")
        urg_check = next(c for c in report.checks if c.name == "urgency_monotonicity")
        assert urg_check.passed is True  # obs urg_mults are monotone, low noise preserves it

    @patch("services.posterior_checks.sample_params_from_trace")
    @patch("services.posterior_checks.load_trace")
    @patch("services.posterior_checks.load_organ_data")
    @patch("services.posterior_checks.trace_exists", return_value=True)
    def test_all_check_fields_populated(self, mock_exists, mock_load_data, mock_load_trace, mock_sample):
        obs = _make_obs_data()
        mock_load_data.return_value = obs
        mock_load_trace.return_value = MagicMock()
        mock_sample.return_value = _make_mock_draws(200, obs, noise=0.05)

        report = run_posterior_checks("kidney")
        for check in report.checks:
            assert isinstance(check, CheckResult)
            assert check.name
            assert check.description
            assert isinstance(check.inside_ci, bool)
            assert isinstance(check.passed, bool)
            assert isinstance(check.discrepancy, float)
            assert check.discrepancy >= 0


# -- CheckResult dataclass --

class TestCheckResult:
    def test_construction(self):
        cr = CheckResult(
            name="test_check",
            description="A test",
            observed=1.0,
            posterior_mean=1.05,
            posterior_ci_90=(0.9, 1.1),
            inside_ci=True,
            discrepancy=0.05,
            passed=True,
        )
        assert cr.name == "test_check"
        assert cr.inside_ci is True
        assert cr.discrepancy == 0.05
