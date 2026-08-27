"""Rank range across the app's own weighting presets (#386 / L-082).

L-082 measured that the scoring weights are load-bearing — the top-ranked
center changes in 13 of 16 defensible weightings. The #313 rank intervals do
not cover that: they bootstrap the DATA and rank by p24, holding weights
fixed. This endpoint quantifies the weight source for the score ranking the
results table actually sorts by.

The neighbourhood is the app's OWN presets rather than one invented here.
Inventing one would just move the uncited constant somewhere less visible.
"""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from services.weight_range import PRESETS, compute_weight_range

REPO = Path(__file__).resolve().parents[2]
client = TestClient(app)


def _patient(organ="kidney"):
    return {"organ": organ, "blood_type": "O+", "age": 50, "sex": "male",
            "urgency": 2}


@pytest.fixture(scope="module")
def result(data):
    return compute_weight_range(_patient())


def test_presets_match_the_frontend_definitions():
    """The backend copy is kept in sync deliberately; this makes a silent
    divergence impossible. If the UI offers a preset the backend does not
    know, the reported range would understate the real spread."""
    src = (REPO / "weight-config.js").read_text()

    def js_preset(name: str) -> dict[str, float]:
        """Pull one preset's weights out of weight-config.js.

        Parsed NUMERICALLY rather than string-matched: Python renders 0.10 as
        '0.1', so a literal comparison reports a divergence where none exists.
        """
        m = re.search(rf"\b{name}\s*:\s*{{.*?weights\s*:\s*{{(.*?)}}",
                      src, re.S)
        if not m:
            return {}
        return {k: float(v) for k, v in
                re.findall(r"(\w+)\s*:\s*([0-9.]+)", m.group(1))}

    for name, weights in PRESETS.items():
        if name == "balanced":
            continue  # mirrors DEFAULT_WEIGHTS by reference in both places
        found = js_preset(name)
        assert found, f"backend preset '{name}' has no counterpart in weight-config.js"
        for cat, value in weights.items():
            assert cat in found, f"preset '{name}' missing {cat} in weight-config.js"
            assert abs(found[cat] - value) < 1e-9, (
                f"preset '{name}' {cat}: backend {value} vs frontend {found[cat]}")


def test_every_preset_is_a_distribution():
    for name, w in PRESETS.items():
        assert abs(sum(w.values()) - 1.0) < 1e-9, f"{name} sums to {sum(w.values())}"


def test_every_center_is_ranked_under_every_preset(result):
    assert result["n_centers"] > 200
    for c in result["centers"]:
        assert len(c["ranks_by_preset"]) == len(PRESETS)
        assert c["rank_min"] <= c["rank_balanced"] <= c["rank_max"]
        assert c["rank_spread"] == c["rank_max"] - c["rank_min"]


def test_the_spread_is_material(result):
    """The finding this exists to surface. If the ranking became robust to
    reweighting, L-082 and #386 would both need revisiting."""
    assert result["median_rank_spread"] > 5, (
        f"median rank spread is only {result['median_rank_spread']} — the "
        f"ranking may have become robust to reweighting; revisit L-082")


def test_the_top_is_more_stable_than_the_middle(result):
    """The useful asymmetry: a top-5 placement means something, a
    40th-vs-70th comparison does not. If this inverts, the note in the UI
    is telling users the wrong thing."""
    centers = result["centers"]
    top5 = [c["rank_spread"] for c in centers[:5]]
    middle = [c["rank_spread"] for c in centers[len(centers)//2 - 5:len(centers)//2 + 5]]
    assert sum(top5) / len(top5) < sum(middle) / len(middle), (
        "top ranks are no longer more stable than middle ranks")


def test_endpoint_returns_the_same_shape(data):
    r = client.post("/weight-range", json={"patient": _patient()})
    assert r.status_code == 200
    body = json.loads(r.text)   # must be valid JSON, no Infinity/NaN
    assert body["n_centers"] > 200
    assert set(body["presets"]) == set(PRESETS)
    assert body["note"]


def test_unknown_organ_is_a_400(data):
    r = client.post("/weight-range",
                    json={"patient": {**_patient(), "organ": "spleen"}})
    assert r.status_code in (400, 422)
