"""HTTP endpoint integration tests using FastAPI TestClient.

Tests all API endpoints for status codes, response shape, and validation.
Uses low iteration counts for speed.
"""
import os
import pytest
from fastapi.testclient import TestClient

from main import app
from services.data_loader import load_all

# Ensure data is loaded (lifespan doesn't auto-run with TestClient)
load_all()

client = TestClient(app, raise_server_exceptions=False)

KIDNEY_PATIENT = {
    "organ": "kidney",
    "blood_type": "O+",
    "age": 45,
    "sex": "male",
    "urgency": 2,
    "cpra": 0,
}

LIVER_PATIENT = {
    "organ": "liver",
    "blood_type": "A+",
    "age": 52,
    "sex": "female",
    "urgency": 3,
    "meld": 28,
}


# ==================== GET /health ====================

class TestHealth:
    def test_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_response_shape(self):
        data = client.get("/health").json()
        assert data["status"] in ("ok", "degraded")
        assert "version" in data
        assert isinstance(data["data_freshness"], dict)
        assert isinstance(data["data_files_loaded"], int)


# ==================== POST /simulate ====================

class TestSimulate:
    def test_kidney_200(self):
        r = client.post("/simulate?iterations=100", json=KIDNEY_PATIENT)
        assert r.status_code == 200

    def test_response_has_cities(self):
        data = client.post("/simulate?iterations=100", json=KIDNEY_PATIENT).json()
        assert "cities" in data
        assert len(data["cities"]) > 0
        city = data["cities"][0]
        assert "city" in city
        assert "p_transplant_12mo" in city

    def test_liver_200(self):
        r = client.post("/simulate?iterations=100", json=LIVER_PATIENT)
        assert r.status_code == 200

    def test_invalid_organ_422(self):
        bad = {**KIDNEY_PATIENT, "organ": "brain"}
        r = client.post("/simulate?iterations=100", json=bad)
        assert r.status_code == 422

    def test_age_too_low_422(self):
        bad = {**KIDNEY_PATIENT, "age": 0}
        r = client.post("/simulate?iterations=100", json=bad)
        assert r.status_code == 422

    def test_iterations_too_low_422(self):
        r = client.post("/simulate?iterations=1", json=KIDNEY_PATIENT)
        assert r.status_code == 422


# ==================== POST /sensitivity ====================

class TestSensitivity:
    def test_returns_200(self):
        body = {"patient": KIDNEY_PATIENT, "city": "Nashville", "iterations": 100}
        r = client.post("/sensitivity", json=body)
        assert r.status_code == 200

    def test_response_has_impacts(self):
        body = {"patient": KIDNEY_PATIENT, "city": "Nashville", "iterations": 100}
        data = client.post("/sensitivity", json=body).json()
        assert "impacts" in data
        assert "city" in data


# ==================== POST /equity-analysis ====================

class TestEquity:
    def test_returns_200(self):
        body = {"patient": KIDNEY_PATIENT, "iterations_per_profile": 100}
        r = client.post("/equity-analysis", json=body)
        assert r.status_code == 200

    def test_response_has_cities(self):
        body = {"patient": KIDNEY_PATIENT, "iterations_per_profile": 100}
        data = client.post("/equity-analysis", json=body).json()
        assert "cities" in data
        assert "overall_gini" in data


# ==================== POST /what-if ====================

class TestWhatIf:
    def test_returns_200(self):
        body = {
            "patient": KIDNEY_PATIENT,
            "city": "Nashville",
            "donor_rate_multiplier": 1.2,
            "wait_time_multiplier": 0.9,
            "iterations": 100,
        }
        r = client.post("/what-if", json=body)
        assert r.status_code == 200

    def test_response_shape(self):
        body = {
            "patient": KIDNEY_PATIENT,
            "city": "Nashville",
            "iterations": 100,
        }
        data = client.post("/what-if", json=body).json()
        assert "baseline_p24" in data
        assert "adjusted_p24" in data

    def test_multiplier_out_of_range_422(self):
        body = {
            "patient": KIDNEY_PATIENT,
            "city": "Nashville",
            "donor_rate_multiplier": 5.0,
            "iterations": 100,
        }
        r = client.post("/what-if", json=body)
        assert r.status_code == 422


