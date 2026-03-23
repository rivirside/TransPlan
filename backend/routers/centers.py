"""GET /centers — List all transplant centers and focus cities.
GET /centers/{code} — Detail for a single center (#160).
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from services.data_loader import get_data
from utils import haversine_distance

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/centers")
def list_centers(
    organ: str | None = Query(default=None, description="Filter by organ program"),
    focus_only: bool = Query(default=False, description="Return only the 22 focus cities"),
):
    """Return all SRTR transplant centers with coordinates and organ programs."""
    data = get_data()
    all_centers = data.all_centers.get("centers", {})
    mapping = data.center_mapping.get("cities", {})

    if focus_only:
        # Return just the 22 focus cities with their primary/alternate centers
        cities = []
        for city, info in mapping.items():
            codes = [info["primary"]] + info.get("alternates", [])
            center_details = []
            for code in codes:
                c = all_centers.get(code)
                if c:
                    center_details.append(c)
            cities.append({
                "city": city,
                "state": info["state"],
                "centers": center_details,
            })
        return {"cities": cities, "total": len(cities)}

    # Return all centers, optionally filtered by organ
    centers = []
    for code, center in all_centers.items():
        if organ and organ not in center.get("organs", []):
            continue
        centers.append(center)

    return {"centers": centers, "total": len(centers)}


@router.get("/centers/{code}")
def get_center_detail(
    code: str,
    nearby_radius_miles: float = Query(default=250, ge=0, le=1000, description="Radius for nearby centers"),
):
    """Return detailed data for a single transplant center (#160).

    Includes basic info, organ-specific wait time factors, competing risks
    adjustments, post-transplant outcomes, and nearby centers.
    """
    data = get_data()
    all_centers = data.all_centers.get("centers", {})

    # Find center (case-insensitive code match)
    center = all_centers.get(code) or all_centers.get(code.upper())
    if not center:
        raise HTTPException(status_code=404, detail=f"Center '{code}' not found")

    code_key = center["code"]

    # Wait time factors per organ
    wait_factors = {}
    wt_data = getattr(data, 'center_wait_times', None)
    if wt_data:
        center_factors = wt_data.get("center_wait_time_factors", {})
        wait_factors = center_factors.get(code_key, {})

    # Competing risks adjustments per organ
    risk_factors = {}
    cr_data = getattr(data, 'center_competing_risks', None)
    if cr_data:
        center_adj = cr_data.get("center_adjustments", {})
        risk_factors = center_adj.get(code_key, {})

    # Post-transplant outcomes per organ
    outcomes = {}
    oc_data = getattr(data, 'center_outcomes', None)
    if oc_data:
        center_oc = oc_data.get("center_outcomes", {})
        outcomes = center_oc.get(code_key, {})

    # Nearby centers within radius
    nearby = []
    if center.get("lat") and center.get("lon"):
        for other_code, other in all_centers.items():
            if other_code == code_key:
                continue
            if not other.get("lat") or not other.get("lon"):
                continue
            dist = haversine_distance(
                center["lat"], center["lon"],
                other["lat"], other["lon"],
            )
            if dist <= nearby_radius_miles:
                nearby.append({
                    "code": other["code"],
                    "name": other["name"],
                    "state_abbr": other.get("state_abbr", ""),
                    "organs": other.get("organs", []),
                    "distance_miles": round(dist, 1),
                })
        nearby.sort(key=lambda x: x["distance_miles"])

    return {
        "center": center,
        "wait_time_factors": wait_factors,
        "competing_risks": risk_factors,
        "outcomes": outcomes,
        "nearby_centers": nearby[:20],  # cap at 20 nearest
        "srtr_url": f"https://www.srtr.org/transplant-centers/{code_key}/",
    }
