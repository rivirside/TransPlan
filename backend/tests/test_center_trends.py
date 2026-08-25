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

    def test_series_shape(self, pick_center):
        code = pick_center("kidney", trends=True)
        s = get_data().center_trends["centers"][code]["kidney"]
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

    def test_zero_years_neutral(self, pick_center):
        p = get_center_trend_projection("kidney", pick_center("kidney", trends=True),
                                        years_forward=0.0)
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
    def test_trend_adjustment_reaches_many_centers(self, kidney_patient):
        """The old city mapping reached only 52/248 centers; per-center trends
        must fire for far more than that (#288/#293)."""
        moved = [
            code for code in get_data().center_trends["centers"]
            if any(v != 1.0 for v in
                   get_center_trend_projection("kidney", code, years_forward=3.0).values())
        ]
        assert len(moved) > 52, (
            f"only {len(moved)} centers get trend adjustments — no better than "
            "the legacy 52-center mapping"
        )

    def test_simulate_trend_changes_center(self, kidney_patient):
        """End to end: simulate with trend_years must move results at a
        center that has a firing trend."""
        target = None
        for code in get_data().center_trends["centers"]:
            p = get_center_trend_projection("kidney", code, years_forward=3.0)
            if p["wait_time_factor"] != 1.0:
                target = code
                break
        if target is None:
            pytest.skip("no kidney center with a firing wait trend")

        base = simulate(kidney_patient, n_iterations=400, seed=42)
        trended = simulate(kidney_patient, n_iterations=400, seed=42, trend_years=3.0)
        b = {c.center_code: c.median_wait_months for c in base.cities}
        t = {c.center_code: c.median_wait_months for c in trended.cities}
        assert target in b and target in t
        assert b[target] != t[target], (
            f"{target}: trend_years had no effect at an unmapped center"
        )


class TestCenterTrendsDisplay:
    def test_get_center_trends_shape(self, pick_center):
        code = pick_center("kidney", trends=True)
        t = get_center_trends("kidney", code)
        assert t is not None
        assert t["center_code"] == code
        assert "wait_time_trend" in t and "sparklines" in t
        assert len(t["sparklines"]["years"]) >= 10
