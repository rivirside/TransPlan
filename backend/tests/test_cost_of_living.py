"""Cost-of-living upgrade (#205): BEA RPP snapshot + exact center lookup."""
import numpy as np
import pytest

from services.data_loader import TransPlanData
from services.spatial_interpolation import _extract_layer_points


# ── Snapshot shape (real committed data) ─────────────────────────────────

class TestSnapshotShape:
    def test_msa_coverage(self, data):
        msas = data.cost_of_living.get("msas", {})
        assert len(msas) >= 300, "BEA MARPP covers ~387 metro areas"

    def test_state_coverage(self, data):
        states = data.cost_of_living.get("states", {})
        assert len(states) >= 51, "50 states + DC"

    def test_values_plausible(self, data):
        col = data.cost_of_living
        values = [m["rpp"] for m in col["msas"].values()] + list(col["states"].values())
        assert all(60 <= v <= 160 for v in values)

    def test_nonmetro_us_present(self, data):
        assert isinstance(data.cost_of_living.get("nonmetroUS"), (int, float))

    def test_legacy_city_block(self, data):
        cities = data.cost_of_living.get("cities", {})
        assert len(cities) >= 20
        assert all(isinstance(v, (int, float)) for v in cities.values())


class TestCenterCbsaMap:
    def test_every_center_mapped(self, data):
        centers = data.all_centers.get("centers", {})
        mapping = data.center_cbsa_map.get("centers", {})
        missing = set(centers) - set(mapping)
        assert not missing, f"centers without CBSA mapping: {sorted(missing)}"

    def test_metro_centers_have_rpp(self, data):
        """Every metro-mapped center's CBSA must exist in the RPP snapshot.

        Exception: Puerto Rico — BEA RPP covers neither its metros nor the
        territory itself, so PR centers fall through to the US nonmetro RPP
        (documented in the clinical-assumptions register).
        """
        msas = data.cost_of_living.get("msas", {})
        unmatched = [
            code for code, m in data.center_cbsa_map.get("centers", {}).items()
            if m.get("cbsa_type") == "metro" and m["cbsa"] not in msas
            and m.get("state_abbr") != "PR"
        ]
        assert not unmatched, f"metro centers with no MSA RPP: {unmatched}"


# ── Lookup chain ─────────────────────────────────────────────────────────

class TestCostOfLivingForCenter:
    def _data(self):
        d = TransPlanData()
        d.cost_of_living = {
            "msas": {"13820": {"name": "Birmingham, AL", "rpp": 89.4}},
            "states": {"AL": 87.8, "NH": 105.4},
            "nonmetroUS": 88.7,
        }
        d.center_cbsa_map = {"centers": {
            "METRO1": {"state_abbr": "AL", "cbsa": "13820", "cbsa_type": "metro"},
            "MICRO1": {"state_abbr": "NH", "cbsa": "30100", "cbsa_type": "micro"},
            "RURAL1": {"state_abbr": None, "cbsa": None, "cbsa_type": "none"},
        }}
        return d

    def test_metro_exact_match(self):
        assert self._data().cost_of_living_for_center("METRO1") == 89.4

    def test_micro_falls_back_to_state(self):
        # Micropolitan CBSAs have no BEA MARPP row → state RPP
        assert self._data().cost_of_living_for_center("MICRO1") == 105.4

    def test_unmapped_center_uses_caller_state(self):
        assert self._data().cost_of_living_for_center("UNKNOWN", state_abbr="AL") == 87.8

    def test_no_state_falls_back_to_nonmetro_us(self):
        assert self._data().cost_of_living_for_center("RURAL1") == 88.7

    def test_empty_snapshot_returns_none(self):
        d = TransPlanData()
        assert d.cost_of_living_for_center("ANY") is None

    def test_real_data_all_centers_resolve(self, data):
        """With the committed snapshot, every real center gets a real RPP."""
        for code in data.all_centers.get("centers", {}):
            rpp = data.cost_of_living_for_center(code)
            assert rpp is not None and 60 <= rpp <= 160, f"{code}: {rpp}"


# ── Spatial layer ────────────────────────────────────────────────────────

class TestSpatialLayer:
    def test_layer_uses_msa_points(self, data):
        result = _extract_layer_points("cost_of_living")
        assert result is not None
        coords, values = result
        assert len(values) >= 300, "layer should use ~387 MSA points, not 22 cities"
        assert np.all((values >= 60) & (values <= 160))
