"""#266/#253: Gaussian-process (kriging) interpolation with prediction
uncertainty, convex-hull extrapolation guard, and output clamping."""
import pytest

from services.data_loader import load_all
from services.spatial_interpolation import get_surface, clear_cache

load_all()


@pytest.fixture(scope="module")
def kriging_surface():
    clear_cache()
    return get_surface("air_quality", method="kriging")


class TestKriging:
    def test_query_is_clamped_to_observed_range(self, kriging_surface):
        s = kriging_surface
        v = s.query(36.16, -86.78)  # Nashville
        assert s._vmin <= v <= s._vmax

    def test_query_with_uncertainty_returns_positive_std(self, kriging_surface):
        _, std = kriging_surface.query_with_uncertainty(36.16, -86.78)
        assert std > 0

    def test_in_hull_detection(self, kriging_surface):
        assert kriging_surface.in_hull(39.0, -95.0) is True   # central US
        assert kriging_surface.in_hull(24.5, -67.0) is False  # off the SE coast

    def test_extrapolation_is_more_uncertain_and_still_clamped(self, kriging_surface):
        s = kriging_surface
        _, std_in = s.query_with_uncertainty(39.0, -95.0)        # inside data hull
        val_out, std_out = s.query_with_uncertainty(24.5, -67.0)  # outside hull
        assert std_out >= std_in
        assert s._vmin <= val_out <= s._vmax
