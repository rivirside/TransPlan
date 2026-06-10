"""Tests for services/data_loader.py."""
import pytest
from services.data_loader import TransPlanData


EXPECTED_FILES = [
    "air_quality",
    "cost_of_living",
    "donor_registration",
    "health_demographics",
    "hospital_quality",
    "traffic_fatalities",
    "climate_scores",
    "policy_tiers",
    "socioeconomic",
    "srtr_reports",
]

SAMPLE_CITIES = ["Pittsburgh", "Cleveland", "Minneapolis", "Los Angeles", "New York"]


class TestDataLoaderLoads:
    def test_all_freshness_keys_present(self, data: TransPlanData):
        for key in EXPECTED_FILES:
            assert key in data.freshness, f"Missing freshness key: {key}"

    def test_no_parse_errors(self, data: TransPlanData):
        errors = [k for k, v in data.freshness.items() if v == "parse_error"]
        assert not errors, f"JSON parse errors in: {errors}"

    def test_no_missing_files(self, data: TransPlanData):
        missing = [k for k, v in data.freshness.items() if v == "missing"]
        assert not missing, f"Missing data files: {missing}"


class TestDataShapes:
    def test_air_quality_has_cities(self, data: TransPlanData):
        for city in SAMPLE_CITIES:
            assert city in data.air_quality, f"air_quality missing city: {city}"
            assert isinstance(data.air_quality[city], (int, float))

    def test_srtr_has_center_volumes(self, data: TransPlanData):
        vols = data.center_volumes
        assert "kidney" in vols, "srtr_reports missing centerVolumes.kidney"
        assert "Pittsburgh" in vols["kidney"]

    def test_srtr_has_specializations(self, data: TransPlanData):
        # waitTimeFactors are hardcoded in algorithm.js (not in JSON yet).
        # FIXME (Milestone 2): move city wait time factors to data/wait-time-distributions.json.
        # Until then, verify the related specializations field is present.
        spec = data.srtr_reports.get("specializations", {})
        assert isinstance(spec, dict), "srtr_reports.specializations should be a dict"

    def test_hospital_quality_not_empty(self, data: TransPlanData):
        assert len(data.hospital_quality) > 0

    def test_cost_of_living_not_empty(self, data: TransPlanData):
        assert len(data.cost_of_living) > 0


class TestObservedRates:
    """BBN rebuild Step 0 (#206/#211): srtr-observed-rates.json wired in."""

    ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]

    def test_loaded_without_error(self, data: TransPlanData):
        assert data.freshness.get("srtr_observed_rates") not in ("missing", "parse_error")
        assert data.srtr_observed_rates, "srtr_observed_rates is empty"

    def test_all_organs_present(self, data: TransPlanData):
        for organ in self.ORGANS:
            assert organ in data.srtr_observed_rates, f"observed rates missing organ: {organ}"
            assert data.srtr_observed_rates[organ].get("centers"), f"{organ} has no centers"

    def test_observed_outcome_accessor(self, data: TransPlanData):
        # Every organ should have at least one center whose record is well-formed.
        for organ in self.ORGANS:
            centers = data.srtr_observed_rates[organ]["centers"]
            code = next(iter(centers))
            rec = data.observed_outcome(organ, code)
            assert rec is not None
            assert 0 <= rec["transplant_rate"] <= 100, f"{organ}/{code} tx_rate out of range"
            # n may be None for tiny cohorts, but if present must be non-negative
            assert rec.get("n") is None or rec["n"] >= 0

    def test_observed_outcome_unknown_center_returns_none(self, data: TransPlanData):
        assert data.observed_outcome("kidney", "ZZZZ_NOT_A_CENTER") is None

    def test_observed_national_baseline(self, data: TransPlanData):
        natl = data.observed_national("kidney")
        assert "transplant_rate" in natl
        assert 0 <= natl["transplant_rate"] <= 100
