"""
Spatial interpolation service for geographic scoring surfaces.

Provides RBF (Radial Basis Function) and IDW (Inverse Distance Weighting)
interpolation over city-level data to estimate values at arbitrary coordinates.

Phase 6B issue #127.
"""
import logging
from functools import lru_cache

import numpy as np
from scipy.interpolate import RBFInterpolator

from services.data_loader import get_data

logger = logging.getLogger(__name__)

# City coordinates from scripts/utils.js (22 focus cities)
_CITY_COORDS = {
    "Pittsburgh": (40.4406, -79.9959),
    "Baltimore": (39.2904, -76.6122),
    "Philadelphia": (39.9526, -75.1652),
    "New York": (40.7128, -74.0060),
    "Minneapolis": (44.9778, -93.2650),
    "Madison": (43.0731, -89.4012),
    "Chicago": (41.8781, -87.6298),
    "Cleveland": (41.4993, -81.6944),
    "St. Louis": (38.6270, -90.1994),
    "Indianapolis": (39.7684, -86.1581),
    "Omaha": (41.2565, -95.9345),
    "Rochester": (44.0121, -92.4802),
    "Nashville": (36.1627, -86.7816),
    "Durham": (35.9940, -78.8986),
    "Miami": (25.7617, -80.1918),
    "Dallas": (32.7767, -96.7970),
    "Houston": (29.7604, -95.3698),
    "Portland": (45.5152, -122.6784),
    "Seattle": (47.6062, -122.3321),
    "San Francisco": (37.7749, -122.4194),
    "Los Angeles": (33.9425, -118.4081),
    "Palo Alto": (37.4419, -122.1430),
}


def _extract_layer_points(layer_name: str) -> tuple[np.ndarray, np.ndarray] | None:
    """
    Extract (coords, values) for a named data layer from loaded data.

    Returns:
        (coords, values) where coords is (N, 2) array of [lat, lon]
        and values is (N,) array. Returns None if insufficient data.
    """
    data = get_data()
    points = []
    values = []

    if layer_name == "air_quality":
        for city, val in data.air_quality.items():
            if city in _CITY_COORDS and isinstance(val, (int, float)):
                points.append(_CITY_COORDS[city])
                values.append(float(val))

    elif layer_name == "cost_of_living":
        for city, val in data.cost_of_living.items():
            if city in _CITY_COORDS and isinstance(val, (int, float)):
                points.append(_CITY_COORDS[city])
                values.append(float(val))

    elif layer_name.startswith("health_"):
        # e.g. "health_diabetesRate", "health_obesityRate"
        metric = layer_name[len("health_"):]
        for city, city_data in data.health_demographics.items():
            if city in _CITY_COORDS and isinstance(city_data, dict):
                val = city_data.get(metric)
                if val is not None:
                    points.append(_CITY_COORDS[city])
                    values.append(float(val))

    elif layer_name == "donor_registration":
        # State-level data, assign to cities by state
        state_rates = data.donor_registration
        state_to_cities = {}
        for city, coords in _CITY_COORDS.items():
            # Find the state for this city
            for c in get_data().cities:
                if c["city"] == city:
                    state_to_cities.setdefault(c["state"], []).append(city)
                    break
        # Map state abbreviation to full name for lookup
        for city, coords in _CITY_COORDS.items():
            for state_name, rate in state_rates.items():
                if isinstance(rate, (int, float)):
                    # Check if this city's state matches
                    pass  # Complex mapping; skip for now

    elif layer_name.startswith("wait_time_factor_"):
        organ = layer_name[len("wait_time_factor_"):]
        center_data = data.center_wait_times.get("center_wait_time_factors", {})
        all_centers = data.all_centers.get("centers", {})
        for code, factors in center_data.items():
            factor = factors.get(organ)
            center = all_centers.get(code, {})
            lat, lon = center.get("lat"), center.get("lon")
            if factor is not None and lat is not None and lon is not None:
                points.append((lat, lon))
                values.append(float(factor))

    elif layer_name.startswith("mortality_factor_"):
        organ = layer_name[len("mortality_factor_"):]
        center_data = data.center_competing_risks.get("center_adjustments", {})
        all_centers = data.all_centers.get("centers", {})
        for code, adjustments in center_data.items():
            adj = adjustments.get(organ, {})
            factor = adj.get("mortality_factor")
            center = all_centers.get(code, {})
            lat, lon = center.get("lat"), center.get("lon")
            if factor is not None and lat is not None and lon is not None:
                points.append((lat, lon))
                values.append(float(factor))

    elif layer_name.startswith("graft_survival_"):
        organ = layer_name[len("graft_survival_"):]
        center_data = data.center_outcomes.get("center_outcomes", {})
        all_centers = data.all_centers.get("centers", {})
        for code, outcomes in center_data.items():
            outcome = outcomes.get(organ, {})
            val = outcome.get("graft_survival_1yr")
            center = all_centers.get(code, {})
            lat, lon = center.get("lat"), center.get("lon")
            if val is not None and lat is not None and lon is not None:
                points.append((lat, lon))
                values.append(float(val))

    if len(points) < 3:
        return None

    return np.array(points), np.array(values)


