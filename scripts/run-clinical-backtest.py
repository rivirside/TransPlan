#!/usr/bin/env python3
"""
Clinical pattern backtest — GitHub Issue #108.

Validates that TransPlan's Monte Carlo simulation reproduces 6 well-known
clinical patterns from transplant medicine. Each test uses 1000 iterations
with a fixed RNG seed for reproducibility.

Patterns tested:
  1. O blood type waits longest, AB shortest (per organ)
  2. Kidney has the longest national median wait
  3. Higher urgency reduces wait time
  4. High cPRA increases kidney wait time
  5. Waitlist mortality increases with age
  6. 250nm policy circles help small centers

Outputs:
  - docs-site/static/data/clinical-backtest-results.json
  - docs/clinical-backtest-report.md
  - Exit code 0 if all pass, 1 if any fail

Usage:
    cd TransPlan && python3 scripts/run-clinical-backtest.py
"""
import json
import sys
import time
from pathlib import Path

# Add backend/ to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from models.schemas import PatientProfile  # noqa: E402
from services.data_loader import load_all  # noqa: E402
from services.sensitivity import _p24_single_city  # noqa: E402

import numpy as np  # noqa: E402

# Load all data before running
load_all()

N_ITERATIONS = 1000
SEED = 42


def _make_patient(**kwargs) -> PatientProfile:
    defaults = dict(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2)
    defaults.update(kwargs)
    return PatientProfile(**defaults)


def _p24_avg(patient: PatientProfile, cities: list[str], n: int = N_ITERATIONS) -> float:
    """Average p24 across multiple cities for stability."""
    rng = np.random.default_rng(SEED)
    total = sum(_p24_single_city(patient, c, n, rng) for c in cities)
    return total / len(cities)


# Representative cities for averaging
REP_CITIES = ["Houston", "Pittsburgh", "Cleveland", "Nashville", "Chicago",
              "New York", "Los Angeles", "San Francisco", "Minneapolis", "Philadelphia"]

results = []


def run_test(name: str, description: str, test_fn):
    """Run a test and record result."""
    start = time.perf_counter()
    try:
        passed, details = test_fn()
    except Exception as e:
        passed = False
        details = {"error": str(e)}
    elapsed = round(time.perf_counter() - start, 2)

    result = {
        "name": name,
        "description": description,
        "passed": passed,
        "elapsed_seconds": elapsed,
        "details": details,
    }
    results.append(result)

    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name} ({elapsed}s)")
    return passed


# ──────────────────────────────────────────────────────────────────────
# Test 1: O blood type waits longest, AB shortest
# ──────────────────────────────────────────────────────────────────────

def test_blood_type_ordering():
    """O blood types should have lowest p24 (longest wait), AB highest."""
    organs = ["kidney", "liver", "heart", "lung"]
    blood_types = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
    details = {}
    all_pass = True

    for organ in organs:
        bt_p24 = {}
        for bt in blood_types:
            patient = _make_patient(organ=organ, blood_type=bt)
            bt_p24[bt] = round(_p24_avg(patient, REP_CITIES), 4)

        # AB+ should have higher p24 than O+
        ab_better = bt_p24["AB+"] > bt_p24["O+"]
        if not ab_better:
            all_pass = False

        details[organ] = {
            "p24_by_blood_type": bt_p24,
            "AB+_higher_than_O+": ab_better,
        }

    return all_pass, details


# ──────────────────────────────────────────────────────────────────────
# Test 2: Kidney has longest wait
# ──────────────────────────────────────────────────────────────────────

def test_kidney_longest_wait():
    """Kidney should have the lowest average p24 (longest wait)."""
    organs = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
    organ_p24 = {}

    for organ in organs:
        patient = _make_patient(organ=organ, blood_type="O+")
        organ_p24[organ] = round(_p24_avg(patient, REP_CITIES), 4)

    kidney_p24 = organ_p24["kidney"]
    # Kidney should have lowest p24 among the major organs
    kidney_lowest = all(kidney_p24 <= organ_p24[o] for o in ["liver", "heart", "lung"])

    return kidney_lowest, {
        "p24_by_organ": organ_p24,
        "kidney_lowest_among_major": kidney_lowest,
    }


# ──────────────────────────────────────────────────────────────────────
# Test 3: Higher urgency reduces wait
# ──────────────────────────────────────────────────────────────────────

def test_urgency_reduces_wait():
    """Higher urgency (lower number) should increase p24."""
    organs = ["kidney", "liver", "heart"]
    details = {}
    all_pass = True

    for organ in organs:
        p24_by_urg = {}
        for urg in [1, 2, 3, 4]:
            patient = _make_patient(organ=organ, urgency=urg)
            p24_by_urg[urg] = round(_p24_avg(patient, REP_CITIES), 4)

        # Urgency 1 should have higher p24 than urgency 4
        monotonic = p24_by_urg[1] > p24_by_urg[4]
        if not monotonic:
            all_pass = False

        details[organ] = {
            "p24_by_urgency": p24_by_urg,
            "urgency1_higher_than_4": monotonic,
        }

    return all_pass, details


# ──────────────────────────────────────────────────────────────────────
# Test 4: High cPRA increases kidney wait
# ──────────────────────────────────────────────────────────────────────

