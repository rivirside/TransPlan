"""
UNOS allocation geography modeling.

Computes donor pool characteristics based on UNOS allocation circles
(250nm and 500nm radius) and center proximity analysis.

Phase 6B issue #130.
"""
import logging
from functools import lru_cache

import numpy as np

from services.data_loader import get_data
from utils import haversine_distance_nm

logger = logging.getLogger(__name__)

# UNOS allocation circle radii in nautical miles
CIRCLE_250NM = 250
CIRCLE_500NM = 500


def _get_center_coords() -> list[dict]:
    """Get all center coordinates from data loader."""
    data = get_data()
    centers = data.all_centers.get("centers", {})
    result = []
    for code, center in centers.items():
        lat, lon = center.get("lat"), center.get("lon")
        if lat is not None and lon is not None:
            result.append({
                "code": code,
                "name": center.get("name", ""),
                "lat": lat,
                "lon": lon,
                "organs": center.get("organs", []),
                "state_abbr": center.get("state_abbr", ""),
            })
    return result


def centers_within_radius(
    lat: float, lon: float, radius_nm: float, organ: str | None = None
) -> list[dict]:
    """
    Find all transplant centers within a given radius (nautical miles).

    Args:
        lat, lon: Query point
        radius_nm: Radius in nautical miles
        organ: If specified, only include centers with this organ program

    Returns:
        List of centers with distance_nm added, sorted by distance.
    """
    all_centers = _get_center_coords()
    results = []

    for center in all_centers:
        if organ and organ not in center["organs"]:
            continue
        dist = haversine_distance_nm(lat, lon, center["lat"], center["lon"])
        if dist <= radius_nm:
            results.append({
                **center,
                "distance_nm": round(dist, 1),
            })

    results.sort(key=lambda c: c["distance_nm"])
    return results


def allocation_circles(lat: float, lon: float, organ: str = "kidney") -> dict:
    """
    Compute UNOS allocation circle analysis for a location.

    Returns the number of competing centers and estimated donor pool
    characteristics within 250nm and 500nm circles.

    The ratio of centers-in-circle to total centers provides a proxy for
    the relative donor pool and competition level at a location.
    """
    all_centers = _get_center_coords()
    organ_centers = [c for c in all_centers if organ in c["organs"]]
    total_organ_centers = len(organ_centers)

    within_250 = centers_within_radius(lat, lon, CIRCLE_250NM, organ)
    within_500 = centers_within_radius(lat, lon, CIRCLE_500NM, organ)

    # Competition score: more centers = more competition for donors
    # Normalized so mean US location ≈ 1.0
    # Average US metro has ~15 kidney centers within 250nm
    _avg_centers_250 = {"kidney": 15, "liver": 10, "heart": 10, "lung": 5, "pancreas": 7, "intestine": 2}
    avg = _avg_centers_250.get(organ, 10)
    competition_250 = len(within_250) / avg if avg > 0 else 1.0

    # Nearest center distance
    nearest = within_250[0] if within_250 else (within_500[0] if within_500 else None)

    return {
        "circle_250nm": {
            "center_count": len(within_250),
            "centers": [{"code": c["code"], "name": c["name"], "distance_nm": c["distance_nm"]}
                        for c in within_250[:10]],  # Top 10 nearest
            "competition_score": round(competition_250, 2),
        },
        "circle_500nm": {
            "center_count": len(within_500),
            "competition_score": round(len(within_500) / (avg * 2.5) if avg > 0 else 1.0, 2),
        },
        "nearest_center": {
            "code": nearest["code"],
            "name": nearest["name"],
            "distance_nm": nearest["distance_nm"],
        } if nearest else None,
        "total_organ_centers": total_organ_centers,
        "organ": organ,
    }


def distance_score(lat: float, lon: float, organ: str = "kidney") -> dict:
    """
    Compute a composite distance/geography score for a location.

    Factors:
    1. Proximity to nearest center (closer = better access)
    2. Competition within 250nm (fewer competing centers = shorter waits)
    3. Donor pool depth within 500nm (more centers = more donors)

    Returns a score 0-100 and component breakdown.
    """
    circles = allocation_circles(lat, lon, organ)

    # Factor 1: Nearest center proximity (0-100, closer = higher)
    nearest = circles.get("nearest_center")
    if nearest:
        dist = nearest["distance_nm"]
        # Logistic: 100 at 0nm, ~50 at 100nm, ~10 at 300nm
        proximity_score = 100 / (1 + (dist / 75) ** 1.5)
    else:
        proximity_score = 0

    # Factor 2: Competition (fewer competing centers = better for wait times)
    # Inverse of competition score, scaled 0-100
    comp = circles["circle_250nm"]["competition_score"]
    competition_score = 100 / (1 + comp * 0.5)  # Lower competition = higher score

    # Factor 3: Donor pool access (more centers in 500nm = larger donor pool)
    centers_500 = circles["circle_500nm"]["center_count"]
    total = circles["total_organ_centers"]
    pool_fraction = centers_500 / total if total > 0 else 0
    donor_pool_score = min(100, pool_fraction * 200)  # Scale so 50% coverage = 100

    # Weighted composite
    composite = (
        proximity_score * 0.40 +
        competition_score * 0.35 +
        donor_pool_score * 0.25
    )

    return {
        "composite": round(composite, 1),
        "proximity": round(proximity_score, 1),
        "competition": round(competition_score, 1),
        "donor_pool": round(donor_pool_score, 1),
        "nearest_center": nearest,
        "centers_250nm": circles["circle_250nm"]["center_count"],
        "centers_500nm": circles["circle_500nm"]["center_count"],
    }
