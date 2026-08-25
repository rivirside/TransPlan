"""Tests for scripts/run-cas-dispersion.py (#349) — the level-shift and
detrending machinery must behave correctly on synthetic data before the
report's conclusions mean anything."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "cas_dispersion",
    Path(__file__).parent.parent.parent / "scripts" / "run-cas-dispersion.py",
)
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def _series(values):
    return {f"r{i:02d}": {"cv": float(v)} for i, v in enumerate(values)}


class TestDispersionMetrics:
    def test_gini_bounds(self):
        assert mod._gini(np.array([50.0, 50.0, 50.0])) == pytest.approx(0.0, abs=1e-9)
        near_max = mod._gini(np.array([0.0] * 99 + [100.0]))
        assert 0.9 < near_max <= 1.0

    def test_dispersion_keys(self):
        d = mod.dispersion([30.0, 50.0, 70.0])
        assert set(d) == {"n_centers", "cv", "iqr_over_median", "gini"}
        assert d["n_centers"] == 3 and d["cv"] > 0


class TestLevelShift:
    def test_detects_synthetic_step(self):
        s = _series([1.0] * 7 + [0.5] * 7)
        r = mod.level_shift(s, "r07")
        assert r["shift"] == pytest.approx(-0.5)
        assert r["p_perm"] < 0.01

    def test_flat_series_no_shift(self):
        s = _series([1.0] * 14)
        r = mod.level_shift(s, "r07")
        assert r["shift"] == pytest.approx(0.0)

    def test_detrended_kills_pure_trend(self):
        """A pure linear decline must NOT register as a boundary step after
        detrending — this is the guard against the secular-trend artifact
        that fooled the naive test on the real data."""
        s = _series(np.linspace(1.0, 0.3, 14))
        naive = mod.level_shift(s, "r07")
        detr = mod.level_shift_detrended(s, "r07")
        assert naive["p_perm"] < 0.01           # naive test IS fooled
        assert abs(detr["shift"]) < 0.02        # detrended is not
        assert detr["p_perm"] > 0.2

    def test_detrended_preserves_real_step(self):
        """Trend + genuine step: detrending must still show the step."""
        trend = np.linspace(1.0, 0.7, 14)
        step = np.array([0.0] * 7 + [-0.3] * 7)
        s = _series(trend + step)
        detr = mod.level_shift_detrended(s, "r07")
        assert detr["shift"] < -0.05
        # The detrended test is CONSERVATIVE: a real step partially absorbs
        # into the fitted slope, inflating p (here ~0.08 at n=14). That
        # conservatism strengthens the real-data conclusion (p ~0.9 there).
        assert detr["p_perm"] < 0.15
