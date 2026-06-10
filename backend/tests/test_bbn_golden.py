"""Golden-snapshot test for the BBN — Step 1.5 of the rebuild plan.

Locks the CURRENT (pre-rebuild) BBN outputs so every later numeric change
(per-organ terciles, empirical CompetingOutcome, etc.) is gated behind an
explicit, reviewed golden update rather than slipping through silently.

BBN inference is exact (no RNG), so outputs are fully deterministic and we can
compare rounded values exactly — no tolerance needed.

Covers the "classic" and "state" granularities across three organs. The 248-
region "full" granularity is deliberately excluded here: its cold build is ~63s
(see scripts/bbn-build-profile.py) and it is slated to move to a precomputed
artifact (plan §4 / Step 3); its golden is added with that work.

To regenerate after an INTENTIONAL change: delete the golden file and re-run;
review the diff before committing.
"""
import json
from pathlib import Path

import pytest

from models.schemas import PatientProfile
from services.bayesian_network import simulate_bbn

GOLDEN = Path(__file__).parent / "golden" / "bbn_baseline.json"

REFERENCE_PATIENTS = {
    "kidney_O+": dict(organ="kidney", blood_type="O+", age=50, sex="male", urgency=2, cpra=20),
    "liver_A+":  dict(organ="liver",  blood_type="A+", age=55, sex="female", urgency=3, meld=22),
    "lung_O+":   dict(organ="lung",   blood_type="O+", age=60, sex="male", urgency=2, las=50.0),
}
GRANULARITIES = ("classic", "state")


def _snapshot() -> dict:
    """Deterministic snapshot: per (patient, granularity), each center's p24
    (rounded) plus the top-5 center ranking."""
    out = {}
    for pname, kw in REFERENCE_PATIENTS.items():
        for g in GRANULARITIES:
            patient = PatientProfile(bbn_granularity=g, **kw)
            res = simulate_bbn(patient)
            p24 = {c.center_code: round(c.p_transplant_24mo, 4) for c in res.cities}
            top5 = [c.center_code for c in res.cities[:5]]
            out[f"{pname}|{g}"] = {"p24": p24, "top5": top5, "n": len(res.cities)}
    return out


def test_bbn_golden_snapshot(data):
    current = _snapshot()
    if not GOLDEN.exists():
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(current, indent=2, sort_keys=True))
        pytest.skip(f"golden baseline created at {GOLDEN} — review & commit it")

    expected = json.loads(GOLDEN.read_text())
    # Compare key-by-key for readable failures.
    assert set(current) == set(expected), "granularity/patient set changed"
    for key in expected:
        assert current[key]["n"] == expected[key]["n"], f"{key}: center count changed"
        assert current[key]["top5"] == expected[key]["top5"], f"{key}: top-5 ranking changed"
        assert current[key]["p24"] == expected[key]["p24"], f"{key}: p24 values changed"
