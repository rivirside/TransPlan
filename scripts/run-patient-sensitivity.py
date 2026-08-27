#!/usr/bin/env python3
"""Which patient inputs actually change WHICH center is recommended? (L-085)

The product's premise is a ranked list of centers "for you". This measures how
much of that "for you" reaches the ranking, by perturbing one patient attribute
at a time and asking two separate questions:

  1. **Which sub-scores does the attribute reach at all?** An attribute that
     changes no sub-score is collected and discarded.
  2. **Does the ordering change?** An attribute that only reaches a
     center-invariant sub-score (see L-084) shifts every center's total by the
     same constant and cannot reorder anything, however large its effect on the
     number displayed.

Those come apart, which is the point. Blood type has a large and correct effect
on a candidate's absolute probability, and no effect whatsoever on which center
is best for them.

Both the scoring path (what the results table sorts by) and, with
--with-simulation, the Monte Carlo path are covered, because they answer
differently and conflating them would overstate the finding.

Usage:
    python scripts/run-patient-sensitivity.py [--with-simulation] [--iterations N]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from artifact_meta import stamped_meta  # noqa: E402
from services.data_loader import load_all  # noqa: E402
from services.scoring import DEFAULT_WEIGHTS, score_all_centers  # noqa: E402

CATEGORIES = list(DEFAULT_WEIGHTS)

# One "hardest" and one "easiest" value per attribute, so each perturbation
# spans the realistic range rather than nudging.
BASE = {"organ": "kidney", "blood_type": "O+", "age": 45, "sex": "male",
        "urgency": 2, "adjust_for_cause_of_death": False}

VARIANTS = {
    "blood_type": ("O-", "AB+"),
    "age": (20, 70),
    "sex": ("male", "female"),
    "urgency": (1, 4),
}
ORGAN_EXTRA = {
    "kidney": {"cpra": (0, 99)},
    "liver": {"meld": (10, 38)},
    "lung": {"las": (30.0, 80.0)},
}


def _rows(patient):
    return {r.code: r for r in score_all_centers(patient, DEFAULT_WEIGHTS)}


def _order(rows):
    return [c for c, _ in sorted(rows.items(), key=lambda kv: -kv[1].total)]


def _spearman(order_a, order_b):
    rank = {c: i for i, c in enumerate(order_a)}
    n = len(order_b)
    if n < 3:
        return 1.0
    d2 = sum((rank[c] - i) ** 2 for i, c in enumerate(order_b))
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def analyze_organ(organ: str, with_simulation: bool, iterations: int) -> dict:
    base = dict(BASE, organ=organ)
    if organ == "liver":
        base["meld"] = 22
    elif organ == "lung":
        base["las"] = 50.0

    variants = dict(VARIANTS)
    variants.update(ORGAN_EXTRA.get(organ, {}))

    out = {"organ": organ, "attributes": {}}
    for attr, (lo, hi) in variants.items():
        rows_lo = _rows(dict(base, **{attr: lo}))
        rows_hi = _rows(dict(base, **{attr: hi}))
        order_lo, order_hi = _order(rows_lo), _order(rows_hi)

        reached = {}
        for cat in CATEGORIES:
            d = max(abs(rows_lo[c].breakdown[cat] - rows_hi[c].breakdown[cat])
                    for c in rows_lo)
            if d > 1e-9:
                reached[cat] = round(float(d), 3)

        entry = {
            "low": lo, "high": hi,
            "categories_reached": reached,
            "reaches_nothing": not reached,
            "identical_order": order_lo == order_hi,
            "spearman": round(_spearman(order_lo, order_hi), 5),
            "same_top_center": order_lo[0] == order_hi[0],
            "n_centers": len(order_lo),
        }
        if with_simulation:
            entry["simulation"] = _simulate_pair(base, attr, lo, hi, iterations)
        out["attributes"][attr] = entry
    return out


def _simulate_pair(base, attr, lo, hi, iterations):
    """The Monte Carlo path answers differently and must not be conflated."""
    from models.schemas import PatientProfile
    from services.monte_carlo import simulate

    def p24(value):
        kwargs = {k: v for k, v in dict(base, **{attr: value}).items()
                  if k != "adjust_for_cause_of_death"}
        r = simulate(PatientProfile(**kwargs), n_iterations=iterations, seed=4242)
        return {c.center_code: c.p_transplant_24mo for c in r.cities}

    a, b = p24(lo), p24(hi)
    shared = [c for c in a if c in b]
    order_a = sorted(shared, key=lambda c: -a[c])
    order_b = sorted(shared, key=lambda c: -b[c])
    return {
        "mean_p24_shift": round(float(np.mean([b[c] - a[c] for c in shared])), 4),
        "spearman": round(_spearman(order_a, order_b), 5),
        "same_top_center": order_a[0] == order_b[0],
    }


def cross_patient(organ: str) -> dict:
    """How many DIFFERENT rankings does the whole patient space produce?

    The one-at-a-time sweep above can only say which inputs matter. It cannot
    say whether the product is, in aggregate, serving one list to everybody —
    and concluding that from the sweep alone would overstate it. So this walks
    a grid of realistic patients and counts the distinct rankings that result.

    The answer is the useful correction: the ranking IS patient-dependent, via
    the inputs that do reorder, but only coarsely.
    """
    import itertools

    grids = {
        "kidney": {"blood_type": ["O-", "O+", "A+", "AB+"], "age": [20, 45, 70],
                   "urgency": [1, 2, 3], "cpra": [0, 50, 99]},
        "liver": {"blood_type": ["O-", "O+", "A+", "AB+"], "age": [20, 45, 70],
                  "meld": [10, 22, 38]},
        "heart": {"blood_type": ["O-", "O+", "A+", "AB+"], "age": [20, 45, 70],
                  "urgency": [1, 2, 3]},
        "lung": {"blood_type": ["O-", "O+", "A+", "AB+"], "age": [20, 45, 70],
                 "las": [30.0, 50.0, 80.0]},
    }
    grid_spec = grids.get(organ)
    if not grid_spec:
        return {}

    base = dict(BASE, organ=organ)
    keys = list(grid_spec)
    patients = [dict(base, **dict(zip(keys, combo)))
                for combo in itertools.product(*(grid_spec[k] for k in keys))]

    orders = [_order(_rows(p)) for p in patients]
    n = len(orders[0])

    pairs = [_spearman(a, b) for a, b in itertools.combinations(orders, 2)]
    top10 = [set(o[:10]) for o in orders]
    overlaps = [len(a & b) for a, b in itertools.combinations(top10, 2)]
    tops = {}
    for o in orders:
        tops[o[0]] = tops.get(o[0], 0) + 1

    return {
        "n_patients": len(patients),
        "n_centers": n,
        "distinct_rankings": len({tuple(o) for o in orders}),
        "distinct_top_centers": len(tops),
        "pairwise_spearman_min": round(float(np.min(pairs)), 4),
        "pairwise_spearman_median": round(float(np.median(pairs)), 4),
        "top10_overlap_median": float(np.median(overlaps)),
        "top10_overlap_min": int(np.min(overlaps)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-simulation", action="store_true")
    ap.add_argument("--iterations", type=int, default=4000)
    ap.add_argument("--organs", nargs="*", default=["kidney", "liver", "heart", "lung"])
    args = ap.parse_args()

    load_all()
    results = [analyze_organ(o, args.with_simulation, args.iterations)
               for o in args.organs]
    for r in results:
        r["cross_patient"] = cross_patient(r["organ"])

    out = REPO / "docs-site" / "static" / "data" / "patient-sensitivity.json"
    out.write_text(json.dumps({
        "organs": {r["organ"]: r for r in results},
        "_meta": stamped_meta(
            script="scripts/run-patient-sensitivity.py",
            method=("one-attribute-at-a-time over its realistic range; reports "
                    "which sub-scores are reached and whether the center order "
                    "changes"),
            with_simulation=args.with_simulation,
        ),
    }, indent=2) + "\n")

    for r in results:
        print(f"\n=== {r['organ']} ===")
        print(f"{'attribute':<12} {'reaches':<28} {'rho':>9} {'same order':>11}")
        for attr, e in r["attributes"].items():
            reached = ", ".join(e["categories_reached"]) or "(nothing)"
            print(f"{attr:<12} {reached[:27]:<28} {e['spearman']:>9.5f} "
                  f"{str(e['identical_order']):>11}")
        cp = r.get("cross_patient") or {}
        if cp:
            print(f"  across {cp['n_patients']} realistic patients: "
                  f"{cp['distinct_rankings']} distinct rankings, "
                  f"{cp['distinct_top_centers']} distinct #1 centers, "
                  f"pairwise rho median {cp['pairwise_spearman_median']}, "
                  f"top-10 overlap median {cp['top10_overlap_median']}/10")
    print(f"\nwrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
