"""
Golden-file validation for SRTR-derived JSON data files (Issue #78).

These tests validate the structural integrity and clinical plausibility
of the committed data files without requiring the SRTR Excel source files.
Runs as part of the normal backend-tests CI job.

Checks:
  - All 6 organs present in each file
  - All 22 cities present in city-level data
  - Values fall within clinically plausible ranges
  - Known ordering invariants (e.g., kidney wait > heart wait)
"""
import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

EXPECTED_ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
EXPECTED_CITIES = [
    "Pittsburgh", "Baltimore", "Philadelphia", "New York",
    "Minneapolis", "Madison", "Chicago", "Cleveland",
    "St. Louis", "Indianapolis", "Omaha", "Rochester",
    "Nashville", "Durham", "Miami", "Dallas",
    "Houston", "Portland", "Seattle", "San Francisco",
    "Los Angeles", "Palo Alto",
]


def _load(filename: str) -> dict:
    path = DATA_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if k != "_meta"}


# ──────────────────────────────────────────────────────────────────────
# wait-time-distributions.json
# ──────────────────────────────────────────────────────────────────────

class TestWaitTimeDistributions:
    @pytest.fixture(autouse=True, scope="class")
    def data(self, request):
        request.cls.wt = _load("wait-time-distributions.json")

    def test_all_organs_present(self):
        for organ in EXPECTED_ORGANS:
            assert organ in self.wt, f"Missing organ: {organ}"

    def test_median_months_in_range(self):
        for organ in EXPECTED_ORGANS:
            median = self.wt[organ]["national_median_months"]
            assert 1.0 <= median <= 60.0, f"{organ} median {median} out of range"

    def test_kidney_longest_wait(self):
        """Kidney should have the longest national median wait time."""
        kidney_median = self.wt["kidney"]["national_median_months"]
        for organ in ["liver", "heart", "lung"]:
            other_median = self.wt[organ]["national_median_months"]
            assert kidney_median > other_median, (
                f"Kidney median ({kidney_median}) should exceed {organ} ({other_median})"
            )

    def test_blood_type_multipliers_present(self):
        expected_bts = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
        for organ in EXPECTED_ORGANS:
            mults = self.wt[organ].get("blood_type_multipliers", {})
            for bt in expected_bts:
                assert bt in mults, f"{organ} missing blood type multiplier for {bt}"
                assert 0.1 <= mults[bt] <= 10.0, f"{organ} {bt} multiplier {mults[bt]} out of range"

    def test_ab_shortest_wait(self):
        """AB blood types should have the lowest multipliers (shortest wait)."""
        for organ in EXPECTED_ORGANS:
            mults = self.wt[organ]["blood_type_multipliers"]
            ab_plus = mults.get("AB+", 1.0)
            o_plus = mults.get("O+", 1.0)
            assert ab_plus < o_plus, (
                f"{organ}: AB+ ({ab_plus}) should have lower multiplier than O+ ({o_plus})"
            )

    def test_log_sigma_positive(self):
        for organ in EXPECTED_ORGANS:
            sigma = self.wt[organ].get("log_sigma", 0)
            assert 0.1 <= sigma <= 3.0, f"{organ} log_sigma {sigma} out of range"

    def test_city_wait_time_factors_present(self):
        factors = self.wt.get("city_wait_time_factors", {})
        for city in EXPECTED_CITIES:
            assert city in factors, f"Missing city factor for {city}"
            val = factors[city]
            assert 0.3 <= val <= 3.0, f"{city} factor {val} out of range"


# ──────────────────────────────────────────────────────────────────────
# competing-risks.json
# ──────────────────────────────────────────────────────────────────────

