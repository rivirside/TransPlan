"""County population and the coverage statistic it unblocks (#336, #113).

The repository had no population data at any geography, which blocked three
issues at once. These pin the properties that make the derived statistic
trustworthy — a silently truncated population file would produce a
plausible-looking but wrong national number.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
POP = REPO / "data" / "county-population.json"
CENTROIDS = REPO / "data" / "health-demographics-counties.json"
COVERAGE = REPO / "docs-site" / "static" / "data" / "coverage-gaps.json"


@pytest.fixture(scope="module")
def population():
    return json.loads(POP.read_text())["counties"]


def test_county_count_and_fips_format(population):
    assert len(population) >= 3000, f"only {len(population)} counties"
    for fips in population:
        assert len(fips) == 5 and fips.isdigit(), f"bad FIPS {fips!r}"


def test_national_total_is_plausible(population):
    total = sum(r["population"] for r in population.values())
    assert 300_000_000 < total < 380_000_000, (
        f"national total {total:,} is not a plausible US population — wrong "
        f"column, or state rows counted as counties?")


def test_every_centroid_county_has_a_population(population):
    """A FIPS-format mismatch would silently drop counties from any
    per-capita rate rather than failing loudly."""
    centroids = json.loads(CENTROIDS.read_text())["counties"]
    missing = [f for f in centroids if f not in population]
    assert not missing, f"{len(missing)} centroid counties lack population: {missing[:5]}"


def test_coverage_shares_are_monotone_in_distance():
    if not COVERAGE.exists():
        pytest.skip("coverage-gaps.json not generated")
    doc = json.loads(COVERAGE.read_text())
    for organ, res in doc["organs"].items():
        shares = res["share_within"]
        bands = sorted(int(b) for b in shares)
        values = [shares[str(b)] for b in bands]
        assert values == sorted(values), (
            f"{organ}: coverage must not decrease with distance: "
            f"{list(zip(bands, values))}")
        assert all(0.0 <= v <= 1.0 for v in values), f"{organ}: share out of range"


def test_more_centers_means_broader_coverage():
    """Kidney is performed at far more centers than intestine, so its
    coverage must be higher. If this inverts, centers or counties are being
    mismatched."""
    if not COVERAGE.exists():
        pytest.skip("coverage-gaps.json not generated")
    organs = json.loads(COVERAGE.read_text())["organs"]
    if "kidney" not in organs or "intestine" not in organs:
        pytest.skip("needed organs absent")
    assert organs["kidney"]["n_centers"] > organs["intestine"]["n_centers"]
    assert (organs["kidney"]["share_within"]["250"] >
            organs["intestine"]["share_within"]["250"])


def test_farthest_counties_are_non_contiguous_or_remote():
    """Alaska has no transplant center, so its remote boroughs must top the
    distance list. If somewhere in the lower 48 outranks them, coordinates
    are wrong."""
    if not COVERAGE.exists():
        pytest.skip("coverage-gaps.json not generated")
    worst = json.loads(COVERAGE.read_text())["organs"]["kidney"]["farthest_counties"]
    assert worst, "no farthest counties recorded"
    assert worst[0]["state"] in ("Alaska", "Hawaii"), (
        f"farthest county is {worst[0]['county']}, {worst[0]['state']} — "
        f"expected a non-contiguous state")
    assert worst[0]["miles_to_nearest"] > 500
