"""Tests for the score explainability service.

Verifies that:
1. Explain output matches production scoring (no drift)
2. Provenance arithmetic is internally consistent (components sum to category, categories sum to total)
3. Schema serialization works end-to-end through the API model
"""
import pytest

from models.schemas import CenterScoreProvenance
from services.scoring import score_all_centers
from services.scoring_explain import (
    explain_all_centers,
    explain_center_score,
    explain_medical_compatibility,
    explain_wait_time,
)


@pytest.fixture
def kidney_patient_dict():
    return {
        "organ": "kidney",
        "blood_type": "O+",
        "age": 45,
        "sex": "male",
        "urgency": 2,
        "insurance": "private",
        "cpra": 0,
        "meld": None,
        "las": None,
        "adjust_for_cause_of_death": False,
        "weight_lbs": None,
        "height_inches": None,
    }


@pytest.fixture
def liver_patient_dict():
    return {
        "organ": "liver",
        "blood_type": "A+",
        "age": 52,
        "sex": "female",
        "urgency": 3,
        "insurance": "private",
        "cpra": None,
        "meld": 28,
        "las": None,
        "adjust_for_cause_of_death": False,
        "weight_lbs": None,
        "height_inches": None,
    }


# ── Drift tests: explain must match production scoring ──────────────────


def test_explain_matches_production_kidney(data, kidney_patient_dict):
    """Explain totals must match production within rounding tolerance."""
    prod = score_all_centers(kidney_patient_dict)
    expl = explain_all_centers(kidney_patient_dict, limit=20)

    prod_by_code = {p.code: p for p in prod[:30]}
    for e in expl[:20]:
        p = prod_by_code.get(e["code"])
        assert p is not None, f"Center {e['code']} missing from production"
        diff = abs(p.total - e["total"])
        assert diff < 0.5, (
            f"Drift for {e['code']}: prod={p.total} vs explain={e['total']} (diff={diff})"
        )


def test_explain_matches_production_liver(data, liver_patient_dict):
    """Same drift check for liver."""
    prod = score_all_centers(liver_patient_dict)
    expl = explain_all_centers(liver_patient_dict, limit=20)

    prod_by_code = {p.code: p for p in prod[:30]}
    for e in expl[:20]:
        p = prod_by_code.get(e["code"])
        assert p is not None
        diff = abs(p.total - e["total"])
        assert diff < 0.5


# ── Internal consistency: components → category → total ────────────────


def test_category_components_sum_to_category_contribution(data, kidney_patient_dict):
    """For weighted-component categories, sum of component contributions must
    equal the category's pre-weight score (within rounding)."""
    expl = explain_all_centers(kidney_patient_dict, limit=3)
    assert len(expl) > 0

    # Categories where components are independently weighted sub-parts
    weighted_categories = {
        "medicalCompatibility",
        "donorAvailability",
        "hospitalQuality",
        "geographic",
    }

    for center in expl:
        for cat in center["categories"]:
            if cat["category"] not in weighted_categories:
                continue
            component_sum = sum(c["contribution"] for c in cat["components"])
            # Allow for clamping to [0,100] and rounding
            assert abs(component_sum - cat["score"]) < 5.0, (
                f"{center['code']} / {cat['category']}: "
                f"components sum to {component_sum} but score is {cat['score']}"
            )


def test_total_equals_weighted_sum_of_categories(data, kidney_patient_dict):
    """Total score must equal sum of (category_score × category_weight)."""
    expl = explain_all_centers(kidney_patient_dict, limit=5)
    for center in expl:
        expected_total = sum(
            cat["score"] * cat["weight"] for cat in center["categories"]
        )
        # Both production and explain clamp to [0, 100]
        expected_total = max(0.0, min(100.0, expected_total))
        assert abs(center["total"] - expected_total) < 0.5, (
            f"{center['code']}: total {center['total']} doesn't match "
            f"weighted sum {expected_total}"
        )


def test_weights_sum_to_one(data, kidney_patient_dict):
    """Weights in the provenance must sum to ~1.0."""
    expl = explain_all_centers(kidney_patient_dict, limit=1)
    for center in expl:
        weight_sum = sum(cat["weight"] for cat in center["categories"])
        assert abs(weight_sum - 1.0) < 0.001


# ── Category-level explain function tests ──────────────────────────────


