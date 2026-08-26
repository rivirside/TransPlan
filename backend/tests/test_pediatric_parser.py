"""Tests for the pediatric SRTR parser + its adult-fitted calibration (#335)."""
import json
from pathlib import Path

import pytest

DATA = Path(__file__).parent.parent.parent / "data" / "pediatric-centers.json"
ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]


@pytest.fixture(scope="module")
def peds():
    if not DATA.exists():
        pytest.skip("pediatric data not generated")
    return json.loads(DATA.read_text())


class TestCoverage:
    def test_expected_program_counts(self, peds):
        """Coverage must match the published pediatric program counts."""
        assert len(peds["kidney"]["centers"]) >= 100
        assert len(peds["liver"]["centers"]) >= 55
        assert len(peds["heart"]["centers"]) >= 55
        # lung is genuinely tiny after the 1.0 person-year exposure floor:
        # 11 of 21 listed lung programs have <1 py of pediatric exposure
        assert len(peds["lung"]["centers"]) >= 8

    def test_center_codes_are_bare(self, peds):
        """The Peds sheet keys on CTR_CD+CTR_TY ('ALCHTX1'); the parser must
        strip the type suffix or nothing will join to other tables."""
        for organ in ORGANS:
            for code in peds.get(organ, {}).get("centers", {}):
                assert len(code) <= 5, f"{organ}/{code} looks unstripped"
                assert not code.endswith(("TX1", "TX2", "TX3", "TX4"))

    def test_registry_gaps_are_declared_not_silent(self, peds, data):
        """Pediatric programs missing from the center registry are a REGISTRY
        gap, not a parse error — but they must be declared in _meta so they
        can never be lost silently. Known gap: TXDL (a pediatric heart
        program with 20 transplants over 12 person-years, tracked as an
        issue). The test fails if the gap GROWS or stops being declared."""
        known = set(data.all_centers.get("centers", {}))
        declared = peds["_meta"].get("unjoinable_centers", {})
        for organ in ORGANS:
            unknown = set(peds.get(organ, {}).get("centers", {})) - known
            assert set(declared.get(organ, [])) == unknown, (
                f"{organ}: undeclared registry gap {sorted(unknown)}"
            )
        total_gap = sum(len(v) for v in declared.values())
        assert total_gap <= 1, f"registry gap grew to {total_gap}: {declared}"


class TestValues:
    def test_rates_are_per_person_year_not_percent(self, peds):
        """Guards the unit trap: these are transplants per person-year, so
        they sit near 0-3, NOT 0-100. A value >10 means someone confused them
        with B7's percentages."""
        for organ in ORGANS:
            for code, rec in peds.get(organ, {}).get("centers", {}).items():
                r = rec.get("transplant_rate")
                assert r is None or 0 <= r < 10, f"{organ}/{code} rate={r}"

    def test_rate_equals_transplants_over_person_years(self, peds):
        """Internal consistency of the published columns."""
        checked = 0
        for organ in ORGANS:
            for code, rec in peds.get(organ, {}).get("centers", {}).items():
                tx, py = rec.get("transplants"), rec.get("person_years")
                if tx and py and py > 1:
                    assert rec["transplant_rate"] == pytest.approx(tx / py, rel=0.02)
                    checked += 1
        assert checked > 50

    def test_survival_percentages_in_range(self, peds):
        for organ in ORGANS:
            for code, rec in peds.get(organ, {}).get("centers", {}).items():
                for key in ("graft_survival_1yr", "patient_survival_1yr"):
                    v = rec.get(key)
                    assert v is None or 0 <= v <= 100, f"{organ}/{code} {key}={v}"

    def test_hazard_ratio_bounds_bracket_estimate(self, peds):
        checked = 0
        for organ in ORGANS:
            for rec in peds.get(organ, {}).get("centers", {}).values():
                hr, lb, ub = (rec.get("mortality_hr"), rec.get("mortality_hr_lb"),
                              rec.get("mortality_hr_ub"))
                if hr is not None and lb is not None and ub is not None:
                    assert lb <= hr <= ub
                    checked += 1
        assert checked > 20


class TestCalibration:
    def test_calibration_present_and_sane(self, peds):
        """The adult-fitted rate->probability conversion, with its residual."""
        for organ in ("kidney", "liver", "heart", "lung"):
            cal = peds[organ].get("calibration")
            assert cal, f"{organ} missing calibration"
            assert 0.2 < cal["k"] < 5.0
            assert cal["n_adult_centers"] >= 20
            # error is in probability units; anything above ~0.15 would mean
            # the conversion is not usable
            assert cal["median_abs_error"] < 0.15, f"{organ}: {cal}"

    def test_calibration_beats_naive_conversion(self, peds):
        """The whole point of fitting k: the naive 1-exp(-rate) is biased low.
        Kidney's fitted k must be materially different from 1."""
        assert peds["kidney"]["calibration"]["k"] > 1.3

    def test_converted_probabilities_are_valid(self, peds):
        import math
        for organ in ("kidney", "liver", "heart", "lung"):
            k = peds[organ]["calibration"]["k"]
            for rec in peds[organ]["centers"].values():
                p = 1 - math.exp(-k * rec["transplant_rate"])
                assert 0.0 <= p <= 1.0
