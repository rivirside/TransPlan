"""Tests for the rate->median inversion gate (#335 phase 2).

The gate decides whether pediatric per-center wait factors may ship at all,
so its machinery must be correct before its verdict means anything.
"""
import importlib.util
from pathlib import Path

import pytest
import scipy.stats

_SPEC = importlib.util.spec_from_file_location(
    "pediatric_inversion",
    Path(__file__).parent.parent.parent / "scripts" / "run-pediatric-inversion.py",
)
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


class TestInversionMachinery:
    def test_roundtrip_recovers_known_median(self):
        """The core property: p_within then invert must return the input."""
        for median, sigma, hazard in ((36.0, 1.2, 0.01), (12.0, 0.9, 0.02),
                                      (2.2, 1.2, 0.05), (1.4, 1.14, 0.03)):
            rate = mod.p_within(median, sigma, hazard)
            back = mod.invert_rate(rate, sigma, hazard)
            assert back == pytest.approx(median, rel=0.02), (
                f"median {median} -> rate {rate:.4f} -> {back}"
            )

    def test_p_within_accurate_at_short_medians(self):
        """The bug this suite exists for: a fixed 241-point grid returns 0.45
        at median 0.05 where the true value is ~0.999, because the whole mass
        falls between the first two grid points. Adaptive integration must not
        have that failure."""
        val = mod.p_within(0.05, 1.2, 0.01)
        assert val > 0.99, f"short-median integration is wrong: {val}"

    def test_p_within_monotone_decreasing_in_median(self):
        prev = 1.1
        for median in (0.5, 1, 2, 6, 12, 24, 60, 200):
            v = mod.p_within(median, 1.2, 0.02)
            assert v < prev
            prev = v

    def test_unreachable_rate_returns_none(self):
        """A rate no finite median can produce must be refused, not clamped."""
        assert mod.invert_rate(0.9999999, 1.2, 5.0) is None
        assert mod.invert_rate(0.0, 1.2, 0.01) is None
        assert mod.invert_rate(1.0, 1.2, 0.01) is None

    def test_higher_hazard_lowers_achievable_rate(self):
        """With a stronger competing hazard the same median yields a lower
        transplant probability."""
        assert mod.p_within(12.0, 1.2, 0.20) < mod.p_within(12.0, 1.2, 0.01)


class TestGateArtifact:
    def test_gate_output_shape(self):
        """The pediatric pipeline reads organs_passing to decide per organ."""
        import json
        from pathlib import Path as P
        p = (P(__file__).parent.parent.parent / "docs-site" / "static" /
             "data" / "pediatric-inversion.json")
        if not p.exists():
            pytest.skip("gate not yet run")
        d = json.loads(p.read_text())
        assert "organs_passing" in d and isinstance(d["organs_passing"], list)
        assert "gate_passed" in d
        for organ, rec in d["organs"].items():
            assert "spearman" in rec and "passes_gate" in rec
            assert rec["passes_gate"] == (rec["spearman"] >= 0.70)
