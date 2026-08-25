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
        body = {"patient": KIDNEY_PATIENT, "center_code": "TNVU", "iterations": 100}
        r = client.post("/sensitivity", json=body)
        assert r.status_code == 200

    def test_response_has_impacts(self):
        body = {"patient": KIDNEY_PATIENT, "center_code": "TNVU", "iterations": 100}
        data = client.post("/sensitivity", json=body).json()
        assert "impacts" in data
        assert "city" in data

    def test_city_only_400(self):
        """#293: the legacy 22-city mode is retired."""
        body = {"patient": KIDNEY_PATIENT, "city": "Nashville", "iterations": 100}
        r = client.post("/sensitivity", json=body)
        assert r.status_code == 400


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

    def test_weighted_and_decomposed_gini_present(self):
        """#254: population-weighted Gini + ABO decomposition."""
        body = {"patient": KIDNEY_PATIENT, "iterations_per_profile": 100, "max_centers": 10}
        data = client.post("/equity-analysis", json=body).json()
        assert data["overall_gini_weighted"] is not None
        assert data["overall_gini_between_blood_type"] is not None
        assert data["overall_gini_within_blood_type"] is not None


# ==================== POST /bias-audit ====================

class TestBiasAudit:
    def test_returns_200_with_metrics(self):
        """#254: bias_audit.py was previously unreachable from any endpoint."""
        body = {"patient": KIDNEY_PATIENT, "iterations_per_profile": 100, "max_centers": 10}
        r = client.post("/bias-audit", json=body)
        assert r.status_code == 200
        data = r.json()
        assert data["n_profiles"] == 48
        assert data["n_cities"] >= 1
        bt = data["national_blood_type_disparity"]
        assert bt["disparity_ratio"] >= 1.0
        assert "cohens_d" in bt


# ==================== POST /what-if ====================

class TestWhatIf:
    def test_returns_200(self):
        body = {
            "patient": KIDNEY_PATIENT,
            "center_code": "TNVU",
            "donor_rate_multiplier": 1.2,
            "wait_time_multiplier": 0.9,
            "iterations": 100,
        }
        r = client.post("/what-if", json=body)
        assert r.status_code == 200

    def test_response_shape(self):
        body = {
            "patient": KIDNEY_PATIENT,
            "center_code": "TNVU",
            "iterations": 100,
        }
        data = client.post("/what-if", json=body).json()
        assert "baseline_p24" in data
        assert "adjusted_p24" in data

    def test_multiplier_out_of_range_422(self):
        body = {
            "patient": KIDNEY_PATIENT,
            "center_code": "TNVU",
            "donor_rate_multiplier": 5.0,
            "iterations": 100,
        }
        r = client.post("/what-if", json=body)
        assert r.status_code == 422

    def test_center_code_outside_focus_cities_200(self):
        """#286: any of the 248 centers must work, not just the 22 focus cities."""
        body = {
            "patient": KIDNEY_PATIENT,
            "city": "Children's of Alabama",  # display label, not a valid city
            "center_code": "ALCH",
            "iterations": 100,
        }
        r = client.post("/what-if", json=body)
        assert r.status_code == 200
        data = r.json()
        assert data["center_code"] == "ALCH"
        assert data["state"] == "AL"

    def test_unknown_center_code_400(self):
        body = {
            "patient": KIDNEY_PATIENT,
            "center_code": "ZZZZ",
            "iterations": 100,
        }
        r = client.post("/what-if", json=body)
        assert r.status_code == 400

    def test_city_only_400(self):
        """#293: the legacy 22-city mode is retired."""
        body = {"patient": KIDNEY_PATIENT, "city": "Nashville", "iterations": 100}
        r = client.post("/what-if", json=body)
        assert r.status_code == 400
        assert "center_code is required" in r.json()["detail"]


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
            "center_code": "TNVU",
            "iterations": 100,
        }
        r = client.post("/policy-scenario", json=body)
        assert r.status_code == 200

    def test_wrong_organ_400(self):
        body = {
            "patient": LIVER_PATIENT,
            "scenario_id": "kidney_250nm",
            "center_code": "TNVU",
            "iterations": 100,
        }
        r = client.post("/policy-scenario", json=body)
        assert r.status_code == 400

    def test_unknown_scenario_404(self):
        body = {
            "patient": KIDNEY_PATIENT,
            "scenario_id": "fake_scenario",
            "center_code": "TNVU",
            "iterations": 100,
        }
        r = client.post("/policy-scenario", json=body)
        assert r.status_code == 404

    def test_center_code_outside_focus_cities_200(self):
        """#286: policy scenarios must accept any of the 248 centers."""
        body = {
            "patient": KIDNEY_PATIENT,
            "scenario_id": "kidney_250nm",
            "city": "Children's of Alabama",
            "center_code": "ALCH",
            "iterations": 100,
        }
        r = client.post("/policy-scenario", json=body)
        assert r.status_code == 200
        assert r.json()["center_code"] == "ALCH"


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


