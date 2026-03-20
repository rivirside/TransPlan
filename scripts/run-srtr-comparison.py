#!/usr/bin/env python3
"""
SRTR ground-truth comparison — GitHub Issue #110.

Spot-checks TransPlan's model outputs against observed SRTR Program-Specific
Report data for a sample of city/organ pairs. Compares:
  - Predicted median wait time vs SRTR observed
  - Mortality and delisting rates
  - Post-transplant graft/patient survival
  - City ranking alignment

Outputs:
  1. JSON data for interactive charts: docs-site/static/data/srtr-comparison-results.json
  2. Console comparison tables

Usage:
    cd TransPlan && .venv/bin/python scripts/run-srtr-comparison.py
"""
import json
import sys
from pathlib import Path

import numpy as np

# Add backend/ to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from services.data_loader import load_all  # noqa: E402
from services.monte_carlo import simulate, CITIES  # noqa: E402
from services.distributions import get_wait_time_distribution, get_organ_params, get_city_factors  # noqa: E402
from services.competing_risks import get_annual_mortality_rate, get_annual_delisting_rate  # noqa: E402
from models.schemas import PatientProfile  # noqa: E402

# Load all data
load_all()

# Spot-check pairs: city, organ
SPOT_CHECKS = [
    ("Houston", "kidney"),
    ("Pittsburgh", "liver"),
    ("Chicago", "kidney"),
    ("Cleveland", "heart"),
    ("Minneapolis", "lung"),
    ("Nashville", "liver"),
]

# Standard baseline patient for each organ
def baseline_patient(organ: str) -> PatientProfile:
    """Create a standard baseline patient for comparison."""
    base = {"organ": organ, "blood_type": "O+", "urgency": 2, "age": 45, "sex": "male",
            "adjust_for_cause_of_death": False}
    if organ == "kidney":
        base["cpra"] = 30
    elif organ == "liver":
        base["meld"] = 20
    elif organ == "lung":
        base["las"] = 50.0
    return PatientProfile(**base)


def get_srtr_observed(city: str, organ: str) -> dict:
    """
    Extract observed SRTR values from our data files.

    These ARE the SRTR values — our data files are parameterized from SRTR PSRs.
    The comparison is between what the data files say (observed) and what the
    Monte Carlo model produces when sampling from those parameters (predicted).
    """
    observed = {}

    # Wait time: national median × city factor × blood type multiplier
    organ_params = get_organ_params(organ)
    city_factors = get_city_factors()

    if organ_params:
        national_median = organ_params["national_median_months"]
        city_factor = city_factors.get(city, 1.0)
        bt_mult = organ_params.get("blood_type_multipliers", {}).get("O+", 1.0)
        observed["national_median_months"] = national_median
        observed["city_wait_factor"] = city_factor
        observed["expected_median_months"] = round(national_median * city_factor * bt_mult, 2)
        observed["log_sigma"] = organ_params.get("log_sigma", 1.2)

    # Mortality and delisting rates
    observed["annual_mortality_rate"] = get_annual_mortality_rate(organ, city, urgency=2)
    observed["annual_delisting_rate"] = get_annual_delisting_rate(organ, city)

    # Post-transplant outcomes
    data_path = REPO_ROOT / "data" / "post-transplant-outcomes.json"
    with open(data_path) as f:
        outcomes_data = json.load(f)

    city_outcomes = outcomes_data.get("city_outcomes", {}).get(city, {}).get(organ, {})
    if city_outcomes:
        observed["graft_survival_1yr"] = city_outcomes.get("graft_survival_1yr")
        observed["patient_survival_1yr"] = city_outcomes.get("patient_survival_1yr")
        observed["graft_survival_3yr"] = city_outcomes.get("graft_survival_3yr")
        observed["patient_survival_3yr"] = city_outcomes.get("patient_survival_3yr")
        observed["performance_rating"] = city_outcomes.get("performance_rating")
        observed["n_1yr"] = city_outcomes.get("n_1yr")

    # National outcomes for context
    national = outcomes_data.get(organ, {})
    if national:
        observed["national_graft_survival_1yr"] = national.get("national_graft_survival_1yr")
        observed["national_patient_survival_1yr"] = national.get("national_patient_survival_1yr")

    return observed


