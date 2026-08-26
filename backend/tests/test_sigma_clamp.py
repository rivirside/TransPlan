"""The log_sigma clamp, and the censored-median reconstruction (#274).

The clamp ceiling of 1.2 binds on 5 of 6 organs, which looked like a defect
(DATA-07, high-risk). A sweep scored against observed SRTR transplant rates
showed the opposite: raising the ceiling makes calibration WORSE on every
assessable organ. These pin that finding, and pin the separate pancreas
defect it surfaced (L-080) so it cannot be quietly forgotten.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SWEEP = REPO / "docs-site" / "static" / "data" / "sigma-clamp-sweep.json"
DISTS = REPO / "data" / "wait-time-distributions.json"


@pytest.fixture(scope="module")
def sweep():
    if not SWEEP.exists():
        pytest.skip("sigma-clamp-sweep.json not generated")
    return json.loads(SWEEP.read_text())


def test_raising_the_ceiling_still_does_not_help(sweep):
    """If a data refresh or model change reverses this, the clamp decision has
    to be re-made rather than inherited."""
    regressions = []
    for organ, r in sweep["organs"].items():
        base = r["spearman_at_1_2"]
        best = r["best_spearman"]
        if base is None or best is None:
            continue
        if r["best_ceiling"] != "1.2" and best - base > 0.005:
            regressions.append((organ, r["best_ceiling"], round(best - base, 4)))
    assert not regressions, (
        f"raising the clamp now IMPROVES calibration for {regressions} — "
        f"#274 was closed on the basis that it did not. Re-open it.")


def test_the_clamp_really_does_bind(sweep):
    """The finding is only interesting because the ceiling is active. If a
    refresh drops every organ below it, the sweep stops meaning anything."""
    binding = [o for o, r in sweep["organs"].items() if r["clamp_binds_at_1_2"]]
    assert len(binding) >= 4, (
        f"only {len(binding)} organs hit the ceiling; the sweep's premise no "
        f"longer holds")


def test_unassessable_organs_say_why(sweep):
    """Pancreas and intestine have no cohort large enough to score. That must
    be stated, not shown as a blank."""
    for organ, r in sweep["organs"].items():
        if r["spearman_at_1_2"] is None:
            assert r["not_assessable_reason"], (
                f"{organ} has no metric and no explanation")
            assert r["max_observed_cohort_n"] < 25


def test_pancreas_median_defect_is_still_recorded():
    """L-080: pancreas publishes 22.8 months where SRTR's median is censored
    at >72. Deliberately NOT fixed by changing sigma — 1.2 gives 29.9, still
    wrong by >2x, and pancreas cannot be validated. This test exists so the
    number cannot drift without the limitation being revisited."""
    pancreas = json.loads(DISTS.read_text())["pancreas"]
    limitations = (REPO / "docs" / "limitations.md").read_text()
    assert "L-080" in limitations, "L-080 was removed while the defect remains"
    # If someone changes the published median, they must have addressed L-080.
    assert pancreas["national_median_months"] == 22.8, (
        "the pancreas median changed — if this was a real fix, update L-080 "
        "and this test together; if it was incidental, it is a regression")


def test_every_other_median_matches_srtr_exactly(sweep):
    """Pancreas is the only organ whose published median is a reconstruction.
    A second one appearing would mean the censored-median branch has started
    affecting more organs."""
    dists = json.loads(DISTS.read_text())
    reconstructed = [o for o, r in sweep["organs"].items() if r["median_censored"]]
    assert reconstructed == ["pancreas"], (
        f"organs with a censored median are now {reconstructed} — the "
        f"L-080 reconstruction affects more than pancreas")
