"""GET /location-delta must only request layers that exist (#350).

The endpoint asked for wait_time_factor_*, mortality_factor_* and
graft_survival_*, all retired in #252 when interpolating center-level
outcomes across space was judged indefensible. Every call therefore reported
three permanently unavailable layers, which made `layers_unavailable`
useless for spotting a real gap.
"""
from fastapi.testclient import TestClient

from main import app
from services.spatial_interpolation import available_layers

client = TestClient(app)

QUERY = ("/location-delta?home_lat=39.1&home_lon=-94.6"
         "&center_lat=42.4&center_lon=-71.1&organ=kidney")


def test_no_permanently_unavailable_layers(data):
    body = client.get(QUERY).json()
    assert body["layers_unavailable"] == [], (
        "endpoint requested layers that do not exist: "
        f"{body['layers_unavailable']}")


def test_retired_center_outcome_layers_not_requested(data):
    body = client.get(QUERY).json()
    for name in body["deltas"]:
        assert not name.startswith(("wait_time_factor", "mortality_factor",
                                    "graft_survival")), \
            f"{name} was retired in #252 but is still requested"


def test_every_requested_layer_resolves(data):
    body = client.get(QUERY).json()
    existing = set(available_layers())
    assert body["deltas"], "no layers returned at all"
    for name, rec in body["deltas"].items():
        assert name in existing, f"{name} is not an available layer"
        assert rec is not None, f"{name} requested but did not resolve"
        assert {"home", "center", "delta"} <= set(rec)
        assert abs((rec["center"] - rec["home"]) - rec["delta"]) < 0.02


def test_organ_still_validated(data):
    assert client.get(QUERY.replace("organ=kidney", "organ=spleen")).status_code == 400
