"""Property-based invariant suite (#312).

Encodes invariants that must hold for ANY input and lets Hypothesis hunt the
input space, catching the bug class that fixed spot-checks structurally miss
(inverted comparisons, clamp gaps, falsy-zero handling, unit slips).

Fast closed-form surfaces get wide fuzzing; the full Monte Carlo engine gets
a few examples with small iteration counts (its invariants are cheap to state
but expensive to evaluate).
"""
import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from models.schemas import PatientProfile

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
BLOOD_TYPES = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]

# Shared fast-profile: no deadline (first-call data loads), modest examples.
FAST = settings(max_examples=60, deadline=None,
                suppress_health_check=[HealthCheck.function_scoped_fixture])
SLOW = settings(max_examples=6, deadline=None,
                suppress_health_check=[HealthCheck.function_scoped_fixture])


@pytest.fixture(autouse=True)
def _load(data):
    pass


organ_st = st.sampled_from(ORGANS)
bt_st = st.sampled_from(BLOOD_TYPES)
age_st = st.integers(min_value=18, max_value=80)
sex_st = st.sampled_from(["male", "female"])
cpra_st = st.integers(min_value=0, max_value=100)
meld_st = st.integers(min_value=6, max_value=40)
las_st = st.floats(min_value=0, max_value=100, allow_nan=False)


def _some_center(organ: str) -> str:
    from services.data_loader import get_data
    return get_data().centers_for_organ(organ)[0]["code"]


class TestWaitTimeParams:
    """distributions.get_wait_time_params — the multiplier chain everything
    else consumes."""

    @FAST
    @given(organ=organ_st, bt=bt_st, age=age_st, sex=sex_st,
           cpra=cpra_st, meld=meld_st, las=las_st)
    def test_params_positive_and_finite(self, organ, bt, age, sex, cpra, meld, las):
        from services.distributions import get_wait_time_params
        sigma, median = get_wait_time_params(
            organ, bt, cpra=cpra, meld=meld, las=las, age=age, sex=sex,
            center_code=_some_center(organ),
        )
        assert 0 < sigma < 5, f"sigma {sigma} out of sane range"
        assert 0 < median < 600, f"median {median} months out of sane range"
        assert np.isfinite(sigma) and np.isfinite(median)

    @FAST
    @given(bt=bt_st, age=age_st, sex=sex_st,
           lo=cpra_st, hi=cpra_st)
    def test_kidney_cpra_never_shortens_wait(self, bt, age, sex, lo, hi):
        """Higher sensitization can never DECREASE the modeled kidney wait."""
        from services.distributions import get_wait_time_params
        lo, hi = min(lo, hi), max(lo, hi)
        _, m_lo = get_wait_time_params("kidney", bt, cpra=lo, age=age, sex=sex)
        _, m_hi = get_wait_time_params("kidney", bt, cpra=hi, age=age, sex=sex)
        assert m_hi >= m_lo - 1e-9, (
            f"cPRA {lo}->{hi} shortened kidney wait: {m_lo} -> {m_hi}"
        )

    @FAST
    @given(organ=organ_st, bt=bt_st, cpra=cpra_st, meld=meld_st, las=las_st,
           age=age_st, sex=sex_st)
    def test_frozen_dist_matches_params(self, organ, bt, cpra, meld, las, age, sex):
        """The frozen distribution and the params path must never drift —
        equity's vectorized fast path depends on this equivalence."""
        from services.distributions import (
            get_lognorm_params, get_wait_time_distribution, get_wait_time_params,
        )
        code = _some_center(organ)
        sigma, median = get_wait_time_params(
            organ, bt, cpra=cpra, meld=meld, las=las, age=age, sex=sex,
            center_code=code)
        s, loc, scale = get_lognorm_params(get_wait_time_distribution(
            organ=organ, blood_type=bt, cpra=cpra, meld=meld, las=las,
            age=age, sex=sex, center_code=code))
        assert s == pytest.approx(sigma)
        assert scale == pytest.approx(median)
        assert loc == 0.0


