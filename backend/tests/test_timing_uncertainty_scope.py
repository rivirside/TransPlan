"""#296 / #226: the wait-timing uncertainty the reported interval leaves out.

Measured 2026-08-28 (docs/timing-uncertainty-report.md). The lognormal sigma
is clamped to [0.3, 1.2]; recomputing the same strategy chain unclamped from
the shipped SRTR percentiles gives 2.529 for kidney, so the model uses less
than half the spread its own data implies. Moving sigma across that band
shifts mean kidney p24 by 0.0968 — **0.56x the width of the interval the app
reports** — and the interval does not include any of it.

It is deliberately NOT folded in: #274 measured that raising the clamp
degrades calibration, so the two endpoints are not equally credible and the
band is not a sampling distribution. Turning it into a variance needs a prior
over sigma, which is a modelling judgement, not arithmetic.

These tests pin the two facts the finding rests on, so it cannot rot quietly.
"""
import json
from pathlib import Path

import pytest

from models.schemas import PatientProfile

REPO = Path(__file__).resolve().parents[2]

# Recomputed unclamped from the shipped percentiles via the same strategy
# chain (P10-P25). Kept as data so a clamp change makes the gap visible.
RAW_SIGMA = {
    "kidney": 2.529, "liver": 1.509, "heart": 1.509,
    "lung": 1.142, "pancreas": 2.247, "intestine": 2.121,
}
CLAMPED_ORGANS = ("kidney", "liver", "heart", "intestine")


@pytest.fixture(scope="module")
def shipped():
    return json.loads((REPO / "data" / "wait-time-distributions.json").read_text())


def test_the_sigma_clamp_is_still_binding(shipped):
    """The band exists only because the clamp bites. If it stops biting, the
    measured spread no longer applies and the report needs redoing."""
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    from srtr_xls_utils import SIGMA_CLAMP

    lo, hi = SIGMA_CLAMP
    assert (lo, hi) == (0.3, 1.2), (
        f"the sigma clamp moved to {SIGMA_CLAMP}; docs/timing-uncertainty-"
        "report.md measured the band against [0.3, 1.2]"
    )
    for organ in CLAMPED_ORGANS:
        assert shipped[organ]["log_sigma"] == pytest.approx(hi), (
            f"{organ} is no longer pinned at the clamp ceiling — either the "
            "clamp changed or the percentiles did; re-measure before trusting "
            "the reported band"
        )


def test_lung_is_the_control_and_is_not_clamped(shipped):
    """The measurement's credibility rests on the one organ with no band
    showing no spread. If lung becomes clamped it stops being a control."""
    assert shipped["lung"]["log_sigma"] < 1.2 - 1e-9, (
        "lung is now at the clamp ceiling, so it no longer serves as the "
        "zero-spread control in the timing-uncertainty measurement"
    )
    assert shipped["lung"]["log_sigma"] == pytest.approx(RAW_SIGMA["lung"], abs=0.01)


def test_the_interval_tracks_the_point_estimate_not_sigma_uncertainty(data, monkeypatch):
    """The omission, stated precisely.

    A first version asserted the interval does not move with sigma at all.
    That is false and the test caught it: `_data_uncertainty_ci` uses
    sqrt(p(1-p)/n), so when sigma shifts p24 the binomial SE shifts too --
    99 of 233 widths moved. The interval tracks the point estimate's
    CURVATURE; it propagates no uncertainty ABOUT sigma.

    The checkable form: moving sigma across the clamp band shifts p24 far
    more than it shifts the interval. If a later change folds timing
    uncertainty into the band, the ratio collapses and this fails -- which is
    the moment to update the report and L-097 rather than leave two documents
    claiming the component is excluded.
    """
    from services import distributions, monte_carlo

    patient = PatientProfile(organ="kidney", blood_type="O+", age=50,
                             sex="male", urgency=2)

    def run(sigma=None):
        if sigma is not None:
            block = dict(distributions._DISTRIBUTIONS["kidney"])
            block["log_sigma"] = sigma
            monkeypatch.setitem(distributions._DISTRIBUTIONS, "kidney", block)
        res = monte_carlo.simulate(patient, n_iterations=1500, seed=9)
        return {c.center_code: (c.p_transplant_24mo,
                                c.confidence_interval_95[1] - c.confidence_interval_95[0])
                for c in res.cities}

    base, wide = run(), run(RAW_SIGMA["kidney"])
    shared = sorted(set(base) & set(wide))
    assert len(shared) > 100

    d_p24 = sum(abs(base[c][0] - wide[c][0]) for c in shared) / len(shared)
    d_width = sum(abs(base[c][1] - wide[c][1]) for c in shared) / len(shared)
    assert d_p24 > 3 * d_width, (
        f"sigma moved p24 by {d_p24:.4f} and the interval width by "
        f"{d_width:.4f}. The interval is now tracking sigma nearly as closely "
        "as the estimate, which would mean timing uncertainty has been folded "
        "in. Update docs/timing-uncertainty-report.md and L-097."
    )


def test_p24_itself_does_move_with_sigma(data, monkeypatch):
    """Guard the guard. The test above asserts an interval does NOT respond;
    that would also pass if sigma had stopped reaching the model at all."""
    from services import distributions, monte_carlo

    patient = PatientProfile(organ="kidney", blood_type="O+", age=50,
                             sex="male", urgency=2)
    base = {c.center_code: c.p_transplant_24mo for c in
            monte_carlo.simulate(patient, n_iterations=1500, seed=9).cities}

    block = dict(distributions._DISTRIBUTIONS["kidney"])
    block["log_sigma"] = RAW_SIGMA["kidney"]
    monkeypatch.setitem(distributions._DISTRIBUTIONS, "kidney", block)
    alt = {c.center_code: c.p_transplant_24mo for c in
           monte_carlo.simulate(patient, n_iterations=1500, seed=9).cities}

    shared = set(base) & set(alt)
    mean_shift = sum(abs(base[c] - alt[c]) for c in shared) / len(shared)
    assert mean_shift > 0.02, (
        f"sigma moved mean |delta p24| by only {mean_shift:.4f}; it was 0.0968 "
        "when measured. If sigma no longer reaches p24, the whole "
        "timing-uncertainty finding needs rechecking"
    )
