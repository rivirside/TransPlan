"""GET /centers — List all transplant centers and focus cities."""
import logging

from fastapi import APIRouter, Query

from services.data_loader import get_data

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
