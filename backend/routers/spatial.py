"""
GET /interpolated-value — Query spatial interpolation surfaces.
GET /spatial-layers — List available interpolation layers.

Phase 6B issue #128.
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from services.spatial_interpolation import available_layers, get_surface, interpolate_at

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/spatial-layers")
def list_spatial_layers():
    """List all available spatial interpolation layers."""
    layers = available_layers()
    return {"layers": layers, "total": len(layers)}


@router.get("/interpolated-value")
def query_interpolated_value(
    lat: float = Query(..., ge=24.0, le=50.0, description="Latitude (US mainland)"),
    lon: float = Query(..., ge=-125.0, le=-66.0, description="Longitude (US mainland)"),
    layer: str = Query(..., description="Data layer name (e.g. 'air_quality', 'wait_time_factor_kidney')"),
    method: str = Query(default="rbf", description="Interpolation method: 'rbf' or 'idw'"),
):
    """Interpolate a single data layer at a given coordinate."""
    try:
        value = interpolate_at(lat, lon, layer, method)
        surface = get_surface(layer, method)
        return {
            "lat": lat,
            "lon": lon,
            "layer": layer,
            "value": round(value, 3),
            "stats": surface.stats,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/interpolated-profile")
def query_interpolated_profile(
    lat: float = Query(..., ge=24.0, le=50.0, description="Latitude"),
    lon: float = Query(..., ge=-125.0, le=-66.0, description="Longitude"),
    organ: str = Query(default="kidney", description="Organ type for center-level layers"),
):
    """
    Interpolate all relevant layers at a single coordinate.
    Returns a complete spatial profile for location scoring.
    """
    results = {}
    layers_to_query = [
        "air_quality",
        "cost_of_living",
        "health_diabetesRate",
        "health_obesityRate",
        "health_ckdRate",
        "health_hypertensionRate",
        "health_smokingRate",
        f"wait_time_factor_{organ}",
        f"mortality_factor_{organ}",
        f"graft_survival_{organ}",
    ]

    for layer in layers_to_query:
        try:
            value = interpolate_at(lat, lon, layer)
            results[layer] = round(value, 3)
        except ValueError:
            results[layer] = None

    return {
        "lat": lat,
        "lon": lon,
        "organ": organ,
        "values": results,
        "interpolation_method": "rbf",
    }