class SpatialSurface:
    """Interpolated spatial surface for a single data layer."""

    def __init__(self, layer_name: str, method: str = "rbf"):
        self.layer_name = layer_name
        self.method = method
        self._interpolator = None
        self._mean = None
        self._std = None
        self._n_points = 0

        result = _extract_layer_points(layer_name)
        if result is None:
            raise ValueError(f"Insufficient data for layer '{layer_name}'")

        coords, values = result
        self._n_points = len(coords)
        self._mean = float(np.mean(values))
        self._std = float(np.std(values))

        if method == "rbf":
            self._interpolator = RBFInterpolator(
                coords, values,
                kernel="thin_plate_spline",
                smoothing=1.0,
            )
        elif method == "idw":
            self._coords = coords
            self._values = values
        else:
            raise ValueError(f"Unknown method: {method}")

    def query(self, lat: float, lon: float) -> float:
        """Interpolate value at a single point."""
        if self.method == "rbf":
            result = self._interpolator(np.array([[lat, lon]]))[0]
            return float(result)
        elif self.method == "idw":
            return self._idw_query(lat, lon)
        raise ValueError(f"Unknown method: {self.method}")

    def query_batch(self, coords: np.ndarray) -> np.ndarray:
        """Interpolate values at multiple points. coords shape: (N, 2)."""
        if self.method == "rbf":
            return self._interpolator(coords)
        elif self.method == "idw":
            return np.array([self._idw_query(c[0], c[1]) for c in coords])
        raise ValueError(f"Unknown method: {self.method}")

    def _idw_query(self, lat: float, lon: float, power: float = 2.0) -> float:
        """Inverse Distance Weighting interpolation."""
        dists = np.sqrt((self._coords[:, 0] - lat) ** 2 + (self._coords[:, 1] - lon) ** 2)
        # Handle exact match
        exact = np.where(dists < 1e-10)[0]
        if len(exact) > 0:
            return float(self._values[exact[0]])
        weights = 1.0 / (dists ** power)
        return float(np.sum(weights * self._values) / np.sum(weights))

    @property
    def stats(self) -> dict:
        return {
            "layer": self.layer_name,
            "method": self.method,
            "n_points": self._n_points,
            "mean": round(self._mean, 2),
            "std": round(self._std, 2),
        }


# Surface cache — avoid rebuilding on every request
_surface_cache: dict[str, SpatialSurface] = {}


def get_surface(layer_name: str, method: str = "rbf") -> SpatialSurface:
    """Get or create an interpolated surface for a data layer."""
    key = f"{layer_name}:{method}"
    if key not in _surface_cache:
        _surface_cache[key] = SpatialSurface(layer_name, method)
        logger.info("Built spatial surface: %s (%d points)", key, _surface_cache[key]._n_points)
    return _surface_cache[key]


def clear_cache():
    """Clear the surface cache (call after data reload)."""
    _surface_cache.clear()


def interpolate_at(lat: float, lon: float, layer_name: str, method: str = "rbf") -> float:
    """Convenience: interpolate a single layer at a single point."""
    surface = get_surface(layer_name, method)
    return surface.query(lat, lon)


def available_layers() -> list[str]:
    """List all layers that have enough data points for interpolation."""
    layers = []

    # City-level layers
    for name in ["air_quality", "cost_of_living"]:
        if _extract_layer_points(name) is not None:
            layers.append(name)

    # Health metrics
    for metric in ["diabetesRate", "obesityRate", "ckdRate", "hypertensionRate", "smokingRate"]:
        name = f"health_{metric}"
        if _extract_layer_points(name) is not None:
            layers.append(name)

    # Center-level layers (per organ)
    organs = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
    for organ in organs:
        for prefix in ["wait_time_factor_", "mortality_factor_", "graft_survival_"]:
            name = f"{prefix}{organ}"
            if _extract_layer_points(name) is not None:
                layers.append(name)

    return layers
