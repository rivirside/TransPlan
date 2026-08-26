"""Tests for services/spatial_interpolation.py — spatial interpolation engine."""
import numpy as np
import pytest

from services.data_loader import load_all, get_data
from services.spatial_interpolation import (
    SpatialSurface,
    available_layers,
    clear_cache,
    get_surface,
    interpolate_at,
    _extract_layer_points,
)


@pytest.fixture(scope="module", autouse=True)
def _load_data():
    """Load data once for the entire test module."""
    load_all()
    clear_cache()


class TestLayerExtraction:
    def test_air_quality_has_points(self):
        result = _extract_layer_points("air_quality")
        assert result is not None
        coords, values = result
        assert len(coords) >= 15  # Most of 22 cities
        assert coords.shape[1] == 2
        assert len(values) == len(coords)

    def test_wait_time_factor_extraction_retired(self):
        """#252: extracting points for a center-outcome layer raises."""
        with pytest.raises(ValueError, match="retired"):
            _extract_layer_points("wait_time_factor_kidney")

    def test_invalid_layer_returns_none(self):
        result = _extract_layer_points("nonexistent_layer")
        assert result is None

    def test_health_metric_extraction(self):
        result = _extract_layer_points("health_diabetesRate")
        assert result is not None
        _, values = result
        # Diabetes rates should be in reasonable range (5-20%)
        assert all(3 < v < 25 for v in values)


class TestSpatialSurface:
    def test_rbf_at_known_point(self):
        """RBF should approximately reproduce known values at data points."""
        surface = SpatialSurface("air_quality", method="rbf")
        # Pittsburgh air quality is 77
        val = surface.query(40.4406, -79.9959)
        assert abs(val - 77) < 5  # Within 5 points of known value

    def test_idw_at_known_point(self, data):
        """IDW should exactly reproduce values at data points."""
        # cost_of_living points are BEA RPP values at MSA centroids (#205) —
        # query exactly at the Pittsburgh MSA centroid.
        centroid = data.cbsa_centroids["cbsas"]["38300"]
        expected = data.cost_of_living["msas"]["38300"]["rpp"]
        surface = SpatialSurface("cost_of_living", method="idw")
        val = surface.query(centroid["lat"], centroid["lon"])
        assert abs(val - expected) < 0.1  # IDW is exact at data points

    def test_interpolation_between_cities(self):
        """Value between two cities should be between their values."""
        surface = SpatialSurface("cost_of_living", method="rbf")
        # Midpoint between Pittsburgh (87) and Cleveland (84)
        mid_lat = (40.4406 + 41.4993) / 2
        mid_lon = (-79.9959 + -81.6944) / 2
        val = surface.query(mid_lat, mid_lon)
        # Should be in a reasonable range (not wildly extrapolated)
        assert 50 < val < 150

    def test_batch_query(self):
        surface = SpatialSurface("air_quality", method="rbf")
        coords = np.array([
            [40.4406, -79.9959],  # Pittsburgh
            [41.4993, -81.6944],  # Cleveland
            [39.96, -82.99],      # Columbus (interpolated)
        ])
        values = surface.query_batch(coords)
        assert len(values) == 3
        assert all(np.isfinite(values))

    def test_stats(self):
        surface = SpatialSurface("air_quality", method="rbf")
        stats = surface.stats
        assert stats["layer"] == "air_quality"
        assert stats["method"] == "rbf"
        assert stats["n_points"] > 0
        assert "mean" in stats
        assert "std" in stats

    def test_retired_layer_surface_rejected(self):
        """#252: constructing a surface from a center-outcome layer raises."""
        with pytest.raises(ValueError, match="retired"):
            SpatialSurface("wait_time_factor_kidney", method="rbf")

    def test_invalid_method(self):
        with pytest.raises(ValueError, match="Unknown method"):
            SpatialSurface("air_quality", method="invalid")

    def test_invalid_layer(self):
        with pytest.raises(ValueError, match="Insufficient data"):
            SpatialSurface("nonexistent_layer")


class TestCaching:
    def test_cache_returns_same_object(self):
        clear_cache()
        s1 = get_surface("air_quality")
        s2 = get_surface("air_quality")
        assert s1 is s2

    def test_clear_cache(self):
        clear_cache()
        s1 = get_surface("air_quality")
        clear_cache()
        s2 = get_surface("air_quality")
        assert s1 is not s2


class TestAvailableLayers:
    def test_has_city_level_layers(self):
        layers = available_layers()
        assert "air_quality" in layers
        assert "cost_of_living" in layers

    def test_has_health_layers(self):
        layers = available_layers()
        assert "health_diabetesRate" in layers
        assert "health_obesityRate" in layers

    def test_outcome_layers_retired(self):
        """#252: center-bound outcomes are not continuous fields — the
        layers must be gone from the listing AND rejected on request."""
        layers = available_layers()
        assert not any(l.startswith(("wait_time_factor_", "mortality_factor_",
                                     "graft_survival_")) for l in layers)
        with pytest.raises(ValueError, match="retired"):
            interpolate_at(40.44, -79.99, "wait_time_factor_kidney")

    def test_total_layer_count(self):
        layers = available_layers()
        # environmental + health layers only after #252 (was >=20 with the
        # invalid outcome layers included)
        assert len(layers) >= 7


class TestConvenienceFunction:
    def test_interpolate_at(self):
        val = interpolate_at(40.4406, -79.9959, "air_quality")
        assert isinstance(val, float)
        assert np.isfinite(val)
