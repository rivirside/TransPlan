#!/usr/bin/env python3
"""
Assumption sensitivity sweep (#294) — the T6 gate from the BBN rebuild plan,
generalized to the whole model.

The clinical assumptions register tracks ~38 unjustified hand-set values that
cannot all be literature-sourced solo. What CAN be measured solo is their
MATERIALITY: perturb each one ±20%, recompute the per-center results, and
report (a) Spearman rank stability of the center ordering and (b) the shift in
absolute probability / score levels. Assumptions that move nothing get demoted
in the register with this evidence; the ones that move rankings become the
sourced-or-refit shortlist.

Two engines are swept:
  1. Simulation core — closed-form p12 per center for a reference patient per
     organ (services.brier_score._analytical_p_transplant_12mo, which threads
     center_code post-#287). Perturbations mutate the loaded in-memory data.
  2. Scoring engine — score_all_centers with each of the 8 category weights
     perturbed ±20% (renormalized), reference patient per organ (SCORE-01).

Multiplier-table knobs perturb the DEVIATION FROM 1 (m' = 1 + (m-1)*f), which
matches the register's question ("is this elasticity magnitude right?");
rates, sigmas, and clamp-bound values are scaled directly.

Outputs:
  - docs-site/static/data/assumption-sweep.json
  - docs/assumption-sweep-report.md

Usage:
    cd TransPlan && .venv/bin/python scripts/run-assumption-sweep.py
"""
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats as sstats

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from services.data_loader import load_all, get_data  # noqa: E402
from services import distributions as dist_mod  # noqa: E402
from services import competing_risks as cr_mod  # noqa: E402
from services.brier_score import _analytical_p_transplant_12mo  # noqa: E402
from services.scoring import score_all_centers, DEFAULT_WEIGHTS  # noqa: E402

JSON_OUT = REPO_ROOT / "docs-site" / "static" / "data" / "assumption-sweep.json"
REPORT = REPO_ROOT / "docs" / "assumption-sweep-report.md"

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]

# Reference patients — identical to scripts/run-center-calibration.py
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

FACTORS = [0.8, 1.2]


# ---------- metric functions ----------

def sim_p12_by_center(organ: str) -> dict[str, float]:
    """Closed-form p12 for the reference patient at every center."""
    ref = REF[organ]
    out = {}
    for c in get_data().centers_for_organ(organ):
        code = c.get("code", "")
        out[code] = _analytical_p_transplant_12mo(
            organ, ref["blood_type"], c.get("name", code),
            urgency=ref["urgency"], cpra=ref["cpra"], meld=ref["meld"],
            las=ref["las"], center_code=code,
            age=ref["age"], sex=ref["sex"],
        )
    return out


def score_by_center(organ: str, weights: dict | None = None) -> dict[str, float]:
    ref = REF[organ]
    patient = {
        "organ": organ, "blood_type": ref["blood_type"], "age": ref["age"],
        "sex": ref["sex"], "urgency": ref["urgency"], "insurance": "private",
        "cpra": ref["cpra"], "meld": ref["meld"], "las": ref["las"],
    }
    results = score_all_centers(patient, custom_weights=weights)
    return {r.code: r.total for r in results}


def compare(base: dict, pert: dict) -> dict:
    common = sorted(set(base) & set(pert))
    b = np.array([base[c] for c in common])
    p = np.array([pert[c] for c in common])
    if len(common) < 8:
        return {"n": len(common), "rank_rho": None, "mean_abs_delta": None, "max_abs_delta": None}
    rho = float(np.asarray(sstats.spearmanr(b, p)[0]))
    return {
        "n": len(common),
        "rank_rho": round(rho, 4),
        "mean_abs_delta": round(float(np.mean(np.abs(p - b))), 4),
        "max_abs_delta": round(float(np.max(np.abs(p - b))), 4),
    }


# ---------- perturbation knobs ----------
# Each knob: (id, register_refs, description, mutate(f) -> restore_callable)

