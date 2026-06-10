#!/usr/bin/env python3
"""
Center-level calibration: TransPlan predictions vs observed SRTR rates.

This is the feasible substitute for the "COMET-Lung comparison" in
docs/landscape/README.md. COMET does NOT rank centers for individual patients
— it's a population-level policy simulator that outputs aggregate waitlist
statistics. So a center-ranking comparison against COMET is not possible.

Instead we validate against the SRTR Program-Specific Reports directly: do the
centers TransPlan predicts as fast-access actually have high observed 1-year
transplant rates? This is the meaningful, publishable calibration.

IMPORTANT — what this does and does not show:
  - Predicted p_transplant_12mo is a single reference patient's probability;
    observed transplant_rate is a population rate over each center's real case
    mix. These live on different scales, so VALUE equality is not expected.
    The valid signal is RANK correlation (Spearman rho): does the model order
    centers the way the registry does?
  - TransPlan's wait-time factors derive from SRTR Table B10 (wait times); the
    observed transplant rate is Table B7 (a different field). So this is a
    cross-field internal-consistency check, not a fully independent external
    benchmark. It verifies the competing-risks model translates wait-time
    structure into transplant rates that track reality.

Outputs:
  - docs-site/static/data/center-calibration-{organ}.json  (scatter + stats)
  - docs/center-calibration-report.md
  - console summary

Usage:
    cd TransPlan && .venv/bin/python scripts/run-center-calibration.py
    cd TransPlan && .venv/bin/python scripts/run-center-calibration.py --organ liver
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from models.schemas import PatientProfile  # noqa: E402
from services.data_loader import load_all  # noqa: E402
from services.monte_carlo import simulate  # noqa: E402

OBSERVED_PATH = REPO_ROOT / "data" / "srtr-observed-rates.json"
JSON_OUT_DIR = REPO_ROOT / "docs-site" / "static" / "data"
REPORT_PATH = REPO_ROOT / "docs" / "center-calibration-report.md"

N_ITERATIONS = 2000
SEED = 42
# Centers with tiny cohorts have noisy observed rates; report a filtered view too.
MIN_N = 10


def reference_patient(organ: str) -> PatientProfile:
    """A single, clearly-stated reference candidate per organ."""
    base = {"organ": organ, "blood_type": "O+", "urgency": 2, "age": 50,
            "sex": "male", "adjust_for_cause_of_death": False}
    if organ == "kidney":
        base["cpra"] = 20
    elif organ == "liver":
        base["meld"] = 22
    elif organ == "lung":
        base["las"] = 50.0
    return PatientProfile(**base)


def _spearman(x, y):
    if len(x) < 3:
        return None, None
    rho, p = stats.spearmanr(x, y)
    return (None if np.isnan(rho) else round(float(rho), 4),
            None if np.isnan(p) else float(p))


def calibrate(organ: str) -> dict:
    observed_all = json.loads(OBSERVED_PATH.read_text())
    if organ not in observed_all:
        raise SystemExit(f"No observed data for {organ}. Run fetch-srtr-observed-rates.py.")
    observed = observed_all[organ]["centers"]

    patient = reference_patient(organ)
    result = simulate(patient, n_iterations=N_ITERATIONS, seed=SEED)

    rows = []
    for c in result.cities:
        obs = observed.get(c.center_code)
        if not obs or obs.get("transplant_rate") is None:
            continue
        rows.append({
            "center_code": c.center_code,
            "center_name": c.center_name,
            "predicted_p12": round(c.p_transplant_12mo, 4),
            "predicted_median_wait": round(c.median_wait_months, 2),
            "observed_tx_rate": obs["transplant_rate"],
            "observed_n": obs.get("n"),
        })

    matched = len(rows)
    pred_p12 = [r["predicted_p12"] for r in rows]
    pred_wait = [r["predicted_median_wait"] for r in rows]
    obs_tx = [r["observed_tx_rate"] for r in rows]

    # Headline: do we rank centers like the registry does?
    rho_p12, p_p12 = _spearman(pred_p12, obs_tx)        # expect positive
    rho_wait, p_wait = _spearman(pred_wait, obs_tx)     # expect negative

    # Filtered to centers with non-tiny cohorts (less noisy ground truth)
    big = [r for r in rows if (r["observed_n"] or 0) >= MIN_N]
    rho_p12_big, p_p12_big = _spearman(
        [r["predicted_p12"] for r in big], [r["observed_tx_rate"] for r in big]
    )

    return {
        "organ": organ,
        "n_iterations": N_ITERATIONS,
        "seed": SEED,
        "reference_patient": {
            "blood_type": patient.blood_type, "age": patient.age,
            "sex": patient.sex, "urgency": patient.urgency,
            "cpra": patient.cpra, "meld": patient.meld, "las": patient.las,
        },
        "matched_centers": matched,
        "stats": {
            "spearman_p12_vs_txrate": {"rho": rho_p12, "p_value": p_p12,
                                       "expected_sign": "positive", "n": matched},
            "spearman_wait_vs_txrate": {"rho": rho_wait, "p_value": p_wait,
                                        "expected_sign": "negative", "n": matched},
            f"spearman_p12_vs_txrate_n>={MIN_N}": {"rho": rho_p12_big, "p_value": p_p12_big,
                                                   "n": len(big)},
        },
        "centers": sorted(rows, key=lambda r: r["observed_tx_rate"], reverse=True),
    }


def write_report(results: list[dict]):
    lines = [
        "# Center-Level Calibration: TransPlan vs Observed SRTR Rates",
        "",
        "_Generated by `scripts/run-center-calibration.py`._",
        "",
        "## What this validates",
        "",
        "Whether the centers TransPlan predicts as fast-access actually have high "
        "observed 1-year transplant rates in the SRTR Program-Specific Reports. The "
        "headline metric is **Spearman rank correlation (ρ)** — predicted and observed "
        "live on different scales (single-patient probability vs population rate), so "
        "rank agreement, not value equality, is the meaningful signal.",
        "",
        "> **Note on COMET:** The originally-planned COMET-Lung comparison is not "
        "feasible — COMET is a population-level policy simulator and does not produce "
        "per-patient center rankings. This SRTR calibration is the substitute. It is a "
        "cross-field internal-consistency check (wait-time-derived model vs observed "
        "transplant rate), not a fully independent external benchmark.",
        "",
        "> **Not circular:** the prediction is driven by wait-time distributions "
        "(SRTR Table B10) and waitlist death/removal rates (Table B7), while the ground "
        "truth is the Table B7 transplant rate (SAL_TOTTX_C12) — a different field that "
        "is not an input to the model. Acceptance modeling (the only center-volume-derived "
        "path) is disabled in this run, so observed transplant volume does not leak into "
        "the prediction.",
        "",
        "## Results",
        "",
        "| Organ | Centers | ρ (p12 vs tx-rate) | p | ρ (wait vs tx-rate) | p |",
        "|-------|---------|--------------------|---|---------------------|---|",
    ]
    for r in results:
        s = r["stats"]
        a, b = s["spearman_p12_vs_txrate"], s["spearman_wait_vs_txrate"]
        lines.append(
            f"| {r['organ']} | {r['matched_centers']} | "
            f"{a['rho']} | {_fmt_p(a['p_value'])} | {b['rho']} | {_fmt_p(b['p_value'])} |"
        )
    lines += [
        "",
        "- **ρ (p12 vs tx-rate)** should be **positive**: centers predicted to transplant "
        "sooner should have higher observed transplant rates.",
        "- **ρ (wait vs tx-rate)** should be **negative**: centers predicted to have longer "
        "waits should have lower observed transplant rates.",
        "",
        "Per-center scatter data: `docs-site/static/data/center-calibration-{organ}.json`.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines))


def _fmt_p(p):
    if p is None:
        return "—"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--organ", default="lung",
                    help="Organ to calibrate, or 'all' (default: lung)")
    args = ap.parse_args()

    load_all()
    observed_all = json.loads(OBSERVED_PATH.read_text())
    organs = [o for o in observed_all if o != "_meta"] if args.organ == "all" else [args.organ]

    JSON_OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for organ in organs:
        print(f"\n{'='*64}\n  Calibrating {organ}\n{'='*64}")
        res = calibrate(organ)
        results.append(res)
        s = res["stats"]
        a = s["spearman_p12_vs_txrate"]
        b = s["spearman_wait_vs_txrate"]
        print(f"  matched centers: {res['matched_centers']}")
        print(f"  Spearman rho (predicted p12  vs observed tx-rate): "
              f"{a['rho']}  (p={_fmt_p(a['p_value'])})  [expect +]")
        print(f"  Spearman rho (predicted wait vs observed tx-rate): "
              f"{b['rho']}  (p={_fmt_p(b['p_value'])})  [expect -]")
        out = JSON_OUT_DIR / f"center-calibration-{organ}.json"
        out.write_text(json.dumps(res, indent=2))
        print(f"  wrote {out.relative_to(REPO_ROOT)}")

    write_report(results)
    print(f"\nWrote {REPORT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
