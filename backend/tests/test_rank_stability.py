"""Rank-stability bootstrap (#313).

The simulator's core output is a ranking, presented with false precision:
center #5 may be statistically indistinguishable from #3-#9 given the finite
SRTR cohorts behind each center's numbers. This service bootstraps each
center's closed-form p24 with binomial noise at the center's OBSERVED cohort
size (the same #226 uncertainty philosophy as the BBN's data-sampling CI) and
reports per-center rank intervals.
"""
import pytest

from models.schemas import PatientProfile
from services.rank_stability import compute_rank_stability


@pytest.fixture(autouse=True)
def _load(data):
    pass


@pytest.fixture
def kidney_patient():
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                          urgency=2, cpra=20)


class TestRankStability:
    def test_shape_and_coverage(self, kidney_patient):
        r = compute_rank_stability(kidney_patient, n_boot=200, seed=42)
        assert r["n_boot"] == 200
        centers = r["centers"]
        assert len(centers) > 200
        for c in centers:
            assert 1 <= c["rank_lo"] <= c["rank_median"] <= c["rank_hi"] <= len(centers)
            # the point rank should lie inside its own interval
            assert c["rank_lo"] <= c["rank"] <= c["rank_hi"]

    def test_deterministic_under_seed(self, kidney_patient):
        a = compute_rank_stability(kidney_patient, n_boot=100, seed=7)
        b = compute_rank_stability(kidney_patient, n_boot=100, seed=7)
        # elapsed_seconds is wall-clock timing, not a model output
        a.pop("elapsed_seconds"), b.pop("elapsed_seconds")
        assert a == b

    def test_intervals_widen_for_sparse_centers(self, kidney_patient):
        """Centers with tiny observed cohorts must have wider rank intervals
        than the highest-volume centers (that's the whole point)."""
        r = compute_rank_stability(kidney_patient, n_boot=200, seed=42)
        by_n = sorted((c for c in r["centers"] if c["n_obs"] > 0),
                      key=lambda c: c["n_obs"])
        k = max(5, len(by_n) // 10)
        sparse = by_n[:k]
        dense = by_n[-k:]
        width = lambda c: c["rank_hi"] - c["rank_lo"]
        avg_sparse = sum(map(width, sparse)) / len(sparse)
        avg_dense = sum(map(width, dense)) / len(dense)
        assert avg_sparse > avg_dense, (
            f"sparse-cohort centers not wider: {avg_sparse:.1f} vs {avg_dense:.1f}"
        )

    def test_tie_groups_partition_the_ranking(self, kidney_patient):
        """Statistical tie groups must cover every center exactly once and be
        ordered."""
        r = compute_rank_stability(kidney_patient, n_boot=200, seed=42)
        seen = []
        for g in r["tie_groups"]:
            seen.extend(g["center_codes"])
        assert sorted(seen) == sorted(c["center_code"] for c in r["centers"])

    def test_point_ranking_matches_closed_form_order(self, kidney_patient):
        r = compute_rank_stability(kidney_patient, n_boot=50, seed=1)
        p24s = [c["p24"] for c in r["centers"]]
        assert p24s == sorted(p24s, reverse=True)


class TestEndpoint:
    def test_endpoint_returns_intervals(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.post("/rank-stability", json={
            "patient": {"organ": "kidney", "blood_type": "O+", "age": 45,
                        "sex": "male", "urgency": 2, "cpra": 20},
            "n_boot": 100, "seed": 42,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["n_boot"] == 100
        assert len(body["centers"]) > 200
        assert body["centers"][0]["rank_lo"] >= 1