def _scale_deviation_inplace(d: dict, f: float):
    """m' = 1 + (m-1)*f for every numeric leaf of a (possibly nested) dict."""
    for k, v in d.items():
        if isinstance(v, dict):
            _scale_deviation_inplace(v, f)
        elif isinstance(v, (int, float)):
            d[k] = 1.0 + (v - 1.0) * f


def _scale_inplace(d: dict, key: str, f: float):
    if key in d and isinstance(d[key], (int, float)):
        d[key] = d[key] * f


def knob_bt_multipliers(organ, f):
    block = dist_mod._DISTRIBUTIONS[organ]["blood_type_multipliers"]
    saved = copy.deepcopy(block)
    _scale_deviation_inplace(block, f)
    return lambda: block.update(saved)


def knob_clinical_multipliers(organ, f):
    block = dist_mod._DISTRIBUTIONS[organ].get("clinical_multipliers", {})
    saved = copy.deepcopy(block)
    _scale_deviation_inplace(block, f)
    return lambda: (block.clear(), block.update(saved))


def knob_log_sigma(organ, f):
    block = dist_mod._DISTRIBUTIONS[organ]
    saved = block.get("log_sigma")
    _scale_inplace(block, "log_sigma", f)
    def restore():
        block["log_sigma"] = saved
    return restore


def knob_base_mortality(organ, f):
    block = cr_mod._RISKS[organ]
    saved = block.get("annual_mortality_rate")
    _scale_inplace(block, "annual_mortality_rate", f)
    def restore():
        block["annual_mortality_rate"] = saved
    return restore


def knob_base_delisting(organ, f):
    block = cr_mod._RISKS[organ]
    saved = block.get("annual_delisting_rate")
    _scale_inplace(block, "annual_delisting_rate", f)
    def restore():
        block["annual_delisting_rate"] = saved
    return restore


def knob_urgency_multipliers(organ, f):
    block = cr_mod._RISKS[organ].get("urgency_mortality_multipliers", {})
    saved = copy.deepcopy(block)
    _scale_deviation_inplace(block, f)
    return lambda: (block.clear(), block.update(saved))


def knob_clamped_wait_factors(organ, f):
    """DATA-24: center wait factors sitting AT the parse-time clamp bounds
    (0.3 / 3.0). Move only those, simulating the unclamped truth."""
    factors = get_data().center_wait_times.get("center_wait_time_factors", {})
    saved = {}
    for code, per_organ in factors.items():
        v = per_organ.get(organ)
        if isinstance(v, (int, float)) and (v <= 0.3 or v >= 3.0):
            saved[(code, organ)] = v
            per_organ[organ] = v * f
    def restore():
        for (code, o), v in saved.items():
            factors[code][o] = v
    restore.n_touched = len(saved)
    return restore


def knob_clamped_competing_factors(organ, f):
    """DATA-25: center mortality/delisting factors at clamp bounds."""
    adj = get_data().center_competing_risks.get("center_adjustments", {})
    saved = {}
    for code, per_organ in adj.items():
        rec = per_organ.get(organ)
        if not isinstance(rec, dict):
            continue
        for key in ("mortality_factor", "delisting_factor"):
            v = rec.get(key)
            if isinstance(v, (int, float)) and (v <= 0.3 or v >= 3.0):
                saved[(code, key)] = v
                rec[key] = v * f
    def restore():
        for (code, key), v in saved.items():
            adj[code][organ][key] = v
    restore.n_touched = len(saved)
    return restore


def knob_age_sex_multiplier(organ, f):
    """SURV age/sex wait multiplier (code constants — patched via wrapper)."""
    real = dist_mod._age_sex_multiplier
    def patched(o, age, sex):
        return 1.0 + (real(o, age, sex) - 1.0) * f
    dist_mod._age_sex_multiplier = patched
    def restore():
        dist_mod._age_sex_multiplier = real
    return restore


