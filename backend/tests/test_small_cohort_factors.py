"""Small-cohort centers are pinned to a clamp bound and ranked high (L-086).

Per-center risk factors are applied at face value regardless of the cohort
they were estimated from. A tiny cohort gives an extreme rate, the factor is
clamped into 0.3-3.0, and a center pinned to 0.3 — the most favourable value
available — ranks near the top of the list.

Pinned as a POSITIVE assertion of the defect: if shrinkage lands (#268) these
fail, and L-086 should be closed rather than left standing as stale prose.

Note what a conventional check would NOT catch here. Shrinkage moves mean p24
by <=0.005 and leaves rank correlation at 0.987-0.999. Only top-10 membership
moves, by 40% for kidney. #294's sweep reported worst rho 0.973 and passed.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CLAMP_LO, CLAMP_HI = 0.3, 3.0


@pytest.fixture(scope="module")
def factors():
    return json.loads((REPO / "data" / "competing-risks-centers.json").read_text())["center_adjustments"]


@pytest.fixture(scope="module")
def cohorts():
    return json.loads((REPO / "data" / "srtr-observed-rates.json").read_text())


def _pairs(factors, cohorts, organ):
    out = []
    for code, per_organ in factors.items():
        f = (per_organ or {}).get(organ, {}).get("mortality_factor")
        rec = (cohorts.get(organ) or {}).get("centers", {}).get(code)
        if f is None or not rec or not rec.get("n"):
            continue
        out.append((code, f, rec["n"]))
    return out


@pytest.mark.parametrize("organ", ["kidney", "liver", "heart"])
def test_every_tiny_cohort_center_sits_on_a_clamp_bound(factors, cohorts, organ):
    """The mechanism: n<=10 means the factor carries no information at all,
    only which bound the noise pushed it against."""
    pairs = _pairs(factors, cohorts, organ)
    tiny = [(c, f, n) for c, f, n in pairs if n <= 10]
    assert tiny, f"{organ}: no centers with n<=10 — the cohort data changed"
    off_bound = [(c, f, n) for c, f, n in tiny if f not in (CLAMP_LO, CLAMP_HI)]
    assert not off_bound, (
        f"{organ}: {len(off_bound)} of {len(tiny)} tiny-cohort centers are no "
        f"longer pinned to a clamp bound: {off_bound[:3]}. If shrinkage "
        "landed, close L-086.")


def test_the_favourable_bound_is_the_common_one(factors, cohorts):
    """Pinning is asymmetric, which is why it inflates rather than cancels.

    Far more centers sit at the FAVOURABLE bound than the unfavourable one, so
    the noise systematically promotes small centers up the ranking instead of
    scattering them both ways.
    """
    for organ in ("kidney", "liver", "heart"):
        vals = [f for _, f, _ in _pairs(factors, cohorts, organ)]
        lo = sum(1 for v in vals if v == CLAMP_LO)
        hi = sum(1 for v in vals if v == CLAMP_HI)
        assert lo > hi, (
            f"{organ}: {lo} at the favourable bound vs {hi} at the "
            "unfavourable one — the asymmetry L-086 describes has changed")


def test_factor_deviation_is_driven_by_cohort_size(factors, cohorts):
    """The statistical claim behind L-086, checked rather than asserted.

    If the factors were real signal, deviation from 1.0 would be unrelated to
    cohort size. It correlates negatively: smaller cohorts deviate more.
    """
    import numpy as np
    for organ in ("kidney", "liver", "heart", "lung"):
        pairs = _pairs(factors, cohorts, organ)
        if len(pairs) < 30:
            continue
        f = np.array([p[1] for p in pairs])
        n = np.array([p[2] for p in pairs], dtype=float)
        corr = float(np.corrcoef(np.abs(f - 1.0), n)[0, 1])
        assert corr < -0.15, (
            f"{organ}: corr(|f-1|, n) is {corr:.3f}; the small-cohort noise "
            "signature L-086 rests on has weakened — recheck the finding")


def test_pancreas_is_excluded_from_that_claim(factors, cohorts):
    """Recorded because it is a counter-example, not an oversight.

    Pancreas inverts the correlation. Its median cohort is 3, so the
    small/large split carries no information and it must not be shrunk on this
    evidence — a reader should not apply L-086's remedy to it blindly.
    """
    import numpy as np
    pairs = _pairs(factors, cohorts, "pancreas")
    if len(pairs) < 30:
        pytest.skip("too few pancreas centers to assess")
    n = np.array([p[2] for p in pairs], dtype=float)
    assert np.median(n) <= 10, (
        "pancreas cohorts have grown; the exclusion in L-086 may no longer "
        "be warranted")
