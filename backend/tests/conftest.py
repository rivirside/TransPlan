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


@pytest.fixture(scope="session")
def pick_center(data):
    """Runtime center selection by precondition (#341).

    Prefer this over pinning live-data center codes in new tests: the weekly
    data refresh can retire a program or re-derive a factor, and a pinned
    code then fails in confusing ways. Returns the first center code
    satisfying every requested precondition; skips the test if none exists
    (which itself signals a data problem worth seeing).
    """
    def _pick(organ: str | None = None, *, wait_factor: bool = False,
              outcomes: bool = False, trends: bool = False,
              all_organs: bool = False) -> str:
        centers = data.all_centers.get("centers", {})
        for code, rec in sorted(centers.items()):
            if organ and organ not in rec.get("organs", []):
                continue
            if all_organs and len(rec.get("organs", [])) < 6:
                continue
            if wait_factor:
                wt = data.center_wait_times.get("center_wait_time_factors", {})
                if not isinstance(wt.get(code, {}).get(organ), (int, float)):
                    continue
            if outcomes and data.observed_outcome(organ, code) is None:
                continue
            if trends:
                series = (data.center_trends.get("centers", {})
                          .get(code, {}).get(organ, {}))
                if len(series.get("years", [])) < 10:
                    continue
            return code
        pytest.skip(f"no center satisfies preconditions: organ={organ}, "
                    f"wait_factor={wait_factor}, outcomes={outcomes}, "
                    f"trends={trends}, all_organs={all_organs}")
    return _pick
