"""Tests for the center-level comprehensive scoring service."""
import pytest

from services.data_loader import load_all, get_data
from services.scoring import (
    DEFAULT_WEIGHTS,
    score_all_centers,
    score_center,
    _medical_compatibility,
    _wait_time_multiplier,
)


@pytest.fixture(scope="module", autouse=True)
def _load_data():
    load_all()


# ── Unit tests for individual scoring functions ─────────────────────────

class TestMedicalCompatibility:
    def test_ab_plus_universal_recipient_highest(self):
        p = {"blood_type": "AB+", "age": 40, "sex": "male", "organ": "kidney"}
        score = _medical_compatibility(p)
        assert score >= 95

    def test_o_minus_lowest_blood_type(self):
        p = {"blood_type": "O-", "age": 40, "sex": "male", "organ": "kidney"}
        score = _medical_compatibility(p)
        assert score < 90

    def test_pediatric_age_bonus(self):
        child = {"blood_type": "A+", "age": 10, "sex": "male", "organ": "kidney"}
        adult = {"blood_type": "A+", "age": 55, "sex": "male", "organ": "kidney"}
        assert _medical_compatibility(child) > _medical_compatibility(adult)

    def test_thoracic_sex_penalty(self):
        male = {"blood_type": "A+", "age": 40, "sex": "male", "organ": "heart"}
        female = {"blood_type": "A+", "age": 40, "sex": "female", "organ": "heart"}
        assert _medical_compatibility(male) > _medical_compatibility(female)

    def test_score_in_range(self):
        p = {"blood_type": "B+", "age": 50, "sex": "female", "organ": "lung"}
        score = _medical_compatibility(p)
        assert 0 <= score <= 100


class TestWaitTimeMultiplier:
    def test_high_cpra_increases_wait(self):
        assert _wait_time_multiplier("kidney", {"cpra": 99, "urgency": 3}) > 3.0

    def test_low_cpra_neutral(self):
        assert _wait_time_multiplier("kidney", {"cpra": 10, "urgency": 3}) == 1.0

    def test_high_meld_reduces_wait(self):
        assert _wait_time_multiplier("liver", {"meld": 38, "urgency": 3}) < 0.2

    def test_high_las_reduces_wait(self):
        assert _wait_time_multiplier("lung", {"las": 55, "urgency": 3}) < 0.4

    def test_urgency_1_fastest(self):
        assert _wait_time_multiplier("heart", {"urgency": 1}) < _wait_time_multiplier("heart", {"urgency": 4})


# ── Integration tests for full scoring ──────────────────────────────────

class TestScoreAllCenters:
    def test_returns_centers_for_kidney(self):
        patient = {"organ": "kidney", "blood_type": "O+", "age": 45, "sex": "female", "urgency": 3, "adjust_for_cause_of_death": False}
        results = score_all_centers(patient)
        assert len(results) > 100  # kidney has the most programs

    def test_returns_fewer_for_intestine(self):
        patient = {"organ": "intestine", "blood_type": "A+", "age": 30, "sex": "male", "urgency": 2, "adjust_for_cause_of_death": False}
        results = score_all_centers(patient)
        assert len(results) > 0
        assert len(results) < 100  # fewer centers do intestine

    def test_scores_in_valid_range(self):
        patient = {"organ": "liver", "blood_type": "B+", "age": 50, "sex": "male", "urgency": 3, "adjust_for_cause_of_death": False}
        results = score_all_centers(patient)
        for r in results:
            assert 0 <= r.total <= 100
            for k, v in r.breakdown.items():
                assert k in DEFAULT_WEIGHTS
                assert 0 <= v <= 100, f"{r.name} {k} = {v}"

    def test_sorted_descending(self):
        patient = {"organ": "heart", "blood_type": "O+", "age": 55, "sex": "male", "urgency": 2, "adjust_for_cause_of_death": False}
        results = score_all_centers(patient)
        for i in range(1, len(results)):
            assert results[i-1].total >= results[i].total

    def test_ranks_assigned(self):
        patient = {"organ": "kidney", "blood_type": "A+", "age": 40, "sex": "female", "urgency": 3, "adjust_for_cause_of_death": False}
        results = score_all_centers(patient)
        assert results[0].rank == 1
        assert results[-1].rank == len(results)

    def test_custom_weights(self):
        patient = {"organ": "kidney", "blood_type": "O+", "age": 45, "sex": "female", "urgency": 3, "adjust_for_cause_of_death": False}
        # Weight everything on wait time
        custom = {k: 0.0 for k in DEFAULT_WEIGHTS}
        custom["waitTime"] = 1.0
        results = score_all_centers(patient, custom)
        assert len(results) > 100
        # Top center should have high wait time score
        assert results[0].breakdown["waitTime"] > 70

    def test_cod_adjustment_changes_scores(self):
        base_patient = {"organ": "kidney", "blood_type": "O+", "age": 45, "sex": "female", "urgency": 3, "adjust_for_cause_of_death": False}
        cod_patient = {**base_patient, "adjust_for_cause_of_death": True}
        base_results = score_all_centers(base_patient)
        cod_results = score_all_centers(cod_patient)
        # At least some scores should differ
        diffs = sum(1 for b, c in zip(base_results[:20], cod_results[:20]) if abs(b.total - c.total) > 0.1)
        assert diffs > 0

    def test_all_8_categories_present(self):
        patient = {"organ": "lung", "blood_type": "A-", "age": 35, "sex": "male", "urgency": 3, "adjust_for_cause_of_death": False}
        results = score_all_centers(patient)
        assert len(results) > 0
        breakdown = results[0].breakdown
        assert set(breakdown.keys()) == set(DEFAULT_WEIGHTS.keys())

    def test_center_has_metadata(self):
        patient = {"organ": "kidney", "blood_type": "O+", "age": 45, "sex": "female", "urgency": 3, "adjust_for_cause_of_death": False}
        results = score_all_centers(patient)
        r = results[0]
        assert r.code  # SRTR center code
        assert r.name  # Human-readable name
        assert r.state  # Full state name
        assert r.state_abbr  # 2-letter abbreviation
        assert r.lat != 0
        assert r.lon != 0