class TestCompetingRisks:
    @pytest.fixture(autouse=True, scope="class")
    def data(self, request):
        request.cls.cr = _load("competing-risks.json")

    def test_all_organs_present(self):
        for organ in EXPECTED_ORGANS:
            assert organ in self.cr, f"Missing organ: {organ}"

    def test_mortality_rates_in_range(self):
        for organ in EXPECTED_ORGANS:
            rate = self.cr[organ]["annual_mortality_rate"]
            assert 0.001 <= rate <= 0.30, f"{organ} mortality rate {rate} out of range"

    def test_delisting_rates_in_range(self):
        for organ in EXPECTED_ORGANS:
            rate = self.cr[organ]["annual_delisting_rate"]
            assert 0.001 <= rate <= 0.50, f"{organ} delisting rate {rate} out of range"

    def test_heart_mortality_exceeds_kidney(self):
        """Heart waitlist mortality should exceed kidney."""
        heart = self.cr["heart"]["annual_mortality_rate"]
        kidney = self.cr["kidney"]["annual_mortality_rate"]
        assert heart > kidney, f"Heart mortality ({heart}) should exceed kidney ({kidney})"

    def test_urgency_multipliers_present(self):
        for organ in EXPECTED_ORGANS:
            mults = self.cr[organ].get("urgency_mortality_multipliers", {})
            for u in ["1", "2", "3", "4"]:
                assert u in mults, f"{organ} missing urgency multiplier for level {u}"

    def test_urgency_monotonic(self):
        """Higher urgency level should have higher mortality multiplier."""
        for organ in EXPECTED_ORGANS:
            mults = self.cr[organ]["urgency_mortality_multipliers"]
            vals = [mults[str(u)] for u in [1, 2, 3, 4]]
            for i in range(len(vals) - 1):
                assert vals[i] <= vals[i + 1], (
                    f"{organ} urgency multipliers not monotonic: {vals}"
                )

    def test_city_adjustments_present(self):
        adj = self.cr.get("city_adjustments", {})
        for city in EXPECTED_CITIES:
            assert city in adj, f"Missing city adjustment for {city}"


# ──────────────────────────────────────────────────────────────────────
# post-transplant-outcomes.json
# ──────────────────────────────────────────────────────────────────────

class TestPostTransplantOutcomes:
    @pytest.fixture(autouse=True, scope="class")
    def data(self, request):
        request.cls.outcomes = _load("post-transplant-outcomes.json")

    def test_all_organs_present(self):
        for organ in EXPECTED_ORGANS:
            assert organ in self.outcomes, f"Missing organ: {organ}"

    def test_national_survival_in_range(self):
        for organ in EXPECTED_ORGANS:
            gs1 = self.outcomes[organ].get("national_graft_survival_1yr")
            # Pancreas may have null graft survival (reported as kidney-pancreas)
            if gs1 is not None:
                assert 50.0 <= gs1 <= 100.0, f"{organ} 1yr graft survival {gs1} out of range"
            # Patient survival should always be present
            ps1 = self.outcomes[organ].get("national_patient_survival_1yr")
            assert ps1 is not None, f"{organ} missing national_patient_survival_1yr"
            assert 70.0 <= ps1 <= 100.0, f"{organ} 1yr patient survival {ps1} out of range"

    def test_1yr_exceeds_3yr_survival(self):
        """1-year survival should always exceed 3-year survival."""
        for organ in EXPECTED_ORGANS:
            gs1 = self.outcomes[organ].get("national_graft_survival_1yr")
            gs3 = self.outcomes[organ].get("national_graft_survival_3yr")
            if gs1 is not None and gs3 is not None:
                assert gs1 >= gs3, (
                    f"{organ}: 1yr survival ({gs1}) should >= 3yr ({gs3})"
                )

    def test_city_outcomes_present(self):
        city_out = self.outcomes.get("city_outcomes", {})
        for city in EXPECTED_CITIES:
            assert city in city_out, f"Missing city outcomes for {city}"

    def test_city_graft_survival_in_range(self):
        city_out = self.outcomes.get("city_outcomes", {})
        for city in EXPECTED_CITIES:
            city_data = city_out.get(city, {})
            for organ in EXPECTED_ORGANS:
                organ_data = city_data.get(organ, {})
                gs1 = organ_data.get("graft_survival_1yr")
                if gs1 is not None:
                    assert 50.0 <= gs1 <= 100.0, (
                        f"{city}/{organ} 1yr graft survival {gs1} out of range"
                    )
