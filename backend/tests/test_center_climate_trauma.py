"""Tests for per-center climate (#289) and trauma (#290) layers.

These replace the 22-point interpolation sources (climate was 35% of the
geographic score, interpolated from 22 hand-curated city values).
"""
import pytest

from services.data_loader import get_data
from services.spatial_interpolation import _extract_layer_points, interpolate_at


@pytest.fixture(autouse=True)
def _load(data):
    pass


class TestCenterClimate:
    def test_file_covers_centers(self):
        centers = get_data().center_climate.get("centers", {})
        assert len(centers) >= 240, f"only {len(centers)} climate scores"
        assert all(0 <= v <= 100 for v in centers.values())

    def test_calibration_recorded(self):
        """The derivation must document its fit against the hand-curated
        22-city scores (the loader strips _meta, so read the file)."""
        import json
        from pathlib import Path
        path = Path(__file__).parent.parent.parent / "data" / "climate-scores-centers.json"
        meta = json.loads(path.read_text())["_meta"]
        assert meta["calibration"]["spearman"] >= 0.7

    def test_layer_uses_center_points(self):
        pts, vals = _extract_layer_points("climate")
        assert len(pts) >= 240, f"climate layer built from only {len(pts)} points"

    def test_mild_coast_beats_cold_midwest(self):
        """Semantic sanity: San Francisco area centers should score higher
        than Minneapolis-area centers (mild marine vs continental extremes)."""
        sf = interpolate_at(37.77, -122.42, "climate")
        msp = interpolate_at(44.98, -93.27, "climate")
        assert sf > msp, f"SF {sf} should beat Minneapolis {msp}"


class TestCenterTrauma:
    def test_file_covers_centers_and_states(self):
        d = get_data().center_trauma
        assert len(d.get("centers", {})) >= 240
        assert len(d.get("state_fatality_rates_per_100k", {})) >= 48

    def test_layer_uses_center_points(self):
        pts, vals = _extract_layer_points("trauma")
        assert len(pts) >= 240, f"trauma layer built from only {len(pts)} points"

    def test_known_rate_ordering(self):
        """Mississippi has among the highest traffic-fatality rates per capita;
        Massachusetts among the lowest (NHTSA state data, stable for years)."""
        rates = get_data().center_trauma["state_fatality_rates_per_100k"]
        assert rates["MS"] > rates["MA"] * 2
