"""Small-cohort center factors are shrunk, not clamp-pinned (L-086 / #268).

Before #268 these tests asserted the DEFECT: per-center risk factors were used
at face value regardless of cohort size, so a tiny cohort produced an extreme
rate, the [0.3, 3.0] clamp pinned it to the most favourable bound, and the
center rose into the top 10. Every center with n <= 10 sat on a bound — kidney
11/11, liver 12/12, heart 20/20 — and the pinning was asymmetric (60 kidney
centers at the favourable bound against 2 at the unfavourable one), so noise
systematically promoted small programs.

Empirical-Bayes shrinkage now runs BEFORE the clamp in
`scripts/parse-srtr-reports.py`, with strength estimated per organ. These
tests assert the fixed state and would fail if the shrinkage were removed or
regressed.

Fixed for KIDNEY ONLY, and the tests say so. In a controlled comparison with
all six organs recomputed in both arms, shrinkage degraded heart (-0.0342) and
liver (-0.0119) Spearman against observed SRTR transplant rates — and it
degraded them on the n>=10 subset too (-0.0222, -0.0103), so this is a real
loss among well-measured centers rather than the metric rewarding reproduction
of small-cohort noise. Lung, pancreas and intestine are not estimable at all.

Kidney is where the defect matters most (232 centers, ~17,000 transplants a
year), but the other five retain it, and `test_excluded_organs_are_still_pinned`
holds that line rather than letting this file imply a clean sweep.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CLAMP_LO, CLAMP_HI = 0.3, 3.0

SHRUNK = ("kidney",)      # the only organ where shrinkage passed the calibration gate
EXCLUDED = ("liver", "heart", "lung", "pancreas", "intestine")


@pytest.fixture(scope="module")
def factors():
    return json.loads((REPO / "data" / "competing-risks-centers.json").read_text())


@pytest.fixture(scope="module")
def cohorts():
    return json.loads((REPO / "data" / "srtr-observed-rates.json").read_text())


def _pairs(factors, cohorts, organ):
    out = []
    for code, per_organ in factors["center_adjustments"].items():
        f = (per_organ or {}).get(organ, {}).get("mortality_factor")
        rec = (cohorts.get(organ) or {}).get("centers", {}).get(code)
        if f is not None and rec and rec.get("n"):
            out.append((code, f, rec["n"]))
    return out


@pytest.mark.parametrize("organ", SHRUNK)
def test_tiny_cohort_centers_are_no_longer_pinned(factors, cohorts, organ):
    """The headline fix: n <= 10 centers come off the clamp bounds."""
    tiny = [(c, f, n) for c, f, n in _pairs(factors, cohorts, organ) if n <= 10]
    assert tiny, f"{organ}: no centers with n<=10 — the cohort data changed"
    pinned = [(c, f, n) for c, f, n in tiny if f in (CLAMP_LO, CLAMP_HI)]
    assert not pinned, (
        f"{organ}: {len(pinned)} of {len(tiny)} tiny-cohort centers are back on "
        f"a clamp bound: {pinned[:3]}. Shrinkage must run BEFORE the clamp — "
        "after it, the clamp has already replaced the estimate.")


@pytest.mark.parametrize("organ", SHRUNK)
def test_shrinkage_pulls_small_cohorts_toward_the_mean(factors, cohorts, organ):
    """Direction check: small cohorts should now sit closer to 1.0 than large ones.

    Before the fix this correlation was NEGATIVE (-0.34 for kidney): small
    cohorts deviated most, which is the noise signature. After shrinking it
    inverts, because small centers are pulled to the mean while large ones keep
    their own estimate.
    """
    import numpy as np
    pairs = _pairs(factors, cohorts, organ)
    f = np.array([p[1] for p in pairs])
    n = np.array([p[2] for p in pairs], dtype=float)
    corr = float(np.corrcoef(np.abs(f - 1.0), n)[0, 1])
    assert corr > 0.05, (
        f"{organ}: corr(|f-1|, n) is {corr:.3f}; small cohorts still deviate "
        "as much as large ones, so shrinkage is not being applied")


def test_the_favourable_bound_is_no_longer_crowded(factors, cohorts):
    """60 kidney / 39 liver / 64 heart centers used to sit on 0.3."""
    for organ in SHRUNK:
        lo = sum(1 for _, f, _ in _pairs(factors, cohorts, organ) if f == CLAMP_LO)
        assert lo == 0, (
            f"{organ}: {lo} centers are pinned to the favourable bound; before "
            "#268 this asymmetry is what promoted small programs")


def test_shrinkage_is_recorded_in_the_artifact(factors):
    """The strength must be auditable, not silently baked into the numbers."""
    meta = factors["_meta"].get("shrinkage")
    assert meta, "_meta.shrinkage missing — the applied strength is unauditable"
    for organ in SHRUNK:
        assert meta[organ]["shrunk"] is True, organ
        w = meta[organ]["median_weight_mortality"]
        assert 0.10 <= w <= 0.95, f"{organ}: median weight {w} outside the sane band"
    for organ in EXCLUDED:
        assert meta[organ]["shrunk"] is False, (
            f"{organ} is now being shrunk — it was excluded because its panel is "
            "too small for a trustworthy tau^2; recheck calibration first")


@pytest.mark.parametrize("organ", ["liver", "heart", "lung"])
def test_excluded_organs_are_still_pinned(factors, cohorts, organ):
    """Held deliberately: the fix is partial and should not read as complete.

    Lung keeps the L-086 defect because shrinking it made the model worse. If
    someone later finds a way to shrink lung safely, this test fails and the
    limitation should be updated rather than the exclusion quietly widened.
    """
    tiny = [(c, f, n) for c, f, n in _pairs(factors, cohorts, organ) if n <= 10]
    assert tiny, f"{organ}: no tiny-cohort centers found"
    pinned = [t for t in tiny if t[1] in (CLAMP_LO, CLAMP_HI)]
    assert pinned, (
        f"{organ}: tiny cohorts are no longer pinned. If that is a real "
        "improvement, update L-086 and move this organ into SHRUNK.")
