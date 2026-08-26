"""Censored national medians must be disclosed, not silently reconstructed
(#376 / L-080).

SRTR censors the pancreas national median at ">72 months" and publishes no
value, so `national_median_months` for pancreas is RECONSTRUCTED from P25.
Every other organ stores SRTR's published P50 verbatim — which is precisely
why the reconstruction was invisible: the field looks identical either way.

The value is deliberately NOT changed. Raising it toward the censored bound
measurably degrades calibration (p12 vs observed across 78 centers: 1.11x
shipped, 1.40x at a median of 72), because sigma must rise with the median
and fattens the left tail too. The fix is disclosure.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DISTS = REPO / "data" / "wait-time-distributions.json"
ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]


@pytest.fixture(scope="module")
def dists():
    return json.loads(DISTS.read_text())


def test_every_organ_declares_whether_its_median_is_censored(dists):
    """A missing flag is the failure mode this fixes — it reads as 'published'."""
    for organ in ORGANS:
        assert "median_censored" in dists[organ], (
            f"{organ} does not declare median_censored; a reconstructed median "
            f"would be indistinguishable from a published one")
        assert isinstance(dists[organ]["median_censored"], bool)


def test_pancreas_is_flagged_and_carries_provenance(dists):
    p = dists["pancreas"]
    assert p["median_censored"] is True
    assert "median_provenance" in p
    assert "RECONSTRUCTED" in p["median_provenance"]
    assert "72" in p["median_provenance"], (
        "the provenance note should state the registry's actual bound")


def test_published_organs_are_not_flagged_or_annotated(dists):
    for organ in ORGANS:
        if organ == "pancreas":
            continue
        assert dists[organ]["median_censored"] is False, f"{organ} wrongly flagged"
        assert "median_provenance" not in dists[organ], (
            f"{organ}'s median IS published; a provenance note would imply "
            f"otherwise")


def test_the_value_itself_is_unchanged(dists):
    """Disclosure, not substitution. If someone raises this toward 72 they
    must also revisit L-080 and the calibration measurement behind it."""
    assert dists["pancreas"]["national_median_months"] == 22.8, (
        "the pancreas median changed — raising it toward the censored bound "
        "was MEASURED to degrade calibration (1.11x -> 1.40x). See L-080.")


def test_provenance_tag_fires_for_the_censored_organ(data):
    from services.provenance import TAG_MEDIAN_RECONSTRUCTED, center_data_quality
    from services.data_loader import get_data
    d = get_data()
    pancreas_code = next(iter(d.centers_for_organ("pancreas")))["code"]
    assert TAG_MEDIAN_RECONSTRUCTED in center_data_quality("pancreas", pancreas_code)
    kidney_code = next(iter(d.centers_for_organ("kidney")))["code"]
    assert TAG_MEDIAN_RECONSTRUCTED not in center_data_quality("kidney", kidney_code)


def test_the_response_carries_a_wait_median_family(data):
    """The tag has to reach the API response, not just the registry."""
    from models.schemas import PatientProfile
    from services.monte_carlo import simulate
    fam = simulate(PatientProfile(organ="pancreas", blood_type="O+", age=45,
                                  sex="male", urgency=2),
                   n_iterations=200, seed=1).data_quality.get("wait_median")
    assert fam, "wait_median family missing from the response"
    assert fam["reconstructed"] > 0 and fam["published"] == 0

    fam_k = simulate(PatientProfile(organ="kidney", blood_type="O+", age=45,
                                    sex="male", urgency=2),
                     n_iterations=200, seed=1).data_quality.get("wait_median")
    assert fam_k["published"] > 0 and fam_k["reconstructed"] == 0
