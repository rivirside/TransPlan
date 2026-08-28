#!/usr/bin/env python3
"""Does the 12->24 month hazard-shape assumption matter? (#233 / BBN-19)

The BBN's CompetingOutcome node is the model's one fully data-grounded node:
each cell is a center's OBSERVED 12-month outcome vector from SRTR Table B7.
But the headline number is at **24 months**, and SRTR does not publish that.
`_extend_12_to_24` bridges the gap by assuming **constant cause-specific
hazards**, so S(24) = S(12)^2.

That assumption is not idle, and the project has already contradicted it
elsewhere: #297 measured the interval removal hazard within a single cohort
and found it FALLS with time on the list for liver, heart, lung and intestine
(depletion of susceptibles — the sickest candidates leave early, so the
survivors are healthier). If the second-year hazard is lower than the first,
S(24) > S(12)^2 and every 24-month probability is overstated.

So the exponent is swept directly:

    S(24) = S(12) ** alpha

    alpha = 1.0   no second-year hazard at all (nothing more happens)
    alpha = 1.5   second-year hazard about half the first (matches #297's
                  direction for the four organs where removal risk falls)
    alpha = 2.0   SHIPPED: constant hazard
    alpha = 2.5   second-year hazard higher than the first
    alpha = 3.0   sharply rising

Each cause-specific CIF scales by (1 - S(24)) / (1 - S(12)), which preserves
the simplex for any alpha.

Usage:
    cd backend && python3 ../scripts/run-horizon-extension-sweep.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent))

from artifact_meta import stamped_meta  # noqa: E402
from models.schemas import PatientProfile  # noqa: E402
from services.data_loader import load_all  # noqa: E402
from reference_patients import reference_patient_kwargs  # noqa: E402

ORGANS = ["kidney", "liver", "heart", "lung"]
GRANULARITIES = ["state", "full"]
ALPHAS = [
    ("1.0 (no second-year hazard)", 1.0),
    ("1.5 (declining, matches #297)", 1.5),
    ("2.0 (SHIPPED: constant hazard)", 2.0),
    ("2.5 (rising)", 2.5),
    ("3.0 (sharply rising)", 3.0),
]


def make_extender(alpha: float):
    """S(24) = S(12)**alpha, with the CIFs rescaled to keep the simplex."""
    def _extend(p12: np.ndarray) -> np.ndarray:
        tx, death, removed, wait = p12
        s24 = wait ** alpha
        denom = 1.0 - wait
        factor = (1.0 - s24) / denom if denom > 1e-12 else 0.0
        return np.array([tx * factor, death * factor, removed * factor, s24])
    return _extend


def apply_alpha(alpha: float) -> None:
    import services.bbn_parameterizer as bp
    bp._extend_12_to_24 = make_extender(alpha)


def outcomes_by_center(organ: str, granularity: str) -> dict[str, dict]:
    """p24 AND the competing-risk breakdown.

    Measuring p24 alone was the first version of this sweep, and it reported
    a perfect null for every variant -- because p24 is ALGEBRAICALLY immune
    to this constant (see the report). The quantity the assumption actually
    governs is the mortality/removal/waiting split, so the sweep has to look
    at it or it is measuring a cancellation and calling it a null result.
    """
    from services.bayesian_network import reset_model, simulate_bbn
    reset_model()
    kwargs = reference_patient_kwargs(organ)
    kwargs.pop("adjust_for_cause_of_death", None)
    patient = PatientProfile(bbn_granularity=granularity, **kwargs)
    return {c.center_code: {
        "p24": c.p_transplant_24mo,
        "mortality": c.competing_risks["p_mortality_24mo"],
        "removed": c.competing_risks["p_delisting_24mo"],
        "waiting": c.competing_risks["p_still_waiting_24mo"],
    } for c in simulate_bbn(patient).cities}


def main() -> int:
    load_all()
    rows = []
    for granularity in GRANULARITIES:
        for organ in ORGANS:
            apply_alpha(2.0)
            base = outcomes_by_center(organ, granularity)
            if len(base) < 10:
                continue
            codes = sorted(base)
            b = [base[c]["p24"] for c in codes]
            base_top10 = [c for c, _ in
                          sorted(base.items(), key=lambda kv: -kv[1]["p24"])[:10]]

            for label, alpha in ALPHAS:
                if alpha == 2.0:
                    continue
                apply_alpha(alpha)
                alt = outcomes_by_center(organ, granularity)
                if set(alt) != set(base):
                    continue
                a = [alt[c]["p24"] for c in codes]
                rho = stats.spearmanr(b, a).statistic
                alt_top10 = [c for c, _ in
                             sorted(alt.items(), key=lambda kv: -kv[1]["p24"])[:10]]
                row = {
                    "granularity": granularity, "organ": organ, "variant": label,
                    "alpha": alpha,
                    "spearman": round(float(rho), 5),
                    "max_abs_delta_p24": round(max(abs(x - y) for x, y in zip(a, b)), 6),
                    "mean_p24_shipped": round(float(np.mean(b)), 4),
                    "mean_p24_variant": round(float(np.mean(a)), 4),
                    "top10_identical": alt_top10 == base_top10,
                    "top10_overlap": len(set(alt_top10) & set(base_top10)),
                }
                # The quantities this constant actually governs.
                for field in ("mortality", "removed", "waiting"):
                    bs = [base[c][field] for c in codes]
                    als = [alt[c][field] for c in codes]
                    row[f"mean_{field}_shipped"] = round(float(np.mean(bs)), 5)
                    row[f"mean_{field}_variant"] = round(float(np.mean(als)), 5)
                    row[f"max_abs_delta_{field}"] = round(
                        max(abs(x - y) for x, y in zip(bs, als)), 5)
                rows.append(row)
            apply_alpha(2.0)

    out = {
        "_meta": stamped_meta(
            description="BBN 12->24 month horizon-extension sweep (#233 / BBN-19)",
            script="scripts/run-horizon-extension-sweep.py"),
        "results": rows,
    }
    dest = Path(__file__).parent.parent / "data" / "horizon-extension-sweep.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")

    largest_p24 = max((r["max_abs_delta_p24"] for r in rows), default=0.0)
    largest_mort = max((r["max_abs_delta_mortality"] for r in rows), default=0.0)
    ratios = [r["mean_mortality_variant"] / r["mean_mortality_shipped"]
              for r in rows if r["mean_mortality_shipped"] > 0]
    print(f"{len(rows)} comparisons")
    print(f"largest |delta p24| (headline):        {largest_p24:.6f}")
    print(f"largest |delta mortality| (breakdown): {largest_mort:.5f}")
    print(f"mean-mortality ratio vs shipped:       "
          f"{min(ratios):.2f}x .. {max(ratios):.2f}x")
    print(f"top-10 identical in:                   "
          f"{sum(1 for r in rows if r['top10_identical'])}/{len(rows)}")
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
