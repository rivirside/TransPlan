#!/usr/bin/env python3
"""
Validate organ recovery rates against OPTN benchmarks (L-049).

Our recovery rates originate from PMC10329409 (2023, data from 2005-2019)
and were cross-validated against OPTN 2023 national data (hrsa.unos.org,
"Deceased Donors Recovered by Cause of Death", retrieved March 2026).

15 of 30 organ×COD cells were updated where OPTN 2023 drift exceeded 10%:
  - Kidney: stroke/anoxia/drug_intox rates increased (expanded DCD, perfusion)
  - Pancreas: all rates decreased (declining transplant volumes)
  - Heart: stroke/anoxia/drug_intox rates decreased (more conservative selection)
  - Lung/Liver: anoxia/drug_intox rates decreased
  - Cardiovascular rates unchanged (no OPTN equivalent to validate against)

Usage:
    python3 scripts/validate-recovery-rates.py
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


# OPTN 2023 national data (hrsa.unos.org, retrieved March 2026)
# "Deceased Donors Recovered by Cause of Death" — organ donors / all donors
# Total 2023 donors: 16,336
OPTN_2023_BENCHMARKS = {
    "kidney": {
        "overall_recovery_rate": 0.947,  # 15,471 / 16,336 — highest utilization organ
        "note": "Expanded DCD, machine perfusion, HCV+ acceptance drove increases",
        "trend": "increasing",
    },
    "liver": {
        "overall_recovery_rate": 0.671,  # 10,969 / 16,336
        "note": "Ex-vivo perfusion (NMP) has increased marginal donor utilization",
        "trend": "increasing (machine perfusion effect)",
    },
    "heart": {
        "overall_recovery_rate": 0.285,  # 4,664 / 16,336
        "note": "DCD heart transplantation began 2020; growing rapidly",
        "trend": "increasing (DCD hearts + OCS TransMedics)",
    },
    "lung": {
        "overall_recovery_rate": 0.201,  # 3,276 / 16,336
        "note": "Ex-vivo lung perfusion (EVLP) has expanded utilization",
        "trend": "increasing (EVLP + XVIVO effect)",
    },
    "pancreas": {
        "overall_recovery_rate": 0.075,  # 1,222 / 16,336
        "note": "Declining utilization; shifting to islet cell transplants",
        "trend": "declining",
    },
    "intestine": {
        "overall_recovery_rate": 0.008,  # <1% of donors yield intestines (~100-150/year)
        "note": "Very rare; not validated per-COD (too few cases)",
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
    # National COD distribution among donors (OPTN 2023: 16,336 total)
    # HEAD TRAUMA: 3565 (21.8%), ANOXIA: 8076 (49.4%), STROKE: 3926 (24.0%), OTHER: 716 (4.4%)
    # OPTN "ANOXIA" includes drug_intox (~60%) + other anoxia (~40%); split estimated from PMC
    if cod_weights is None:
        cod_weights = {
            "trauma": 0.218,
            "cardiovascular": 0.044,
            "drug_intox": 0.296,
            "stroke": 0.240,
            "anoxia": 0.198,
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
    print(f"\nOur source: PMC10329409 (2005-2019), updated with OPTN 2023 cross-validation")
    print(f"Benchmark: OPTN 2023 national data (hrsa.unos.org, March 2026)")
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

    print("\nNOTES:")
    print("  - Rates were cross-validated against OPTN 2023 (March 2026)")
    print("  - 15/30 cells updated where drift >10% from PMC 2005-2019 averages")
    print("  - Cardiovascular rates unchanged (no OPTN equivalent category)")
    print("  - Drug_intox/anoxia split maintained from PMC ratio; OPTN lumps both as ANOXIA")
    print("  - Re-run validation annually when new OPTN reports are released")
    print()

    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
