"""Performance regression gates (#342).

Budgets sit ~10x above the 2026-08-25 measured values, so they never flake
on a slow CI machine but still catch order-of-magnitude regressions — the
class found in the 2026-08 review (equity freezing 11k scipy distributions
per request: 0.23s -> 3.5s, a serverless-timeout risk).

Measured baselines (M-series laptop, warm data):
  equity closed-form, 233 kidney centers ........ 0.23s  (budget 3s)
  BBN full-granularity model build (cold) ....... 0.45s  (budget 8s)
  travel-subsidy closed-form sweep, 4 tiers ..... <1s    (budget 5s)
"""
import time

import pytest

from models.schemas import PatientProfile


@pytest.fixture(autouse=True)
def _load(data):
    pass


def test_equity_closed_form_budget():
    from services.equity import compute_equity_analysis
    p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                       urgency=2)
    compute_equity_analysis(p, seed=42)  # warm caches
    t0 = time.perf_counter()
    result = compute_equity_analysis(p, seed=42)
    elapsed = time.perf_counter() - t0
    assert len(result.cities) > 200
    assert elapsed < 3.0, (
        f"equity closed-form took {elapsed:.2f}s for {len(result.cities)} "
        f"centers (budget 3s; 2026-08 baseline 0.23s) — check for per-profile "
        f"frozen-distribution regressions"
    )


def test_bbn_full_build_budget():
    from services import bayesian_network
    bayesian_network._MODEL_CACHE.pop("full", None)  # force a cold build
    t0 = time.perf_counter()
    bayesian_network.build_model("full")
    elapsed = time.perf_counter() - t0
    assert elapsed < 8.0, (
        f"cold full-granularity BBN build took {elapsed:.2f}s "
        f"(budget 8s; 2026-08 baseline 0.45s)"
    )


def test_travel_subsidy_sweep_budget():
    from services.data_loader import get_data
    from services.policy_scenarios import (
        TRAVEL_SUBSIDY_TIERS, get_center_multipliers, get_scenario,
    )
    from services.what_if import closed_form_adjusted, closed_form_baseline

    p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                       urgency=2)
    centers = get_data().centers_for_organ("kidney")
    t0 = time.perf_counter()
    baselines = {}
    for c in centers:
        code = c.get("code", "")
        try:
            baselines[code] = closed_form_baseline(p, code)
        except ValueError:
            continue
    n_rows = 0
    for amount in TRAVEL_SUBSIDY_TIERS:
        scenario = get_scenario(f"travel_assistance_{amount // 1000}k")
        for code, baseline in baselines.items():
            d, w = get_center_multipliers(scenario, code, organ="kidney")
            closed_form_adjusted(baseline, d, w)
            n_rows += 1
    elapsed = time.perf_counter() - t0
    assert n_rows > 800
    assert elapsed < 5.0, (
        f"travel-subsidy sweep took {elapsed:.2f}s for {n_rows} rows "
        f"(budget 5s) — the tier-invariant baseline may be recomputed per tier"
    )
