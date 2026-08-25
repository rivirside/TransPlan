"""Tests for scripts/run-panel-variance.py (#317) — the ANOVA machinery must
recover known variance components before the empirical priors mean anything."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "panel_variance",
    Path(__file__).parent.parent.parent / "scripts" / "run-panel-variance.py",
)
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def _synthetic(k=600, t=13, sigma_c=0.3, sigma_e=0.15, seed=1):
    rng = np.random.default_rng(seed)
    effects = rng.normal(0, sigma_c, size=k)
    return [rng.normal(e, sigma_e, size=t) for e in effects]


class TestAnovaRecovery:
    def test_recovers_known_components(self):
        groups = _synthetic(sigma_c=0.3, sigma_e=0.15)
        r = mod.anova_components(groups)
        assert r["sigma_center"] == pytest.approx(0.3, rel=0.15)
        assert r["sigma_within"] == pytest.approx(0.15, rel=0.15)
        true_frac = 0.3**2 / (0.3**2 + 0.15**2)
        assert r["frac_signal"] == pytest.approx(true_frac, abs=0.06)

    def test_pure_noise_gives_zero_signal(self):
        rng = np.random.default_rng(2)
        groups = [rng.normal(0, 0.2, size=13) for _ in range(120)]
        r = mod.anova_components(groups)
        assert r["frac_signal"] < 0.1

    def test_pure_signal_gives_one(self):
        rng = np.random.default_rng(3)
        effects = rng.normal(0, 0.3, size=80)
        groups = [np.full(13, e) + rng.normal(0, 1e-6, 13) for e in effects]
        r = mod.anova_components(groups)
        assert r["frac_signal"] > 0.99

    def test_unbalanced_panel_handled(self):
        rng = np.random.default_rng(4)
        groups = [rng.normal(rng.normal(0, 0.3), 0.15, size=n)
                  for n in rng.integers(8, 14, size=100)]
        r = mod.anova_components(groups)
        assert 0.5 < r["frac_signal"] < 0.95

    def test_detrend_removes_drift_inflation(self):
        """Per-center linear drift must inflate the RAW within-variance but
        not the detrended one."""
        rng = np.random.default_rng(5)
        base = _synthetic(sigma_c=0.3, sigma_e=0.10, seed=5)
        slopes = rng.normal(0, 0.03, size=len(base))
        drifted = [g + s * np.arange(len(g)) for g, s in zip(base, slopes)]
        raw = mod.anova_components(drifted)
        det = mod.anova_components(mod.detrend(drifted))
        assert det["sigma_within"] < raw["sigma_within"]
        assert det["frac_signal"] > raw["frac_signal"]
