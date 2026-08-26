"""Accrued waiting time input (#329).

Kidney waiting time backdates to dialysis start (or eGFR <= 20) and travels
with the patient; for other organs the clock runs from listing. Until now
the simulator could only answer "patient starting from zero." The
months_waiting input conditions the wait distribution on the time already
served: T_remaining ~ (T - t0 | T > t0), a left truncation of the SAME
lognormal — no new model, just the correct conditional of the existing one.

Honest subtlety (documented, not hidden): for heavy-tailed lognormals the
remaining-wait median can INCREASE with time served (the inspection
paradox — having waited long is evidence of being in the long tail). Tests
assert distributional correctness against the closed-form conditional CDF,
not an assumed monotonicity.
"""
import numpy as np
import pytest
import scipy.stats

from models.schemas import PatientProfile
from services.stats_utils import truncated_wait_times, conditional_p_within


@pytest.fixture(autouse=True)
def _load(data):
    pass


class TestConditionalMath:
    def test_truncated_samples_match_conditional_cdf(self):
        """Empirical CDF of (T - t0 | T > t0) must match
        (F(t0+x) - F(t0)) / (1 - F(t0))."""
        dist = scipy.stats.lognorm(s=0.8, scale=30.0)
        t0 = 24.0
        rng = np.random.default_rng(42)
        remaining = truncated_wait_times(dist, t0, size=200_000, rng=rng)
        assert np.all(remaining > 0)
        for x in (6.0, 12.0, 24.0, 48.0):
            emp = float(np.mean(remaining <= x))
            F = dist.cdf
            expected = (F(t0 + x) - F(t0)) / (1.0 - F(t0))
            assert emp == pytest.approx(expected, abs=0.01), f"x={x}"

    def test_zero_accrued_is_the_unconditional_distribution(self):
        dist = scipy.stats.lognorm(s=0.8, scale=30.0)
        rng = np.random.default_rng(1)
        samples = truncated_wait_times(dist, 0.0, size=100_000, rng=rng)
        assert float(np.median(samples)) == pytest.approx(30.0, rel=0.02)

    def test_conditional_p_within_closed_form(self):
        """conditional_p_within must equal the integral of the conditional
        density times competing-risk survival."""
        dist = scipy.stats.lognorm(s=0.7, scale=20.0)
        t0, horizon, hazard = 12.0, 24.0, 0.02
        p = conditional_p_within(dist, t0, horizon, hazard)
        # brute-force check by dense numerical integration
        x = np.linspace(1e-6, horizon, 20001)
        f_cond = dist.pdf(t0 + x) / dist.sf(t0)
        brute = np.trapezoid(f_cond * np.exp(-hazard * x), x)
        assert p == pytest.approx(float(brute), abs=1e-4)
        assert 0.0 <= p <= 1.0

    def test_t0_zero_matches_grid_p24(self):
        """At t0=0 the conditional integral reduces to the existing #216
        closed form."""
        from services.equity import _grid_p24
        dist = scipy.stats.lognorm(s=0.7, scale=20.0)
        hazard = 0.03
        assert conditional_p_within(dist, 0.0, 24.0, hazard) == pytest.approx(
            _grid_p24(dist, hazard), abs=1e-6)


class TestSchemaAndEngine:
    def test_months_waiting_accepted_and_bounded(self):
        p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                           urgency=2, months_waiting=36.0)
        assert p.months_waiting == 36.0
        with pytest.raises(Exception):
            PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                           urgency=2, months_waiting=-1)

    def test_no_accrued_time_unchanged_bitwise(self):
        """months_waiting=None must leave the engine's draws untouched —
        existing results and seeds cannot shift."""
        from services.monte_carlo import simulate
        base_kwargs = dict(organ="kidney", blood_type="O+", age=45, sex="male",
                           urgency=2, cpra=20)
        a = simulate(PatientProfile(**base_kwargs), n_iterations=200, seed=9)
        b = simulate(PatientProfile(**base_kwargs, months_waiting=None),
                     n_iterations=200, seed=9)
        assert [(c.center_code, c.p_transplant_24mo) for c in a.cities] == \
               [(c.center_code, c.p_transplant_24mo) for c in b.cities]

    def test_accrued_time_changes_probabilities(self):
        from services.monte_carlo import simulate
        fresh = simulate(PatientProfile(organ="kidney", blood_type="O+", age=45,
                                        sex="male", urgency=2, cpra=20),
                         n_iterations=400, seed=9)
        served = simulate(PatientProfile(organ="kidney", blood_type="O+", age=45,
                                         sex="male", urgency=2, cpra=20,
                                         months_waiting=36.0),
                          n_iterations=400, seed=9)
        f = {c.center_code: c.p_transplant_24mo for c in fresh.cities}
        s = {c.center_code: c.p_transplant_24mo for c in served.cities}
        moved = sum(1 for c in f if c in s and f[c] != s[c])
        assert moved > 0.8 * len(f), "accrued time barely reaches the engine"

    def test_probabilities_stay_valid_under_extreme_accrual(self):
        from services.monte_carlo import simulate
        r = simulate(PatientProfile(organ="kidney", blood_type="O+", age=45,
                                    sex="male", urgency=2, cpra=20,
                                    months_waiting=120.0),
                     n_iterations=300, seed=3)
        for c in r.cities:
            assert 0.0 <= c.p_transplant_6mo <= c.p_transplant_12mo \
                <= c.p_transplant_24mo <= c.p_transplant_36mo <= 1.0
            assert c.median_wait_months > 0
