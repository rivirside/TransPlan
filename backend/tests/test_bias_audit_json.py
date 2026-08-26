"""The bias audit must always serialize to valid JSON (#350 review).

A p24 of exactly 0 — a highly sensitized profile at a slow center — made the
disparity ratio float("inf"). FastAPI emits that as bare `Infinity`, which is
not valid JSON, so the browser's response.json() rejects and the entire panel
reports as a backend failure. One unreachable demographic cell took out the
whole audit.
"""
import json

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _audit(organ="kidney", **kw):
    body = {"patient": {"organ": organ, "blood_type": "O+", "age": 45,
                        "sex": "male", "urgency": 2, **kw},
            "max_centers": 12}
    return client.post("/bias-audit", json=body)


def test_response_is_parseable_json(data):
    r = _audit()
    assert r.status_code == 200
    json.loads(r.text)  # raises on bare Infinity/NaN


def test_extreme_profile_stays_finite(data):
    """cPRA 98 drives some cells to near-zero p24 — the case that produced
    the infinite ratio."""
    r = _audit(cpra=98)
    assert r.status_code == 200
    doc = json.loads(r.text)
    for profile in doc["city_profiles"]:
        assert profile["overall_disparity_ratio"] == profile["overall_disparity_ratio"]
        assert profile["overall_disparity_ratio"] != float("inf")
        for dim in ("blood_type_disparity", "age_disparity", "sex_disparity"):
            ratio = profile[dim]["disparity_ratio"]
            assert ratio == ratio and ratio != float("inf"), (
                f"{dim} ratio is not finite: {ratio}")


def test_no_raw_infinity_token_in_the_payload(data):
    assert "Infinity" not in _audit(cpra=98).text
    assert "NaN" not in _audit(cpra=98).text
