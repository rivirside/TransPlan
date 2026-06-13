"""#268: Gamma-Poisson empirical-Bayes shrinkage of noisy per-center
mortality/delisting factors, computed from raw rates + cohort exposure.

Replaces the old raw-rate-ratio-clamped-to-[0.3,3.0] approach, whose hard
clamp piled ~28% of centers onto the 0.3 floor (mostly zero-event small
centers). EB pulls low-information centers toward the organ rate (factor 1.0)
by a data-derived amount; high-volume centers keep their signal."""
import statistics as st

import pytest

from services.data_loader import load_all, get_data

load_all()


class TestGammaPoissonEB:
    def test_no_between_variance_collapses_to_one(self):
        from services.competing_risks import _gamma_poisson_eb
        # All units share the same rate → no real between-unit signal → all 1.0.
        events = [5.0, 10.0, 2.0]
        exposure = [5.0, 10.0, 2.0]  # rate = 1.0 everywhere
        assert _gamma_poisson_eb(events, exposure) == pytest.approx([1.0, 1.0, 1.0])

    def test_high_exposure_keeps_signal_low_exposure_shrinks(self):
        from services.competing_risks import _gamma_poisson_eb
        # Mostly rate~1 units to establish the prior, plus two rate~3 outliers:
        # one with tiny exposure (should shrink toward 1) and one with large
        # exposure (should keep more of its 3x signal).
        rows = [(1.0, 50.0)] * 20 + [(3.0, 1.0), (3.0, 200.0)]  # (rate, exposure)
        events = [r * e for r, e in rows]
        exposure = [e for _, e in rows]
        ratios = _gamma_poisson_eb(events, exposure)
        small_ratio, big_ratio = ratios[-2], ratios[-1]
        assert small_ratio < big_ratio          # tiny center shrunk harder
        assert big_ratio > 1.5                   # high-exposure outlier keeps signal
        assert small_ratio < 1.8                 # tiny outlier pulled well down


class TestCenterFactorsFromData:
    def test_zero_event_small_center_shrinks_toward_one_not_floor(self):
        """The key fix: a small center with zero observed delistings used to be
        clamped to the 0.3 floor; EB pulls it toward ~1.0 (no signal)."""
        from services.competing_risks import _center_adjustment
        d = get_data()
        target = None
        for code in d.center_competing_risks.get("center_adjustments", {}):
            rec = d.observed_outcome("kidney", code)
            if rec and rec.get("n") and 0 < int(rec["n"]) <= 25 and (rec.get("delisting_rate") or 0.0) == 0.0:
                target = code
                break
        assert target, "expected a small kidney center with zero observed delistings"
        df = _center_adjustment(target, "kidney")["delisting_factor"]
        assert df > 0.6, f"zero-event center should shrink toward 1.0, got {df}"

    def test_factors_centered_near_one(self):
        from services.competing_risks import _eb_factor_table
        table = _eb_factor_table("kidney")
        assert len(table) > 100
        mfs = [v["mortality_factor"] for v in table.values()]
        assert all(f > 0 for f in mfs)
        assert 0.85 < st.median(mfs) < 1.15  # ratios are centered around 1.0

    def test_eb_less_extreme_than_raw_clamped(self):
        """EB factors should be less dispersed than the raw clamped ratios
        (the whole point: stop the boundary pile-ups)."""
        from services.competing_risks import _eb_factor_table, _raw_center_adjustment
        table = _eb_factor_table("kidney")
        raw, eb = [], []
        for code, v in table.items():
            r = _raw_center_adjustment(code, "kidney")
            if r.get("mortality_factor"):
                raw.append(r["mortality_factor"])
                eb.append(v["mortality_factor"])
        assert st.pstdev(eb) < st.pstdev(raw)
