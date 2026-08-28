"""#299: the Distance Score card's fields must match what the API returns.

Found 2026-08-28 while relabelling the card. `explorer/spatial-analysis.js`
read `composite_score`, `proximity_score`, `competition_score` and
`donor_pool_score`; `distance_score()` has always returned `composite`,
`proximity`, `competition` and `donor_pool`.

**All four tiles rendered `--`, permanently.** It was silent because the
fallback IS `--`: a card that never populated is indistinguishable from a
card waiting for input, and nothing errored.

Same family as the print stylesheet (#197) and the snapshot tool's 0/0/0
(#137) — machinery that cannot fail, and so reads as working. This one is
worse in one respect: I nearly shipped a rewritten caveat for a card that
displayed nothing, because the values in the screenshot I checked the layout
against were ones I had injected by hand.

Checked here rather than in Jest because the field names are the API's, and
this is where a change to them would originate.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
JS = REPO / "explorer" / "spatial-analysis.js"

TILES = {
    "scoreComposite": "composite",
    "scoreProximity": "proximity",
    "scoreCompetition": "competition",
    "scoreDonorPool": "donor_pool",
}


@pytest.fixture(scope="module")
def response(data):
    from services.allocation_geography import distance_score
    return distance_score(40.758, -73.9855, "kidney")


def test_every_field_the_card_reads_exists_in_the_response(response):
    src = JS.read_text(encoding="utf-8")
    for element_id, field in TILES.items():
        assert re.search(rf"el\('{element_id}'\).*?data\.{field}\b", src, re.S), (
            f"{element_id} no longer reads data.{field} — if the binding "
            "changed, check it against the API's actual field names"
        )
        assert field in response, (
            f"distance_score() no longer returns '{field}', which "
            f"{element_id} reads; the card would silently show '--'"
        )
        assert isinstance(response[field], (int, float)), (
            f"{field} is {type(response[field]).__name__}; toFixed(1) in the "
            "card would throw or print '--'"
        )


def test_the_card_does_not_read_the_old_suffixed_names():
    """The exact bug: *_score names that the API never returned."""
    src = JS.read_text(encoding="utf-8")
    for field in TILES.values():
        assert f"data.{field}_score" not in src, (
            f"data.{field}_score is back. The API returns '{field}'; the "
            "suffixed name silently renders '--' on every tile."
        )


def test_the_guard_is_not_vacuous(response):
    """If TILES drifted from the real element ids, the checks above would
    pass while testing nothing."""
    src = JS.read_text(encoding="utf-8")
    assert len(TILES) == 4
    for element_id in TILES:
        assert element_id in src, f"{element_id} is not in spatial-analysis.js"


def test_competition_is_sourced_from_the_opo_measure(response):
    """The tile is labelled 'Competition (OPO)', so it must be."""
    assert response["competition_basis"] == "opo"
    html = (REPO / "explorer.html").read_text(encoding="utf-8")
    assert "Competition (OPO)" in html


# ── the allocation-circles consumer had the same bug (#183) ─────────────────

CIRCLE_JS = REPO / "explorer" / "spatial-analysis.js"


def test_the_circle_tooltips_read_the_field_the_api_returns(data):
    """Second instance of the same defect, found by generalising the first.

    The JS read `circles_250nm` / `circles_500nm` (plural) for fields the API
    has always called `circle_250nm` / `circle_500nm`. With `|| 0` behind
    them, every tooltip reported "0 centers" regardless of location —
    Manhattan has 55 within 250 nm. Worse than the blank tile in the Distance
    Score card, because zero reads as a measurement rather than as missing.
    """
    from services.allocation_geography import allocation_circles
    src = CIRCLE_JS.read_text(encoding="utf-8")
    resp = allocation_circles(40.758, -73.9855, "kidney")

    assert "data.circles_250nm" not in src, "the plural (wrong) name is back"
    assert "data.circles_500nm" not in src
    for field in ("circle_250nm", "circle_500nm"):
        assert f"data.{field}" in src, f"the JS no longer reads {field}"
        assert field in resp, f"the API no longer returns {field}"
        assert resp[field]["center_count"] > 0, (
            "Manhattan should have centers in range; if not, this test's "
            "premise is gone"
        )


def test_circle_centers_carry_coordinates(data):
    """The marker loop guards on `c.lat && c.lon`, so without coordinates it
    silently drew nothing even once the field names were right."""
    from services.allocation_geography import allocation_circles
    centers = allocation_circles(40.758, -73.9855, "kidney")["circle_250nm"]["centers"]
    assert centers, "no centers returned for Manhattan"
    for c in centers:
        assert isinstance(c.get("lat"), (int, float)), f"{c.get('code')} has no lat"
        assert isinstance(c.get("lon"), (int, float)), f"{c.get('code')} has no lon"

    src = CIRCLE_JS.read_text(encoding="utf-8")
    assert "c.lat && c.lon" in src, (
        "the marker guard changed; re-check whether coordinates are still needed"
    )