class TestClosedFormWhatIf:
    """what_if closed-form: multiplier directions can never invert."""

    @FAST
    @given(organ=organ_st, bt=bt_st, age=age_st, sex=sex_st,
           wait_mult=st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
           donor_mult=st.floats(min_value=0.5, max_value=2.0, allow_nan=False))
    def test_probability_bounds_and_directions(self, organ, bt, age, sex,
                                               wait_mult, donor_mult):
        from services.what_if import compute_what_if_closed_form
        p = PatientProfile(organ=organ, blood_type=bt, age=age, sex=sex, urgency=2)
        r = compute_what_if_closed_form(
            p, _some_center(organ),
            donor_rate_multiplier=donor_mult, wait_time_multiplier=wait_mult,
        )
        assert 0.0 <= r["baseline_p24"] <= 1.0
        assert 0.0 <= r["adjusted_p24"] <= 1.0
        assert r["adjusted_median_wait"] > 0
        # Longer waits / fewer donors can never RAISE p24 (rounding tolerance)
        if wait_mult >= 1.0 and donor_mult <= 1.0:
            assert r["adjusted_p24"] <= r["baseline_p24"] + 1e-4
        if wait_mult <= 1.0 and donor_mult >= 1.0:
            assert r["adjusted_p24"] >= r["baseline_p24"] - 1e-4

    @FAST
    @given(organ=organ_st, bt=bt_st)
    def test_neutral_multipliers_zero_delta(self, organ, bt):
        from services.what_if import compute_what_if_closed_form
        p = PatientProfile(organ=organ, blood_type=bt, age=45, sex="male", urgency=2)
        r = compute_what_if_closed_form(p, _some_center(organ))
        assert r["delta_p24"] == 0.0


class TestGridP24:
    @FAST
    @given(median=st.floats(min_value=0.5, max_value=200, allow_nan=False),
           sigma=st.floats(min_value=0.1, max_value=2.0, allow_nan=False),
           h1=st.floats(min_value=1e-4, max_value=1.0, allow_nan=False),
           h2=st.floats(min_value=1e-4, max_value=1.0, allow_nan=False))
    def test_bounded_and_decreasing_in_hazard(self, median, sigma, h1, h2):
        """P(transplant first, <=24mo) is a probability and can only shrink
        as the competing hazard grows."""
        import scipy.stats
        from services.equity import _grid_p24
        dist = scipy.stats.lognorm(s=sigma, scale=median)
        lo, hi = min(h1, h2), max(h1, h2)
        p_lo_hazard = _grid_p24(dist, lo)
        p_hi_hazard = _grid_p24(dist, hi)
        assert 0.0 <= p_hi_hazard <= p_lo_hazard <= 1.0


class TestMonteCarloEngine:
    """Full-engine invariants: few examples, small iteration counts."""

    @SLOW
    @given(organ=organ_st, bt=bt_st, age=age_st)
    def test_horizons_monotonic_and_bounded(self, organ, bt, age):
        from services.monte_carlo import simulate
        p = PatientProfile(organ=organ, blood_type=bt, age=age, sex="male",
                           urgency=2)
        result = simulate(p, n_iterations=150, seed=7)
        assert result.cities, "no centers returned"
        for c in result.cities:
            assert 0.0 <= c.p_transplant_6mo <= c.p_transplant_12mo \
                <= c.p_transplant_24mo <= c.p_transplant_36mo <= 1.0, (
                    f"{c.center_code}: horizons not monotonic"
                )
            assert c.median_wait_months > 0

    def test_shortlist_isolation(self):
        """Filtering to a shortlist must not change the values of the
        centers that remain (same seed)."""
        from services.monte_carlo import simulate
        p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                           urgency=2)
        full = simulate(p, n_iterations=150, seed=11)
        codes = [c.center_code for c in full.cities[:4]]
        p.center_codes = codes
        short = simulate(p, n_iterations=150, seed=11)
        full_map = {c.center_code: c.p_transplant_24mo for c in full.cities}
        for c in short.cities:
            assert c.p_transplant_24mo == full_map[c.center_code], (
                f"{c.center_code}: value changed under shortlist filtering"
            )

    def test_seed_determinism(self):
        from services.monte_carlo import simulate
        p = PatientProfile(organ="liver", blood_type="A+", age=50, sex="female",
                           urgency=2, meld=22)
        a = simulate(p, n_iterations=150, seed=3)
        b = simulate(p, n_iterations=150, seed=3)
        assert [(c.center_code, c.p_transplant_24mo) for c in a.cities] == \
               [(c.center_code, c.p_transplant_24mo) for c in b.cities]
