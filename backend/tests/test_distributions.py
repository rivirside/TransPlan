"""Tests for services/distributions.py — wait time distribution models."""
import numpy as np
import pytest
import scipy.stats

from services.distributions import (
    get_wait_time_distribution,
    get_organ_params,
    _get_range_multiplier,
)


class TestRangeMultiplier:
    def test_exact_boundaries(self):
        ranges = {"0-20": 1.0, "21-80": 1.5, "81-97": 2.5, "98-100": 5.0}
        assert _get_range_multiplier(0, ranges) == 1.0
        assert _get_range_multiplier(20, ranges) == 1.0
        assert _get_range_multiplier(21, ranges) == 1.5
        assert _get_range_multiplier(80, ranges) == 1.5
        assert _get_range_multiplier(98, ranges) == 5.0
        assert _get_range_multiplier(100, ranges) == 5.0

    def test_missing_range_returns_default(self):
        ranges = {"0-20": 1.0}
        assert _get_range_multiplier(50, ranges) == 1.0


class TestDataLoading:
    def test_all_six_organs_have_params(self):
        for organ in ("kidney", "liver", "heart", "lung", "pancreas", "intestine"):
            params = get_organ_params(organ)
            assert params is not None, f"Missing params for {organ}"
            assert "national_median_months" in params
            assert "log_sigma" in params
            assert "blood_type_multipliers" in params

    def test_center_factors_loaded(self, data):
        """#293: location factors are per-center only now."""
        from services.data_loader import get_data
        factors = get_data().center_wait_times.get("center_wait_time_factors", {})
        assert len(factors) >= 200

    def test_center_factors_plausible_range(self, data):
        from services.data_loader import get_data
        factors = get_data().center_wait_times.get("center_wait_time_factors", {})
        for code, per_organ in factors.items():
            for organ, f in per_organ.items():
                assert 0.3 <= f <= 3.0, f"Implausible factor {code}/{organ}: {f}"

    def test_all_blood_types_present_per_organ(self):
        expected_types = {"O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"}
        for organ in ("kidney", "liver", "heart", "lung", "pancreas", "intestine"):
            params = get_organ_params(organ)
            bt = set(params["blood_type_multipliers"].keys())
            assert bt == expected_types, f"{organ} missing blood types: {expected_types - bt}"


class TestDistributionShape:
    def test_returns_frozen_distribution(self):
        dist = get_wait_time_distribution("kidney", "O+", "Pittsburgh")
        assert isinstance(dist, scipy.stats.rv_continuous) or hasattr(dist, "rvs")

    def test_median_matches_adjusted_value(self, data):
        """Verify that the distribution median equals the adjusted national median."""
        from services.data_loader import get_data
        params = get_organ_params("kidney")
        bt_mult = params["blood_type_multipliers"]["A+"]
        center_mult = get_data().center_wait_times["center_wait_time_factors"]["OHCC"]["kidney"]
        expected_median = params["national_median_months"] * bt_mult * center_mult

        dist = get_wait_time_distribution("kidney", "A+", center_code="OHCC")
        assert abs(dist.median() - expected_median) < 0.01

    def test_samples_are_positive(self):
        dist = get_wait_time_distribution("kidney", "O+", "Pittsburgh")
        samples = dist.rvs(size=1000, random_state=42)
        assert np.all(samples > 0), "Wait times must be positive"

    def test_samples_are_right_skewed(self):
        dist = get_wait_time_distribution("kidney", "O+", "Pittsburgh")
        samples = dist.rvs(size=10000, random_state=42)
        assert np.mean(samples) > np.median(samples), "Log-normal should be right-skewed"


