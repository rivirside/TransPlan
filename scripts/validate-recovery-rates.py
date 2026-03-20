#!/usr/bin/env python3
"""
Validate organ recovery rates against OPTN benchmarks (L-049).

Our recovery rates come from PMC10329409 (2023, data from 2005-2019).
This script compares them against known OPTN annual report figures
and flags rates that may be outdated due to:
  - Expanded DCD (donation after circulatory death) utilization
  - Ex-vivo perfusion technology adoption
  - Broader HCV+ donor acceptance
  - Improved preservation techniques

Usage:
    python3 scripts/validate-recovery-rates.py
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


# OPTN 2023 Annual Data Report benchmarks (national averages)
# Source: optn.transplant.hrsa.gov/data/view-data-reports/national-data/
# These are organ recovery rates per donor (all causes combined)
OPTN_2023_BENCHMARKS = {
    "kidney": {
        "overall_recovery_rate": 0.82,  # ~82% of donors yield kidneys
        "note": "Includes DCD donors; DCD kidney utilization grew 35% 2019-2023",
        "trend": "stable to slightly increasing",
    },
    "liver": {
        "overall_recovery_rate": 0.72,  # ~72% of donors yield livers
        "note": "Ex-vivo perfusion (NMP) has increased marginal donor utilization",
        "trend": "increasing (machine perfusion effect)",
    },
    "heart": {
        "overall_recovery_rate": 0.38,  # ~38% of donors yield hearts
        "note": "DCD heart transplantation began 2020; growing rapidly",
        "trend": "increasing (DCD hearts + OCS TransMedics)",
    },
    "lung": {
        "overall_recovery_rate": 0.24,  # ~24% of donors yield lungs
        "note": "Ex-vivo lung perfusion (EVLP) has expanded utilization",
        "trend": "increasing (EVLP + XVIVO effect)",
    },
    "pancreas": {
        "overall_recovery_rate": 0.12,  # ~12% of donors yield pancreata
        "note": "Declining utilization due to shifting to islet cell transplants",
        "trend": "stable to declining",
    },
    "intestine": {
        "overall_recovery_rate": 0.008,  # <1% of donors yield intestines
        "note": "Very rare; ~100-150 per year nationally",
        "trend": "stable (small numbers)",
    },
}


def load_our_rates():
    """Load our organ recovery rates from cause-of-death data."""
    path = DATA_DIR / "cause-of-death-by-region.json"
    with open(path) as f:
        data = json.load(f)
    return data["organRecoveryRates"]


def compute_weighted_average(rates: dict, cod_weights: dict = None) -> float:
    """Compute weighted average recovery rate across COD categories."""
    # Default national COD distribution among donors (approximate)
    if cod_weights is None:
        cod_weights = {
            "trauma": 0.20,
            "cardiovascular": 0.22,
            "drug_intox": 0.38,
            "stroke": 0.15,
            "anoxia": 0.05,
        }

    total = 0.0
    weight_sum = 0.0
    for cause, weight in cod_weights.items():
        if cause in rates:
            total += rates[cause] * weight
            weight_sum += weight

    return total / weight_sum if weight_sum > 0 else 0.0


def main():
    our_rates = load_our_rates()

    print("=" * 70)
    print("ORGAN RECOVERY RATE VALIDATION (L-049)")
    print("=" * 70)
    print(f"\nOur source: PMC10329409 (2023, OPTN data 2005-2019)")
    print(f"Benchmark: OPTN 2023 Annual Data Report")
    print()

    issues = []

    for organ, benchmark in OPTN_2023_BENCHMARKS.items():
        our_organ_rates = our_rates.get(organ, {})
        our_weighted_avg = compute_weighted_average(our_organ_rates)
        optn_rate = benchmark["overall_recovery_rate"]
        delta = our_weighted_avg - optn_rate
        pct_diff = (delta / optn_rate) * 100 if optn_rate > 0 else 0

        # Flag if our rate differs by >15%
        flag = "REVIEW" if abs(pct_diff) > 15 else "OK"
        if abs(pct_diff) > 25:
            flag = "ACTION"

        print(f"  {organ.upper():12s}  Ours: {our_weighted_avg:.3f}  OPTN: {optn_rate:.3f}  "
              f"Δ={delta:+.3f} ({pct_diff:+.1f}%)  [{flag}]")

        if flag != "OK":
            issues.append({
                "organ": organ,
                "our_rate": our_weighted_avg,
                "optn_rate": optn_rate,
                "pct_diff": pct_diff,
                "trend": benchmark["trend"],
                "note": benchmark["note"],
            })

        # Print per-COD breakdown
        for cause in ["trauma", "cardiovascular", "drug_intox", "stroke", "anoxia"]:
            rate = our_organ_rates.get(cause)
            if rate is not None:
                print(f"    {cause:20s} {rate:.3f}")

        print()

    # Summary
    print("=" * 70)
    if not issues:
        print("All organ recovery rates within 15% of OPTN 2023 benchmarks.")
    else:
        print(f"VALIDATION ISSUES ({len(issues)}):\n")
        for issue in issues:
            print(f"  {issue['organ'].upper()}: Our weighted avg ({issue['our_rate']:.3f}) vs "
                  f"OPTN ({issue['optn_rate']:.3f}) = {issue['pct_diff']:+.1f}%")
            print(f"    Trend: {issue['trend']}")
            print(f"    Note: {issue['note']}")
            print()

    print("\nRECOMMENDATIONS:")
    print("  1. Heart rates may underestimate due to DCD heart program (started 2020)")
    print("  2. Lung rates may underestimate due to EVLP technology adoption")
    print("  3. Liver rates may underestimate due to machine perfusion expansion")
    print("  4. Consider modeling rates as Beta distributions with PMC10329409 as priors")
    print("  5. Re-run validation annually when new OPTN reports are released")
    print()

    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
