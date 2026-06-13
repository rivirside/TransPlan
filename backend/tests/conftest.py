"""Shared pytest fixtures for TransPlan backend tests."""
import pytest
from services.data_loader import load_all, TransPlanData
from models.schemas import PatientProfile


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the global rate-limiter window before each test.

    The limiter is a process-wide singleton keyed by client IP ("testclient"
    under TestClient), so without this reset the per-minute buckets would
    accumulate across the session and cause spurious 429s once rate limiting
    is applied to the unprefixed routes (#245)."""
    from middleware.rate_limit import _limiter
    with _limiter._lock:
        _limiter._windows.clear()
    yield


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
