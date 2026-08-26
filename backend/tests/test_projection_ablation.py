"""#266 asked for an Albers projection so GP distances are not degree-distorted.

Measured instead of assumed: fitting the same kernel on Albers kilometres
rather than raw degrees changes holdout RMSE by under 1% on every layer
(mean +0.2%). The anisotropic-kernel argument in `_fit_gp`'s docstring holds
empirically, so the projection is recorded as measured-and-rejected.

These tests pin the finding so a future change to the kernel or the layer
density has to re-open the question rather than silently invalidate it.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "docs-site" / "static" / "data" / "projection-ablation.json"


@pytest.fixture(scope="module")
def doc():
    if not ARTIFACT.exists():
        pytest.skip("projection-ablation.json not generated")
    return json.loads(ARTIFACT.read_text())


def test_finding_still_holds(doc):
    """If a kernel or data change makes projection matter, this fails and the
    decision has to be revisited rather than inherited."""
    s = doc["summary"]
    assert abs(s["mean_relative_improvement"]) < 0.02, (
        f"projection now changes RMSE by "
        f"{s['mean_relative_improvement']:+.1%} — #266's projection clause "
        f"was closed on the basis that it did not. Re-open it.")


def test_every_layer_was_indistinguishable(doc):
    for layer in doc["layers"]:
        assert abs(layer["relative_improvement"]) < 0.02, (
            f"{layer['layer']}: projection changed RMSE by "
            f"{layer['relative_improvement']:+.1%}")


def test_the_comparison_was_actually_fair(doc):
    """The result only means anything if both coordinate systems got a real
    fit. A degenerate RMSE on either side would make 'no difference' vacuous."""
    for layer in doc["layers"]:
        assert layer["degrees_rmse"] > 0
        assert layer["albers_rmse"] > 0
        assert layer["n_points"] >= 60
        # Per-split errors must vary; identical values across splits would
        # mean the holdout was not actually resampled.
        assert len(set(layer["degrees_rmse_by_split"])) > 1


def test_albers_projection_is_correct():
    """A wrong projection would also produce 'no difference', for the wrong
    reason — so check it against known distances."""
    import importlib.util
    import math
    spec = importlib.util.spec_from_file_location(
        "pa", REPO / "scripts" / "run-projection-ablation.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    import numpy as np
    # Houston (29.76, -95.37) to Dallas (32.78, -96.80): ~362 km great-circle.
    xy = mod.albers(np.array([29.76, 32.78]), np.array([-95.37, -96.80]))
    d = math.dist(xy[0], xy[1])
    assert 340 < d < 385, f"Houston-Dallas projected to {d:.0f} km, expected ~362"

    # A degree of longitude must shrink with latitude — the whole point.
    south = mod.albers(np.array([30.0, 30.0]), np.array([-96.0, -95.0]))
    north = mod.albers(np.array([48.0, 48.0]), np.array([-96.0, -95.0]))
    d_south = math.dist(south[0], south[1])
    d_north = math.dist(north[0], north[1])
    assert d_south > d_north, (
        f"one degree of longitude measured {d_south:.1f} km at 30N and "
        f"{d_north:.1f} km at 48N — the projection is not converging")
    assert 90 < d_south < 105 and 68 < d_north < 82
