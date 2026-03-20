#!/usr/bin/env python3
"""
Sensitivity analysis report generator — GitHub Issue #109.

Runs sensitivity sweeps for all 6 organs × 3 patient profiles per organ,
capturing which parameters dominate p_transplant_24mo. Outputs:
  1. JSON data for interactive charts: docs-site/static/data/sensitivity-results.json
  2. Console summary for report writing

Usage:
    cd TransPlan && .venv/bin/python scripts/run-sensitivity-report.py
"""
import json
import sys
from pathlib import Path

# Add backend/ to path so we can import services directly
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from services.data_loader import load_all  # noqa: E402
from services.sensitivity import compute_sensitivity  # noqa: E402
from models.schemas import PatientProfile  # noqa: E402

# Ensure data is loaded before running any simulations
load_all()

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]

# 22 cities to sweep sensitivity across (sample of representative cities)
SENSITIVITY_CITIES = [
    "Houston", "Pittsburgh", "Phoenix", "Cleveland",
    "Minneapolis", "Nashville", "New York", "Los Angeles",
    "Chicago", "San Francisco",
]

# 3 patient profiles per organ: standard, rare, extreme
def build_profiles(organ: str) -> list[dict]:
    """Build 3 representative patient profiles for a given organ."""
    base = {"organ": organ, "urgency": 2, "age": 45, "sex": "male",
            "adjust_for_cause_of_death": False}

    if organ == "kidney":
        return [
            {"label": "Standard (O+, cPRA 30)", **base, "blood_type": "O+", "cpra": 30},
            {"label": "Rare (AB+, cPRA 0)", **base, "blood_type": "AB+", "cpra": 0, "urgency": 1},
            {"label": "Extreme (O-, cPRA 95)", **base, "blood_type": "O-", "cpra": 95, "urgency": 3},
        ]
    elif organ == "liver":
        return [
            {"label": "Standard (A+, MELD 20)", **base, "blood_type": "A+", "meld": 20},
            {"label": "Rare (AB+, MELD 10)", **base, "blood_type": "AB+", "meld": 10, "urgency": 1},
            {"label": "Extreme (O+, MELD 35)", **base, "blood_type": "O+", "meld": 35, "urgency": 3},
        ]
    elif organ == "lung":
        return [
            {"label": "Standard (B+, LAS 50)", **base, "blood_type": "B+", "las": 50.0},
            {"label": "Rare (AB-, LAS 30)", **base, "blood_type": "AB-", "las": 30.0, "urgency": 1},
            {"label": "Extreme (O+, LAS 80)", **base, "blood_type": "O+", "las": 80.0, "urgency": 3},
        ]
    else:
        # heart, pancreas, intestine — only urgency varies
        return [
            {"label": "Standard (O+)", **base, "blood_type": "O+"},
            {"label": "Rare (AB+)", **base, "blood_type": "AB+", "urgency": 1},
            {"label": "Extreme (O-, high urgency)", **base, "blood_type": "O-", "urgency": 4},
        ]