def test_medical_compatibility_components_present(kidney_patient_dict):
    """Each medical compatibility component is returned with required fields."""
    score, components = explain_medical_compatibility(kidney_patient_dict)
    assert 0 <= score <= 100
    assert len(components) == 4
    for c in components:
        assert "name" in c
        assert "value" in c
        assert "weight_within_category" in c
        assert "contribution" in c
        assert "source" in c


def test_wait_time_includes_clinical_multiplier_note(data, kidney_patient_dict):
    """Wait time provenance must surface the clinical multiplier source."""
    # Use a high cPRA patient so the multiplier is clearly nontrivial
    kidney_patient_dict["cpra"] = 85
    expl = explain_all_centers(kidney_patient_dict, limit=1)
    assert len(expl) > 0
    wait_cat = next(c for c in expl[0]["categories"] if c["category"] == "waitTime")
    component_names = " ".join(c["name"] for c in wait_cat["components"])
    assert "cPRA=85" in component_names or "Clinical multiplier" in component_names


# ── Schema serialization ───────────────────────────────────────────────


def test_provenance_serializes_to_pydantic(data, kidney_patient_dict):
    """Explain dicts must validate against the CenterScoreProvenance schema."""
    expl = explain_all_centers(kidney_patient_dict, limit=3)
    for center_dict in expl:
        # Should not raise
        model = CenterScoreProvenance(**center_dict)
        assert model.code == center_dict["code"]
        assert len(model.categories) == 8


# ── Data sources ───────────────────────────────────────────────────────


def test_data_sources_include_key_files(data, kidney_patient_dict):
    """Provenance must list the key data files consulted."""
    expl = explain_all_centers(kidney_patient_dict, limit=1)
    sources = expl[0]["data_sources"]
    sources_joined = " ".join(sources)
    assert "wait-time-distributions-centers.json" in sources_joined
    assert "post-transplant-outcomes-centers.json" in sources_joined


def test_cod_adjustment_listed_when_enabled(data, kidney_patient_dict):
    """When COD is enabled, provenance must mention the data source."""
    kidney_patient_dict["adjust_for_cause_of_death"] = True
    expl = explain_all_centers(kidney_patient_dict, limit=1)
    sources = expl[0]["data_sources"]
    assert any("cause-of-death" in s for s in sources)


# ── Edge cases ─────────────────────────────────────────────────────────


def test_explain_skips_centers_that_dont_perform_organ(data):
    """Centers without the requested organ are excluded."""
    intestine_patient = {
        "organ": "intestine",
        "blood_type": "O+",
        "age": 30,
        "sex": "male",
        "urgency": 2,
        "insurance": "private",
        "cpra": None,
        "meld": None,
        "las": None,
        "adjust_for_cause_of_death": False,
        "weight_lbs": None,
        "height_inches": None,
    }
    expl = explain_all_centers(intestine_patient, limit=10)
    # Only a few centers do intestine; result should be much smaller than 248
    assert len(expl) < 50


def test_limit_caps_results(data, kidney_patient_dict):
    """Limit parameter caps the number of provenance trails returned."""
    expl = explain_all_centers(kidney_patient_dict, limit=5)
    assert len(expl) == 5


# ── HTTP endpoint integration ──────────────────────────────────────────


def test_score_explain_endpoint_returns_200():
    """The POST /score/explain endpoint returns valid provenance."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app, raise_server_exceptions=False)
    r = client.post(
        "/score/explain?limit=3",
        json={
            "organ": "kidney",
            "blood_type": "O+",
            "age": 45,
            "sex": "male",
            "urgency": 2,
            "cpra": 0,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "provenance" in body
    assert "centers" in body
    assert len(body["provenance"]) == 3
    # Each provenance entry has the expected structure
    for prov in body["provenance"]:
        assert "code" in prov
        assert "total" in prov
        assert "categories" in prov
        assert len(prov["categories"]) == 8
        assert "data_sources" in prov


def test_score_explain_limit_validation():
    """The limit parameter validates correctly."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app, raise_server_exceptions=False)
    r = client.post(
        "/score/explain?limit=0",
        json={
            "organ": "kidney",
            "blood_type": "O+",
            "age": 45,
            "sex": "male",
            "urgency": 2,
            "cpra": 0,
        },
    )
    # ge=1 constraint should reject limit=0
    assert r.status_code == 422
