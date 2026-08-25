#!/usr/bin/env python3
"""
Decile calibration (#295) — the T-calibration gate from the BBN rebuild plan.

Buckets centers into deciles of the model's prediction and compares each
decile's mean prediction against the mean OBSERVED SRTR rate, for:

  1. Transplant: closed-form reference-patient p12 vs observed 1-yr
     transplant rate (SAL_TOTTX_C12, cohorts n >= 10).
  2. Mortality: the model's annual waitlist mortality (center-adjusted) vs
     observed 1-yr waitlist death rate (SAL_WLDIED_C12).

Honest scope: predictions are reference-patient quantities, observed rates are
case-mix population rates — LEVELS are not expected to match. What decile
calibration checks is monotonicity and proportionality: do centers the model
calls riskier/slower actually lose/transplant more patients, decile by decile?
Reported per decile plus a Spearman over deciles and an OLS slope of observed
on predicted decile means.

Outputs:
  - docs-site/static/data/decile-calibration.json
  - docs/decile-calibration-report.md

Usage:
    cd TransPlan && .venv/bin/python scripts/run-decile-calibration.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats as sstats

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from services.data_loader import load_all, get_data  # noqa: E402
from services.brier_score import _analytical_p_transplant_12mo  # noqa: E402
from services.competing_risks import get_annual_mortality_rate  # noqa: E402

JSON_OUT = REPO_ROOT / "docs-site" / "static" / "data" / "decile-calibration.json"
REPORT = REPO_ROOT / "docs" / "decile-calibration-report.md"

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
MIN_N = 10
MIN_CENTERS = 30  # need enough centers for deciles to mean anything

import importlib.util as _ilu
_rp_spec = _ilu.spec_from_file_location(
    "reference_patients", Path(__file__).parent / "reference_patients.py")
_rp = _ilu.module_from_spec(_rp_spec)
_rp_spec.loader.exec_module(_rp)
reference_patient_kwargs = _rp.reference_patient_kwargs

# #339: identical to run-center-calibration.py BY CONSTRUCTION — one shared
# definition instead of a parity claim in a comment.
REF = {
    organ: {
        **{"cpra": None, "meld": None, "las": None},
        **{k: v for k, v in reference_patient_kwargs(organ).items()
           if k not in ("organ", "adjust_for_cause_of_death")},
    }
    for organ in _rp.ORGANS
}


def _observed(organ: str) -> dict[str, dict]:
    block = get_data().srtr_observed_rates.get(organ, {})
    out = {}
    for code, rec in block.get("centers", {}).items():
        if (rec.get("n") or 0) >= MIN_N:
            out[code] = rec
    return out


def _decile_table(pred: dict[str, float], obs: dict[str, float]) -> dict | None:
    common = sorted(set(pred) & set(obs))
    if len(common) < MIN_CENTERS:
        return None
    p = np.array([pred[c] for c in common])
    o = np.array([obs[c] for c in common])
    # Decile assignment by predicted value (ties broken by stable order)
    order = np.argsort(p, kind="stable")
    deciles = np.empty(len(common), dtype=int)
    for i, idx in enumerate(order):
        deciles[idx] = min(9, i * 10 // len(common))

    rows = []
    for d in range(10):
        mask = deciles == d
        if not np.any(mask):
            continue
        rows.append({
            "decile": d + 1,
            "n_centers": int(np.sum(mask)),
            "mean_predicted": round(float(np.mean(p[mask])), 4),
            "mean_observed": round(float(np.mean(o[mask])), 4),
        })
    mp = np.array([r["mean_predicted"] for r in rows])
    mo = np.array([r["mean_observed"] for r in rows])
    rho = float(np.asarray(sstats.spearmanr(mp, mo)[0]))
    slope, intercept = np.polyfit(mp, mo, 1)
    return {
        "n_centers": len(common),
        "decile_rows": rows,
        "decile_spearman": round(rho, 4),
        "ols_slope": round(float(slope), 4),
        "ols_intercept": round(float(intercept), 4),
    }


def main():
    load_all()
    result = {"transplant": {}, "mortality": {}}

    for organ in ORGANS:
        ref = REF[organ]
        obs = _observed(organ)
        centers = get_data().centers_for_organ(organ)

        pred_tx, pred_mort, obs_tx, obs_mort = {}, {}, {}, {}
        for c in centers:
            code = c.get("code", "")
            rec = obs.get(code)
            if not rec:
                continue
            if rec.get("transplant_rate") is not None:
                pred_tx[code] = _analytical_p_transplant_12mo(
                    organ, ref["blood_type"], c.get("name", code),
                    urgency=ref["urgency"], cpra=ref["cpra"], meld=ref["meld"],
                    las=ref["las"], center_code=code, age=ref["age"], sex=ref["sex"],
                )
                obs_tx[code] = rec["transplant_rate"] / 100.0
            if rec.get("waitlist_death_rate") is not None:
                pred_mort[code] = get_annual_mortality_rate(
                    organ=organ, city=c.get("name", ""), urgency=ref["urgency"],
                    meld=ref["meld"], center_code=code,
                )
                obs_mort[code] = rec["waitlist_death_rate"] / 100.0

        tx = _decile_table(pred_tx, obs_tx)
        mort = _decile_table(pred_mort, obs_mort)
        if tx:
            result["transplant"][organ] = tx
        if mort:
            result["mortality"][organ] = mort
        print(f"  {organ}: transplant {'ok' if tx else 'skipped'}, "
              f"mortality {'ok' if mort else 'skipped'}")

    payload = {
        "_meta": {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "script": "scripts/run-decile-calibration.py",
            "min_cohort_n": MIN_N,
            "min_centers": MIN_CENTERS,
            "method": ("Centers bucketed into deciles of the model prediction; "
                       "per-decile mean prediction vs mean observed SRTR rate. "
                       "Monotonicity/proportionality check, not level identity "
                       "(reference-patient prediction vs case-mix rate)."),
        },
        **result,
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=1))
    print(f"Wrote {JSON_OUT}")
    _write_report(payload)
    print(f"Wrote {REPORT}")


def _write_report(payload):
    lines = [
        "# Decile Calibration Report — #295 (T-calibration gate)",
        "",
        f"Generated {payload['_meta']['generated']} by `scripts/run-decile-calibration.py`.",
        "",
        "Centers are bucketed into deciles of the model's prediction; each decile's",
        "mean prediction is compared with its mean observed SRTR rate. Predictions",
        "are reference-patient quantities and observed rates are case-mix population",
        "rates, so **levels are not expected to match** — the check is monotonic",
        "proportionality: do centers the model calls slower/riskier actually",
        "transplant less / lose more patients, decile by decile?",
        "",
    ]
    for kind, pred_label, obs_label in [
        ("transplant", "predicted p12 (reference patient)", "observed 1-yr transplant rate"),
        ("mortality", "model annual mortality (center-adjusted)", "observed 1-yr waitlist death rate"),
    ]:
        lines += [f"## {kind.title()} calibration", ""]
        block = payload.get(kind, {})
        if not block:
            lines += ["_No organ had enough centers._", ""]
            continue
        lines += [
            f"| Organ | Centers | Decile Spearman ρ | OLS slope | Deciles monotone? |",
            "|---|---|---|---|---|",
        ]
        for organ, t in block.items():
            mo = [r["mean_observed"] for r in t["decile_rows"]]
            monotone = "yes" if all(b >= a for a, b in zip(mo, mo[1:])) else "no (noisy)"
            lines.append(
                f"| {organ} | {t['n_centers']} | {t['decile_spearman']} | "
                f"{t['ols_slope']} | {monotone} |"
            )
        lines += ["",
                  f"_Columns: {pred_label} vs {obs_label}; per-decile detail in the JSON._",
                  ""]
    skipped = [o for o in ORGANS
               if o not in payload.get("transplant", {}) and o not in payload.get("mortality", {})]
    if skipped:
        lines += [
            f"**Not covered:** {', '.join(skipped)} — fewer than "
            f"{payload['_meta']['min_centers']} centers with cohort n ≥ "
            f"{payload['_meta']['min_cohort_n']}; deciles would be noise.",
            "",
        ]
    lines += [
        "See also: `docs/center-calibration-report.md` (per-center scatter),",
        "`docs/temporal-forecast-report.md` (out-of-sample forecast),",
        "`docs/assumption-sweep-report.md` (rank robustness).",
        "",
    ]
    REPORT.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
