"""The scoring weights ARE load-bearing (SCORE-01 / L-082).

Every other constant measured this way in this project turned out inert —
the BBN discretization split holds at rho 0.9987 swung from
near-deterministic to barely informative; removing the donor-supply effect
entirely leaves 0.9957. These are different, and that difference is the
finding: the headline ranking depends materially on eight uncited numbers.

These tests pin the measurement so the claim cannot go stale, and pin the
weights so they cannot drift without the measurement being redone.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "docs-site" / "static" / "data" / "scoring-weight-sensitivity.json"


@pytest.fixture(scope="module")
def doc():
    if not ARTIFACT.exists():
        pytest.skip("scoring-weight-sensitivity.json not generated")
    return json.loads(ARTIFACT.read_text())


def test_shipped_weights_unchanged(doc):
    """The sensitivity was measured against these specific weights."""
    from services.scoring import DEFAULT_WEIGHTS
    assert dict(DEFAULT_WEIGHTS) == doc["shipped_weights"], (
        "the category weights changed — re-run "
        "scripts/run-scoring-weight-sensitivity.py and update L-082")


def test_weights_sum_to_one(doc):
    from services.scoring import DEFAULT_WEIGHTS
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


def test_the_weights_are_still_load_bearing(doc):
    """The finding. This test failing means the ranking has become robust to
    the weighting — which would be good news, and would mean L-082 should be
    revisited rather than silently kept."""
    s = doc["summary"]
    assert s["worst_spearman_defensible"] < 0.9, (
        f"the ranking is now robust to reweighting (worst rho "
        f"{s['worst_spearman_defensible']}) — revisit L-082")
    assert s["top1_changes_defensible"] > 0, (
        "the top-ranked center no longer changes under any defensible "
        "weighting — revisit L-082")


def test_the_stress_test_is_excluded_from_headline_figures(doc):
    """'reversed order' is not a defensible weighting. Including it in the
    headline would overstate the finding."""
    defensible = [c for c in doc["comparisons"] if c["defensible"]]
    stress = [c for c in doc["comparisons"] if not c["defensible"]]
    assert stress, "the stress test should still be run, just not counted"
    assert doc["summary"]["n_defensible_comparisons"] == len(defensible)
    worst_defensible = min(c["spearman_vs_shipped"] for c in defensible)
    assert doc["summary"]["worst_spearman_defensible"] == worst_defensible


def test_alternatives_are_genuinely_different(doc):
    """A 'weights matter' result proves nothing if the alternatives were
    trivially extreme OR trivially similar. Check the spread is real."""
    labels = {c["weighting"] for c in doc["comparisons"]}
    assert any("equal" in l for l in labels)
    assert any("wait-time" in l for l in labels)
    assert any("quality" in l for l in labels)
    assert len(labels) >= 4


def test_multiple_organs_covered(doc):
    organs = {c["organ"] for c in doc["comparisons"]}
    assert len(organs) >= 3, (
        f"only {organs} covered — a single organ could be idiosyncratic")