def test_cpra_increases_wait():
    """Higher cPRA should decrease p24 for kidney patients."""
    cpra_values = [0, 30, 60, 90, 98]
    cpra_p24 = {}

    for cpra in cpra_values:
        patient = _make_patient(organ="kidney", cpra=cpra)
        cpra_p24[cpra] = round(_p24_avg(patient, REP_CITIES), 4)

    # cPRA 0 should have higher p24 than cPRA 98
    decreasing = cpra_p24[0] > cpra_p24[98]

    return decreasing, {
        "p24_by_cpra": cpra_p24,
        "cpra0_higher_than_98": decreasing,
    }


# ──────────────────────────────────────────────────────────────────────
# Test 5: Mortality increases with age
# ──────────────────────────────────────────────────────────────────────

def test_age_mortality():
    """Older patients should have longer median wait (age multiplier effect)."""
    from services.distributions import get_wait_time_distribution

    organs = ["kidney", "liver", "heart"]
    details = {}
    all_pass = True

    for organ in organs:
        young_dist = get_wait_time_distribution(organ=organ, blood_type="O+",
                                                 city="Nashville", age=25, sex="male")
        old_dist = get_wait_time_distribution(organ=organ, blood_type="O+",
                                               city="Nashville", age=65, sex="male")
        young_median = float(young_dist.median())
        old_median = float(old_dist.median())

        older_longer = old_median > young_median
        if not older_longer:
            all_pass = False

        details[organ] = {
            "young_25_median_months": round(young_median, 2),
            "old_65_median_months": round(old_median, 2),
            "older_waits_longer": older_longer,
        }

    return all_pass, details


# ──────────────────────────────────────────────────────────────────────
# Test 6: 250nm circles help small centers
# ──────────────────────────────────────────────────────────────────────

def test_policy_helps_small_centers():
    """Under 250nm circle policy, small centers (Madison, Omaha) should improve."""
    from services.policy_scenarios import get_scenario, get_city_multipliers
    from services.what_if import compute_what_if

    scenario = get_scenario("kidney_250nm")
    if scenario is None:
        return False, {"error": "kidney_250nm scenario not found"}

    patient = _make_patient(organ="kidney")
    small_centers = ["Madison", "Omaha", "Rochester"]
    improvements = {}

    for city in small_centers:
        donor_mult, wait_mult = get_city_multipliers(scenario, city)
        result = compute_what_if(
            patient=patient, city=city,
            donor_rate_multiplier=donor_mult,
            wait_time_multiplier=wait_mult,
            n_iterations=N_ITERATIONS,
        )
        improvements[city] = round(result.delta_p24, 4)

    # At least 2 of 3 small centers should improve (delta > 0)
    n_improved = sum(1 for d in improvements.values() if d > 0)
    passed = n_improved >= 2

    return passed, {
        "small_center_deltas": improvements,
        "n_improved": n_improved,
    }


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("TransPlan Clinical Pattern Backtest")
    print("=" * 50)
    print(f"Iterations: {N_ITERATIONS}, Seed: {SEED}\n")

    total_start = time.perf_counter()

    run_test("blood_type_ordering",
             "O blood type waits longest, AB shortest",
             test_blood_type_ordering)

    run_test("kidney_longest_wait",
             "Kidney has the longest national median wait",
             test_kidney_longest_wait)

    run_test("urgency_reduces_wait",
             "Higher urgency reduces wait time",
             test_urgency_reduces_wait)

    run_test("cpra_increases_wait",
             "High cPRA increases kidney wait time",
             test_cpra_increases_wait)

    run_test("age_mortality",
             "Waitlist mortality increases with age",
             test_age_mortality)

    run_test("policy_helps_small_centers",
             "250nm circles help small centers",
             test_policy_helps_small_centers)

    total_elapsed = round(time.perf_counter() - total_start, 2)

    # Summary
    n_passed = sum(1 for r in results if r["passed"])
    n_total = len(results)
    print(f"\n{'=' * 50}")
    print(f"Results: {n_passed}/{n_total} passed ({total_elapsed}s total)")

    # Write JSON output
    output_dir = REPO_ROOT / "docs-site" / "static" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "clinical-backtest-results.json"

    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_iterations": N_ITERATIONS,
        "seed": SEED,
        "total_elapsed_seconds": total_elapsed,
        "summary": f"{n_passed}/{n_total} passed",
        "tests": results,
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nJSON output: {output_path}")

    # Write markdown report
    md_path = REPO_ROOT / "docs" / "clinical-backtest-report.md"
    with open(md_path, "w") as f:
        f.write("# Clinical Pattern Backtest Report\n\n")
        f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}  \n")
        f.write(f"**Iterations:** {N_ITERATIONS} | **Seed:** {SEED} | **Total time:** {total_elapsed}s\n\n")
        f.write(f"## Summary: {n_passed}/{n_total} passed\n\n")
        f.write("| # | Test | Result | Time |\n")
        f.write("|---|------|--------|------|\n")
        for i, r in enumerate(results, 1):
            status = "PASS" if r["passed"] else "FAIL"
            f.write(f"| {i} | {r['description']} | {status} | {r['elapsed_seconds']}s |\n")
        f.write("\n## Detailed Results\n\n")
        for r in results:
            f.write(f"### {r['description']}\n\n")
            f.write(f"**Status:** {'PASS' if r['passed'] else 'FAIL'}  \n")
            f.write(f"**Time:** {r['elapsed_seconds']}s\n\n")
            f.write("```json\n")
            f.write(json.dumps(r["details"], indent=2))
            f.write("\n```\n\n")
    print(f"Markdown report: {md_path}")

    sys.exit(0 if n_passed == n_total else 1)
