"""Empirical-Bayes shrinkage for small-cohort center factors (#268 / L-086).

A center's mortality/delisting factor is a ratio estimated from that center's
cohort. With n = 3 the ratio is almost pure noise, it lands at an extreme, the
[0.3, 3.0] clamp pins it to the most favourable value, and the center ranks
near the top. Measured: every center with n <= 10 sits on a clamp bound, and
shrinkage drops centers with cohorts of 3/5/8/9 out of kidney's top 10 in
favour of centers with 437/706/200/29.

The shrinkage weight is DERIVED rather than chosen. Under a hierarchical model

    Var(f) = tau^2 + c/n

so solving on a small-n / large-n split gives both terms by method of moments,
and k = c/tau^2 follows. That is the whole point: a hand-picked k would be one
more uncited constant of exactly the kind this project keeps finding.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "eb_shrinkage", REPO / "scripts" / "eb_shrinkage.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── the weight function ────────────────────────────────────────────────────

def test_weight_is_zero_at_no_data_and_approaches_one():
    eb = _mod()
    assert eb.shrink(2.5, n=0, k=20) == pytest.approx(1.0), (
        "a center with no cohort must fall back entirely to the organ mean")
    assert eb.shrink(2.5, n=10**9, k=20) == pytest.approx(2.5, rel=1e-6), (
        "a huge cohort must keep essentially its own estimate")


def test_weight_is_monotone_in_cohort_size():
    eb = _mod()
    prev = 0.0
    for n in (1, 5, 10, 50, 200, 1000):
        w = n / (n + 20)
        assert w > prev
        prev = w
        # a factor above 1 shrinks DOWN toward 1, never past it
        assert 1.0 <= eb.shrink(2.0, n=n, k=20) <= 2.0


def test_shrinkage_never_crosses_the_mean():
    """A favourable factor must not become unfavourable, or vice versa."""
    eb = _mod()
    for raw in (0.3, 0.75, 1.0, 1.4, 3.0):
        for n in (1, 3, 25, 400):
            out = eb.shrink(raw, n=n, k=18.4)
            lo, hi = sorted((raw, 1.0))
            assert lo - 1e-9 <= out <= hi + 1e-9, (raw, n, out)


# ── the estimator ──────────────────────────────────────────────────────────

def test_estimator_recovers_a_known_prior_strength():
    """Generate from the actual model and check M comes back.

    Without this the estimator could return anything and the weight tests above
    would still pass — they only check `shrink()`'s shape.
    """
    eb = _mod()
    rng = np.random.default_rng(11)
    m, M = 0.02, 25.0                       # national rate, prior strength
    a, b = m * M, (1 - m) * M
    ns = np.concatenate([rng.integers(5, 40, 500), rng.integers(100, 900, 500)])
    p_true = rng.beta(a, b, size=ns.size)
    x = rng.binomial(ns, p_true)
    est = eb.estimate_k((x / ns).tolist(), ns.tolist(), m)
    assert est is not None
    assert 10 < est < 60, f"recovered M={est}, expected ~25"


def test_estimator_declines_when_spread_is_all_sampling_noise():
    """No between-center signal must yield None, not a huge constant.

    As tau^2 -> 0 the estimate runs to infinity, which is arithmetically
    correct — it shrinks every center to the mean. But flattening a variable is
    a modelling decision, not something an estimator should impose on a caller
    that only asked how much to shrink. So it declines and the caller leaves
    the organ alone.
    """
    eb = _mod()
    rng = np.random.default_rng(5)
    m = 0.02
    ns = rng.integers(3, 30, 600)
    x = rng.binomial(ns, m)                 # identical true rate everywhere
    assert eb.estimate_k((x / ns).tolist(), ns.tolist(), m) is None


def test_estimator_declines_on_too_few_centers():
    eb = _mod()
    assert eb.estimate_k([0.02, 0.03], [5, 100], 0.02) is None


def test_estimator_declines_without_a_national_rate():
    eb = _mod()
    assert eb.estimate_k([0.02] * 50, [50] * 50, 0.0) is None


# ── the real data ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("organ", ["kidney", "liver", "heart"])
def test_estimates_on_shipped_data_are_plausible(organ):
    """Assert the implied WEIGHT, not the raw constant.

    The constant is only interpretable next to a cohort size — kidney's 759 and
    liver's 77 both describe sane shrinkage because their cohorts and event
    rates differ. The weight a median center retains is the quantity a reader
    can actually judge, and it is what a data refresh should keep stable.
    """
    import json
    eb = _mod()
    adj = json.loads((REPO / "data" / "competing-risks-centers.json").read_text())["center_adjustments"]
    obs = json.loads((REPO / "data" / "srtr-observed-rates.json").read_text())
    rates, ns = [], []
    for c in (obs.get(organ) or {}).get("centers", {}).values():
        if isinstance(c, dict) and c.get("n"):
            rates.append((c.get("waitlist_death_rate") or 0) / 100.0)
            ns.append(c["n"])
    nat = ((obs.get(organ) or {}).get("national", {}).get("waitlist_death_rate") or 0) / 100.0
    k = eb.estimate_k(rates, ns, nat)
    assert k is not None, f"{organ}: M not estimable from shipped data"
    import statistics as st
    w_med = eb.implied_weight(k, st.median(ns))
    w_max = eb.implied_weight(k, max(ns))
    assert 0.01 <= w_med <= 0.90, (
        f"{organ}: median center keeps {w_med:.2f} of its own estimate "
        f"(M={k:.0f}) — outside anything defensible as shrinkage")
    assert w_max > w_med, "the largest center must keep more than the median one"


@pytest.mark.parametrize("organ", ["pancreas", "intestine"])
def test_sparse_organs_are_not_shrinkable_and_say_so(organ):
    """The estimator must decline, not return a number, where the model fails.

    Pancreas and intestine: 70 of 75 small pancreas centers record zero deaths.
    Lung: only 73 centers, which makes tau^2 — an excess-of-variance estimate —
    too noisy; shrinking it degraded Spearman against observed SRTR transplant
    rates by 0.0569 in a controlled comparison. Declining here is what keeps a
    caller from silently shrinking an organ where it makes the model worse.
    """
    import json
    eb = _mod()
    adj = json.loads((REPO / "data" / "competing-risks-centers.json").read_text())["center_adjustments"]
    obs = json.loads((REPO / "data" / "srtr-observed-rates.json").read_text())
    rates, ns = [], []
    for c in (obs.get(organ) or {}).get("centers", {}).values():
        if isinstance(c, dict) and c.get("n"):
            rates.append((c.get("waitlist_death_rate") or 0) / 100.0)
            ns.append(c["n"])
    nat = ((obs.get(organ) or {}).get("national", {}).get("waitlist_death_rate") or 0) / 100.0
    assert rates, f"no {organ} centers found"
    assert eb.estimate_k(rates, ns, nat) is None, (
        f"{organ} became estimable — it is excluded because its panel is too "
        "small for a trustworthy tau^2 (lung) or its small centers record "
        "almost no events (pancreas, intestine). Re-run the controlled "
        "calibration comparison before shrinking it.")


# ── order of operations: shrink BEFORE clamp ───────────────────────────────

def test_shrink_then_clamp_differs_from_clamp_then_shrink():
    """The ordering is the whole implementation, so it needs its own guard.

    Found by negative-testing: reversing the order in the parser did NOT fail
    the data-level tests, because at tiny n both orders land near 1.0. They
    diverge where the raw ratio is outside the clamp AND the cohort is big
    enough to retain real weight — there, clamping first has already destroyed
    the estimate that shrinkage is supposed to weigh.
    """
    eb = _mod()
    raw, n, k = 8.0, 300.0, 70.0          # far outside [0.3, 3.0], substantial cohort
    correct = min(max(eb.shrink(raw, n, k), 0.3), 3.0)
    reversed_ = eb.shrink(min(max(raw, 0.3), 3.0), n, k)
    assert abs(correct - reversed_) > 0.3, (
        f"the two orders agree ({correct:.3f} vs {reversed_:.3f}); pick a case "
        "where they genuinely differ or this guard proves nothing")
    assert correct > reversed_, (
        "clamping first discards how extreme the estimate was, so it always "
        "understates a large deviation")


def test_parser_shrinks_before_clamping():
    """Structural check on the generator, since the data cannot reveal this."""
    src = (REPO / "scripts" / "parse-srtr-reports.py").read_text()
    for quantity in ("mort", "delist"):
        line = next((l for l in src.splitlines()
                     if f'{quantity}_factor = round(' in l and "eb_shrinkage.shrink" in l), None)
        assert line, f"could not find the {quantity}_factor assignment"
        shrink_at = line.index("eb_shrinkage.shrink")
        clamp_at = line.index("max(0.3")
        assert clamp_at < shrink_at, (
            f"{quantity}_factor clamps before shrinking:\n  {line.strip()}\n"
            "Shrinkage must be applied to the RAW ratio; after the clamp the "
            "estimate has already been replaced by a bound.")


def test_allowlist_is_narrower_than_estimability():
    """Estimable is not the same as beneficial, and the code must keep them apart.

    liver and heart ARE estimable — the estimator returns a number for both —
    but shrinking them measurably degraded calibration, so they are excluded by
    SHRINKABLE_ORGANS rather than by the estimator. Collapsing the two concepts
    would silently start shrinking them again.
    """
    eb = _mod()
    assert eb.SHRINKABLE_ORGANS == frozenset({"kidney"}), (
        "the allowlist changed — re-run `run-center-calibration.py --organ all` "
        "as a controlled comparison before widening it")
