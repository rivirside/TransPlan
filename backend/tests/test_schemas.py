"""Tests for models/schemas.py Pydantic validation."""
import pytest
from pydantic import ValidationError
from models.schemas import PatientProfile, CityProbability, SimulationResult


class TestPatientProfileValidation:
    def test_valid_kidney_patient(self):
        p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2, cpra=30)
        assert p.organ == "kidney"
        assert p.cpra == 30

    def test_valid_liver_patient(self):
        p = PatientProfile(organ="liver", blood_type="A-", age=52, sex="female", urgency=3, meld=28)
        assert p.meld == 28

    def test_valid_lung_patient(self):
        p = PatientProfile(organ="lung", blood_type="B+", age=38, sex="male", urgency=4, las=45.5)
        assert p.las == 45.5

    def test_optional_fields_default_none(self):
        p = PatientProfile(organ="heart", blood_type="AB+", age=60, sex="female", urgency=1)
        assert p.cpra is None
        assert p.meld is None
        assert p.las is None
        assert p.insurance is None

    def test_invalid_blood_type_rejected(self):
        with pytest.raises(ValidationError):
            PatientProfile(organ="kidney", blood_type="Z+", age=45, sex="male", urgency=2)

    def test_invalid_organ_rejected(self):
        with pytest.raises(ValidationError):
            PatientProfile(organ="spleen", blood_type="O+", age=45, sex="male", urgency=2)

    def test_age_bounds(self):
        with pytest.raises(ValidationError):
            PatientProfile(organ="kidney", blood_type="O+", age=-1, sex="male", urgency=2)
        with pytest.raises(ValidationError):
            PatientProfile(organ="kidney", blood_type="O+", age=100, sex="male", urgency=2)

    def test_urgency_bounds(self):
        with pytest.raises(ValidationError):
            PatientProfile(organ="kidney", blood_type="O+", age=40, sex="male", urgency=0)
        with pytest.raises(ValidationError):
            PatientProfile(organ="kidney", blood_type="O+", age=40, sex="male", urgency=5)

    def test_cpra_bounds(self):
        with pytest.raises(ValidationError):
            PatientProfile(organ="kidney", blood_type="O+", age=40, sex="male", urgency=2, cpra=-1)
        with pytest.raises(ValidationError):
            PatientProfile(organ="kidney", blood_type="O+", age=40, sex="male", urgency=2, cpra=101)

    def test_meld_bounds(self):
        with pytest.raises(ValidationError):
            PatientProfile(organ="liver", blood_type="O+", age=40, sex="male", urgency=2, meld=5)
        with pytest.raises(ValidationError):
            PatientProfile(organ="liver", blood_type="O+", age=40, sex="male", urgency=2, meld=41)

    def test_all_blood_types_valid(self):
        for bt in ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]:
            p = PatientProfile(organ="kidney", blood_type=bt, age=40, sex="male", urgency=2)
            assert p.blood_type == bt

    def test_all_organs_valid(self):
        for organ in ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]:
            p = PatientProfile(organ=organ, blood_type="O+", age=40, sex="male", urgency=2)
            assert p.organ == organ

    def test_home_center_accepted(self):
        p = PatientProfile(
            organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
            home_center="Nashville"
        )
        assert p.home_center == "Nashville"

    def test_home_center_defaults_none(self):
        p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2)
        assert p.home_center is None

    def test_adjust_for_cause_of_death_defaults_false(self):
        p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2)
        assert p.adjust_for_cause_of_death is False

    def test_adjust_for_cause_of_death_accepted(self):
        p = PatientProfile(
            organ="heart", blood_type="A+", age=50, sex="male", urgency=1,
            adjust_for_cause_of_death=True
        )
        assert p.adjust_for_cause_of_death is True

    # --- Phase 4 M1: custom_weights validation ---

    VALID_WEIGHTS = {
        "medicalCompatibility": 0.25, "waitTime": 0.20, "donorAvailability": 0.18,
        "hospitalQuality": 0.15, "geographic": 0.10, "healthDemographics": 0.07,
        "policy": 0.03, "socioeconomic": 0.02
    }

    def test_custom_weights_defaults_none(self):
        p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2)
        assert p.custom_weights is None

    def test_custom_weights_valid_accepted(self):
        p = PatientProfile(
            organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
            custom_weights=self.VALID_WEIGHTS
        )
        assert p.custom_weights == self.VALID_WEIGHTS

    def test_custom_weights_clinical_preset(self):
        clinical = {
            "medicalCompatibility": 0.35, "waitTime": 0.15, "donorAvailability": 0.10,
            "hospitalQuality": 0.25, "geographic": 0.05, "healthDemographics": 0.05,
            "policy": 0.03, "socioeconomic": 0.02
        }
        p = PatientProfile(
            organ="liver", blood_type="A-", age=52, sex="female", urgency=3,
            custom_weights=clinical
        )
        assert p.custom_weights["medicalCompatibility"] == 0.35

    def test_custom_weights_missing_key_rejected(self):
        incomplete = {k: v for k, v in self.VALID_WEIGHTS.items() if k != "policy"}
        with pytest.raises(ValidationError, match="custom_weights must have exactly"):
            PatientProfile(
                organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
                custom_weights=incomplete
            )

    def test_custom_weights_extra_key_rejected(self):
        extra = {**self.VALID_WEIGHTS, "bogus": 0.0}
        with pytest.raises(ValidationError, match="custom_weights must have exactly"):
            PatientProfile(
                organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
                custom_weights=extra
            )

    def test_custom_weights_negative_value_rejected(self):
        bad = {**self.VALID_WEIGHTS, "policy": -0.01}
        with pytest.raises(ValidationError, match="must be >= 0"):
            PatientProfile(
                organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
                custom_weights=bad
            )

    def test_custom_weights_sum_too_high_rejected(self):
        doubled = {k: v * 2 for k, v in self.VALID_WEIGHTS.items()}
        with pytest.raises(ValidationError, match="must sum to ~1.0"):
            PatientProfile(
                organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
                custom_weights=doubled
            )

    def test_custom_weights_sum_too_low_rejected(self):
        halved = {k: v * 0.5 for k, v in self.VALID_WEIGHTS.items()}
        with pytest.raises(ValidationError, match="must sum to ~1.0"):
            PatientProfile(
                organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
                custom_weights=halved
            )

    def test_custom_weights_within_tolerance_accepted(self):
        # Sum = 1.04 — within ±0.05 tolerance
        slightly_off = {**self.VALID_WEIGHTS, "socioeconomic": 0.06}
        p = PatientProfile(
            organ="kidney", blood_type="O+", age=45, sex="male", urgency=2,
            custom_weights=slightly_off
        )
        assert abs(sum(p.custom_weights.values()) - 1.04) < 0.001

    def test_custom_weights_round_trip_preserved(self):
        """Weights survive serialization/deserialization (export fidelity)."""
        p = PatientProfile(
            organ="heart", blood_type="B+", age=55, sex="female", urgency=1,
            custom_weights=self.VALID_WEIGHTS
        )
        data = p.model_dump()
        p2 = PatientProfile(**data)
        assert p2.custom_weights == self.VALID_WEIGHTS


class TestCityProbabilityValidation:
    def test_valid_city_probability(self):
        cp = CityProbability(
            city="Pittsburgh", state="PA",
            p_transplant_6mo=0.10, p_transplant_12mo=0.25,
            p_transplant_24mo=0.55, p_transplant_36mo=0.72,
            confidence_interval_95=(0.48, 0.62),
            median_wait_months=18.5,
        )
        assert cp.city == "Pittsburgh"
        assert cp.competing_risks is None

    def test_probability_out_of_range(self):
        with pytest.raises(ValidationError):
            CityProbability(
                city="X", state="Y",
                p_transplant_6mo=1.1,  # > 1.0 — invalid
                p_transplant_12mo=0.25, p_transplant_24mo=0.55, p_transplant_36mo=0.72,
                confidence_interval_95=(0.48, 0.62),
                median_wait_months=18.5,
            )
