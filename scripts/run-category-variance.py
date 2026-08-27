#!/usr/bin/env python3
"""Which scoring categories can actually move the ranking? (L-084)

A weight can only affect the center ranking through a sub-score that VARIES
between centers. A category that is identical everywhere contributes the same
constant to every center's total, so its weight — however large — cannot
change the order.

This turns out not to be hypothetical. `_medical_compatibility` takes only the
patient profile ("Pure patient-profile scoring — no geographic data needed"),
so it is by construction the same for all centers. It carries the LARGEST
weight in the model, 0.25.

The rank-driving share reported here is `weight x between-center SD`,
normalised across categories. It is the honest answer to "what is this ranking
actually made of", as opposed to the weight vector, which is what the UI shows.
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from artifact_meta import stamped_meta  # noqa: E402
from reference_patients import ORGANS, reference_patient_kwargs  # noqa: E402
from services.data_loader import load_all  # noqa: E402
from services.scoring import DEFAULT_WEIGHTS, score_all_centers  # noqa: E402

# Below this, a category's between-center spread is float noise rather than
# signal — i.e. the sub-score is constant and the category is inert.
INERT_SD = 1e-9


def analyze(organ: str) -> dict:
    rows = score_all_centers(reference_patient_kwargs(organ), DEFAULT_WEIGHTS)
    out = {"organ": organ, "n_centers": len(rows), "categories": {}}
    contrib = {}
    for cat, weight in DEFAULT_WEIGHTS.items():
        vals = np.array([r.breakdown.get(cat, 0.0) for r in rows], dtype=float)
        sd = float(vals.std())
        contrib[cat] = weight * sd
        out["categories"][cat] = {
            "weight": weight,
            "between_center_sd": sd,
            "inert": sd < INERT_SD,
            "constant_value": float(vals[0]) if sd < INERT_SD else None,
        }
    total = sum(contrib.values())
    for cat, c in contrib.items():
        out["categories"][cat]["rank_driving_share"] = (
            round(c / total, 4) if total else 0.0)
    out["inert_weight_mass"] = round(
        sum(w for c, w in DEFAULT_WEIGHTS.items()
            if out["categories"][c]["inert"]), 4)
    return out


def main() -> None:
    load_all()
    results = [analyze(o) for o in ORGANS]

    out = REPO / "docs-site" / "static" / "data" / "category-variance.json"
    out.write_text(json.dumps({
        "organs": {r["organ"]: r for r in results},
        "_meta": stamped_meta(
            script="scripts/run-category-variance.py",
            metric="weight x between-center SD, normalised across categories",
        ),
    }, indent=2) + "\n")

    for r in results:
        print(f"\n=== {r['organ']} (n={r['n_centers']}) — "
              f"inert weight mass {r['inert_weight_mass']:.2f} ===")
        print(f"{'category':<22} {'weight':>7} {'sd':>8} {'rank share':>11}")
        for cat, c in sorted(r["categories"].items(),
                             key=lambda kv: -kv[1]["rank_driving_share"]):
            flag = "  <- INERT" if c["inert"] else ""
            print(f"{cat:<22} {c['weight']:>7.2f} {c['between_center_sd']:>8.2f} "
                  f"{100 * c['rank_driving_share']:>10.1f}%{flag}")
    print(f"\nwrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
