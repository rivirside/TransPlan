"""The ordered-simplex sampler must actually be uniform (L-082 remedy 2).

`scripts/run-ordinal-weight-robustness.py` rests on one mathematical claim:
sorting a Dirichlet(1,...,1) draw descending yields a uniform draw from the
ordered simplex {w1 >= ... >= wk, sum = 1}. Every number in the report is
meaningless if that is wrong, and "it looks uniform" is not a check.

It is checkable in closed form. For a uniform draw on the k-simplex, the
expected value of the i-th LARGEST component is

    E[w_(i)] = (1/k) * sum_{j=i..k} 1/j

which is exactly the rank-order-centroid formula the script already computes
for a different purpose. So the sampler and the ROC weights are two
independent routes to the same vector, and they must agree.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))


def _load():
    """Import the script by path — its filename is not a valid module name."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ordinal_robustness",
        REPO / "scripts" / "run-ordinal-weight-robustness.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sampler_mean_matches_the_closed_form_order_statistics():
    """Sample mean of the sorted draws == rank-order centroid.

    This is the load-bearing check: it would fail for a sampler that is
    ordered but not uniform (e.g. sorting a Dirichlet with non-unit
    concentration, or drawing the sorted vector by any ad-hoc construction).
    """
    mod = _load()
    rng = np.random.default_rng(12345)
    draws = mod.sample_ordered_simplex(rng, 40_000)
    observed = draws.mean(axis=0)
    expected = np.array([mod.roc_weights()[c] for c in mod.CATEGORIES])

    # Monte Carlo error at n=40k is ~1e-3 on the largest component.
    assert np.allclose(observed, expected, atol=3e-3), (
        f"sampler mean {observed.round(4)} != ROC {expected.round(4)} — "
        "the draws are ordered but not uniform on the ordered simplex"
    )


def test_sampler_is_actually_ordered_and_normalised():
    mod = _load()
    rng = np.random.default_rng(7)
    draws = mod.sample_ordered_simplex(rng, 500)
    assert np.all(np.diff(draws, axis=1) <= 1e-12), "rows are not descending"
    assert np.allclose(draws.sum(axis=1), 1.0)
    assert np.all(draws >= 0)


def test_a_non_uniform_sampler_would_be_caught():
    """Negative control for the test above.

    Dirichlet(5,...,5) sorted descending is ordered, normalised, and looks
    entirely plausible — but it is concentrated near the centre of the simplex
    and so is NOT uniform on the ordered region. If the closed-form check
    cannot tell the two apart, it is not testing anything.
    """
    mod = _load()
    rng = np.random.default_rng(99)
    draws = -np.sort(-rng.dirichlet(np.ones(len(mod.CATEGORIES)) * 5, size=40_000), axis=1)
    expected = np.array([mod.roc_weights()[c] for c in mod.CATEGORIES])
    assert not np.allclose(draws.mean(axis=0), expected, atol=3e-3)


def test_ordering_guard_fires_when_default_weights_are_reordered(monkeypatch):
    """The script's premise is that DEFAULT_WEIGHTS is descending."""
    mod = _load()
    monkeypatch.setitem(mod.DEFAULT_WEIGHTS, "socioeconomic", 0.99)
    with pytest.raises(SystemExit, match="no longer in descending order"):
        mod._assert_ordering_holds()


# ── Pin the published findings (L-082 sharpening / L-083) ──────────────────

ARTIFACT = REPO / "docs-site" / "static" / "data" / "ordinal-weight-robustness.json"


@pytest.fixture(scope="module")
def report():
    if not ARTIFACT.exists():
        pytest.skip("ordinal-weight-robustness.json not generated")
    return json.loads(ARTIFACT.read_text())["organs"]


def test_magnitudes_alone_do_not_move_the_ranking(report):
    """The headline sharpening of L-082.

    Holding the category ORDERING fixed and letting the magnitudes range over
    everything that ordering permits leaves the ranking nearly unchanged. The
    contrast that matters is against L-082's 0.624, which was measured while
    REORDERING the categories. If this drifts down toward 0.624 the two
    findings have collapsed into one and L-082's retargeting is wrong.
    """
    worst = min(r["rho_vs_shipped_min"] for r in report.values())
    assert worst > 0.85, (
        f"worst rho holding the ordering fixed is {worst}, approaching "
        "L-082's reorder-driven 0.624 — the claim that the uncited "
        "MAGNITUDES are not load-bearing no longer holds; re-run "
        "scripts/run-ordinal-weight-robustness.py and revisit L-082")


def test_ordering_alone_reproduces_the_shipped_top_center(report):
    """Rank-order centroid uses no magnitude information at all."""
    for organ, r in report.items():
        assert r["roc_top_center"] == r["shipped_top_center"], (
            f"{organ}: ROC (ordering only) picks {r['roc_top_center']} but "
            f"the shipped weights pick {r['shipped_top_center']} — the "
            "shipped magnitudes are no longer unremarkable for their "
            "ordering; revisit L-082")
        assert r["roc_rho_vs_shipped"] > 0.95, organ


def test_lung_top_center_is_a_near_tie(report):
    """L-083: high rho does not mean the top is determined.

    Pinned as a POSITIVE assertion of the defect so the disclosure and the
    measurement cannot drift apart: if lung's leader becomes determinate,
    L-083 should be closed rather than left standing.
    """
    lung = report["lung"]
    assert lung["shipped_top_center_share"] < 0.5, (
        f"lung's top center now leads {lung['shipped_top_center_share']} of "
        "draws — the near-tie L-083 documents may be resolved; recheck it")
    assert lung["distinct_top_centers"] >= 5
    # The point of L-083 is the DIVERGENCE: aggregate stability stays high
    # while the top is undetermined.
    assert lung["rho_vs_shipped_median"] > 0.95


def test_organs_with_a_determinate_top_are_still_determinate(report):
    """The other half of L-083 — the contrast is what makes it actionable."""
    for organ in ("kidney", "heart"):
        assert report[organ]["shipped_top_center_share"] >= 0.95, (
            f"{organ} used to have a fully determinate top center; it no "
            "longer does, which widens L-083 beyond lung")
