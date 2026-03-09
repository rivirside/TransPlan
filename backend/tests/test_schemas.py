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
