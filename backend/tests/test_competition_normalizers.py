"""The allocation-circle normalizers must match the data (#299 / L-064).

`allocation_circles` divides the centers-within-250nm count by a per-organ
constant, with the stated intent "normalized so mean US location ~= 1.0" and
the claim "average US metro has ~15 kidney centers within 250nm".

Both were checkable against shipped data all along, and both were wrong: the
population-weighted mean is 25.6 for kidney, so the score averaged 1.71 rather
than the 1.0 it claimed. Every organ was understated by 24-72%.

These constants are now DERIVED rather than asserted: this test recomputes them
from the shipped county centroids and populations and fails if the shipped
values drift away from what the data says. A round number that nothing checks
is how the original values survived.

The 500nm normalizer (2.5x the 250nm figure) was measured too, and it is fine —
the actual ratio is 2.38-2.51. Recorded so it is not "fixed" needlessly.
"""
import json
from pathlib import Path

import pytest

from services.allocation_geography import (
    AVG_CENTERS_250NM,
    CIRCLE_250NM,
    CIRCLE_500NM,
    CIRCLE_500_RATIO,
    centers_within_radius,
)

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def population_weighted_counts(data):
    """Mean centers within each circle, weighted by county population.

    Population weighting is the right denominator for "the average US
    location" — an unweighted county mean over-represents empty rural
    counties, and the constant is meant to normalize a typical *patient's*
    competition, not a typical square mile's.
    """
    geo = json.loads((REPO / "data" / "health-demographics-counties.json").read_text())["counties"]
    pop = json.loads((REPO / "data" / "county-population.json").read_text())["counties"]
    locs = [(g["lat"], g["lon"], (pop.get(f) or {}).get("population", 0))
            for f, g in geo.items() if isinstance(g, dict) and "lat" in g]
    assert len(locs) > 3000, f"only {len(locs)} county centroids — the source moved"

    out = {}
    total_w = sum(p for *_, p in locs)
    assert total_w > 300_000_000, f"population total {total_w:,} is implausible for the US"
    for organ in AVG_CENTERS_250NM:
        s250 = sum(len(centers_within_radius(la, lo, CIRCLE_250NM, organ)) * p for la, lo, p in locs)
        s500 = sum(len(centers_within_radius(la, lo, CIRCLE_500NM, organ)) * p for la, lo, p in locs)
        out[organ] = (s250 / total_w, s500 / total_w)
    return out


def test_250nm_normalizers_match_the_data(population_weighted_counts):
    """The constant must be what it claims to be: the actual mean."""
    off = []
    for organ, shipped in AVG_CENTERS_250NM.items():
        actual = population_weighted_counts[organ][0]
        if abs(shipped - actual) / actual > 0.10:
            off.append(f"{organ}: shipped {shipped} vs measured {actual:.1f}")
    assert not off, (
        "allocation-circle normalizers no longer match the shipped center "
        f"geography: {off}. They are meant to be the population-weighted mean "
        "count, so recompute rather than adjusting by feel.")


def test_the_normalization_actually_normalizes(population_weighted_counts):
    """The docstring's own claim — mean competition score ~= 1.0 — must hold.

    It did not: with 15 for kidney against a real 25.6, the mean was 1.71.
    """
    for organ, shipped in AVG_CENTERS_250NM.items():
        mean_score = population_weighted_counts[organ][0] / shipped
        assert 0.9 <= mean_score <= 1.1, (
            f"{organ}: mean competition score is {mean_score:.2f}, not ~1.0 — "
            "the normalizer does not normalize")


def test_500nm_ratio_is_still_supported(population_weighted_counts):
    """Measured and found sound; pinned so it is neither broken nor churned."""
    for organ, (c250, c500) in population_weighted_counts.items():
        ratio = c500 / c250
        assert abs(ratio - CIRCLE_500_RATIO) / CIRCLE_500_RATIO < 0.15, (
            f"{organ}: actual 500/250 ratio {ratio:.2f} vs shipped "
            f"{CIRCLE_500_RATIO}")


def test_every_organ_has_a_normalizer(data):
    """A missing organ silently fell back to 10, which is not a measurement."""
    from services.allocation_geography import _get_center_coords
    organs = {o for c in _get_center_coords() for o in c["organs"]}
    missing = sorted(organs - set(AVG_CENTERS_250NM))
    assert not missing, f"organs with no measured normalizer: {missing}"
