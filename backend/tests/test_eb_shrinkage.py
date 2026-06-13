"""#268: empirical-Bayes shrinkage of noisy small-volume center factors.

Low-volume centers have unstable mortality/delisting factors (e.g. 0.37 vs
1.82); shrinking them toward the organ baseline (1.0) in proportion to cohort
size stabilizes per-center estimates. The shrinkage strength K is the median
cohort size (data-derived, not a magic constant)."""
import math

import pytest

from services.data_loader import load_all

load_all()


class TestShrinkFactor:
    def test_high_volume_barely_moves(self):
        from services.competing_risks import _shrink_factor
        # n >> K → weight ~1 → factor essentially unchanged.
        assert _shrink_factor(2.0, n=10000, K=100) == pytest.approx(2.0, abs=0.05)

    def test_low_volume_pulled_toward_baseline(self):
        from services.competing_risks import _shrink_factor
        # n << K → weight ~0 → factor pulled toward 1.0.
        shrunk = _shrink_factor(2.0, n=2, K=100)
        assert 1.0 < shrunk < 1.2

    def test_low_volume_closer_to_baseline_than_high_volume(self):
        from services.competing_risks import _shrink_factor
        low = _shrink_factor(0.4, n=5, K=100)    # protective extreme, tiny cohort
        high = _shrink_factor(0.4, n=5000, K=100)
        assert abs(low - 1.0) < abs(high - 1.0)

    def test_log_space_symmetry_at_n_equals_k(self):
        from services.competing_risks import _shrink_factor
        # At n == K, weight = 0.5 → geometric half-way to 1.0: sqrt(factor).
        assert _shrink_factor(4.0, n=100, K=100) == pytest.approx(math.sqrt(4.0), abs=1e-6)

    def test_degenerate_inputs_passthrough(self):
        from services.competing_risks import _shrink_factor
        assert _shrink_factor(1.5, n=0, K=100) == 1.5   # no cohort info
        assert _shrink_factor(1.5, n=50, K=0) == 1.5     # no prior strength
        assert _shrink_factor(0.0, n=50, K=100) == 0.0   # guard nonpositive


class TestShrinkageStrength:
    def test_k_is_positive_median_cohort(self):
        from services.competing_risks import _shrinkage_K
        K = _shrinkage_K("kidney")
        assert K > 0

    def test_center_adjustment_shrinks_a_low_volume_center(self):
        """A low-volume center's stored factor should be pulled toward 1.0 by
        _center_adjustment relative to its raw stored value."""
        from services.competing_risks import _center_adjustment, _raw_center_adjustment
        from services.data_loader import get_data
        d = get_data()
        # Find a kidney center with a small cohort and a non-trivial factor.
        target = None
        for code, organs in d.center_competing_risks.get("center_adjustments", {}).items():
            raw = organs.get("kidney", {})
            rec = d.observed_outcome("kidney", code)
            n = int(rec["n"]) if rec and rec.get("n") else 0
            mf = raw.get("mortality_factor")
            if n and 0 < n <= 20 and mf and abs(mf - 1.0) > 0.3:
                target = (code, n, mf)
                break
        assert target, "expected at least one low-volume kidney center with an extreme factor"
        code, n, raw_mf = target
        shrunk = _center_adjustment(code, "kidney")["mortality_factor"]
        # Shrunk value is strictly between the raw factor and the baseline 1.0.
        assert abs(shrunk - 1.0) < abs(raw_mf - 1.0)