class TestOrganSanityChecks:
    """Verify that median wait times are clinically plausible."""

    def test_kidney_o_plus_cleveland_median(self):
        """Kidney O+ in Cleveland should have median ~3-5 years."""
        dist = get_wait_time_distribution("kidney", "O+", "Cleveland")
        median_months = dist.median()
        assert 30 < median_months < 70, f"Kidney O+ Cleveland median {median_months:.1f}mo out of range"

    def test_kidney_ab_plus_shorter_than_o_plus(self):
        """AB+ should wait significantly less than O+ (same city)."""
        dist_o = get_wait_time_distribution("kidney", "O+", "Pittsburgh")
        dist_ab = get_wait_time_distribution("kidney", "AB+", "Pittsburgh")
        assert dist_ab.median() < dist_o.median() * 0.7, "AB+ should be much shorter than O+"

    def test_liver_median_reasonable(self):
        """Liver median wait ~ 2-18 months (SRTR empirical data)."""
        dist = get_wait_time_distribution("liver", "A+", "Nashville")
        assert 1 < dist.median() < 25, f"Liver median {dist.median():.1f}mo out of range"

    def test_heart_median_shorter_than_kidney(self):
        dist_heart = get_wait_time_distribution("heart", "O+", "Cleveland")
        dist_kidney = get_wait_time_distribution("kidney", "O+", "Cleveland")
        assert dist_heart.median() < dist_kidney.median()

    def test_lung_median_very_short(self):
        """Lung waits are typically < 6 months (LAS-based allocation)."""
        dist = get_wait_time_distribution("lung", "A+", "Durham")
        assert dist.median() < 10, f"Lung median {dist.median():.1f}mo should be short"


class TestClinicalMultipliers:
    def test_high_cpra_longer_kidney_wait(self):
        dist_low = get_wait_time_distribution("kidney", "O+", "Pittsburgh", cpra=10)
        dist_high = get_wait_time_distribution("kidney", "O+", "Pittsburgh", cpra=99)
        assert dist_high.median() > dist_low.median() * 2, "cPRA 99 should be >2x longer than cPRA 10"

    def test_high_meld_shorter_liver_wait(self):
        dist_low = get_wait_time_distribution("liver", "A+", "Nashville", meld=10)
        dist_high = get_wait_time_distribution("liver", "A+", "Nashville", meld=35)
        assert dist_high.median() < dist_low.median() * 0.5, "High MELD should be much shorter wait"

    def test_high_las_shorter_lung_wait(self):
        dist_low = get_wait_time_distribution("lung", "B+", "Durham", las=35)
        dist_high = get_wait_time_distribution("lung", "B+", "Durham", las=75)
        assert dist_high.median() < dist_low.median() * 0.5, "High LAS should be much shorter wait"

    def test_no_clinical_score_uses_base(self, data):
        """If cPRA/MELD/LAS not provided, clinical multiplier should be 1.0."""
        from services.data_loader import get_data
        params = get_organ_params("kidney")
        bt_mult = params["blood_type_multipliers"]["O+"]
        center_mult = get_data().center_wait_times["center_wait_time_factors"]["PAPT"]["kidney"]
        expected = params["national_median_months"] * bt_mult * center_mult

        dist = get_wait_time_distribution("kidney", "O+", center_code="PAPT")
        assert abs(dist.median() - expected) < 0.01


class TestCityEffects:
    def test_high_factor_center_longer_wait(self, data):
        """#293: location effects are per-center. A high-factor center should
        wait longer than a low-factor one."""
        from services.data_loader import get_data
        factors = {c: p.get("kidney") for c, p in
                   get_data().center_wait_times["center_wait_time_factors"].items()
                   if isinstance(p.get("kidney"), (int, float))}
        hi = max(factors, key=factors.get)
        lo = min(factors, key=factors.get)
        dist_hi = get_wait_time_distribution("kidney", "O+", center_code=hi)
        dist_lo = get_wait_time_distribution("kidney", "O+", center_code=lo)
        assert dist_hi.median() > dist_lo.median()

    def test_unknown_city_uses_national_average(self):
        """Unknown city gets factor 1.0 (national average)."""
        dist_unknown = get_wait_time_distribution("kidney", "O+", "Atlantis")
        params = get_organ_params("kidney")
        bt_mult = params["blood_type_multipliers"]["O+"]
        expected = params["national_median_months"] * bt_mult * 1.0
        assert abs(dist_unknown.median() - expected) < 0.01


class TestFallback:
    def test_unknown_organ_returns_fallback(self):
        """Unknown organ should return a generic fallback distribution."""
        dist = get_wait_time_distribution("spleen", "O+", "Pittsburgh")
        assert hasattr(dist, "rvs"), "Fallback should still be a valid distribution"
        assert dist.median() == pytest.approx(24.0, rel=0.01)
