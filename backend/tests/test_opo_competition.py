"""#299: an OPO-based competition measure, because the circle one predicts nothing.

Measured 2026-08-28 (docs/allocation-competition-validation.md): counting
centers within 250 nm shows no relationship with observed SRTR transplant
rates (16 tests, nothing below p 0.178), and neither does counting the
candidates inside that circle. Counting centers in the same **OPO** does —
kidney rho −0.188 (p 0.005), lung −0.361 (p 0.004), both controlling for the
center's own cohort, both surviving Bonferroni across the four organ-level
tests. UNOS region, a coarser grouping of the same centers, predicts nothing,
which is what makes it the allocation unit rather than any grouping.

The effect is small — about 3.5% of rank variance — so this exposes a better
number, not a strong one, and the disclosure stays conservative.

A location has no OPO of its own (the shipped mapping is county-based and
runtime geocoding is not available), so a query point inherits the OPO of its
nearest center for the organ. That is the OPO whose match run the patient
would actually be listed into.
"""
import pytest

from services.allocation_geography import (
    allocation_circles,
    opo_competition,
)

# A few real metros, chosen to span dense and sparse transplant geography.
PLACES = {
    "manhattan": (40.7580, -73.9855),
    "chicago": (41.8781, -87.6298),
    "billings_mt": (45.7833, -108.5007),
    "honolulu": (21.3069, -157.8583),
}


def test_a_location_gets_the_opo_of_its_nearest_center(data):
    for name, (lat, lon) in PLACES.items():
        out = opo_competition(lat, lon, "kidney")
        assert out["opo"], f"{name}: no OPO resolved"
        assert out["nearest_center"], f"{name}: no nearest center"
        assert out["centers_in_opo"] >= 1, (
            f"{name}: the nearest center is itself in the OPO, so the count "
            "can never be zero"
        )


def test_the_score_is_normalised_around_one(data):
    """Same convention as the circle score: ~1.0 is a typical location."""
    scores = [opo_competition(lat, lon, "kidney")["competition_score"]
              for lat, lon in PLACES.values()]
    assert all(s > 0 for s in scores)
    assert min(scores) < 2.5 and max(scores) > 0.2, scores


def test_dense_and_sparse_geography_differ(data):
    """Guard the guard: a score that is constant everywhere measures nothing.

    Manhattan sits in an OPO with many kidney programs; Montana's has few.
    """
    dense = opo_competition(*PLACES["manhattan"], "kidney")
    sparse = opo_competition(*PLACES["billings_mt"], "kidney")
    assert dense["centers_in_opo"] > sparse["centers_in_opo"], (
        f"NY {dense['centers_in_opo']} vs MT {sparse['centers_in_opo']} — "
        "the measure is not distinguishing transplant geography"
    )
    assert dense["competition_score"] > sparse["competition_score"]


def test_it_differs_from_the_circle_measure(data):
    """If it tracked the circle count it would inherit the circle's null.

    They must disagree somewhere, or replacing one with the other is pointless.
    """
    disagreements = 0
    for lat, lon in PLACES.values():
        circle = allocation_circles(lat, lon, "kidney")["circle_250nm"]["competition_score"]
        opo = opo_competition(lat, lon, "kidney")["competition_score"]
        if abs(circle - opo) > 0.15:
            disagreements += 1
    assert disagreements >= 2, (
        "the OPO score tracks the circle score almost everywhere, so it "
        "cannot carry the signal the circle measure lacks"
    )


@pytest.mark.parametrize("organ", ["kidney", "liver", "heart", "lung"])
def test_every_organ_resolves(data, organ):
    out = opo_competition(*PLACES["chicago"], organ)
    assert out["opo"] and out["centers_in_opo"] >= 1
    assert out["competition_score"] > 0


def test_an_organ_with_no_nearby_program_degrades_honestly(data):
    """Intestine has 21 programs nationally. A remote point may have none in
    its nearest center's OPO beyond that center itself — the function must say
    so rather than divide by zero."""
    out = opo_competition(*PLACES["billings_mt"], "intestine")
    assert out["centers_in_opo"] >= 0
    assert out["competition_score"] is None or out["competition_score"] > 0


# ── the composite consumes it (#299) ────────────────────────────────────────

def test_the_distance_score_uses_the_opo_measure(data):
    """A component measured NOT to predict has no business driving 35% of a
    displayed score. The composite now sources competition from the OPO."""
    from services.allocation_geography import distance_score
    for lat, lon in PLACES.values():
        out = distance_score(lat, lon, "kidney")
        assert out["competition_basis"] == "opo", out["competition_basis"]
        assert out["opo_competition"]["competition_score"] is not None
        # The circle figure is retained for comparison, not discarded.
        assert "circle_competition_score" in out


def test_a_sparse_location_no_longer_scores_as_competition_free(data):
    """Billings has no center within 250 nm, so the circle called it ZERO
    competition -- a perfect 100 on that component -- while the patient is
    listed into an OPO with eight competing kidney programs.

    This is the concrete failure the OPO measure exists to fix, so it is
    pinned rather than left to the correlation tables.
    """
    from services.allocation_geography import distance_score
    out = distance_score(*PLACES["billings_mt"], "kidney")
    assert out["circle_competition_score"] == 0.0, (
        "Billings now has a center within 250 nm; pick another sparse "
        "location or this test no longer demonstrates anything"
    )
    assert out["competition"] < 90, (
        f"competition scored {out['competition']} at a location the circle "
        "measure calls competition-free -- the OPO basis is not being used"
    )
    assert out["opo_competition"]["centers_in_opo"] >= 2


def test_the_circle_fallback_still_exists_for_unreachable_organs(data):
    """If an organ has no program whose OPO can be resolved, the composite
    must still produce a number rather than raising."""
    from services.allocation_geography import distance_score
    out = distance_score(*PLACES["honolulu"], "intestine")
    assert out["composite"] is not None
    assert out["competition_basis"] in ("opo", "circle_250nm")
