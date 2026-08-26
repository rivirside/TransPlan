"""Multi-listing joint-probability analyzer (#321 / L-074).

Mechanism (verified against OPTN policy in the 2026-08 fact-check): every
deceased-donor organ generates ONE national match run; a second listing adds
a second independently-scored entry with proximity measured from the second
hospital. Two listings' offer processes are therefore POSITIVELY CORRELATED
in proportion to their donor-pool overlap (allocation-circle intersection):
same-metro centers add almost nothing, distant centers approach
independence.

Model: joint P(first transplant <= t) = P(min(T_A..T_k) <= t AND transplant
beats the patient-level competing risks), with the wait times coupled by a
Gaussian copula whose pairwise correlation is the 250nm-circle overlap
fraction. Probability bounds are structural:
    max(marginals) <= joint <= 1 - prod(1 - marginals)
with overlap -> 1 approaching the lower bound and overlap -> 0 the upper.
"""
import pytest

from models.schemas import PatientProfile
from services.multi_listing import (
    circle_overlap_fraction,
    compute_multi_listing,
)


@pytest.fixture(autouse=True)
def _load(data):
    pass


@pytest.fixture
def kidney_patient():
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                          urgency=2, cpra=20)


class TestCircleOverlap:
    def test_zero_distance_full_overlap(self):
        assert circle_overlap_fraction(0.0) == pytest.approx(1.0)

    def test_beyond_two_radii_no_overlap(self):
        assert circle_overlap_fraction(501.0) == 0.0

    def test_monotone_decreasing(self):
        prev = 1.1
        for d in range(0, 520, 20):
            f = circle_overlap_fraction(float(d))
            assert f <= prev + 1e-12
            prev = f

    def test_half_separation_partial(self):
        f = circle_overlap_fraction(250.0)
        assert 0.2 < f < 0.6


class TestJointProbability:
    def _run(self, patient, codes, **kw):
        return compute_multi_listing(patient, codes, seed=42, **kw)

    def _two_distant_codes(self, data, organ="kidney"):
        # PAPT (Pittsburgh) and CASF (San Francisco) — far beyond 500nm
        return ["PAPT", "CASF"]

    def test_bounds_hold(self, kidney_patient, data):
        r = self._run(kidney_patient, self._two_distant_codes(data))
        marginals = [c["p24"] for c in r["listings"]]
        upper = 1.0 - (1.0 - marginals[0]) * (1.0 - marginals[1])
        assert max(marginals) - 0.02 <= r["joint_p24"] <= upper + 0.02

    def test_distant_pair_beats_best_single(self, kidney_patient, data):
        r = self._run(kidney_patient, self._two_distant_codes(data))
        assert r["joint_p24"] > max(c["p24"] for c in r["listings"])
        assert r["gain_over_best_single"] > 0

    def test_same_metro_adds_little(self, kidney_patient, data):
        """Two co-located centers share a donor pool — the joint gain must be
        far smaller than for a distant pair (OPTN's own guidance)."""
        from services.data_loader import get_data
        # NYCP and NYNY are both New York City kidney centers
        near = self._run(kidney_patient, ["NYCP", "NYNY"])
        far = self._run(kidney_patient, self._two_distant_codes(data))
        near_gain = near["gain_over_best_single"] / max(
            c["p24"] for c in near["listings"])
        far_gain = far["gain_over_best_single"] / max(
            c["p24"] for c in far["listings"])
        assert near_gain < far_gain, (
            f"co-located gain {near_gain:.3f} not below distant gain {far_gain:.3f}"
        )

    def test_deterministic_under_seed(self, kidney_patient, data):
        a = self._run(kidney_patient, self._two_distant_codes(data))
        b = self._run(kidney_patient, self._two_distant_codes(data))
        a.pop("elapsed_seconds"), b.pop("elapsed_seconds")
        assert a == b

    def test_rejects_duplicates_and_wrong_organ(self, kidney_patient):
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            self._run(kidney_patient, ["PAPT", "PAPT"])
        heart = PatientProfile(organ="heart", blood_type="O+", age=50,
                               sex="male", urgency=2)
        with pytest.raises(ValueError, match="does not perform"):
            compute_multi_listing(heart, ["PAPT", "CALA"], seed=1)

    def test_three_listings_ordered_gains(self, kidney_patient, data):
        """Adding a third listing can only increase the joint probability."""
        two = self._run(kidney_patient, ["PAPT", "CASF"])
        three = self._run(kidney_patient, ["PAPT", "CASF", "TXHH"])
        assert three["joint_p24"] >= two["joint_p24"] - 0.01

    def test_accrued_time_supported(self, data):
        p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                           urgency=2, cpra=20, months_waiting=36.0)
        r = compute_multi_listing(p, ["PAPT", "CASF"], seed=42)
        assert 0.0 <= r["joint_p24"] <= 1.0
        assert r["accrued_time_note"]  # kidney time travels — must be said


class TestEndpoint:
    def test_endpoint_contract(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.post("/multi-listing", json={
            "patient": {"organ": "kidney", "blood_type": "O+", "age": 45,
                        "sex": "male", "urgency": 2, "cpra": 20},
            "center_codes": ["PAPT", "CASF"],
            "seed": 42,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["joint_p24"] >= max(c["p24"] for c in body["listings"]) - 0.02
        assert "pairwise_overlap" in body

    def test_endpoint_rejects_single_code(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.post("/multi-listing", json={
            "patient": {"organ": "kidney", "blood_type": "O+", "age": 45,
                        "sex": "male", "urgency": 2},
            "center_codes": ["PAPT"],
        })
        assert resp.status_code == 422
