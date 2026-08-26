"""Per-organ waitlist composition weights for equity (#337).

EQSP-31 weighted the 48 equity cells with a single all-organ guess
(11/38/51 age, 60/40 sex) and EQSP-32 used US general-population blood-type
prevalence. SRTR publishes the actual per-organ waitlist composition, and it
differs where it matters: type B is over-represented on the kidney waitlist
and faces among the longest waits, so general-population weighting
understated the very disparity the analysis measures.
"""
import pytest

from services.equity import (AGE_BRACKETS, BLOOD_TYPES, SEXES,
                             _profile_weight, waitlist_weights)


@pytest.fixture(autouse=True)
def _load(data):
    pass


def test_weights_come_from_srtr_not_the_fallback():
    for organ in ("kidney", "liver", "heart", "lung"):
        w = waitlist_weights(organ)
        assert w["source"] == "srtr_waitlist_composition", (
            f"{organ} fell back to general-population weights")


def test_each_dimension_is_a_distribution():
    for organ in ("kidney", "liver", "heart", "lung", "pancreas", "intestine"):
        w = waitlist_weights(organ)
        for dim in ("blood_type", "age", "sex"):
            total = sum(w[dim].values())
            assert abs(total - 1.0) < 0.02, f"{organ}.{dim} sums to {total}"


def test_every_matrix_cell_has_a_nonzero_weight():
    """A missing key would silently zero-weight a demographic cell, which
    reads as 'nobody like this is listed' rather than as a data gap."""
    w = waitlist_weights("kidney")
    for bt in BLOOD_TYPES:
        for ab in AGE_BRACKETS:
            for sex in SEXES:
                weight = _profile_weight(bt, ab["label"], sex, None, w)
                assert weight > 0, f"zero weight for {bt}/{ab['label']}/{sex}"


def test_type_b_is_weighted_higher_than_general_population():
    """The substantive point of #337."""
    from services.equity import BLOOD_TYPE_PREVALENCE
    w = waitlist_weights("kidney")
    assert w["blood_type"]["B+"] > BLOOD_TYPE_PREVALENCE["B+"] * 1.2, (
        f"kidney waitlist B+ weight {w['blood_type']['B+']} should exceed the "
        f"general-population {BLOOD_TYPE_PREVALENCE['B+']}")


def test_composition_varies_by_organ():
    """A single global mix cannot fit every organ — that was the defect."""
    kidney = waitlist_weights("kidney")
    pancreas = waitlist_weights("pancreas")
    heart = waitlist_weights("heart")
    assert pancreas["age"]["18-34"] > 2 * kidney["age"]["18-34"]
    assert heart["sex"]["male"] > pancreas["sex"]["male"] + 0.15


def test_age_brackets_match_the_weight_keys():
    """Brackets are unions of SRTR's published bands; if a label is renamed
    without updating the parser, every age weight silently becomes zero."""
    labels = {b["label"] for b in AGE_BRACKETS}
    for organ in ("kidney", "heart"):
        assert set(waitlist_weights(organ)["age"]) == labels


def test_missing_data_falls_back_rather_than_zero_weighting():
    from services.data_loader import get_data
    saved = get_data().waitlist_composition
    try:
        get_data().waitlist_composition = {}
        w = waitlist_weights("kidney")
        assert w["source"] == "fallback_general_population"
        assert abs(sum(w["age"].values()) - 1.0) < 0.02
    finally:
        get_data().waitlist_composition = saved