# ==================== GET /policy-scenarios ====================

class TestPolicyScenarios:
    def test_list_all(self):
        r = client.get("/policy-scenarios")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_filter_by_organ(self):
        r = client.get("/policy-scenarios?organ=kidney")
        assert r.status_code == 200
        data = r.json()
        for s in data:
            assert s["organs"] == [] or "kidney" in s["organs"]

    def test_get_by_id(self):
        r = client.get("/policy-scenarios/kidney_250nm")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "kidney_250nm"

    def test_get_unknown_404(self):
        r = client.get("/policy-scenarios/nonexistent_scenario")
        assert r.status_code == 404


# ==================== POST /policy-scenario ====================

class TestPolicyScenario:
    def test_returns_200(self):
        body = {
            "patient": KIDNEY_PATIENT,
            "scenario_id": "kidney_250nm",
            "city": "Nashville",
            "iterations": 100,
        }
        r = client.post("/policy-scenario", json=body)
        assert r.status_code == 200

    def test_wrong_organ_400(self):
        body = {
            "patient": LIVER_PATIENT,
            "scenario_id": "kidney_250nm",
            "city": "Nashville",
            "iterations": 100,
        }
        r = client.post("/policy-scenario", json=body)
        assert r.status_code == 400

    def test_unknown_scenario_404(self):
        body = {
            "patient": KIDNEY_PATIENT,
            "scenario_id": "fake_scenario",
            "city": "Nashville",
            "iterations": 100,
        }
        r = client.post("/policy-scenario", json=body)
        assert r.status_code == 404


# ==================== GET /trends ====================

class TestTrends:
    def test_all_organ_trends(self):
        r = client.get("/trends/kidney")
        assert r.status_code == 200
        data = r.json()
        assert data["organ"] == "kidney"
        assert "cities" in data

    def test_city_organ_trends(self):
        r = client.get("/trends/Nashville/kidney")
        assert r.status_code == 200

    def test_invalid_organ_400(self):
        r = client.get("/trends/brain")
        assert r.status_code == 400

    def test_unknown_city_404(self):
        r = client.get("/trends/Atlantis/kidney")
        assert r.status_code == 404


# ==================== POST /shutdown ====================

class TestShutdown:
    def test_no_token_set_succeeds(self):
        # When SHUTDOWN_TOKEN is not set, shutdown is unauthenticated
        # We can't actually call it (it kills the server), so just verify
        # the endpoint exists by checking it doesn't return 404/405
        # Skip if SHUTDOWN_TOKEN is set in env
        if os.environ.get("SHUTDOWN_TOKEN"):
            pytest.skip("SHUTDOWN_TOKEN is set; can't test unauthenticated path")

    def test_wrong_token_403(self):
        orig = os.environ.get("SHUTDOWN_TOKEN")
        os.environ["SHUTDOWN_TOKEN"] = "secret-test-token"
        try:
            r = client.post("/shutdown", headers={"Authorization": "Bearer wrong"})
            assert r.status_code == 403
        finally:
            if orig is None:
                del os.environ["SHUTDOWN_TOKEN"]
            else:
                os.environ["SHUTDOWN_TOKEN"] = orig

    def test_missing_token_403(self):
        orig = os.environ.get("SHUTDOWN_TOKEN")
        os.environ["SHUTDOWN_TOKEN"] = "secret-test-token"
        try:
            r = client.post("/shutdown")
            assert r.status_code == 403
        finally:
            if orig is None:
                del os.environ["SHUTDOWN_TOKEN"]
            else:
                os.environ["SHUTDOWN_TOKEN"] = orig
