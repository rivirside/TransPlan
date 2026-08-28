"""#233 / BBN-19: what the 12->24 month extension can and cannot reach.

Two properties, and both need pinning for opposite reasons.

**p24 is invariant** to the hazard-shape exponent, by algebra rather than by
a weak effect: `_extend_12_to_24` scales tx/death/removed by a common factor,
and `_combine_outcomes` uses only their ratio

    q = (death + delist) / (tx + death + delist)

so the factor cancels exactly. If someone reshapes the extension such that
p24 becomes alpha-dependent, that is a real change in what the headline
number means and should not pass silently.

**The breakdown is highly sensitive** — mortality spans 0.41x to 1.76x of
the shipped value across defensible exponents. That half is pinned because
the first version of the sweep measured p24 alone, saw a perfect null, and
would have concluded "this assumption does not matter". It matters a great
deal; the metric just could not see it. A test that only checked invariance
would enshrine exactly that mistake.

docs/horizon-extension-report.md
"""
import numpy as np
import pytest

from models.schemas import PatientProfile

ALPHAS = (1.0, 1.5, 2.5, 3.0)          # 2.0 is shipped


def _extender(alpha):
    def f(p12):
        tx, death, removed, wait = p12
        s24 = wait ** alpha
        den = 1.0 - wait
        factor = (1.0 - s24) / den if den > 1e-12 else 0.0
        return np.array([tx * factor, death * factor, removed * factor, s24])
    return f


@pytest.fixture
def sweep(data, monkeypatch):
    """Run the BBN under a given exponent, returning per-center outcomes."""
    import services.bbn_parameterizer as bp
    from services.bayesian_network import reset_model, simulate_bbn

    def run(alpha):
        if alpha is not None:
            monkeypatch.setattr(bp, "_extend_12_to_24", _extender(alpha))
        reset_model()
        patient = PatientProfile(organ="kidney", blood_type="O+", age=50,
                                 sex="male", urgency=2, bbn_granularity="state")
        cities = simulate_bbn(patient).cities
        return {c.center_code: {
            "p24": c.p_transplant_24mo,
            "mortality": c.competing_risks["p_mortality_24mo"],
            "waiting": c.competing_risks["p_still_waiting_24mo"],
        } for c in cities}

    yield run
    reset_model()


def test_the_headline_probability_is_invariant_to_the_hazard_shape(sweep):
    base = sweep(None)
    for alpha in ALPHAS:
        alt = sweep(alpha)
        worst = max(abs(base[c]["p24"] - alt[c]["p24"]) for c in base)
        assert worst < 1e-9, (
            f"alpha={alpha} moved p24 by {worst:.6f}. That used to be "
            "algebraically impossible: the extension scales tx/death/removed "
            "by a common factor and p24 depends only on their ratio. If the "
            "formula changed deliberately, docs/horizon-extension-report.md "
            "and register row BBN-19 both need revising."
        )


def test_the_extension_is_not_simply_inert(sweep):
    """Guard the guard.

    The invariance above would also hold if the extension stopped doing
    anything at all, or if CompetingOutcome stopped reaching the output. The
    breakdown must still respond, or the test above is measuring nothing.
    """
    base = sweep(None)
    low, high = sweep(1.0), sweep(3.0)
    mean = lambda d, k: float(np.mean([v[k] for v in d.values()]))

    assert mean(low, "mortality") < mean(base, "mortality") < mean(high, "mortality"), (
        "the outcome breakdown no longer responds to the hazard-shape "
        "exponent, so the invariance test above proves nothing"
    )
    ratio = mean(high, "mortality") / mean(low, "mortality")
    assert ratio > 2.0, (
        f"mortality spans only {ratio:.2f}x across alpha 1.0-3.0; it was "
        "~4.3x when measured. Either the extension was narrowed or the "
        "breakdown stopped depending on it"
    )


def test_the_outcome_vector_still_sums_to_one(sweep):
    """Any alpha must preserve the simplex — the rescaling exists for that."""
    for alpha in (None,) + ALPHAS:
        out = sweep(alpha)
        for code, v in out.items():
            total = v["p24"] + v["mortality"] + v["waiting"] + (
                1.0 - v["p24"] - v["mortality"] - v["waiting"])
            assert abs(total - 1.0) < 1e-9, (code, alpha)


def test_waiting_moves_opposite_to_mortality(sweep):
    """A rising second-year hazard must convert waiting into terminal
    outcomes, not create probability from nowhere."""
    low, high = sweep(1.0), sweep(3.0)
    mean = lambda d, k: float(np.mean([v[k] for v in d.values()]))
    assert mean(high, "waiting") < mean(low, "waiting")
    assert mean(high, "mortality") > mean(low, "mortality")
