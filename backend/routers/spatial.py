"""
Spatial analysis endpoints:
  GET /interpolated-value — Query spatial interpolation surfaces
  GET /spatial-layers — List available interpolation layers
  GET /interpolated-profile — Multi-layer profile at a coordinate
  GET /allocation-circles — UNOS allocation circle analysis
  GET /distance-score — Composite distance/geography score
  GET /spatial-grid — Grid of interpolated values for heatmap rendering
  GET /location-delta — Delta scores vs. patient's current location

Phase 6B issues #128, #129, #130, #131.
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from services.allocation_geography import allocation_circles, distance_score
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


@router.get("/allocation-circles")
def query_allocation_circles(
    lat: float = Query(..., ge=24.0, le=50.0, description="Latitude"),
    lon: float = Query(..., ge=-125.0, le=-66.0, description="Longitude"),
    organ: str = Query(default="kidney", description="Organ type"),
):
    """UNOS allocation circle analysis at a coordinate."""
    return allocation_circles(lat, lon, organ)


@router.get("/distance-score")
def query_distance_score(
    lat: float = Query(..., ge=24.0, le=50.0, description="Latitude"),
    lon: float = Query(..., ge=-125.0, le=-66.0, description="Longitude"),
    organ: str = Query(default="kidney", description="Organ type"),
):
    """Composite distance/geography score at a coordinate."""
    return distance_score(lat, lon, organ)


@router.get("/spatial-grid")
def query_spatial_grid(
    layer: str = Query(..., description="Data layer name"),
    resolution: int = Query(default=30, ge=10, le=100, description="Grid cells per axis"),
    method: str = Query(default="rbf", description="Interpolation method"),
):
    """
    Generate a grid of interpolated values for heatmap rendering.
    Returns a lat/lon/value array covering CONUS.
    """
    import numpy as np
    try:
        surface = get_surface(layer, method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # CONUS bounding box
    lat_min, lat_max = 25.0, 49.0
    lon_min, lon_max = -124.0, -67.0

    lats = np.linspace(lat_min, lat_max, resolution)
    lons = np.linspace(lon_min, lon_max, resolution)
    grid_lats, grid_lons = np.meshgrid(lats, lons)
    coords = np.column_stack([grid_lats.ravel(), grid_lons.ravel()])

    values = surface.query_batch(coords)

    # Build heatmap-ready array: [[lat, lon, intensity], ...]
    v_min, v_max = float(np.min(values)), float(np.max(values))
    v_range = v_max - v_min if v_max > v_min else 1.0
    points = []
    for i, (lat, lon) in enumerate(coords):
        intensity = (float(values[i]) - v_min) / v_range
        points.append([round(float(lat), 3), round(float(lon), 3), round(intensity, 3)])

    return {
        "layer": layer,
        "resolution": resolution,
        "points": points,
        "value_range": {"min": round(v_min, 2), "max": round(v_max, 2)},
        "stats": surface.stats,
    }


@router.get("/location-delta")
def query_location_delta(
    home_lat: float = Query(..., ge=24.0, le=50.0, description="Patient home latitude"),
    home_lon: float = Query(..., ge=-125.0, le=-66.0, description="Patient home longitude"),
    center_lat: float = Query(..., ge=24.0, le=50.0, description="Center latitude"),
    center_lon: float = Query(..., ge=-125.0, le=-66.0, description="Center longitude"),
    organ: str = Query(default="kidney", description="Organ type"),
):
    """
    Compare spatial profile at patient home vs. a transplant center.
    Returns delta values for each interpolation layer ("air quality +15, cost -8").
    Phase 6B issue #131.
    """
    layers = [
        "air_quality",
        "cost_of_living",
        "health_diabetesRate",
        "health_obesityRate",
        "health_hypertensionRate",
        "health_smokingRate",
        f"wait_time_factor_{organ}",
        f"mortality_factor_{organ}",
        f"graft_survival_{organ}",
    ]

    deltas = {}
    for layer in layers:
        try:
            home_val = interpolate_at(home_lat, home_lon, layer)
            center_val = interpolate_at(center_lat, center_lon, layer)
            deltas[layer] = {
                "home": round(home_val, 2),
                "center": round(center_val, 2),
                "delta": round(center_val - home_val, 2),
            }
        except ValueError:
            deltas[layer] = None

    return {
        "home": {"lat": home_lat, "lon": home_lon},
        "center": {"lat": center_lat, "lon": center_lon},
        "organ": organ,
        "deltas": deltas,
    }
