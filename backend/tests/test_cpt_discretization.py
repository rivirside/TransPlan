"""Are the BBN discretization probabilities load-bearing? (#213)

`_CPT_STRONG/_MEDIUM/_WEAK` map a continuous variable's tercile onto a
discrete node. #213 filed them as arbitrary; they now carry a source
(Druzdzel & van der Gaag 2000) AND a sensitivity: swept from
near-deterministic (90/9/1) to barely informative (50/35/15), the worst rank
correlation against the shipped values is 0.99869 and the largest change in
any center's p24 is 0.019.

A citation and a sensitivity are different claims — a cited constant can
still dominate a model. These pin the second one.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "docs-site" / "static" / "data" / "cpt-discretization.json"

# Anchored to what the project has already measured about its own uncertainty:
# #309 put the recoverable ranking ceiling at rho ~= 0.92, and #311 measured
# that intervals needed 1.25x widening. A perturbation inside that cannot be
# what a user should worry about.
RHO_FLOOR = 0.99
DELTA_CEILING = 0.05


@pytest.fixture(scope="module")
def doc():
    if not ARTIFACT.exists():
        pytest.skip("cpt-discretization.json not generated")
    return json.loads(ARTIFACT.read_text())


def test_shipped_values_are_unchanged():
    """The sensitivity was measured against these specific values. If they
    change, the measurement no longer describes what ships."""
    from services.bbn_parameterizer import _CPT_MEDIUM, _CPT_STRONG, _CPT_WEAK
    assert _CPT_STRONG == [0.70, 0.25, 0.05]
    assert _CPT_MEDIUM == [0.15, 0.70, 0.15]
    assert _CPT_WEAK == [0.05, 0.25, 0.70]


def test_each_vector_is_a_distribution():
    from services.bbn_parameterizer import _CPT_MEDIUM, _CPT_STRONG, _CPT_WEAK
    for name, vec in (("strong", _CPT_STRONG), ("medium", _CPT_MEDIUM),
                      ("weak", _CPT_WEAK)):
        assert abs(sum(vec) - 1.0) < 1e-9, f"{name} sums to {sum(vec)}"
        assert all(v > 0 for v in vec), f"{name} has a zero — no misclassification floor"


def test_the_split_is_still_not_load_bearing(doc):
    """The finding. If a model change makes the discretization matter, #213
    has to be re-opened rather than left closed on a stale measurement."""
    s = doc["summary"]
    assert s["worst_spearman_vs_shipped"] > RHO_FLOOR, (
        f"the discretization now moves rankings (worst rho "
        f"{s['worst_spearman_vs_shipped']}) — re-open #213")
    assert s["worst_max_abs_delta_p24"] < DELTA_CEILING, (
        f"the discretization now moves p24 by "
        f"{s['worst_max_abs_delta_p24']} — re-open #213")


def test_the_sweep_was_wide_enough_to_be_meaningful(doc):
    """A 'no effect' result proves nothing if the perturbation was tiny. The
    sweep must span genuinely different discretizations."""
    variants = {c["variant"] for c in doc["comparisons"]}
    assert any("90/9/1" in v for v in variants), "missing the sharp extreme"
    assert any("50/35/15" in v for v in variants), "missing the soft extreme"
    assert doc["summary"]["comparisons_run"] >= 16, (
        f"only {doc['summary']['comparisons_run']} comparisons — too few "
        f"organs or granularities to generalize")


def test_both_granularities_were_covered(doc):
    grans = {c["granularity"] for c in doc["comparisons"]}
    assert grans == {"state", "full"}, (
        f"only {grans} covered; 'full' has 248 regions and is where a "
        f"discretization effect would be most visible")


def test_probabilities_stayed_valid_under_every_variant(doc):
    """A perturbation that produced out-of-range probabilities would make the
    comparison meaningless."""
    for c in doc["comparisons"]:
        assert 0 <= c["max_abs_delta_p24"] <= 1
        assert -1 <= c["spearman_vs_shipped"] <= 1
        assert c["n_centers"] >= 10
