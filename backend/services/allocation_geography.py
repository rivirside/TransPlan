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


# Population-weighted mean number of centers within 250nm of a US resident,
# measured from data/health-demographics-counties.json centroids weighted by
# data/county-population.json (#299 / L-064). Dividing the local count by this
# makes the competition score average ~1.0, which is what the score claims to
# do.
#
# These replace round numbers whose comment asserted "average US metro has ~15
# kidney centers within 250nm". The real figure is 25.6, so the score averaged
# 1.71 rather than 1.0, and every organ was understated by 24-72%. They are
# recomputed and pinned by backend/tests/test_competition_normalizers.py, so a
# change in center geography fails a test rather than silently skewing the
# score.
AVG_CENTERS_250NM = {
    "kidney": 25.6,
    "liver": 15.7,
    "heart": 16.2,
    "lung": 8.6,
    "pancreas": 11.7,
    "intestine": 2.5,
}

# Centers within 500nm run ~2.4x the 250nm count. Unlike the figures above,
# this round number was MEASURED to be sound (actual 2.38-2.51 across organs),
# so it is kept rather than churned.
CIRCLE_500_RATIO = 2.5


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

    # Competition score: more centers = more competition for donors.
    # Normalized so the mean US location scores ~1.0 — see AVG_CENTERS_250NM,
    # which is measured rather than assumed (#299).
    avg = AVG_CENTERS_250NM.get(organ, 10)
    competition_250 = len(within_250) / avg if avg > 0 else 1.0

    # Nearest center distance
    nearest = within_250[0] if within_250 else (within_500[0] if within_500 else None)

    return {
        "circle_250nm": {
            "center_count": len(within_250),
            # lat/lon included because the Explorer plots these as markers
            # inside the drawn circle; without them the marker loop's
            # `if (c.lat && c.lon)` silently drew nothing (#183).
            "centers": [{"code": c["code"], "name": c["name"],
                         "distance_nm": c["distance_nm"],
                         "lat": c["lat"], "lon": c["lon"]}
                        for c in within_250[:10]],  # Top 10 nearest
            "competition_score": round(competition_250, 2),
        },
        "circle_500nm": {
            "center_count": len(within_500),
            "competition_score": round(len(within_500) / (avg * CIRCLE_500_RATIO) if avg > 0 else 1.0, 2),
        },
        "nearest_center": {
            "code": nearest["code"],
            "name": nearest["name"],
            "distance_nm": nearest["distance_nm"],
        } if nearest else None,
        "total_organ_centers": total_organ_centers,
        "organ": organ,
    }


# ──────────────────────────────────────────────────────────────────────
# OPO-based competition (#299)
#
# The circle measure above does not predict observed transplant rates -- 16
# tests, nothing below p 0.178, and counting the CANDIDATES inside the circle
# is no better. Counting centers in the same OPO does: kidney rho -0.188
# (p 0.005), lung -0.361 (p 0.004), controlling for the center's own cohort
# and surviving Bonferroni across the four organ-level tests. UNOS region, a
# coarser grouping of the same centers, predicts nothing -- which is what
# makes this the allocation unit rather than any grouping.
#
# Small, though: about 3.5% of rank variance. A better number, not a strong
# one. See docs/allocation-competition-validation.md.
# ──────────────────────────────────────────────────────────────────────

_OPO_MAP: dict | None = None


def _opo_data() -> dict:
    """Lazy-load data/opo-mapping.json (248 centers -> OPO, via HRSA)."""
    global _OPO_MAP
    if _OPO_MAP is None:
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[2] / "data" / "opo-mapping.json"
        _OPO_MAP = json.loads(path.read_text(encoding="utf-8"))
    return _OPO_MAP


def opo_competition(lat: float, lon: float, organ: str = "kidney") -> dict:
    """Competition faced at a location, counted over its OPO rather than a circle.

    A location has no OPO of its own -- the shipped mapping is county-based
    and runtime geocoding is not available -- so the query point inherits the
    OPO of its nearest center performing the organ. That is the OPO whose
    match run a patient listing there would enter.

    `competition_score` is normalised so a typical location scores ~1.0, the
    same convention as the circle score, and is None when the organ has no
    reachable program (rather than dividing by zero and returning a number
    that looks measured).
    """
    mapping = _opo_data()
    center_opo = mapping.get("centerOpoMap", {})

    organ_centers = [c for c in _get_center_coords() if organ in c["organs"]]
    if not organ_centers:
        return {"opo": None, "nearest_center": None, "centers_in_opo": 0,
                "competition_score": None, "organ": organ}

    nearest = min(
        organ_centers,
        key=lambda c: haversine_distance_nm(lat, lon, c["lat"], c["lon"]),
    )
    opo = center_opo.get(nearest["code"])
    if not opo:
        return {"opo": None, "nearest_center": nearest["code"],
                "centers_in_opo": 0, "competition_score": None, "organ": organ}

    in_opo = [c for c in organ_centers if center_opo.get(c["code"]) == opo]

    # Normalise against the mean centers-per-OPO for this organ, so the score
    # is comparable across organs with very different program counts.
    opos_used = {center_opo.get(c["code"]) for c in organ_centers}
    opos_used.discard(None)
    mean_per_opo = len(organ_centers) / len(opos_used) if opos_used else 0.0

    score = (len(in_opo) / mean_per_opo) if mean_per_opo > 0 else None
    return {
        "opo": opo,
        "opo_name": (mapping.get("opos", {}).get(opo) or {}).get("name"),
        "nearest_center": nearest["code"],
        "centers_in_opo": len(in_opo),
        "mean_centers_per_opo": round(mean_per_opo, 2),
        "competition_score": round(score, 2) if score is not None else None,
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

    # Factor 2: Competition (fewer competing centers = better for wait times).
    #
    # #299: this used the 250nm circle count, which was MEASURED not to
    # predict observed SRTR transplant rates (16 tests, nothing below
    # p 0.178). Counting centers in the same OPO does -- kidney rho -0.188
    # (p 0.005), lung -0.361 (p 0.004) -- so the composite uses that instead.
    #
    # The circle measure is kept in the response for comparison, but a
    # component known not to predict has no business driving 35% of a score.
    # Billings MT is the clearest case: no center within 250nm, so the circle
    # calls it zero competition, while the patient is in fact listed into an
    # OPO with eight competing kidney programs.
    opo = opo_competition(lat, lon, organ)
    comp = opo.get("competition_score")
    if comp is None:                       # no reachable program for the organ
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
        "competition_basis": "opo" if opo.get("competition_score") is not None else "circle_250nm",
        "opo_competition": opo,
        "circle_competition_score": circles["circle_250nm"]["competition_score"],
        "donor_pool": round(donor_pool_score, 1),
        "nearest_center": nearest,
        "centers_250nm": circles["circle_250nm"]["center_count"],
        "centers_500nm": circles["circle_500nm"]["center_count"],
    }
