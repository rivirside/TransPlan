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
from scipy.spatial import Delaunay

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

    Prefers dense data sources (county-level, monitor-level) when available,
    falling back to city-level aggregates (~22 points).

    Returns:
        (coords, values) where coords is (N, 2) array of [lat, lon]
        and values is (N,) array. Returns None if insufficient data.
    """
    data = get_data()
    points = []
    values = []

    if layer_name == "air_quality":
        # Prefer per-monitor data (~2000-4000 points) over city aggregates (~22)
        monitors = data.air_quality_monitors.get("monitors", [])
        if monitors:
            for m in monitors:
                lat, lon, score = m.get("lat"), m.get("lon"), m.get("score")
                if lat is not None and lon is not None and score is not None:
                    points.append((lat, lon))
                    values.append(float(score))
        else:
            # Fallback: city-level aggregates
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
        # Prefer county-level data (~3000 points) over city aggregates (~22)
        counties = data.health_demographics_counties.get("counties", {})
        if counties:
            for fips, county in counties.items():
                if not isinstance(county, dict):
                    continue
                lat, lon = county.get("lat"), county.get("lon")
                val = county.get(metric)
                if lat is not None and lon is not None and val is not None:
                    points.append((lat, lon))
                    values.append(float(val))
        if not points:
            # Fallback: city-level aggregates
            for city, city_data in data.health_demographics.items():
                if city in _CITY_COORDS and isinstance(city_data, dict):
                    val = city_data.get(metric)
                    if val is not None:
                        points.append(_CITY_COORDS[city])
                        values.append(float(val))

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

    elif layer_name == "climate":
        # Climate recovery scores from 22 focus cities
        for city, val in data.climate_scores.items():
            if city in _CITY_COORDS and isinstance(val, (int, float)):
                points.append(_CITY_COORDS[city])
                values.append(float(val))

    elif layer_name == "trauma":
        # Traffic/trauma scores from city data + accident hotspots
        traffic = data.traffic_fatalities
        trauma_scores = traffic.get("traumaScores", {})
        for city, val in trauma_scores.items():
            if city in _CITY_COORDS and isinstance(val, (int, float)):
                points.append(_CITY_COORDS[city])
                values.append(float(val))
        # Also include accident hotspot intensities (0-1 scale → 0-100)
        for hotspot in traffic.get("accidentHotspots", []):
            lat, lon = hotspot.get("lat"), hotspot.get("lon")
            intensity = hotspot.get("intensity")
            if lat is not None and lon is not None and intensity is not None:
                points.append((lat, lon))
                values.append(float(intensity) * 100)

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
        # Observed value range — used to clamp interpolated/extrapolated output
        # so a layer can never produce e.g. a negative rate or >100% (#253).
        self._vmin = float(np.min(values))
        self._vmax = float(np.max(values))
        self._coords = coords
        self._values = values
        # Convex hull of the data points — queries outside it are extrapolation.
        try:
            self._hull = Delaunay(coords) if len(coords) >= 4 else None
        except Exception:
            self._hull = None

        if method == "rbf":
            self._interpolator = RBFInterpolator(
                coords, values,
                kernel="thin_plate_spline",
                smoothing=1.0,
            )
        elif method == "idw":
            pass  # uses _coords/_values directly
        elif method == "kriging":
            self._fit_gp(coords, values)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _fit_gp(self, coords: np.ndarray, values: np.ndarray) -> None:
        """Fit a Gaussian-process regressor that yields prediction variance.

        Uses an anisotropic RBF kernel (independent length-scales per axis), so
        the distortion from treating lat/lon degrees as Cartesian is absorbed by
        the learned per-axis scales rather than biasing distances. Large layers
        are subsampled (GP fitting is O(n^3)); a smooth field needs far fewer
        than thousands of points.
        """
        try:
            from sklearn.gaussian_process import GaussianProcessRegressor
            from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
        except ImportError as e:
            # scikit-learn is a local/dev-tier dependency (too heavy for the
            # Vercel Lambda bundle). Surface a clean error the router turns
            # into a 400 rather than a 500.
            raise ValueError(
                "kriging interpolation requires scikit-learn (local tier only); "
                "use method='rbf' or 'idw' on the hosted service"
            ) from e

        MAX_FIT = 800
        if len(coords) > MAX_FIT:
            rng = np.random.default_rng(0)
            idx = rng.choice(len(coords), size=MAX_FIT, replace=False)
            coords, values = coords[idx], values[idx]

        kernel = (
            ConstantKernel(1.0, (1e-2, 1e3))
            * RBF(length_scale=[2.0, 2.0], length_scale_bounds=(1e-1, 1e2))
            + WhiteKernel(noise_level=1.0, noise_level_bounds=(1e-3, 1e3))
        )
        self._gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True)
        self._gp.fit(coords, values)

    def in_hull(self, lat: float, lon: float) -> bool:
        """True if (lat, lon) lies within the convex hull of the data points."""
        if self._hull is None:
            return True
        return bool(self._hull.find_simplex(np.array([lat, lon])) >= 0)

    def _clamp(self, value: float) -> float:
        return min(max(value, self._vmin), self._vmax)

    def query_with_uncertainty(self, lat: float, lon: float) -> tuple[float, float]:
        """Return (value, std). Value is clamped to the observed range; std is
        the GP prediction standard deviation (kriging) and is widened for points
        that fall outside the data hull (extrapolation) (#266/#253)."""
        if self.method == "kriging":
            mean, std = self._gp.predict(np.array([[lat, lon]]), return_std=True)
            value, sd = float(mean[0]), float(std[0])
        else:
            value, sd = self.query(lat, lon), self._std
        if not self.in_hull(lat, lon):
            sd += self._std  # extrapolation: inflate uncertainty
        return self._clamp(value), sd

    def query(self, lat: float, lon: float) -> float:
        """Interpolate value at a single point."""
        if self.method == "rbf":
            result = self._interpolator(np.array([[lat, lon]]))[0]
            return float(result)
        elif self.method == "idw":
            return self._idw_query(lat, lon)
        elif self.method == "kriging":
            mean = self._gp.predict(np.array([[lat, lon]]))
            return self._clamp(float(mean[0]))
        raise ValueError(f"Unknown method: {self.method}")

    def query_batch(self, coords: np.ndarray) -> np.ndarray:
        """Interpolate values at multiple points. coords shape: (N, 2)."""
        if self.method == "rbf":
            return self._interpolator(coords)
        elif self.method == "idw":
            return np.array([self._idw_query(c[0], c[1]) for c in coords])
        elif self.method == "kriging":
            preds = self._gp.predict(coords)
            return np.clip(preds, self._vmin, self._vmax)
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
