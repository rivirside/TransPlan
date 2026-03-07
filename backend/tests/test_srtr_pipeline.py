"""
Tests for M5: SRTR data pipeline.

Tests the parse-srtr-reports.py output (wait-time-distributions.json and
competing-risks.json) to ensure they are valid for the backend Monte Carlo engine.
Also tests the parser's log-normal fitting logic.
"""
import json
import math
import os
import sys

import importlib.util

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _import_parser():
    """Import parse-srtr-reports.py (hyphenated filename, not a normal import)."""
    spec = importlib.util.spec_from_file_location(
        "parse_srtr_reports",
        os.path.join(SCRIPTS_DIR, "parse-srtr-reports.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
CITIES = [
    "Pittsburgh", "Baltimore", "Philadelphia", "New York", "Minneapolis",
    "Madison", "Chicago", "Cleveland", "St. Louis", "Indianapolis",
    "Omaha", "Rochester", "Nashville", "Durham", "Miami", "Dallas",
    "Houston", "Portland", "Seattle", "San Francisco", "Los Angeles", "Palo Alto",
]


# ---------- fixtures ----------


@pytest.fixture(scope="module")
def wait_data():
    with open(os.path.join(DATA_DIR, "wait-time-distributions.json")) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def competing_data():
    with open(os.path.join(DATA_DIR, "competing-risks.json")) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def center_mapping():
    with open(os.path.join(DATA_DIR, "srtr-center-mapping.json")) as f:
        return json.load(f)


# ---------- wait-time-distributions.json tests ----------


class TestWaitTimeDistributions:
    def test_has_all_organs(self, wait_data):
        for organ in ORGANS:
            assert organ in wait_data, f"Missing organ: {organ}"

    def test_organ_has_required_fields(self, wait_data):
        for organ in ORGANS:
            entry = wait_data[organ]
            assert "national_median_months" in entry
            assert "log_sigma" in entry
            assert "blood_type_multipliers" in entry

    def test_median_positive(self, wait_data):
        for organ in ORGANS:
            median = wait_data[organ]["national_median_months"]
            assert median > 0, f"{organ} median should be positive, got {median}"

    def test_sigma_in_range(self, wait_data):
        for organ in ORGANS:
            sigma = wait_data[organ]["log_sigma"]
            assert 0.3 <= sigma <= 1.2, f"{organ} sigma={sigma} out of range [0.3, 1.2]"

    def test_blood_type_multipliers_complete(self, wait_data):
        expected_types = {"O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"}
        for organ in ORGANS:
            bt = set(wait_data[organ]["blood_type_multipliers"].keys())
            assert bt == expected_types, f"{organ} missing blood types: {expected_types - bt}"

    def test_blood_type_multipliers_positive(self, wait_data):
        for organ in ORGANS:
            for bt, mult in wait_data[organ]["blood_type_multipliers"].items():
                assert mult > 0, f"{organ} {bt} multiplier should be positive"

    def test_city_wait_time_factors_has_all_cities(self, wait_data):
        factors = wait_data["city_wait_time_factors"]
        for city in CITIES:
            assert city in factors, f"Missing city factor: {city}"

    def test_city_factors_reasonable_range(self, wait_data):
        factors = wait_data["city_wait_time_factors"]
        for city in CITIES:
            f = factors[city]
            assert 0.3 <= f <= 3.0, f"{city} factor={f} out of range [0.3, 3.0]"

    def test_meta_has_source(self, wait_data):
        assert "_meta" in wait_data
        assert "source" in wait_data["_meta"]
        assert "SRTR" in wait_data["_meta"]["source"]

    def test_kidney_median_plausible(self, wait_data):
        """Kidney national median should be in the 20-50 month range per SRTR data."""
        median = wait_data["kidney"]["national_median_months"]
        assert 10 <= median <= 60, f"Kidney median={median} seems implausible"

    def test_liver_faster_than_kidney(self, wait_data):
        """Liver median wait should be shorter than kidney (generally true)."""
        assert wait_data["liver"]["national_median_months"] < wait_data["kidney"]["national_median_months"]

    def test_lung_fastest_major_organ(self, wait_data):
        """Lung typically has shortest wait among major organs."""
        lung = wait_data["lung"]["national_median_months"]
        for organ in ["kidney", "liver"]:
            assert lung < wait_data[organ]["national_median_months"], \
                f"Lung ({lung}) should be faster than {organ}"


class TestCityFactorSanity:
    """Sanity checks based on known transplant geography."""

    def test_sf_longer_than_average(self, wait_data):
        """San Francisco / California is known for long kidney waits."""
        assert wait_data["city_wait_time_factors"]["San Francisco"] > 1.0

    def test_la_longer_than_average(self, wait_data):
        assert wait_data["city_wait_time_factors"]["Los Angeles"] > 1.0

    def test_variation_exists(self, wait_data):
        """There should be meaningful variation across cities."""
        factors = [v for k, v in wait_data["city_wait_time_factors"].items() if not k.startswith("_")]
        assert max(factors) - min(factors) > 0.5, "City factors should vary by at least 0.5"


# ---------- competing-risks.json tests ----------


class TestCompetingRisks:
    def test_has_all_organs(self, competing_data):
        for organ in ORGANS:
            assert organ in competing_data, f"Missing organ: {organ}"

    def test_organ_has_required_fields(self, competing_data):
        for organ in ORGANS:
            entry = competing_data[organ]
            assert "annual_mortality_rate" in entry
            assert "annual_delisting_rate" in entry
            assert "urgency_mortality_multipliers" in entry

    def test_mortality_rate_positive(self, competing_data):
        for organ in ORGANS:
            rate = competing_data[organ]["annual_mortality_rate"]
            assert 0 < rate < 1.0, f"{organ} mortality rate={rate} out of range"

    def test_delisting_rate_positive(self, competing_data):
        for organ in ORGANS:
            rate = competing_data[organ]["annual_delisting_rate"]
            assert 0 < rate < 1.0, f"{organ} delisting rate={rate} out of range"

    def test_urgency_multipliers_have_4_levels(self, competing_data):
        for organ in ORGANS:
            mult = competing_data[organ]["urgency_mortality_multipliers"]
            assert len(mult) == 4, f"{organ} should have 4 urgency levels"
            for level in ["1", "2", "3", "4"]:
                assert level in mult

    def test_urgency_multipliers_increasing(self, competing_data):
        """Higher urgency should have higher mortality multiplier."""
        for organ in ORGANS:
            mult = competing_data[organ]["urgency_mortality_multipliers"]
            for i in range(1, 4):
                assert mult[str(i)] <= mult[str(i + 1)], \
                    f"{organ}: urgency {i} mult should be <= urgency {i+1}"

    def test_city_adjustments_has_all_cities(self, competing_data):
        adjs = competing_data["city_adjustments"]
        for city in CITIES:
            assert city in adjs, f"Missing city adjustment: {city}"
            assert "mortality_factor" in adjs[city]
            assert "delisting_factor" in adjs[city]

    def test_city_adjustment_factors_reasonable(self, competing_data):
        adjs = competing_data["city_adjustments"]
        for city in CITIES:
            mf = adjs[city]["mortality_factor"]
            df = adjs[city]["delisting_factor"]
            assert 0.3 <= mf <= 3.0, f"{city} mortality_factor={mf} out of range"
            assert 0.3 <= df <= 3.0, f"{city} delisting_factor={df} out of range"

    def test_liver_has_meld_multipliers(self, competing_data):
        """Liver should have MELD-based mortality multipliers."""
        assert "meld_mortality_multipliers" in competing_data["liver"]

    def test_meta_has_source(self, competing_data):
        assert "_meta" in competing_data
        assert "SRTR" in competing_data["_meta"]["source"]


# ---------- center mapping tests ----------


class TestCenterMapping:
    def test_has_all_cities(self, center_mapping):
        for city in CITIES:
            assert city in center_mapping["cities"], f"Missing city: {city}"

    def test_primary_code_format(self, center_mapping):
        """SRTR center codes are 4 uppercase characters."""
        for city, info in center_mapping["cities"].items():
            code = info["primary"]
            assert len(code) == 4, f"{city} code '{code}' should be 4 chars"
            assert code == code.upper(), f"{city} code '{code}' should be uppercase"

    def test_states_match_cities(self, center_mapping):
        expected = {
            "Pittsburgh": "PA", "Cleveland": "OH", "Houston": "TX",
            "San Francisco": "CA", "Miami": "FL", "Seattle": "WA",
        }
        for city, state in expected.items():
            assert center_mapping["cities"][city]["state"] == state


# ---------- log-normal fitting tests ----------


class TestLogNormalFit:
    """Test the fit_lognormal function from the parser."""

    @pytest.fixture(autouse=True)
    def _load_parser(self):
        self.parser = _import_parser()

    def test_fit_from_all_percentiles(self):
        # P10=2, P25=5, P50=12, P75=30
        result = self.parser.fit_lognormal(2.0, 5.0, 12.0, 30.0)
        assert result is not None
        mu, sigma = result
        # mu should be ln(12) ≈ 2.485
        assert abs(mu - math.log(12)) < 0.01
        assert 0.3 <= sigma <= 1.2

    def test_fit_with_censored_p75(self):
        CENSORED = self.parser.CENSORED
        # P75 is censored — should use P10-P25 method
        result = self.parser.fit_lognormal(1.0, 5.0, 20.0, CENSORED)
        assert result is not None
        mu, sigma = result
        assert abs(mu - math.log(20)) < 0.01

    def test_fit_with_censored_p50(self):
        CENSORED = self.parser.CENSORED
        # P50 is censored — should estimate from P25
        result = self.parser.fit_lognormal(1.0, 8.0, CENSORED, CENSORED)
        assert result is not None
        mu, sigma = result
        # mu should be approximated from P25
        assert mu > math.log(8)  # mu > ln(P25)

    def test_fit_returns_none_for_all_invalid(self):
        CENSORED = self.parser.CENSORED
        result = self.parser.fit_lognormal(CENSORED, CENSORED, CENSORED, CENSORED)
        assert result is None

    def test_sigma_clamped(self):
        # Very wide spread should be clamped to 1.2
        result = self.parser.fit_lognormal(0.1, 100.0, 500.0, 2000.0)
        _, sigma = result
        assert sigma <= 1.2

    def test_valid_helper(self):
        CENSORED = self.parser.CENSORED
        assert self.parser._is_valid(5.0)
        assert not self.parser._is_valid(None)
        assert not self.parser._is_valid(CENSORED)
        assert not self.parser._is_valid(0)
        assert not self.parser._is_valid(-1)
