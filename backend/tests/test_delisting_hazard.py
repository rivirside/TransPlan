"""Observed delisting hazard vs the shipped WaitCategory multipliers (#297).

`build_delisting_risk_cpt` uses wait_delist_mults = [0.5, 0.8, 1.2, 1.8],
encoding a single monotonic RISE applied to every organ. Measured from SRTR's
6/12/18-month national removal counts, the hazard falls with time on the list
for liver, heart, lung and intestine — the shipped values have the wrong SIGN
for four of six organs.

The multipliers are deliberately NOT changed here (see the report): the CPT
is a discretized tercile summary rather than a hazard model, so a like-for-
like substitution is not automatic and has to clear the calibration gate.
These tests pin the measurement so the discrepancy cannot be forgotten and
cannot silently change.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "docs-site" / "static" / "data" / "delisting-hazard.json"


@pytest.fixture(scope="module")
def doc():
    if not ARTIFACT.exists():
        pytest.skip("delisting-hazard.json not generated")
    return json.loads(ARTIFACT.read_text())


def test_shipped_multipliers_are_unchanged(doc):
    """If someone edits wait_delist_mults, this fails and they must revisit
    the measurement rather than changing the numbers in isolation."""
    from services.bbn_parameterizer import build_delisting_risk_cpt  # noqa: F401
    src = (REPO / "backend" / "services" / "bbn_parameterizer.py").read_text()
    assert "wait_delist_mults = [0.5, 0.8, 1.2, 1.8]" in src, (
        "the delisting multipliers changed — re-run "
        "scripts/run-delisting-hazard-fit.py and update the report and #297")
    assert doc["current_multipliers"] == [0.5, 0.8, 1.2, 1.8]


def test_hazard_direction_disagrees_for_several_organs(doc):
    """The substantive finding. If a data refresh reverses it, the conclusion
    in the report and in #297 no longer holds."""
    falling = [o for o, r in doc["organs"].items()
               if r.get("assessable")
               and r["hazard_ratio_vs_first_6mo"]["12-18"] < 0.95]
    assert len(falling) >= 3, (
        f"only {falling} show a falling hazard; the report claims the shipped "
        f"multipliers have the wrong sign for several organs")


def test_kidney_still_rises(doc):
    """Kidney is the organ the shipped direction actually fits — it is what
    makes 'one set of multipliers cannot serve every organ' true rather than
    'the multipliers are simply backwards'."""
    k = doc["organs"]["kidney"]["hazard_ratio_vs_first_6mo"]
    assert k["6-12"] > 1.0 and k["12-18"] > k["6-12"]


def test_hazards_are_positive_and_finite(doc):
    for organ, r in doc["organs"].items():
        if not r.get("assessable"):
            continue
        for interval, h in r["monthly_hazard"].items():
            assert h > 0 and h < 1, f"{organ} {interval} hazard {h} implausible"


def test_cumulative_removals_are_monotone(doc):
    """A cumulative share that decreases with horizon would mean the columns
    were misread — the hazard maths would still produce numbers."""
    for organ, r in doc["organs"].items():
        if not r.get("assessable"):
            continue
        cum = r["cumulative_removed"]
        vals = [cum[str(m)] for m in (6, 12, 18)]
        assert vals == sorted(vals), f"{organ} cumulative removals decrease: {vals}"
        assert all(0 <= v < 1 for v in vals)


def test_band_four_is_reported_as_unmeasurable(doc):
    """>24 months lies beyond every published horizon. Claiming a measured
    value for it would be the failure mode this report exists to avoid."""
    assert "beyond every published horizon" in doc["_meta"]["coverage"]
    for r in doc["organs"].values():
        if r.get("assessable"):
            assert "18-24" not in r["monthly_hazard"]
            assert "24+" not in r["monthly_hazard"]