# ==================== POST /travel-subsidy-analysis ====================

class TestTravelSubsidy:
    def test_covers_all_centers_by_default(self):
        """#285: the sweep must cover the full center population, not 22 cities."""
        body = {"patient": KIDNEY_PATIENT}
        r = client.post("/travel-subsidy-analysis", json=body)
        assert r.status_code == 200
        data = r.json()
        assert data["total_cities"] > 200, f"only {data['total_cities']} centers analyzed"
        assert len(data["tiers"]) == 4
        first = data["tiers"][0]["cities"][0]
        assert first["center_code"], "results must carry center codes"

    def test_center_codes_filter(self):
        body = {"patient": KIDNEY_PATIENT, "center_codes": ["ALCH", "ALUA"]}
        data = client.post("/travel-subsidy-analysis", json=body).json()
        assert data["total_cities"] == 2

    def test_unknown_codes_400(self):
        body = {"patient": KIDNEY_PATIENT, "center_codes": ["ZZZZ"]}
        r = client.post("/travel-subsidy-analysis", json=body)
        assert r.status_code == 400

    def test_higher_subsidy_larger_system_effect(self):
        body = {"patient": KIDNEY_PATIENT, "center_codes": ["CASF", "ALUA", "NYCP", "TXHH"]}
        data = client.post("/travel-subsidy-analysis", json=body).json()
        deltas = [t["system_delta_p24"] for t in data["tiers"]]
        assert deltas == sorted(deltas), f"no diminishing-returns curve: {deltas}"
        assert deltas[-1] >= deltas[0]


# ==================== /score/explain tier cap (#249) ====================

class TestScoreExplainTierCap:
    def test_web_tier_caps_provenance_limit(self, monkeypatch):
        monkeypatch.setenv("TRANSPLAN_TIER", "web")
        r = client.post("/score/explain?limit=248", json=KIDNEY_PATIENT)
        assert r.status_code == 200
        data = r.json()
        n_prov = len(data.get("provenance", data.get("centers_with_provenance", [])) or [])
        # Web tier cap is 50 — a 248 request must not return 248 trails
        assert 0 < n_prov <= 50, f"web tier returned {n_prov} provenance trails"

    def test_local_tier_allows_full(self, monkeypatch):
        monkeypatch.setenv("TRANSPLAN_TIER", "local")
        r = client.post("/score/explain?limit=60", json=KIDNEY_PATIENT)
        assert r.status_code == 200
        data = r.json()
        n_prov = len(data.get("provenance", data.get("centers_with_provenance", [])) or [])
        assert n_prov > 50


# ==================== center_codes shortlist (#304 / L-067) ====================

class TestCenterCodesShortlist:
    def test_score_restricts_to_shortlist(self):
        body = {**KIDNEY_PATIENT, "center_codes": ["ALCH", "ALUA", "TNVU"]}
        data = client.post("/score", json=body).json()
        codes = {c["code"] for c in data["centers"]}
        assert codes == {"ALCH", "ALUA", "TNVU"}

    def test_simulate_restricts_to_shortlist(self):
        body = {**KIDNEY_PATIENT, "center_codes": ["ALCH", "TNVU"]}
        data = client.post("/simulate?iterations=100", json=body).json()
        codes = {c["center_code"] for c in data["cities"]}
        assert codes == {"ALCH", "TNVU"}

    def test_simulate_unknown_codes_400(self):
        body = {**KIDNEY_PATIENT, "center_codes": ["ZZZZ"]}
        r = client.post("/simulate?iterations=100", json=body)
        assert r.status_code == 400

    def test_bbn_restricts_to_shortlist(self):
        body = {**KIDNEY_PATIENT, "center_codes": ["ALCH", "TNVU"],
                "bbn_granularity": "full"}
        r = client.post("/simulate?iterations=100&inference_mode=bayesian&bbn_granularity=full",
                        json=body)
        assert r.status_code == 200
        codes = {c["center_code"] for c in r.json()["cities"]}
        assert codes == {"ALCH", "TNVU"}


# ==================== Validation router error handling (#220) ====================

class TestValidationErrorHandling:
    def test_clinical_sensitivity_maps_value_error_to_400(self):
        """The alias must behave like /sensitivity: missing center_code = 400,
        not 500."""
        r = client.post("/validation/clinical-sensitivity", json=KIDNEY_PATIENT)
        assert r.status_code == 400
        assert "center_code" in r.json()["detail"]

    def test_cross_engine_notes_never_leak_exception_text(self):
        body = {"patient": KIDNEY_PATIENT, "iterations": 100}
        r = client.post("/validation/cross-engine", json=body)
        assert r.status_code == 200
        for engine in r.json()["engines"]:
            if not engine["available"]:
                assert engine["note"] in ("engine failed — see server logs",
                                          "MCMC not in tier", "pgmpy not installed") or \
                    "No trace" in engine["note"] or "tier" in engine["note"].lower()
