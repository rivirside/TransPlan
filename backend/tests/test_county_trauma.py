"""County-resolution trauma scores (#336).

trauma-scores-centers.json gave every center in a state the same score, and
its own _meta named the fix: "county-level FARS + county population". That
was blocked until the repository had population data at any geography.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
COUNTY = REPO / "data" / "trauma-scores-counties.json"


@pytest.fixture(scope="module")
def doc():
    if not COUNTY.exists():
        pytest.skip("trauma-scores-counties.json not generated")
    return json.loads(COUNTY.read_text())


def test_most_centers_reach_county_resolution(doc):
    scores = doc["center_scores"]
    county = [c for c, r in scores.items() if r["resolution"] == "county"]
    assert len(county) > 200, (
        f"only {len(county)} centers at county resolution — centroid matching "
        f"may be failing")


def test_centroid_matches_are_close(doc):
    """Nearest-centroid assignment has no boundary polygons behind it, so a
    large match distance means the county attribution is probably wrong."""
    dists = [r["match_distance_miles"] for r in doc["center_scores"].values()
             if r["resolution"] == "county"]
    assert dists
    dists.sort()
    median = dists[len(dists) // 2]
    assert median < 20, f"median centroid match {median} mi is too far to trust"
    assert max(dists) <= 60, f"a center matched {max(dists)} mi away"


def test_scores_are_on_the_documented_scale(doc):
    scores = [r["score"] for r in doc["county_scores"].values()]
    assert scores
    assert min(scores) >= 0
    assert abs(max(scores) - 100.0) < 0.51, (
        "scores must be normalized so the highest county is 100, matching the "
        "state file's semantics")


def test_small_counties_are_shrunk_toward_their_state(doc):
    """A 4,000-person county with two fatal crashes computes to 50 per 100k —
    four times the worst state. Shrinkage is what stops that shipping."""
    counties = doc["county_scores"]
    extreme = [(f, r) for f, r in counties.items()
               if r["population"] < 10000 and r["raw_rate_per_100k"] > 40]
    if not extreme:
        pytest.skip("no tiny high-rate counties in this vintage")
    for fips, rec in extreme:
        assert rec["shrunk_rate_per_100k"] < rec["raw_rate_per_100k"], (
            f"{fips} was not shrunk: raw {rec['raw_rate_per_100k']} -> "
            f"{rec['shrunk_rate_per_100k']}")


def test_county_resolution_adds_within_state_variation(doc):
    """The whole point: centers in one state must no longer be identical."""
    import collections
    centers = json.loads(
        (REPO / "data" / "srtr-all-centers.json").read_text())["centers"]
    by_state = collections.defaultdict(list)
    for code, rec in doc["center_scores"].items():
        if rec["resolution"] != "county":
            continue
        abbr = (centers.get(code) or {}).get("state_abbr")
        if abbr:
            by_state[abbr].append(rec["score"])
    varied = [s for s, vals in by_state.items()
              if len(vals) >= 3 and max(vals) - min(vals) > 1.0]
    assert len(varied) >= 15, (
        f"only {len(varied)} states show within-state variation — county "
        f"scores may have collapsed back to state values")


def test_surface_prefers_county_scores(data):
    """The refinement must actually reach the scoring surface, not just the
    data directory."""
    from services.data_loader import get_data
    d = get_data()
    assert d.county_trauma.get("center_scores"), "county trauma not loaded"
