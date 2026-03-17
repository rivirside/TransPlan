"""GET /trends — Historical trend data for transplant centers.

Returns trend analysis (direction, slope, significance) and sparkline data
for a city/organ combination. Data sourced from multi-year SRTR PSR releases.
"""
from fastapi import APIRouter, HTTPException

from services.trends import get_city_trends, get_all_trends, VALID_ORGANS

router = APIRouter()


@router.get("/trends/{city}/{organ}")
def get_trends(city: str, organ: str) -> dict:
    """Get historical trend analysis for a specific city and organ."""
    if organ not in VALID_ORGANS:
        raise HTTPException(status_code=400, detail=f"Invalid organ: {organ}. Valid: {sorted(VALID_ORGANS)}")

    trend = get_city_trends(organ, city)
    if trend is None:
        raise HTTPException(status_code=404, detail=f"No trend data for {city} / {organ}")

    return trend


@router.get("/trends/{organ}")
def get_all_organ_trends(organ: str) -> dict:
    """Get trend analysis for all cities for a given organ."""
    if organ not in VALID_ORGANS:
        raise HTTPException(status_code=400, detail=f"Invalid organ: {organ}. Valid: {sorted(VALID_ORGANS)}")

    trends = get_all_trends(organ)
    if not trends:
        raise HTTPException(status_code=404, detail=f"No trend data available for {organ}")

    return {"organ": organ, "cities": trends}
