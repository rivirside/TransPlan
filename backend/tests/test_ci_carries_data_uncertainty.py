"""#296: `confidence_interval_95` must mean the same thing in both engines.

Measured 2026-08-27, before the fix. The Monte Carlo engine's interval came
from bootstrapping its own simulated outcomes, so it was *simulation* error
and nothing else:

  * NJBI, whose SRTR cohort is **2 patients**, got width 0.0252.
  * TXHS, whose cohort is **833**, got width 0.0254.
  * Across all 233 kidney centers the width spanned only 0.0156-0.0296, and
    that spread is p(1-p) curvature, not data quality.
  * Raising iterations 500 -> 5000 narrowed the band 0.076 -> 0.026.

So the default engine told a candidate that a two-patient center's estimate
was as precise as an 833-patient one, and offered to make both look more
precise by spending CPU. Meanwhile the BBN's field of the same name has meant
data-sampling uncertainty since #226 and correctly widens for sparse centers.

These tests pin the properties, not the numbers: an interval must respond to
how much data there is, and must NOT collapse as iterations rise.
"""
import pytest

from models.schemas import PatientProfile
from services import monte_carlo


def _patient(organ="kidney"):
    return PatientProfile(organ=organ, blood_type="O+", age=50, sex="male",
                          urgency=2)


def _by_code(result):
    return {c.center_code: c for c in result.cities}


def _width(city):
    lo, hi = city.confidence_interval_95
    return hi - lo


@pytest.fixture(scope="module")
def run_5000(data):
    return _by_code(monte_carlo.simulate(_patient(), n_iterations=5000, seed=3))


@pytest.fixture(scope="module")
def cohorts(data):
    """(sparsest, densest) kidney center codes with an observed cohort."""
    obs = data.srtr_observed_rates["kidney"]["centers"]
    sized = [(c, int(v.get("n") or 0)) for c, v in obs.items()]
    with_data = [t for t in sized if t[1] > 0]
    return min(with_data, key=lambda t: t[1]), max(sized, key=lambda t: t[1])


def test_a_sparse_center_gets_a_wider_interval_than_a_dense_one(run_5000, cohorts):
    (sparse, n_sparse), (dense, n_dense) = cohorts
    assert n_dense > n_sparse * 50, "fixture did not find a real contrast"
    w_sparse, w_dense = _width(run_5000[sparse]), _width(run_5000[dense])
    assert w_sparse > w_dense * 2, (
        f"{sparse} (n={n_sparse}) width {w_sparse:.4f} vs {dense} "
        f"(n={n_dense}) width {w_dense:.4f} — the interval is not responding "
        "to cohort size, which is the whole defect (#296)"
    )


def test_the_interval_does_not_collapse_when_iterations_rise(data, cohorts):
    """More compute must not look like more knowledge.

    A pure bootstrap shrinks as 1/sqrt(n); the data term does not move at all,
    so a sparse center's interval should be almost unchanged.
    """
    (sparse, _), _ = cohorts
    lo = _width(_by_code(monte_carlo.simulate(_patient(), n_iterations=500, seed=3))[sparse])
    hi = _width(_by_code(monte_carlo.simulate(_patient(), n_iterations=5000, seed=3))[sparse])
    assert hi > lo * 0.8, (
        f"10x the iterations shrank the sparse-center interval {lo:.4f} -> "
        f"{hi:.4f}; it is still dominated by simulation error"
    )


def test_the_widths_vary_by_much_more_than_curvature_alone(run_5000):
    """Before the fix the whole population spanned 1.9x, all of it p(1-p).
    Data quality varies far more than that across 233 centers."""
    widths = [_width(c) for c in run_5000.values()]
    assert max(widths) / min(widths) > 4.0, (
        f"width ratio across centers is only {max(widths)/min(widths):.1f}x — "
        "too flat to be carrying cohort information"
    )


def test_the_interval_still_brackets_the_estimate(run_5000):
    for c in run_5000.values():
        lo, hi = c.confidence_interval_95
        assert 0.0 <= lo <= c.p_transplant_24mo <= hi <= 1.0, c.center_code


def test_both_engines_agree_on_what_the_field_means(data):
    """The BBN has carried data uncertainty since #226. After #296 the Monte
    Carlo field is the same notion plus simulation error, so the two should be
    within an order of magnitude — not the 1:8 they were."""
    from services.bayesian_network import simulate_bbn
    p = _patient()
    mc = _by_code(monte_carlo.simulate(p, n_iterations=5000, seed=3))
    bb = _by_code(simulate_bbn(p))
    shared = set(mc) & set(bb)
    assert len(shared) > 100
    ratios = [_width(mc[c]) / _width(bb[c]) for c in shared if _width(bb[c]) > 0]
    ratios.sort()
    median = ratios[len(ratios) // 2]
    assert 0.2 < median < 5.0, (
        f"median MC/BBN interval-width ratio is {median:.2f}; one engine's "
        "confidence_interval_95 means something very different from the other's"
    )


def test_quadrature_not_addition(data):
    """Independent sources combine in quadrature. Addition would overstate,
    and the point of this change is to be honest, not merely wider."""
    import math
    from services.bayesian_network import _data_uncertainty_ci
    ci = monte_carlo._widen_for_data_uncertainty((0.40, 0.60), 0.50, "kidney", "")
    sim_half = 0.10
    data_half = _data_uncertainty_ci(0.50, 0, organ="kidney")
    expected = math.hypot(sim_half, data_half)
    assert abs((ci[1] - ci[0]) / 2 - expected) < 1e-9
    assert (ci[1] - ci[0]) / 2 < sim_half + data_half, "combined additively"
