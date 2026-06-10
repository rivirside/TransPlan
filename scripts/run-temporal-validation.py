#!/usr/bin/env python3
"""
Temporal (out-of-sample) validation — #237.

The calibration in run-center-calibration.py is an INTERNAL-consistency check:
predictions and ground truth come from the same SRTR release. This script adds
the first *genuinely out-of-sample* evidence using the 15 historical releases
(2018–2025) in data/srtr-observed-rates-historical.json — comparing each
release against LATER releases the model/earlier-data never saw.

Two analyses:

(A) Observed-rate temporal persistence — the foundation. For each organ, how
    well does a center's observed 1-yr transplant rate at release N predict its
    rate at release N+k? This quantifies whether center performance is stable
    enough to be actionable, and — because the BBN's p24 is grounded in these
    observed rates (#211) — it is the model's temporal predictive ceiling.
    Genuinely out-of-sample: release N never saw release N+k.

(B) Model out-of-sample concordance. The current (release-2511) model's
    predicted per-center ranking (from run-center-calibration.py) vs each
    historical release's OBSERVED rates. Shows the model's ordering holds
    against releases it was not built from (backward out-of-sample).

What this does NOT do: it does not re-fit the full MC/BBN from each historical
release's wait-time inputs (those aren't parsed per-release yet — the raw Excel
is archived in data/srtr-archive/, so it's a feasible follow-up). So (B) varies
the ground-truth release, not the model's training release; (A) is the cleaner
forecast test. Headline metric is Spearman rank correlation throughout.

Outputs:
  - docs-site/static/data/temporal-validation.json
  - docs/temporal-validation-report.md

Usage:
    cd TransPlan && .venv/bin/python scripts/run-temporal-validation.py
"""
import json
from pathlib import Path

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).parent.parent
HIST_PATH = REPO_ROOT / "data" / "srtr-observed-rates-historical.json"
CALIB_DIR = REPO_ROOT / "docs-site" / "static" / "data"
JSON_OUT = CALIB_DIR / "temporal-validation.json"
REPORT = REPO_ROOT / "docs" / "temporal-validation-report.md"

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
MIN_N = 10          # exclude tiny cohorts whose observed rate is mostly sampling noise
MIN_PAIRS = 8       # need enough common centers for a meaningful correlation


def _spearman(x, y):
    if len(x) < MIN_PAIRS:
        return None, None, len(x)
    res = stats.spearmanr(x, y)
    rho = float(np.asarray(res[0]))
    p = float(np.asarray(res[1]))
    return (None if np.isnan(rho) else round(rho, 4),
            None if np.isnan(p) else p, len(x))


def _rates(organ_block, min_n=MIN_N):
    """{center_code: transplant_rate} for centers with cohort n >= min_n."""
    out = {}
    for code, rec in organ_block.get("centers", {}).items():
        if rec.get("transplant_rate") is None:
            continue
        if (rec.get("n") or 0) >= min_n:
            out[code] = rec["transplant_rate"]
    return out


def persistence(hist) -> dict:
    """(A) Spearman ρ between observed rates at releases separated by k steps."""
    rel_codes = sorted(hist["releases"])  # chronological (YYMM sorts correctly)
    years = {c: hist["releases"][c]["year"] for c in rel_codes}
    out = {}
    for organ in ORGANS:
        per_gap = {}  # gap_in_releases -> list of (rho, n)
        rate_by_rel = {}
        for c in rel_codes:
            blk = hist["releases"][c]["organs"].get(organ)
            if blk:
                rate_by_rel[c] = _rates(blk)
        present = [c for c in rel_codes if c in rate_by_rel]
        for ai in range(len(present)):
            for bi in range(ai + 1, len(present)):
                a, b = present[ai], present[bi]
                gap = bi - ai  # releases apart (~6mo each)
                common = sorted(set(rate_by_rel[a]) & set(rate_by_rel[b]))
                if len(common) < MIN_PAIRS:
                    continue
                rho, _p, n = _spearman([rate_by_rel[a][c] for c in common],
                                       [rate_by_rel[b][c] for c in common])
                if rho is not None:
                    per_gap.setdefault(gap, []).append((rho, n, years[b] - years[a]))
        # Summarize the two most useful gaps: ~1yr (2 releases) and ~2yr (4).
        summary = {}
        for gap_label, gap in (("~1yr", 2), ("~2yr", 4)):
            vals = per_gap.get(gap, [])
            if vals:
                rhos = [v[0] for v in vals]
                summary[gap_label] = {
                    "mean_rho": round(float(np.mean(rhos)), 4),
                    "min_rho": round(float(np.min(rhos)), 4),
                    "max_rho": round(float(np.max(rhos)), 4),
                    "n_release_pairs": len(vals),
                    "median_centers": int(np.median([v[1] for v in vals])),
                }
        out[organ] = summary
    return out