SIM_KNOBS = [
    ("blood_type_multipliers", "DATA-01", "ABO wait multipliers (deviation ±20%)", knob_bt_multipliers),
    ("clinical_multipliers", "DATA-02/03/04", "cPRA/MELD/LAS wait multipliers (deviation ±20%)", knob_clinical_multipliers),
    ("log_sigma", "SURV-13/DATA-07/#274", "Log-normal sigma (kidney pinned at 1.2 ceiling)", knob_log_sigma),
    ("base_mortality_rate", "SURV-02", "Organ annual waitlist mortality rate", knob_base_mortality),
    ("base_delisting_rate", "SURV-03", "Organ annual delisting rate", knob_base_delisting),
    ("urgency_mortality_multipliers", "DATA-05/GEN-12", "Urgency mortality multipliers (deviation ±20%)", knob_urgency_multipliers),
    ("clamped_wait_factors", "DATA-24", "Center wait factors AT clamp bounds (0.3/3.0)", knob_clamped_wait_factors),
    ("clamped_competing_factors", "DATA-25", "Center mort/delist factors AT clamp bounds", knob_clamped_competing_factors),
    ("age_sex_multiplier", "#48 demographics", "Age/sex wait multiplier (deviation ±20%)", knob_age_sex_multiplier),
]


def sweep_simulation() -> list[dict]:
    rows = []
    for organ in ORGANS:
        base = sim_p12_by_center(organ)
        if len(base) < 8:
            continue
        for knob_id, reg, desc, apply_fn in SIM_KNOBS:
            for f in FACTORS:
                restore = apply_fn(organ, f)
                try:
                    pert = sim_p12_by_center(organ)
                finally:
                    n_touched = getattr(restore, "n_touched", None)
                    restore()
                row = {"engine": "simulation", "knob": knob_id, "register": reg,
                       "description": desc, "organ": organ, "factor": f,
                       **compare(base, pert)}
                if n_touched is not None:
                    row["n_values_touched"] = n_touched
                rows.append(row)
        print(f"  simulation sweep: {organ} done ({len(base)} centers)")
    return rows


def sweep_scoring() -> list[dict]:
    rows = []
    for organ in ORGANS:
        base = score_by_center(organ)
        if len(base) < 8:
            continue
        for cat in DEFAULT_WEIGHTS:
            for f in FACTORS:
                w = dict(DEFAULT_WEIGHTS)
                w[cat] = w[cat] * f
                pert = score_by_center(organ, weights=w)
                rows.append({"engine": "scoring", "knob": f"weight:{cat}",
                             "register": "SCORE-01", "organ": organ, "factor": f,
                             "description": f"Category weight '{cat}' ±20% (renormalized)",
                             **compare(base, pert)})
        print(f"  scoring sweep: {organ} done ({len(base)} centers)")
    return rows


def main():
    load_all()
    print("Simulation-core sweep ...")
    sim_rows = sweep_simulation()
    print("Scoring-weight sweep ...")
    score_rows = sweep_scoring()
    rows = sim_rows + score_rows

    # Per-knob worst case across organs/directions (the register-facing number)
    knobs = {}
    for r in rows:
        k = (r["engine"], r["knob"])
        if r["rank_rho"] is None:
            continue
        cur = knobs.setdefault(k, {"engine": r["engine"], "knob": r["knob"],
                                   "register": r["register"],
                                   "description": r["description"],
                                   "min_rank_rho": 1.0, "max_mean_abs_delta": 0.0,
                                   "max_max_abs_delta": 0.0})
        cur["min_rank_rho"] = min(cur["min_rank_rho"], r["rank_rho"])
        cur["max_mean_abs_delta"] = max(cur["max_mean_abs_delta"], r["mean_abs_delta"])
        cur["max_max_abs_delta"] = max(cur["max_max_abs_delta"], r["max_abs_delta"])
    knob_summary = sorted(knobs.values(), key=lambda x: x["min_rank_rho"])

    result = {
        "_meta": {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "script": "scripts/run-assumption-sweep.py",
            "method": ("Each hand-set assumption perturbed ±20% (multiplier tables: "
                       "deviation from 1; rates/sigmas/clamped values: scaled). "
                       "Rank stability = Spearman rho of per-center ordering vs "
                       "baseline; deltas are absolute p12 (simulation) or 0-100 "
                       "score (scoring) shifts. Reference patients as in "
                       "run-center-calibration.py."),
            "rank_stability_gate": 0.9,
        },
        "knob_summary": knob_summary,
        "rows": rows,
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(result, indent=1))
    print(f"Wrote {JSON_OUT} ({len(rows)} rows)")
    _write_report(result)
    print(f"Wrote {REPORT}")


