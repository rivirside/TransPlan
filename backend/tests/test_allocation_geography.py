"""Tests for services/allocation_geography.py — UNOS allocation circle modeling."""
import pytest

from services.data_loader import load_all
from services.allocation_geography import (
    allocation_circles,
    centers_within_radius,
    distance_score,
)


@pytest.fixture(scope="module", autouse=True)
def _load_data():
    load_all()


class TestCentersWithinRadius:
    def test_pittsburgh_250nm(self):
        centers = centers_within_radius(40.4406, -79.9959, 250)
        assert len(centers) > 10  # Dense northeast corridor
        # Should include PAPT (Pittsburgh) at ~0nm
        codes = [c["code"] for c in centers]
        assert "PAPT" in codes or "PAAG" in codes or "PACH" in codes

    def test_sorted_by_distance(self):
        centers = centers_within_radius(40.4406, -79.9959, 250)
        dists = [c["distance_nm"] for c in centers]
        assert dists == sorted(dists)

    def test_organ_filter(self):
        all_centers = centers_within_radius(40.4406, -79.9959, 500)
        kidney_only = centers_within_radius(40.4406, -79.9959, 500, organ="kidney")
        intestine_only = centers_within_radius(40.4406, -79.9959, 500, organ="intestine")
        # Kidney programs are much more common than intestine
        assert len(kidney_only) > len(intestine_only)
        assert len(kidney_only) <= len(all_centers)

    def test_zero_radius(self):
        centers = centers_within_radius(40.4406, -79.9959, 0)
        # Only centers at exact same coordinates (possibly PAAG at same coords)
        assert len(centers) <= 5


class TestAllocationCircles:
    def test_structure(self):
        result = allocation_circles(40.4406, -79.9959, "kidney")
        assert "circle_250nm" in result
        assert "circle_500nm" in result
        assert "nearest_center" in result
        assert "total_organ_centers" in result
        assert result["organ"] == "kidney"

    def test_250nm_has_centers(self):
        result = allocation_circles(40.4406, -79.9959, "kidney")
        assert result["circle_250nm"]["center_count"] > 0
        assert "competition_score" in result["circle_250nm"]
        assert len(result["circle_250nm"]["centers"]) <= 10  # Capped at 10

    def test_500nm_gte_250nm(self):
        result = allocation_circles(40.4406, -79.9959, "kidney")
        assert result["circle_500nm"]["center_count"] >= result["circle_250nm"]["center_count"]

    def test_nearest_center(self):
        result = allocation_circles(40.4406, -79.9959, "kidney")
        nearest = result["nearest_center"]
        assert nearest is not None
        assert "code" in nearest
        assert "distance_nm" in nearest
        assert nearest["distance_nm"] >= 0

    def test_rural_area_fewer_centers(self):
        # Rural Kansas vs NYC
        rural = allocation_circles(38.5, -98.7, "kidney")
        urban = allocation_circles(40.7128, -74.0060, "kidney")
        assert rural["circle_250nm"]["center_count"] < urban["circle_250nm"]["center_count"]


class TestDistanceScore:
    def test_structure(self):
        result = distance_score(40.4406, -79.9959, "kidney")
        assert "composite" in result
        assert "proximity" in result
        assert "competition" in result
        assert "donor_pool" in result
        assert 0 <= result["composite"] <= 100
        assert 0 <= result["proximity"] <= 100

    def test_near_center_high_proximity(self):
        # Right at a major center should have high proximity
        result = distance_score(40.4406, -79.9959, "kidney")
        assert result["proximity"] > 80

    def test_rural_lower_proximity(self):
        rural = distance_score(38.5, -98.7, "kidney")
        urban = distance_score(40.4406, -79.9959, "kidney")
        assert rural["proximity"] < urban["proximity"]

    def test_different_organs(self):
        kidney = distance_score(40.4406, -79.9959, "kidney")
        intestine = distance_score(40.4406, -79.9959, "intestine")
        # Kidney has more centers, so different competition dynamics
        assert kidney["centers_250nm"] > intestine["centers_250nm"]
