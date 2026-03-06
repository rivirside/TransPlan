"""Shared pytest fixtures for TransPlan backend tests."""
import pytest
from services.data_loader import load_all, TransPlanData
from models.schemas import PatientProfile


@pytest.fixture(scope="session")
def data() -> TransPlanData:
    """Load real data files once for the entire test session."""
    return load_all()


@pytest.fixture
def kidney_patient() -> PatientProfile:
    return PatientProfile(
        organ="kidney",
        blood_type="O+",
        age=45,
        sex="male",
        urgency=2,
        cpra=0,
    )


@pytest.fixture
def high_cpra_patient() -> PatientProfile:
    return PatientProfile(
        organ="kidney",
        blood_type="O+",
        age=45,
        sex="male",
        urgency=2,
        cpra=98,
    )


@pytest.fixture
def liver_patient() -> PatientProfile:
    return PatientProfile(
        organ="liver",
        blood_type="A+",
        age=52,
        sex="female",
        urgency=3,
        meld=28,
    )