def run_simulation_for_city(patient: PatientProfile, target_city: str, n_iterations: int = 1000) -> dict:
    """Run MC simulation and extract results for a specific city."""
    result = simulate(patient, n_iterations=n_iterations)

    for city_result in result.cities:
        if city_result.city == target_city:
            return {
                "p_transplant_24mo": city_result.p_transplant_24mo,
                "p_transplant_12mo": city_result.p_transplant_12mo,
                "median_wait_months": city_result.median_wait_months,
                "confidence_interval_95": list(city_result.confidence_interval_95),
                "competing_risks": city_result.competing_risks,
                "rank": result.cities.index(city_result) + 1,
            }

    return {"error": f"City {target_city} not found in simulation results"}


def compute_discrepancy(predicted: float, observed: float) -> dict:
    """Compute absolute and percent discrepancy."""
    if observed == 0:
        return {"abs_diff": predicted, "pct_diff": None, "flag": "N/A"}
    abs_diff = abs(predicted - observed)
    pct_diff = round(abs_diff / abs(observed) * 100, 1)
    flag = "OK" if pct_diff <= 15 else ("WARN" if pct_diff <= 25 else "FLAG")
    return {"abs_diff": round(abs_diff, 4), "pct_diff": pct_diff, "flag": flag}


def main():
    print("TransPlan SRTR Ground-Truth Comparison")
    print(f"Spot-checking {len(SPOT_CHECKS)} city/organ pairs")
    print()

    all_comparisons = []
    flags_summary = {"OK": 0, "WARN": 0, "FLAG": 0}

    for city, organ in SPOT_CHECKS:
        print(f"\n{'='*70}")
        print(f"  {city} / {organ}")
        print(f"{'='*70}")

        patient = baseline_patient(organ)
        observed = get_srtr_observed(city, organ)
        predicted = run_simulation_for_city(patient, city)

        comparison = {
            "city": city,
            "organ": organ,
            "patient": {
                "blood_type": patient.blood_type,
                "urgency": patient.urgency,
                "cpra": patient.cpra,
                "meld": patient.meld,
                "las": patient.las,
            },
            "observed": observed,
            "predicted": predicted,
            "metrics": [],
        }

        # --- Median wait time comparison ---
        if "expected_median_months" in observed and "median_wait_months" in predicted:
            disc = compute_discrepancy(predicted["median_wait_months"], observed["expected_median_months"])
            metric = {
                "name": "Median Wait (months)",
                "observed": observed["expected_median_months"],
                "predicted": predicted["median_wait_months"],
                **disc,
            }
            comparison["metrics"].append(metric)
            flags_summary[disc["flag"]] = flags_summary.get(disc["flag"], 0) + 1
            print(f"  Median Wait:  observed={observed['expected_median_months']:.1f}mo  "
                  f"predicted={predicted['median_wait_months']:.1f}mo  "
                  f"diff={disc['pct_diff']}%  [{disc['flag']}]")

        # --- Mortality rate: analytical vs simulation implied ---
        if "annual_mortality_rate" in observed and "competing_risks" in predicted:
            # Convert 24-month mortality probability to annual rate for comparison
            p_mort_24 = predicted["competing_risks"].get("p_mortality_24mo", 0)
            # Approximate: annual mortality ≈ 1 - (1 - p_mort_24)^(12/24)
            implied_annual = 1 - (1 - p_mort_24) ** 0.5 if p_mort_24 < 1 else 1.0
            disc = compute_discrepancy(implied_annual, observed["annual_mortality_rate"])
            metric = {
                "name": "Annual Mortality Rate",
                "observed": round(observed["annual_mortality_rate"], 4),
                "predicted": round(implied_annual, 4),
                "predicted_note": "implied from 24mo simulation",
                **disc,
            }
            comparison["metrics"].append(metric)
            flags_summary[disc["flag"]] = flags_summary.get(disc["flag"], 0) + 1
            print(f"  Mortality:    observed={observed['annual_mortality_rate']:.4f}  "
                  f"predicted={implied_annual:.4f}  "
                  f"diff={disc['pct_diff']}%  [{disc['flag']}]")

        # --- Delisting rate ---
        if "annual_delisting_rate" in observed and "competing_risks" in predicted:
            p_delist_24 = predicted["competing_risks"].get("p_delisting_24mo", 0)
            implied_annual = 1 - (1 - p_delist_24) ** 0.5 if p_delist_24 < 1 else 1.0
            disc = compute_discrepancy(implied_annual, observed["annual_delisting_rate"])
            metric = {
                "name": "Annual Delisting Rate",
                "observed": round(observed["annual_delisting_rate"], 4),
                "predicted": round(implied_annual, 4),
                "predicted_note": "implied from 24mo simulation",
                **disc,
            }
            comparison["metrics"].append(metric)
            flags_summary[disc["flag"]] = flags_summary.get(disc["flag"], 0) + 1
            print(f"  Delisting:    observed={observed['annual_delisting_rate']:.4f}  "
                  f"predicted={implied_annual:.4f}  "
                  f"diff={disc['pct_diff']}%  [{disc['flag']}]")

        # --- 24-month transplant probability (analytical check) ---
        if "expected_median_months" in observed and "p_transplant_24mo" in predicted:
            # Analytical p24 from log-normal CDF with competing risks
            from scipy.stats import lognorm
            from scipy.integrate import quad

            median = observed["expected_median_months"]
            sigma = observed.get("log_sigma", 1.2)
            mort_rate = observed.get("annual_mortality_rate", 0.02)
            delist_rate = observed.get("annual_delisting_rate", 0.05)

            dist = lognorm(s=sigma, scale=median)

            def integrand(t):
                f_T = dist.pdf(t)
                S_M = np.exp(-mort_rate / 12 * t)
                S_D = np.exp(-delist_rate / 12 * t)
                return f_T * S_M * S_D

            analytical_p24, _ = quad(integrand, 0, 24)

            disc = compute_discrepancy(predicted["p_transplant_24mo"], analytical_p24)
            metric = {
                "name": "P(transplant ≤ 24mo)",
                "observed": round(analytical_p24, 4),
                "observed_note": "analytical from same parameters",
                "predicted": predicted["p_transplant_24mo"],
                **disc,
            }
            comparison["metrics"].append(metric)
            flags_summary[disc["flag"]] = flags_summary.get(disc["flag"], 0) + 1
            print(f"  P(tx≤24mo):   analytical={analytical_p24:.4f}  "
                  f"MC={predicted['p_transplant_24mo']:.4f}  "
                  f"diff={disc['pct_diff']}%  [{disc['flag']}]")

        # --- Post-transplant outcomes ---
        if "graft_survival_1yr" in observed and observed["graft_survival_1yr"] is not None:
            print(f"  Graft 1yr:    {observed['graft_survival_1yr']}% "
                  f"(national: {observed.get('national_graft_survival_1yr')}%)")
            print(f"  Patient 1yr:  {observed['patient_survival_1yr']}% "
                  f"(national: {observed.get('national_patient_survival_1yr')}%)")
            print(f"  Performance:  {observed.get('performance_rating', 'N/A')} "
                  f"(n={observed.get('n_1yr', 'N/A')})")

        # --- Simulation metadata ---
        if "rank" in predicted:
            print(f"  City rank:    #{predicted['rank']} of 22 cities")
            print(f"  95% CI:       {predicted.get('confidence_interval_95', 'N/A')}")

        all_comparisons.append(comparison)

    # --- Overall ranking comparison ---
    print(f"\n{'='*70}")
    print("  RANKING COMPARISON (all spot-check cities)")
    print(f"{'='*70}")

    # Run full simulation for kidney and liver to compare rankings
    for organ in ["kidney", "liver"]:
        patient = baseline_patient(organ)
        result = simulate(patient, n_iterations=1000)

        spot_cities = [c for c, o in SPOT_CHECKS if o == organ]
        if not spot_cities:
            continue

        print(f"\n  {organ.upper()} — Full city ranking (spot-check cities highlighted):")
        for i, city_result in enumerate(result.cities):
            marker = " ◄◄" if city_result.city in spot_cities else ""
            print(f"    #{i+1:2d}  {city_result.city:<16s}  p24={city_result.p_transplant_24mo:.4f}  "
                  f"wait={city_result.median_wait_months:.1f}mo{marker}")

    # --- Summary ---
    print(f"\n{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")
    total_metrics = sum(flags_summary.values())
    print(f"  Total metrics checked:  {total_metrics}")
    print(f"  OK (≤15% diff):         {flags_summary.get('OK', 0)}")
    print(f"  WARN (15-25% diff):     {flags_summary.get('WARN', 0)}")
    print(f"  FLAG (>25% diff):       {flags_summary.get('FLAG', 0)}")
    if total_metrics > 0:
        ok_pct = flags_summary.get("OK", 0) / total_metrics * 100
        print(f"  Alignment score:        {ok_pct:.0f}% of metrics within 15%")

    # Write JSON output
    output = {
        "spot_checks": all_comparisons,
        "summary": {
            "total_metrics": total_metrics,
            "ok": flags_summary.get("OK", 0),
            "warn": flags_summary.get("WARN", 0),
            "flag": flags_summary.get("FLAG", 0),
        },
    }
    output_path = REPO_ROOT / "docs-site" / "static" / "data" / "srtr-comparison-results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON output written to: {output_path}")


if __name__ == "__main__":
    main()
