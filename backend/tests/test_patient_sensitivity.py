"""Which patient inputs reach the ranking (L-085).

Pinned as POSITIVE assertions of the current behaviour, so that if the model
gains an ABO-by-center interaction (#390) these fail and L-085 gets closed
rather than left standing as a stale disclosure.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "docs-site" / "static" / "data" / "patient-sensitivity.json"


@pytest.fixture(scope="module")
def report():
    if not ARTIFACT.exists():
        pytest.skip("patient-sensitivity.json not generated")
    return json.loads(ARTIFACT.read_text())["organs"]


def test_blood_type_cannot_reorder_centers_in_any_organ(report):
    """The headline: the ordering is byte-identical between O- and AB+."""
    for organ, r in report.items():
        bt = r["attributes"]["blood_type"]
        assert bt["identical_order"], (
            f"{organ}: blood type now reorders centers — L-085 should be "
            "revisited and possibly closed")
        assert bt["spearman"] == 1.0
        assert list(bt["categories_reached"]) == ["medicalCompatibility"], (
            f"{organ}: blood type now reaches "
            f"{list(bt['categories_reached'])} — it used to reach only the "
            "center-invariant sub-score, which is why it could not reorder")


def test_the_only_channel_blood_type_has_is_the_inert_one(report):
    """Ties L-085 to L-084 — the mechanism, not just the symptom.

    Blood type cannot reorder because its single channel is the sub-score that
    is identical at every center. If either half changes, the explanation in
    docs/patient-sensitivity-report.md stops being true.
    """
    variance = REPO / "docs-site" / "static" / "data" / "category-variance.json"
    if not variance.exists():
        pytest.skip("category-variance.json not generated")
    cv = json.loads(variance.read_text())["organs"]
    for organ, r in report.items():
        if organ not in cv:
            continue
        channel = list(r["attributes"]["blood_type"]["categories_reached"])
        assert channel == ["medicalCompatibility"]
        assert cv[organ]["categories"]["medicalCompatibility"]["inert"], (
            f"{organ}: medicalCompatibility now varies between centers, so "
            "blood type has gained a real channel — recheck L-084 and L-085")


def test_severity_measures_do_reorder(report):
    """The contrast that makes the finding actionable rather than trivia.

    If NOTHING reordered, the ranking would simply be patient-independent and
    there would be no inconsistency to report. The point is that some
    immunological/severity inputs interact with centers and blood type does not.
    """
    reordering = {
        "kidney": "cpra",
        "liver": "meld",
        "lung": "las",
    }
    for organ, attr in reordering.items():
        if organ not in report:
            continue
        e = report[organ]["attributes"][attr]
        assert not e["identical_order"], f"{organ}/{attr} no longer reorders"
        assert e["spearman"] < 0.99, (
            f"{organ}/{attr} spearman {e['spearman']} — the asymmetry with "
            "blood type documented in L-085 has narrowed")


def test_cpra_and_blood_type_are_treated_asymmetrically(report):
    """The specific inconsistency L-085 names, pinned as a number."""
    cpra = report["kidney"]["attributes"]["cpra"]
    bt = report["kidney"]["attributes"]["blood_type"]
    assert cpra["spearman"] < 0.85 and bt["spearman"] == 1.0, (
        "cPRA and blood type are no longer treated asymmetrically — both are "
        "immunological access constraints, so this converging is GOOD news "
        "and means L-085's central complaint is resolved")


def test_inputs_that_reach_nothing_are_still_recorded(report):
    """Collected-and-discarded fields, pinned so the list cannot rot silently."""
    discarded = {(o, a) for o, r in report.items()
                 for a, e in r["attributes"].items() if e["reaches_nothing"]}
    # Known at the time of writing; a change either way should be deliberate.
    assert ("kidney", "sex") in discarded
    assert ("liver", "urgency") in discarded, (
        "liver urgency now reaches a sub-score — liver is MELD-driven, so if "
        "this changed, docs/patient-sensitivity-report.md needs updating")


# ── Simulation path (present only when the artifact was built with it) ──────

def _sim(report, organ, attr):
    e = report.get(organ, {}).get("attributes", {}).get(attr, {})
    s = e.get("simulation")
    if s is None:
        pytest.skip("artifact built without --with-simulation")
    return s


def test_blood_type_moves_magnitudes_but_not_the_ranking(report):
    """The one-line finding, pinned on the engine where blood type DOES work.

    A large shift with an unchanged ordering is the whole point; if the shift
    ever vanished, blood type would be broken rather than merely uninfluential
    on rank, and that is a different (worse) bug.
    """
    s = _sim(report, "kidney", "blood_type")
    assert s["mean_p24_shift"] > 0.15, (
        f"blood type now shifts kidney p24 by only {s['mean_p24_shift']} — it "
        "used to be a large, correct effect; check the simulation path")
    assert s["spearman"] > 0.99, (
        "blood type now reorders centers in simulation — L-085 should be "
        "revisited")


def test_sex_changes_no_output_at_all_for_some_organs(report):
    """Required form fields that move nothing, in either engine."""
    for organ in ("liver", "heart", "lung"):
        s = _sim(report, organ, "sex")
        assert s["mean_p24_shift"] == 0.0, (
            f"{organ}: sex now moves p24 by {s['mean_p24_shift']} — it used to "
            "change no output at all, so L-085's 'required field that changes "
            "nothing' claim needs updating")


def test_the_two_engines_disagree_about_cpra(report):
    """Scoring and simulation give different answers to the same question.

    Both are surfaced to users in the same results table, so a large gap is
    itself worth tracking rather than being averaged away.
    """
    scoring_rho = report["kidney"]["attributes"]["cpra"]["spearman"]
    sim_rho = _sim(report, "kidney", "cpra")["spearman"]
    assert sim_rho - scoring_rho > 0.15, (
        f"the scoring/simulation gap on cPRA has closed (scoring {scoring_rho}, "
        f"simulation {sim_rho}) — good news, and L-085 should say so")
