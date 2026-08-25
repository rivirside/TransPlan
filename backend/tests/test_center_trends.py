"""Tests for per-center trend projections (#288).

Before this fix, trend adjustments (trend_years > 0) reached only the 52
centers mapped through the legacy 22-city list — the other ~196 centers
silently got no adjustment.
"""
import numpy as np
import pytest

from models.schemas import PatientProfile
from services.data_loader import get_data
from services.trends import get_center_trend_projection, get_center_trends
from services.monte_carlo import simulate


@pytest.fixture(autouse=True)
def _load(data):
    pass


@pytest.fixture
def kidney_patient() -> PatientProfile:
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                          urgency=2, cpra=20)


class TestCenterTrendData:
    def test_center_trends_loaded(self):
        centers = get_data().center_trends.get("centers", {})
        assert len(centers) > 200, f"only {len(centers)} centers have trend series"

    def test_series_shape(self):
        s = get_data().center_trends["centers"]["ALCH"]["kidney"]
        assert len(s["years"]) == len(s["median_wait_months"]) == len(s["mortality_rate"])
        assert len(s["years"]) >= 10  # 15 releases, minus any gaps


class TestCenterTrendProjection:
    def test_factors_clamped_and_neutral_default(self):
        for code in list(get_data().center_trends["centers"])[:50]:
            p = get_center_trend_projection("kidney", code, years_forward=2.0)
            for k in ("wait_time_factor", "mortality_factor", "delisting_factor"):
                assert 0.5 <= p[k] <= 2.0

    def test_unknown_center_neutral(self):
        p = get_center_trend_projection("kidney", "ZZZZ", years_forward=2.0)
        assert p == {"wait_time_factor": 1.0, "mortality_factor": 1.0,
                     "delisting_factor": 1.0}

    def test_zero_years_neutral(self):
        p = get_center_trend_projection("kidney", "ALCH", years_forward=0.0)
        assert p["wait_time_factor"] == 1.0

    def test_some_center_has_significant_trend(self):
        """With 15 releases of real data, at least one center should show a
        statistically significant projected change."""
        moved = 0
        for code in get_data().center_trends["centers"]:
            p = get_center_trend_projection("kidney", code, years_forward=3.0)
            if any(p[k] != 1.0 for k in p):
                moved += 1
        assert moved > 0, "no center trend ever fires — projection path is dead"


class TestCoverageBeyondLegacyMapping:
    def test_trend_adjustment_reaches_unmapped_centers(self, kidney_patient):
        """The 52/248 gap: centers outside the legacy city mapping must also
        get trend adjustments when their history supports one."""
        mapping = get_data().center_mapping.get("cities", {})
        mapped = set()
        for info in mapping.values():
            mapped.add(info.get("primary", ""))
            mapped.update(info.get("alternates", []))

        moved_unmapped = []
        for code in get_data().center_trends["centers"]:
            if code in mapped:
                continue
            p = get_center_trend_projection("kidney", code, years_forward=3.0)
            if any(p[k] != 1.0 for k in p):
                moved_unmapped.append(code)
        assert moved_unmapped, (
            "no unmapped center gets a trend adjustment — the 52/248 gap persists"
        )

    def test_simulate_trend_changes_unmapped_center(self, kidney_patient):
        """End to end: simulate with trend_years must move results at an
        unmapped center that has a firing trend."""
        mapping = get_data().center_mapping.get("cities", {})
        mapped = set()
        for info in mapping.values():
            mapped.add(info.get("primary", ""))
            mapped.update(info.get("alternates", []))
        target = None
        for code in get_data().center_trends["centers"]:
            if code in mapped:
                continue
            p = get_center_trend_projection("kidney", code, years_forward=3.0)
            if p["wait_time_factor"] != 1.0:
                target = code
                break
        if target is None:
            pytest.skip("no unmapped kidney center with a firing wait trend")

        base = simulate(kidney_patient, n_iterations=400, seed=42)
        trended = simulate(kidney_patient, n_iterations=400, seed=42, trend_years=3.0)
        b = {c.center_code: c.median_wait_months for c in base.cities}
        t = {c.center_code: c.median_wait_months for c in trended.cities}
        assert target in b and target in t
        assert b[target] != t[target], (
            f"{target}: trend_years had no effect at an unmapped center"
        )


class TestCenterTrendsDisplay:
    def test_get_center_trends_shape(self):
        t = get_center_trends("kidney", "ALCH")
        assert t is not None
        assert t["center_code"] == "ALCH"
        assert "wait_time_trend" in t and "sparklines" in t
        assert len(t["sparklines"]["years"]) >= 10