def _write_report(result):
    gate = result["_meta"]["rank_stability_gate"]
    lines = [
        "# Assumption Sensitivity Sweep — #294 (T6 gate)",
        "",
        f"Generated {result['_meta']['generated']} by `scripts/run-assumption-sweep.py`.",
        "",
        "Every hand-set assumption below was perturbed ±20% and the per-center",
        "results recomputed. **min rank ρ** is the worst Spearman rank stability",
        "across organs and directions (1.0 = center ordering completely unaffected);",
        "**max Δ** columns show how far absolute values move (p12 for the simulation",
        f"engine, 0–100 points for the scoring engine). Gate: rank ρ > {gate}.",
        "",
        "Interpretation: an assumption with rank ρ ≈ 1.0 cannot change which center",
        "looks better — it only shifts absolute levels, which the tool already",
        "presents with uncertainty. Those are demoted to rank-immaterial in the",
        "register (their citations still matter for calibration, not for ranking).",
        "Assumptions failing the gate are the real justification backlog.",
        "",
        "## Knob summary (worst case across organs and ±20% directions)",
        "",
        "| Engine | Assumption | Register | min rank ρ | max mean Δ | max Δ | Gate |",
        "|---|---|---|---|---|---|---|",
    ]
    for k in result["knob_summary"]:
        flag = "✅" if k["min_rank_rho"] >= gate else "❌ FAILS"
        lines.append(
            f"| {k['engine']} | {k['knob']} | {k['register']} | "
            f"{k['min_rank_rho']:.4f} | {k['max_mean_abs_delta']:.4f} | "
            f"{k['max_max_abs_delta']:.4f} | {flag} |"
        )
    fails = [k for k in result["knob_summary"] if k["min_rank_rho"] < gate]
    lines += [
        "",
        "## Verdict",
        "",
        (f"**{len(fails)} assumption(s) fail the rank-stability gate:** "
         + ", ".join(f"`{k['knob']}`" for k in fails)
         if fails else
         "**All swept assumptions pass the rank-stability gate** — at ±20% none of "
         "them changes the center ordering materially. The hand-set magnitudes "
         "affect absolute probabilities (see Δ columns), not which centers rank "
         "highest."),
        "",
        "## Scope and honesty",
        "",
        "- Patient-level multiplier tables (ABO/cPRA/MELD/LAS) are center-invariant",
        "  by construction, so their rank ρ = 1.0 is a structural fact, now proven",
        "  rather than assumed. Their magnitudes still matter for absolute",
        "  probabilities — calibration (see center-calibration/temporal-forecast",
        "  reports) is the check on levels.",
        "- Clamp-bound knobs (DATA-24/25) move only the values sitting AT the parse",
        "  clamps, simulating an unclamped truth 20% beyond the bound.",
        "- Not swept (code-structural, need dedicated experiments): copula θ (#255,",
        "  off in the closed form), SUPPLY_WAIT_ELASTICITY (COD path off for the",
        "  reference patient), BBN CPT internals (#213/#214), spatial/equity-specific",
        "  constants (EQSP-*), acceptance-rate composite (DATA-20/21).",
        "- Full sweep rows (per organ × direction) in",
        "  `docs-site/static/data/assumption-sweep.json`.",
        "",
    ]
    REPORT.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
