"""Tests for scripts/run-parameter-recovery.py (#309) — the synthetic world
and observation machinery must be correct before the study's ceiling numbers
mean anything."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "param_recovery",
    Path(__file__).parent.parent.parent / "scripts" / "run-parameter-recovery.py",
)
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


class TestWorldAndObservation:
    def test_truth_monotone(self):
        """Higher true wait factor must mean lower true p12."""
        rng = np.random.default_rng(1)
        w = mod.make_world(rng)
        order = np.argsort(w["factors"])
        p = w["p12"][order]
        assert np.all(np.diff(p) <= 1e-9)

    def test_observation_censors_like_srtr(self):
        rng = np.random.default_rng(2)
        w = mod.make_world(rng)
        t = mod.observe_tables(w, rng)
        vals = [p for c in t["b10"].values() for p in c.values()]
        assert all(v == mod.sx.CENSORED or 0 < v <= 72.0 for v in vals)

    def test_infinite_cohort_recovers_truth(self):
        """With huge cohorts the pipeline must recover the true ranking
        almost perfectly — the noise, not the machinery, is the limit."""
        import scipy.stats
        rng = np.random.default_rng(3)
        w = mod.make_world(rng)
        w["n"] = np.full(mod.N_CENTERS, 20_000)
        t = mod.observe_tables(w, rng)
        hat = mod.run_pipeline(t)
        idx = sorted(hat["p12_hat"])
        rho = scipy.stats.spearmanr(
            w["p12"][idx], [hat["p12_hat"][i] for i in idx]).statistic
        assert rho > 0.99

    def test_tiny_cohorts_degrade(self):
        import scipy.stats
        rng = np.random.default_rng(4)
        w = mod.make_world(rng)
        w["n"] = np.full(mod.N_CENTERS, 15)
        t = mod.observe_tables(w, rng)
        hat = mod.run_pipeline(t)
        idx = sorted(hat["p12_hat"])
        rho = scipy.stats.spearmanr(
            w["p12"][idx], [hat["p12_hat"][i] for i in idx]).statistic
        assert rho < 0.9  # visibly noise-limited
