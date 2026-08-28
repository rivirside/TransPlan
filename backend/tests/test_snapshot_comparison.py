"""#137: the cross-iteration comparator, and the two silent zeros it had.

The snapshot half of #137 shipped and works. Nothing ever consumed the
snapshots, so model drift between iterations was captured and never measured
— and in that unexercised state two defects accumulated, both of the same
shape: a number that means "could not compare" being reported as 0.

  1. The extractor read `competing_risks["p_transplant"]`, but the keys carry
     a `_24mo` suffix. Every snapshot recorded 0/0/0, so the tool built to
     detect drift was structurally blind to competing-risk drift.
  2. The first version of the comparator (written in this same change) then
     reported `max_abs_delta_competing_risk: 0.0` when two snapshots used
     different key names — reproducing the bug one layer up.

Validated end to end against a known change: two snapshots differing only in
whether Rh is live (#413) move `liver/O-` on all three engines and nothing
else on Monte Carlo or MCMC, while three Rh-POSITIVE profiles move on the
BBN alone — the DonorSupply tercile coupling documented in L-088.
"""
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "snapshot-model-outputs.py"


@pytest.fixture(scope="module")
def snap():
    spec = importlib.util.spec_from_file_location("snapshot_model_outputs", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _snapshot(label, p24_by_center, cr_keys=("p_transplant_24mo",)):
    cities = {
        name: {
            "p_transplant_24mo": p,
            "median_wait_months": 10.0,
            "competing_risks": {k: 0.5 for k in cr_keys},
            "ci_95": [max(0.0, p - 0.05), min(1.0, p + 0.05)],
        }
        for name, p in p24_by_center.items()
    }
    return {
        "_meta": {"label": label, "git": {"commit": "deadbeef"}, "seed": 1},
        "profiles": [{
            "patient": {"organ": "kidney", "blood_type": "O+", "age": 45,
                        "sex": "male", "urgency": 2},
            "engines": {"monte_carlo": {"cities": cities}},
            "deterministic_scores": {},
        }],
    }


BASE = {"Alpha": 0.80, "Bravo": 0.60, "Charlie": 0.40, "Delta": 0.20}


def test_a_snapshot_compared_to_itself_reports_no_drift(snap):
    """The vacuity guard. A comparator that always reports change is as
    useless as one that never does."""
    a = _snapshot("x", BASE)
    r = snap.compare_snapshots(a, json.loads(json.dumps(a)))
    assert r["summary"]["engine_runs_compared"] == 1
    assert r["summary"]["engine_runs_that_moved"] == 0
    assert r["summary"]["largest_p24_shift"] == 0.0
    assert "No drift" in snap.render_comparison(r)


def test_a_real_change_is_detected_and_quantified(snap):
    moved = dict(BASE, Charlie=0.95)          # Charlie jumps to the top
    r = snap.compare_snapshots(_snapshot("old", BASE), _snapshot("new", moved))
    m = r["by_profile"][0]["engines"]["monte_carlo"]
    assert m["max_abs_delta_p24"] == pytest.approx(0.55)
    assert m["top_center_changed"] is True
    assert m["top_center"] == {"from": "Alpha", "to": "Charlie"}
    assert m["spearman"] < 1.0


def test_reordering_without_magnitude_change_still_shows_in_spearman(snap):
    swapped = {"Alpha": 0.60, "Bravo": 0.80, "Charlie": 0.40, "Delta": 0.20}
    r = snap.compare_snapshots(_snapshot("old", BASE), _snapshot("new", swapped))
    m = r["by_profile"][0]["engines"]["monte_carlo"]
    assert m["spearman"] < 1.0
    assert m["top_center_changed"] is True


def test_incomparable_competing_risk_keys_report_none_not_zero(snap):
    """The bug this file exists to prevent. Different key sets mean the
    fields could not be compared — reporting 0.0 would read as 'measured,
    unchanged' and hide exactly what the tool is for."""
    old = _snapshot("old", BASE, cr_keys=("p_transplant",))          # legacy
    new = _snapshot("new", BASE, cr_keys=("p_transplant_24mo",))     # current
    m = snap.compare_snapshots(old, new)["by_profile"][0]["engines"]["monte_carlo"]
    assert m["competing_risk_fields_compared"] == 0
    assert m["max_abs_delta_competing_risk"] is None
    assert "n/a" in snap.render_comparison(snap.compare_snapshots(old, new))


def test_comparable_competing_risks_are_actually_measured(snap):
    old = _snapshot("old", BASE)
    new = json.loads(json.dumps(old))
    new["_meta"]["label"] = "new"
    cities = new["profiles"][0]["engines"]["monte_carlo"]["cities"]
    cities["Alpha"]["competing_risks"]["p_transplant_24mo"] = 0.9
    m = snap.compare_snapshots(old, new)["by_profile"][0]["engines"]["monte_carlo"]
    assert m["competing_risk_fields_compared"] == 4
    assert m["max_abs_delta_competing_risk"] == pytest.approx(0.4)


def test_the_extractor_refuses_to_invent_zeros(snap):
    """`_competing_risks` must raise on the legacy key names rather than
    silently recording 0.0 for every center, as it did until #137."""
    class FakeCity:
        center_code = "TEST"
        competing_risks = {"p_transplant": 0.7}   # legacy names

    with pytest.raises(KeyError, match="p_transplant_24mo"):
        snap._competing_risks(FakeCity())


def test_profiles_present_in_only_one_snapshot_are_reported(snap):
    old = _snapshot("old", BASE)
    new = _snapshot("new", BASE)
    new["profiles"][0]["patient"]["organ"] = "liver"
    r = snap.compare_snapshots(old, new)
    assert r["profiles_compared"] == 0
    assert len(r["profiles_only_in_one"]) == 2
    assert "NOT COMPARABLE" in snap.render_comparison(r)


def test_spearman_handles_ties(snap):
    """Averaging ties matters: without it, a near-constant vector produces a
    correlation that is an artifact of input order."""
    assert snap._spearman([1, 1, 1, 1], [4, 3, 2, 1]) == pytest.approx(1.0)
    assert snap._spearman([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
    assert snap._spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)


def test_snapshots_record_the_seed_they_used(snap):
    """Unseeded, run-to-run noise alone moved every profile and changed the
    top center in 15 of 24 engine runs. A snapshot without a recorded seed
    cannot be trusted in a comparison."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert '"seed": args.seed' in src
    assert "--seed" in src
