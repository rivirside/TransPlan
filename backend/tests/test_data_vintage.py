"""Data-vintage disclosure (#334).

Every result reflects SRTR cohorts from ~1-3 years before the release date,
and allocation policy is actively changing — responses must say which release
they are built on instead of presenting the numbers as current-day truth.
"""
import pytest

from models.schemas import PatientProfile


@pytest.fixture(autouse=True)
def _load(data):
    pass


class TestVintageHelper:
    def test_srtr_vintage_shape(self):
        from services.data_loader import get_data
        v = get_data().srtr_vintage()
        assert "srtr_source" in v and v["srtr_source"], "no SRTR source string"
        assert "fetched" in v and v["fetched"], "no fetch timestamp"
        assert "note" in v and "cohort" in v["note"].lower()

    def test_source_names_a_release(self):
        """The source string must identify a specific SRTR release."""
        from services.data_loader import get_data
        src = get_data().srtr_vintage()["srtr_source"]
        assert "SRTR" in src
        assert any(ch.isdigit() for ch in src), (
            f"source string carries no release identifier: {src!r}"
        )


class TestVintageOnResponses:
    def test_simulate_carries_vintage(self):
        from services.monte_carlo import simulate
        p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                           urgency=2)
        result = simulate(p, n_iterations=100, seed=1)
        assert result.data_vintage is not None
        assert "SRTR" in result.data_vintage["srtr_source"]

    def test_bbn_carries_vintage(self):
        from services.bayesian_network import simulate_bbn
        p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                           urgency=2, bbn_granularity="state")
        result = simulate_bbn(p)
        assert result.data_vintage is not None

    def test_score_endpoint_carries_vintage(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        r = client.post("/score", json={
            "organ": "kidney", "blood_type": "O+", "age": 45, "sex": "male",
            "urgency": 2,
        })
        assert r.status_code == 200
        body = r.json()
        assert body.get("data_vintage"), "/score response has no data_vintage"
        assert "SRTR" in body["data_vintage"]["srtr_source"]
