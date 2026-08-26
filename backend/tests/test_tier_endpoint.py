"""GET /tier must expose every cap the tier defines (#350).

The endpoint hand-listed its caps and drifted: five fields existed in
TierConfig but were never serialized, and simulator/tier-panel.js already
read one of them, silently falling back to a default forever.
"""
import dataclasses

from fastapi.testclient import TestClient

from main import app
from tier_config import get_tier

client = TestClient(app)


def test_every_tier_field_is_exposed():
    caps = client.get("/tier").json()["caps"]
    tier = get_tier()
    missing = [f.name for f in dataclasses.fields(tier)
               if f.name != "name" and f.name not in caps]
    assert not missing, f"/tier omits caps the tier defines: {missing}"


def test_previously_missing_caps_present():
    caps = client.get("/tier").json()["caps"]
    for name in ("max_rank_stability_boot", "max_validation_iterations",
                 "max_validation_sweep_steps", "max_validation_train_years",
                 "max_score_explain_limit"):
        assert name in caps, f"{name} still missing"
        assert isinstance(caps[name], (int, float))


def test_values_match_the_active_tier():
    body = client.get("/tier").json()
    tier = get_tier()
    assert body["name"] == tier.name
    for field in dataclasses.fields(tier):
        if field.name == "name":
            continue
        expected = getattr(tier, field.name)
        actual = body["caps"][field.name]
        if isinstance(expected, tuple):
            assert actual == list(expected)
        else:
            assert actual == expected


def test_tuples_serialize_as_lists():
    caps = client.get("/tier").json()["caps"]
    assert isinstance(caps["allowed_inference_modes"], list)
    assert isinstance(caps["allowed_bbn_granularity"], list)