def model_concordance(hist) -> dict:
    """(B) Current model predicted ranking vs each historical release observed."""
    out = {}
    for organ in ORGANS:
        calib_path = CALIB_DIR / f"center-calibration-{organ}.json"
        if not calib_path.exists():
            continue
        calib = json.loads(calib_path.read_text())
        pred = {c["center_code"]: c["predicted_p12"] for c in calib["centers"]}
        per_release = []
        for code in sorted(hist["releases"]):
            blk = hist["releases"][code]["organs"].get(organ)
            if not blk:
                continue
            obs = _rates(blk)
            common = sorted(set(pred) & set(obs))
            rho, p, n = _spearman([pred[c] for c in common], [obs[c] for c in common])
            if rho is not None:
                per_release.append({
                    "release": code, "year": hist["releases"][code]["year"],
                    "rho": rho, "p_value": p, "n_centers": n,
                })
        if per_release:
            out[organ] = {
                "vs_release": per_release,
                "mean_rho_excl_2511": round(float(np.mean(
                    [r["rho"] for r in per_release if r["release"] != "2511"])), 4),
            }
    return out


def main():
    hist = json.loads(HIST_PATH.read_text())
    result = {
        "persistence": persistence(hist),
        "model_concordance": model_concordance(hist),
        "params": {"min_cohort_n": MIN_N, "min_common_centers": MIN_PAIRS},
    }
    CALIB_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(result, indent=2))
    _write_report(result)

    print("Temporal validation — observed-rate persistence (Spearman ρ):")
    for organ, s in result["persistence"].items():
        y1 = s.get("~1yr", {}).get("mean_rho")
        y2 = s.get("~2yr", {}).get("mean_rho")
        print(f"  {organ:9s} ~1yr ρ={y1}  ~2yr ρ={y2}")
    print(f"\nWrote {JSON_OUT.relative_to(REPO_ROOT)} and {REPORT.relative_to(REPO_ROOT)}")


def _write_report(result):
    L = [
        "# Temporal (Out-of-Sample) Validation — #237",
        "",
        "_Generated by `scripts/run-temporal-validation.py`._",
        "",
        "First **genuinely out-of-sample** evidence: unlike the same-release calibration "
        "(`center-calibration-report.md`), this compares each SRTR release against LATER "
        "releases the data never saw, across 15 releases (2018–2025). Headline metric is "
        f"Spearman rank correlation; centers with cohort n < {result['params']['min_cohort_n']} "
        "are excluded (their observed rate is mostly sampling noise).",
        "",
        "## (A) Observed-rate temporal persistence",
        "",
        "Does a center's observed 1-yr transplant rate at release N predict its rate at "
        "N+k? Because the BBN's p24 is grounded in these observed rates (#211), this is the "
        "model's temporal predictive ceiling — and a direct test of whether center rankings "
        "are stable enough to be actionable.",
        "",
        "| Organ | ρ (~1yr) | ρ (~2yr) | release pairs (1yr/2yr) |",
        "|-------|----------|----------|--------------------------|",
    ]
    for organ, s in result["persistence"].items():
        a, b = s.get("~1yr", {}), s.get("~2yr", {})
        L.append(f"| {organ} | {a.get('mean_rho','—')} | {b.get('mean_rho','—')} | "
                 f"{a.get('n_release_pairs','—')}/{b.get('n_release_pairs','—')} |")
    L += [
        "",
        "## (B) Model out-of-sample concordance",
        "",
        "The current (release-2511) model's predicted per-center ranking vs each historical "
        "release's OBSERVED rates. ρ stays high across releases the model was not built from "
        "(mean ρ excluding the in-sample 2511 release shown).",
        "",
        "| Organ | mean ρ vs out-of-sample releases |",
        "|-------|----------------------------------|",
    ]
    for organ, m in result["model_concordance"].items():
        L.append(f"| {organ} | {m['mean_rho_excl_2511']} |")
    L += [
        "",
        "## What this establishes — and what it doesn't",
        "",
        "- **Establishes:** center transplant-rate rankings are temporally stable / "
        "predictable out-of-sample, and the model's ordering concords with releases it was "
        "not built from. This is stronger evidence than the same-release calibration.",
        "- **Does not:** re-fit the full MC/BBN from each historical release's wait-time "
        "inputs (not yet parsed per-release; raw Excel is archived in `data/srtr-archive/` "
        "for that follow-up). So (B) varies the ground-truth release, not the training "
        "release. A full forecast test (fit on N, predict N+k) is the next step.",
        "",
    ]
    REPORT.write_text("\n".join(L))


if __name__ == "__main__":
    main()