def run_sweep() -> dict:
    """Run full sensitivity sweep and return structured results."""
    results = {}
    n_iterations = 500  # balance speed vs stability

    for organ in ORGANS:
        print(f"\n{'='*60}")
        print(f"  ORGAN: {organ.upper()}")
        print(f"{'='*60}")

        organ_results = {"profiles": [], "summary": {}}
        profiles = build_profiles(organ)

        all_profile_impacts = []

        for profile_def in profiles:
            label = profile_def.pop("label")
            patient = PatientProfile(**profile_def)
            print(f"\n  Profile: {label}")
            print(f"    Blood type: {patient.blood_type}, Urgency: {patient.urgency}")

            city_sweeps = []
            for city in SENSITIVITY_CITIES:
                result = compute_sensitivity(patient, city=city, n_iterations=n_iterations)

                city_data = {
                    "city": city,
                    "impacts": [],
                }
                for impact in result.impacts:
                    impact_data = {
                        "parameter": impact.parameter,
                        "label": impact.label,
                        "baseline_value": impact.baseline_value,
                        "low_value": impact.low_value,
                        "high_value": impact.high_value,
                        "p24_baseline": impact.p24_baseline,
                        "p24_at_low": impact.p24_at_low,
                        "p24_at_high": impact.p24_at_high,
                        "swing": round(abs(impact.p24_at_high - impact.p24_at_low), 4),
                    }
                    city_data["impacts"].append(impact_data)

                city_sweeps.append(city_data)

            # Aggregate: average swing across cities per parameter
            param_swings: dict[str, list[float]] = {}
            for cs in city_sweeps:
                for imp in cs["impacts"]:
                    param_swings.setdefault(imp["parameter"], []).append(imp["swing"])

            avg_swings = {
                param: round(sum(vals) / len(vals), 4)
                for param, vals in param_swings.items()
            }
            sorted_params = sorted(avg_swings.items(), key=lambda x: x[1], reverse=True)

            profile_result = {
                "label": label,
                "patient": {
                    "organ": patient.organ,
                    "blood_type": patient.blood_type,
                    "urgency": patient.urgency,
                    "cpra": patient.cpra,
                    "meld": patient.meld,
                    "las": patient.las,
                },
                "cities": city_sweeps,
                "avg_parameter_swings": avg_swings,
                "dominant_parameters": [p[0] for p in sorted_params[:3]],
            }
            organ_results["profiles"].append(profile_result)
            all_profile_impacts.append(avg_swings)

            print(f"    Average parameter swings (across {len(SENSITIVITY_CITIES)} cities):")
            for param, swing in sorted_params:
                bar = "█" * int(swing * 100)
                print(f"      {param:30s}  {swing:.4f}  {bar}")

        # Cross-profile consistency: do the same parameters dominate?
        all_dominant = [set(p.get("dominant_parameters", [])[:2]) for p in organ_results["profiles"]]
        consistent = len(set.intersection(*all_dominant)) > 0 if all_dominant else False

        organ_results["summary"] = {
            "cross_profile_consistent": consistent,
            "dominant_across_all_profiles": list(set.intersection(*all_dominant)) if consistent else [],
        }

        results[organ] = organ_results
        print(f"\n  Cross-profile consistency: {'YES' if consistent else 'NO'}")
        if consistent:
            print(f"  Dominant parameters: {organ_results['summary']['dominant_across_all_profiles']}")

    return results


def main():
    print("TransPlan Sensitivity Analysis Report Generator")
    print(f"Organs: {', '.join(ORGANS)}")
    print(f"Cities: {', '.join(SENSITIVITY_CITIES)}")
    print(f"Profiles per organ: 3 (standard, rare, extreme)")
    print()

    results = run_sweep()

    # Write JSON for interactive charts
    output_path = REPO_ROOT / "docs-site" / "static" / "data" / "sensitivity-results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nJSON output written to: {output_path}")

    # Print summary table for report
    print("\n" + "=" * 80)
    print("SUMMARY: Top Parameters by Organ")
    print("=" * 80)
    print(f"{'Organ':<12} {'#1 Parameter':<30} {'Avg Swing':<12} {'#2 Parameter':<30} {'Avg Swing':<12}")
    print("-" * 96)
    for organ in ORGANS:
        profiles = results[organ]["profiles"]
        # Use standard profile (index 0) for summary
        swings = profiles[0]["avg_parameter_swings"]
        sorted_s = sorted(swings.items(), key=lambda x: x[1], reverse=True)
        p1 = sorted_s[0] if len(sorted_s) > 0 else ("—", 0)
        p2 = sorted_s[1] if len(sorted_s) > 1 else ("—", 0)
        print(f"{organ:<12} {p1[0]:<30} {p1[1]:<12.4f} {p2[0]:<30} {p2[1]:<12.4f}")


if __name__ == "__main__":
    main()
