#!/usr/bin/env python3
"""Pediatric per-center calibration against SRTR's own tier ratings (#335).

WHY NOT THE OBVIOUS CHECK
-------------------------
The adult calibration (scripts/run-center-calibration.py) correlates predicted
p12 against the observed SRTR transplant rate. Running that same check on the
pediatric path would be **circular and therefore worthless**: the pediatric
engine ANCHORS each center's 12-month probability to that center's calibrated
observed pediatric rate (monte_carlo._pediatric_dist). Correlating an anchor
with the thing it was anchored to measures arithmetic, not agreement. This
script computes that number anyway and reports it flagged as circular, purely
so nobody re-derives it later and mistakes it for evidence.

THE ACTUAL GROUND TRUTH
-----------------------
SRTR publishes a risk-adjusted 5-tier rating per program, including a
PEDIATRIC-specific "transplant rate faster than expected" tier
(`pediatric_transplant_faster` in data/srtr-tiers-centers.json, tier 1 = much
slower than expected, tier 5 = much faster). That grade comes from SRTR's own
risk-adjustment model, not from ours, and it is not an input to any part of
the pediatric pipeline. Ranking our pediatric predictions against it is a
genuine external check.

Two things get measured against it:
  1. Does the pediatric engine rank centers the way SRTR's pediatric tiers do?
  2. Does the small-cohort shrinkage HELP? Thin pediatric cohorts are noisy, so
     shrinkage should improve agreement with a risk-adjusted grade. If it does
     not, the shrinkage constant is wrong and should be revisited. (This is the
     same question #358 asked of panel shrinkage, where the answer was no.)

Outputs: docs/pediatric-calibration-report.md,
         docs-site/static/data/pediatric-calibration.json
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from reference_patients import pediatric_reference_patient_kwargs  # noqa: E402

from models.schemas import PatientProfile  # noqa: E402
from services.data_loader import get_data, load_all  # noqa: E402
from services.monte_carlo import simulate  # noqa: E402

ORGANS = ["kidney", "liver", "heart", "lung"]
TIER_FIELD = "pediatric_transplant_faster"
N_ITER = 2000
SEED = 42
MIN_CENTERS = 15        # below this a Spearman on a 5-level tier is noise
SHRINK_PY = 10.0        # mirrors monte_carlo._PEDS_SHRINK_PY


def _spearman(x, y):
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None, None
    r = stats.spearmanr(x, y)
    return float(r.statistic), float(r.pvalue)


def calibrate(organ: str) -> dict | None:
    data = get_data()
    tiers = json.loads((REPO / "data" / "srtr-tiers-centers.json").read_text())
    organ_tiers = tiers.get(organ, {})
    peds = data.pediatric.get(organ, {}).get("centers", {})
    if not peds:
        return None

    patient = PatientProfile(**pediatric_reference_patient_kwargs(organ))
    result = simulate(patient, n_iterations=N_ITER, seed=SEED)

    rows = []
    for c in result.cities:
        rec = peds.get(c.center_code)
        tier = (organ_tiers.get(c.center_code) or {}).get(TIER_FIELD)
        if rec is None or tier is None:
            continue
        rows.append({
            "center_code": c.center_code,
            "center_name": c.center_name,
            "predicted_p12": round(c.p_transplant_12mo, 4),
            "predicted_median_wait": round(c.median_wait_months, 2),
            "srtr_pediatric_tier": tier,
            "observed_ped_rate": rec.get("transplant_rate"),
            "observed_ped_ratio": rec.get("transplant_ratio"),
            "person_years": round(rec.get("person_years") or 0.0, 1),
        })

    if len(rows) < MIN_CENTERS:
        return {"organ": organ, "matched_centers": len(rows),
                "insufficient": True}

    p12 = [r["predicted_p12"] for r in rows]
    tier = [r["srtr_pediatric_tier"] for r in rows]
    rho_tier, p_tier = _spearman(p12, tier)

    # The independent check, restricted to centers whose pediatric cohort is
    # thick enough that neither side is mostly noise.
    thick = [r for r in rows if r["person_years"] >= 10.0]
    rho_thick, p_thick = _spearman([r["predicted_p12"] for r in thick],
                                   [r["srtr_pediatric_tier"] for r in thick])

    # Does shrinkage help? This must compare the shrinkage step against
    # ITSELF, not predicted p12 against the raw rate — p12 also carries
    # competing risks, blood-type matching and the lognormal solve, so that
    # comparison would attribute the whole pipeline's error to shrinkage.
    # Here the ONLY difference between the two series is the shrinkage weight.
    peds_block = data.pediatric.get(organ, {})
    nat_rate = (peds_block.get("national") or {}).get("transplant_rate")
    rated = [r for r in rows if r["observed_ped_rate"] is not None]
    raw = [r["observed_ped_rate"] for r in rated]
    raw_tier = [r["srtr_pediatric_tier"] for r in rated]
    rho_raw, _ = _spearman(raw, raw_tier)
    if nat_rate is not None:
        shrunk_rate = []
        for r in rated:
            py = r["person_years"]
            w = py / (py + SHRINK_PY)
            shrunk_rate.append(w * r["observed_ped_rate"] + (1.0 - w) * nat_rate)
        rho_shrunk_rate, _ = _spearman(shrunk_rate, raw_tier)
    else:
        rho_shrunk_rate = None

    # The circular one, computed only to be labelled as such.
    rho_circular, _ = _spearman(
        [r["predicted_p12"] for r in rows if r["observed_ped_rate"] is not None],
        raw)

    # SRTR's own risk-adjusted O/E ratio, a second (also SRTR-produced) view.
    ratio_rows = [r for r in rows if r["observed_ped_ratio"] is not None]
    rho_ratio, _ = _spearman([r["predicted_p12"] for r in ratio_rows],
                             [r["observed_ped_ratio"] for r in ratio_rows])

    return {
        "organ": organ,
        "matched_centers": len(rows),
        "thick_cohort_centers": len(thick),
        "reference_patient": pediatric_reference_patient_kwargs(organ),
        "n_iterations": N_ITER,
        "seed": SEED,
        "stats": {
            "spearman_p12_vs_srtr_tier": {
                "rho": None if rho_tier is None else round(rho_tier, 4),
                "p_value": p_tier, "independent": True,
                "note": "Primary result. SRTR's risk-adjusted pediatric tier "
                        "is not an input to the pediatric pipeline."},
            "spearman_p12_vs_srtr_tier_thick_cohorts": {
                "rho": None if rho_thick is None else round(rho_thick, 4),
                "p_value": p_thick, "n": len(thick), "independent": True},
            "shrinkage_ablation": {
                "shrunk_rho": (None if rho_shrunk_rate is None
                               else round(rho_shrunk_rate, 4)),
                "raw_rho": None if rho_raw is None else round(rho_raw, 4),
                "delta": (None if (rho_shrunk_rate is None or rho_raw is None)
                          else round(rho_shrunk_rate - rho_raw, 4)),
                "shrink_py": SHRINK_PY,
                "n": len(rated),
                "shrinkage_helps": (rho_shrunk_rate is not None
                                    and rho_raw is not None
                                    and rho_shrunk_rate > rho_raw),
                "note": "Shrunk vs raw pediatric RATE, both ranked against the "
                        "SRTR tier. Only the shrinkage weight differs between "
                        "the two series, so the delta is attributable to "
                        "shrinkage alone."},
            "spearman_p12_vs_srtr_oe_ratio": {
                "rho": None if rho_ratio is None else round(rho_ratio, 4),
                "n": len(ratio_rows), "independent": True},
            "spearman_p12_vs_observed_rate_CIRCULAR": {
                "rho": None if rho_circular is None else round(rho_circular, 4),
                "independent": False,
                "note": "NOT EVIDENCE. p12 is anchored to this rate by "
                        "construction; a high value here is arithmetic."},
        },
        "centers": rows,
    }


def main() -> int:
    load_all()
    out = {"organs": {}, "_meta": {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "scripts/run-pediatric-calibration.py",
        "ground_truth": f"data/srtr-tiers-centers.json :: {TIER_FIELD}",
        "method": "Spearman rank correlation between the pediatric engine's "
                  "predicted 12-month transplant probability and SRTR's "
                  "risk-adjusted pediatric transplant-rate tier.",
    }}

    lines = ["# Pediatric center calibration (#335)", "",
             "Predicted pediatric access vs **SRTR's own risk-adjusted",
             "pediatric tier** — the one pediatric ground truth that is not an",
             "input to our pipeline.", "",
             "| organ | centers | ρ vs SRTR tier | ρ (cohorts ≥10 py) | "
             "ρ vs SRTR O/E ratio | shrinkage helps? |",
             "|---|---|---|---|---|---|"]

    for organ in ORGANS:
        res = calibrate(organ)
        if res is None:
            continue
        if res.get("insufficient"):
            lines.append(f"| {organ} | {res['matched_centers']} | — | — | — | "
                         f"too few matched centers |")
            out["organs"][organ] = res
            continue
        s = res["stats"]
        a = s["spearman_p12_vs_srtr_tier"]["rho"]
        b = s["spearman_p12_vs_srtr_tier_thick_cohorts"]
        c = s["spearman_p12_vs_srtr_oe_ratio"]["rho"]
        helps = s["shrinkage_ablation"]
        def fmt(v):
            return "—" if v is None else f"{v:.3f}"

        lines.append(
            f"| {organ} | {res['matched_centers']} | {fmt(a)} | "
            f"{fmt(b['rho'])} (n={b['n']}) | {fmt(c)} | "
            f"{'yes' if helps['shrinkage_helps'] else 'no'} "
            f"({fmt(helps['shrunk_rho'])} vs raw {fmt(helps['raw_rho'])}) |")
        out["organs"][organ] = res
        print(f"{organ:8s} n={res['matched_centers']:3d} "
              f"rho_tier={a} rho_thick={b['rho']} rho_ratio={c} "
              f"shrinkage_helps={helps['shrinkage_helps']}")

    lines += ["", "## How to read this", "",
              "SRTR's pediatric tier is a 1-5 grade (1 = much slower than",
              "expected, 5 = much faster) produced by SRTR's own",
              "risk-adjustment model. It is coarse — five levels across a",
              "hundred centers means many ties — so the attainable rank",
              "correlation is capped well below 1 even for a perfect model.",
              "Read these as directional agreement, not as a score.", "",
              "The `_CIRCULAR` entry in the JSON is deliberately included and",
              "deliberately excluded from this table: the pediatric engine",
              "anchors each center's 12-month probability to that center's",
              "observed pediatric rate, so correlating the two measures",
              "arithmetic. It is recorded only to stop anyone re-deriving it",
              "and reporting it as validation.", "",
              "The shrinkage column is an ABLATION, not a comparison of the",
              "engine against a baseline: both series are pediatric transplant",
              "rates ranked against the SRTR tier, and the only difference",
              "between them is whether the shrinkage weight was applied. An",
              "earlier version of this script compared predicted p12 against",
              "the raw rate instead, which attributed the entire pipeline's",
              "error to shrinkage and made shrinkage look catastrophic for",
              "heart (-0.24) and lung (-0.40). Those numbers were an artifact",
              "of the confound; the isolated effect is small in both",
              "directions. Read the delta column, not its sign alone.", "",
              "This is the same question the panel-shrinkage study (#358) asked",
              "of cross-release pooling, where the answer was a clear no — so",
              "it is measured here rather than assumed.", "",
              f"Generated by `scripts/run-pediatric-calibration.py` on "
              f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')} "
              f"(seed {SEED}, {N_ITER} iterations).", ""]

    (REPO / "docs" / "pediatric-calibration-report.md").write_text("\n".join(lines))
    (REPO / "docs-site" / "static" / "data" / "pediatric-calibration.json").write_text(
        json.dumps(out, indent=1))
    print("\nWrote docs/pediatric-calibration-report.md + "
          "docs-site/static/data/pediatric-calibration.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
