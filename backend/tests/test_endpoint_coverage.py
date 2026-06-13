"""#265: HTTP-level integration tests for previously-uncovered endpoints —
/centers, /centers/{code}, /spatial-*, and a /validation smoke test."""
import pytest
from fastapi.testclient import TestClient

from main import app
from services.data_loader import load_all

load_all()
client = TestClient(app, raise_server_exceptions=False)

NASHVILLE = {"lat": 36.16, "lon": -86.78}
KIDNEY_PATIENT = {"organ": "kidney", "blood_type": "O+", "age": 45, "sex": "male", "urgency": 2, "cpra": 0}


class TestCenters:
    def test_list_returns_centers(self):
        r = client.get("/centers")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] > 0
        assert len(body["centers"]) == body["total"]

    def test_filter_by_organ(self):
        r = client.get("/centers", params={"organ": "kidney"})
        assert r.status_code == 200
        assert all("kidney" in c.get("organs", []) for c in r.json()["centers"])

    def test_focus_only_returns_cities(self):
        r = client.get("/centers", params={"focus_only": True})
        assert r.status_code == 200
        assert r.json()["total"] > 0
        assert "cities" in r.json()

    def test_detail_for_valid_code(self):
        code = client.get("/centers").json()["centers"][0]["code"]
        r = client.get(f"/centers/{code}")
        assert r.status_code == 200
        assert r.json()["center"]["code"].upper() == code.upper()

    def test_detail_unknown_code_404(self):
        r = client.get("/centers/NOTAREALCODE")
        assert r.status_code == 404


class TestSpatial:
    def test_list_layers(self):
        r = client.get("/spatial-layers")
        assert r.status_code == 200
        assert r.json()["total"] > 0

    def test_interpolated_value(self):
        r = client.get("/interpolated-value", params={**NASHVILLE, "layer": "air_quality"})
        assert r.status_code == 200
        assert "value" in r.json()

    def test_interpolated_value_unknown_layer_400(self):
        r = client.get("/interpolated-value", params={**NASHVILLE, "layer": "not_a_layer"})
        assert r.status_code == 400

    def test_interpolated_value_out_of_bounds_422(self):
        # Latitude outside the CONUS clamp must be rejected by validation.
        r = client.get("/interpolated-value", params={"lat": 80.0, "lon": -86.78, "layer": "air_quality"})
        assert r.status_code == 422

    def test_allocation_circles(self):
        r = client.get("/allocation-circles", params={**NASHVILLE, "organ": "kidney"})
        assert r.status_code == 200

    def test_spatial_grid(self):
        r = client.get("/spatial-grid", params={"layer": "air_quality", "resolution": 10})
        assert r.status_code == 200


class TestValidationSmoke:
    def test_calibration_returns_brier_fields(self):
        r = client.post("/validation/calibration", json={"patient": KIDNEY_PATIENT, "iterations": 100, "seed": 1})
        assert r.status_code == 200
        body = r.json()
        assert "brier_score_24mo" in body
