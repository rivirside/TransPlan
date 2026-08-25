#!/usr/bin/env python3
"""
Temporal FORECAST validation — the fit-on-N / predict-N+k test (#237, answers #251).

run-temporal-validation.py established (A) observed-rate persistence and
(B) current-model backward concordance, but explicitly could not vary the
model's TRAINING release because per-release wait-time inputs were unparsed.
This script closes that gap:

For every archived release N (data/srtr-archive/, 15 releases 2018-2025):
  1. Parse Table B10 (wait-time percentiles) and Table B7/B6 (waitlist
     outcomes) for ALL centers, era-proof (column scan, not sheet names).
  2. Rebuild the model's center-ranking core from release-N inputs only:
       - per-center wait median = national median x clamp(p50_c/p50_nat, .3, 3)
         (exactly parse-srtr-reports.py's factor derivation)
       - sigma from the release's national percentiles (same fit + clamp)
       - per-center competing risks scaled by the release's death/delist ratios
       - predicted p12 = closed-form competing-risks integral (same formula as
         services/brier_score.py / equity #216)
     Patient-level multipliers (blood type, cPRA, ...) are center-invariant and
     cancel in cross-center RANKING, so this reduced core produces the same
     ordering as the full engine for a reference patient.
  3. Score Spearman rho of that prediction against the OBSERVED 1-yr transplant
     rate at every LATER release N+k (data/srtr-observed-rates-historical.json,
     cohorts n >= 10), i.e. a genuine forward, cross-field forecast.
  4. Report next to the persistence ceiling (obs_N vs obs_N+k) computed on the
     SAME center subset, so model-vs-ceiling is apples to apples.

Outputs:
  - docs-site/static/data/temporal-forecast.json
  - docs/temporal-forecast-report.md

Usage:
    cd TransPlan && .venv/bin/python scripts/run-temporal-forecast.py
"""
import io
import json
import math
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xlrd
from scipy import stats

REPO_ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = REPO_ROOT / "data" / "srtr-archive"
HIST_PATH = REPO_ROOT / "data" / "srtr-observed-rates-historical.json"
JSON_OUT = REPO_ROOT / "docs-site" / "static" / "data" / "temporal-forecast.json"
REPORT = REPO_ROOT / "docs" / "temporal-forecast-report.md"

ORGANS = {"kidney": "KI", "liver": "LI", "heart": "HR",
          "lung": "LU", "pancreas": "PA", "intestine": "IN"}
MIN_N = 10        # cohort floor for ground-truth rates (matches run-temporal-validation)
MIN_PAIRS = 8     # minimum common centers for a meaningful correlation
CENSORED = -999.0

# Column names are stable across eras; only SHEET names changed (B9->B10,
# B6->B7 at release 2111), so we scan sheets for the columns.
B10_CTR = {"p10": "TTT_10_C", "p25": "TTT_25_C", "p50": "TTT_50_C", "p75": "TTT_75_C"}
B10_NAT = {"p10": "TTT_10_U", "p25": "TTT_25_U", "p50": "TTT_50_U", "p75": "TTT_75_U"}
B7_CTR = {"died": "SAL_WLDIED_C12", "tx": "SAL_TOTTX_C12", "worse": "SAL_REMDET_C12",
          "n": "SAL_N_C"}
B7_NAT = {"died": "SAL_WLDIED_U12", "worse": "SAL_REMDET_U12"}

# Reference competing-risk base rates (annual), constant across releases and
# centers-invariant in level — only the per-release center RATIOS matter for
# ranking. Values mirror competing-risks.json organ baselines in spirit; the
# rank result is insensitive to the absolute level.
BASE_MORT = {"kidney": 0.06, "liver": 0.12, "heart": 0.12, "lung": 0.15,
             "pancreas": 0.05, "intestine": 0.10}
BASE_DELIST = {"kidney": 0.04, "liver": 0.06, "heart": 0.05, "lung": 0.06,
               "pancreas": 0.04, "intestine": 0.06}


# ---------- Excel helpers (mirroring parse-srtr-reports.py, era-proof) ----------

def _safe_float(val):
    if isinstance(val, (int, float)):
        return float(val) if val != "" else None
    s = str(val).strip()
    if not s:
        return None
    if s.startswith(">"):
        return CENSORED
    try:
        return float(s)
    except ValueError:
        return None


def _is_valid(v):
    return v is not None and v != CENSORED and v > 0


def _find_sheet_with(wb, required_col: str):
    """Return (sheet, header list) for the first sheet whose row 0 has required_col."""
    for name in wb.sheet_names():
        sh = wb.sheet_by_name(name)
        if sh.nrows < 3 or sh.ncols < 2:
            continue
        hdr = [str(sh.cell_value(0, c)).strip() for c in range(sh.ncols)]
        if required_col in hdr:
            return sh, hdr
    return None, None


def _col(hdr, name):
    try:
        return hdr.index(name)
    except ValueError:
        return -1


def _is_center_code(v) -> bool:
    s = str(v).strip()
    return bool(re.fullmatch(r"[A-Z0-9]{3,5}", s)) and s != "CTR_CD"


def _all_rows(sheet, hdr, cols: dict) -> dict:
    """{center_code: {key: value}} for every center row."""
    ctr = _col(hdr, "CTR_CD")
    if ctr < 0:
        return {}
    idx = {k: _col(hdr, c) for k, c in cols.items()}
    out = {}
    for r in range(1, sheet.nrows):
        code = str(sheet.cell_value(r, ctr)).strip()
        if not _is_center_code(code):
            continue
        out[code] = {k: (_safe_float(sheet.cell_value(r, i)) if i >= 0 else None)
                     for k, i in idx.items()}
    return out


def _national_row(sheet, hdr, cols: dict) -> dict:
    idx = {k: _col(hdr, c) for k, c in cols.items()}
    for r in range(1, min(sheet.nrows, 6)):
        vals = {k: (_safe_float(sheet.cell_value(r, i)) if i >= 0 else None)
                for k, i in idx.items()}
        if any(v is not None for v in vals.values()):
            return vals
    return {}


def fit_sigma(p10, p25, p50, p75) -> float:
    """National sigma from percentiles — same strategy + clamps as
    parse-srtr-reports.py fit_lognormal."""
    if _is_valid(p10) and _is_valid(p25) and p25 > p10:
        sigma = (math.log(p25) - math.log(p10)) / (1.2816 - 0.6745)
    elif _is_valid(p25) and _is_valid(p75) and p75 > p25:
        sigma = (math.log(p75) - math.log(p25)) / (2 * 0.6745)
    elif _is_valid(p10) and _is_valid(p50) and p50 > p10:
        sigma = (math.log(p50) - math.log(p10)) / 1.2816
    else:
        sigma = 0.8
    return max(0.3, min(sigma, 1.2))


def wait_factor(ctr: dict, nat: dict):
    """Center wait factor — same derivation + clamps as parse-srtr-reports.py."""
    p50_c, p25_c = ctr.get("p50"), ctr.get("p25")
    p50_n, p25_n = nat.get("p50"), nat.get("p25")
    if _is_valid(p50_c) and _is_valid(p50_n):
        return max(0.3, min(p50_c / p50_n, 3.0))
    if _is_valid(p25_c) and _is_valid(p25_n):
        return max(0.3, min(p25_c / p25_n, 3.0))
    if p50_c == CENSORED and _is_valid(p50_n):
        return 2.5
    return None


# ---------- The model core, fit on one release ----------

_GRID = np.linspace(0.0, 12.0, 121)


def predict_p12(median_months: float, sigma: float, annual_mort: float,
                annual_delist: float) -> float:
    """Closed-form P(transplant first AND within 12mo) — the same integral as
    services/brier_score.py / equity (#216): lognormal transplant pdf x
    exponential survival of the two competing risks."""
    dist = stats.lognorm(s=sigma, scale=median_months)
    lam = (annual_mort + annual_delist) / 12.0
    integrand = dist.pdf(_GRID) * np.exp(-lam * _GRID)
    trapz = getattr(np, "trapezoid", None) or np.trapz
    return float(np.clip(trapz(integrand, _GRID), 0.0, 1.0))


def fit_release(zip_path: Path) -> dict:
    """Parse one release zip -> {organ: {center: predicted_p12}} plus coverage."""
    zf = zipfile.ZipFile(zip_path)
    members = {}
    for name in zf.namelist():
        m = re.search(r"_(KI|LI|HR|LU|PA|IN)\.xls$", name, re.I)
        if m and not name.endswith("/"):
            members[m.group(1).upper()] = name

    out = {}
    for organ, oc in ORGANS.items():
        if oc not in members:
            continue
        wb = xlrd.open_workbook(file_contents=zf.read(members[oc]))

        b10, hdr10 = _find_sheet_with(wb, "TTT_50_C")
        b7, hdr7 = _find_sheet_with(wb, "SAL_TOTTX_C12")
        if b10 is None or b7 is None:
            continue

        nat10 = _national_row(b10, hdr10, B10_NAT)
        nat_median = nat10.get("p50")
        if not _is_valid(nat_median):
            continue
        sigma = fit_sigma(nat10.get("p10"), nat10.get("p25"),
                          nat10.get("p50"), nat10.get("p75"))

        ctr10 = _all_rows(b10, hdr10, B10_CTR)
        ctr7 = _all_rows(b7, hdr7, B7_CTR)
        nat7 = _national_row(b7, hdr7, B7_NAT)
        nat_died = nat7.get("died")
        nat_worse = nat7.get("worse")

        preds = {}
        for code, wt in ctr10.items():
            factor = wait_factor(wt, nat10)
            if factor is None:
                continue
            # Competing-risk ratios from the release's B7 (center vs national,
            # same clamp range as the parser's factor outputs)
            cr = ctr7.get(code, {})
            mort_ratio = 1.0
            delist_ratio = 1.0
            if cr.get("died") is not None and nat_died:
                mort_ratio = max(0.3, min(cr["died"] / nat_died, 3.0))
            if cr.get("worse") is not None and nat_worse:
                delist_ratio = max(0.3, min(cr["worse"] / nat_worse, 3.0))

            preds[code] = predict_p12(
                median_months=nat_median * factor,
                sigma=sigma,
                annual_mort=BASE_MORT[organ] * mort_ratio,
                annual_delist=BASE_DELIST[organ] * delist_ratio,
            )
        if preds:
            out[organ] = preds
    return out


# ---------- Scoring ----------

def _spearman(x, y):
    if len(x) < MIN_PAIRS:
        return None, len(x)
    rho = float(np.asarray(stats.spearmanr(x, y)[0]))
    return (None if np.isnan(rho) else round(rho, 4)), len(x)


def _obs_rates(hist, rel: str, organ: str) -> dict:
    block = hist["releases"].get(rel, {}).get("organs", {}).get(organ, {})
    out = {}
    for code, rec in block.get("centers", {}).items():
        if rec.get("transplant_rate") is not None and (rec.get("n") or 0) >= MIN_N:
            out[code] = rec["transplant_rate"]
    return out


def _lag_months(a: str, b: str) -> int:
    return (int(b[:2]) - int(a[:2])) * 12 + (int(b[2:]) - int(a[2:]))


def main():
    hist = json.loads(HIST_PATH.read_text())
    zips = sorted(ARCHIVE_DIR.glob("csrs_final_tables_*all.zip"))
    codes = [re.search(r"_(\d{4})all", z.name).group(1) for z in zips]
    print(f"Releases in archive: {codes}")

    predictions = {}
    for z, code in zip(zips, codes):
        print(f"  fitting {code} ...")
        predictions[code] = fit_release(z)

    rows = []  # one row per (organ, train, test)
    for i, train in enumerate(codes):
        for test in codes[i + 1:]:
            lag = _lag_months(train, test)
            for organ in ORGANS:
                preds = predictions.get(train, {}).get(organ)
                obs_test = _obs_rates(hist, test, organ)
                obs_train = _obs_rates(hist, train, organ)
                if not preds or not obs_test:
                    continue
                common = sorted(set(preds) & set(obs_test))
                rho_model, n = _spearman([preds[c] for c in common],
                                         [obs_test[c] for c in common])
                # Persistence ceiling on the SAME subset that also has obs_train
                common_p = sorted(set(common) & set(obs_train))
                rho_persist, n_p = _spearman([obs_train[c] for c in common_p],
                                             [obs_test[c] for c in common_p])
                if rho_model is None:
                    continue
                rows.append({
                    "organ": organ, "train": train, "test": test,
                    "lag_months": lag, "n_centers": n,
                    "rho_forecast": rho_model,
                    "rho_persistence": rho_persist, "n_persistence": n_p,
                })

    # Aggregate: per organ x lag bucket
    buckets = [(6, "6mo"), (12, "12mo"), (24, "24mo"), (48, "36-48mo"), (999, ">48mo")]

    def bucket(lag):
        for hi, label in buckets:
            if lag <= hi:
                return label
        return ">48mo"

    summary = {}
    for organ in ORGANS:
        summary[organ] = {}
        for _, label in buckets:
            sel = [r for r in rows if r["organ"] == organ and bucket(r["lag_months"]) == label]
            if not sel:
                continue
            summary[organ][label] = {
                "median_rho_forecast": round(float(np.median([r["rho_forecast"] for r in sel])), 3),
                "median_rho_persistence": round(float(np.median(
                    [r["rho_persistence"] for r in sel if r["rho_persistence"] is not None])), 3)
                    if any(r["rho_persistence"] is not None for r in sel) else None,
                "n_pairs": len(sel),
                "median_centers": int(np.median([r["n_centers"] for r in sel])),
            }

    # Headline: earliest usable train release -> latest test
    headline = {}
    for organ in ORGANS:
        organ_rows = [r for r in rows if r["organ"] == organ and r["test"] == codes[-1]]
        if organ_rows:
            first = min(organ_rows, key=lambda r: r["train"])
            headline[organ] = first

    result = {
        "_meta": {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "script": "scripts/run-temporal-forecast.py",
            "method": (
                "Model ranking core re-fit from each archived release's Table B10 "
                "wait-time percentiles + Table B7/B6 competing-risk rates; predicted "
                "closed-form p12 ranked against later releases' observed 1-yr "
                "transplant rates (n>=10). rho_persistence = observed-rate "
                "autocorrelation on the same center subset (the ceiling)."
            ),
            "releases": codes,
            "min_cohort_n": MIN_N,
        },
        "summary": summary,
        "headline_earliest_to_latest": headline,
        "pairs": rows,
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(result, indent=1))
    print(f"Wrote {JSON_OUT} ({len(rows)} (organ, train, test) rows)")

    _write_report(result)
    print(f"Wrote {REPORT}")


def _write_report(result):
    lines = [
        "# Temporal Forecast Validation (fit-on-N / predict-N+k) — #237",
        "",
        f"Generated {result['_meta']['generated']} by `scripts/run-temporal-forecast.py`.",
        "",
        "**What this is.** The genuinely out-of-sample forecast test: the model's",
        "center-ranking core is re-fit from each archived SRTR release's inputs",
        "(Table B10 wait-time percentiles, Table B7/B6 competing-risk rates) and its",
        "predicted per-center p12 ranking is scored against the observed 1-yr",
        "transplant rates of every LATER release. The training release never saw the",
        "test release. This completes the follow-up left open by",
        "`docs/temporal-validation-report.md` and addresses #251's core critique.",
        "",
        "**Reading the numbers.** `rho_forecast` is the model's forward Spearman;",
        "`rho_persistence` is the observed-rate autocorrelation on the same centers —",
        "the practical ceiling (no wait-time-based model can beat simply knowing the",
        "outcome variable's own past). A forecast near the ceiling means the model's",
        "inputs (wait times + competing risks) carry most of the persistent signal;",
        "the gap is what better inputs could still recover.",
        "",
        "## Median Spearman ρ by organ × forecast horizon",
        "",
        "| Organ | Horizon | ρ forecast | ρ persistence (ceiling) | pairs | median centers |",
        "|---|---|---|---|---|---|",
    ]
    for organ, blocks in result["summary"].items():
        for label, s in blocks.items():
            lines.append(
                f"| {organ} | {label} | {s['median_rho_forecast']} | "
                f"{s['median_rho_persistence']} | {s['n_pairs']} | {s['median_centers']} |"
            )
    lines += [
        "",
        "## Headline: earliest release → latest release",
        "",
        "| Organ | Train | Test | Lag (months) | ρ forecast | ρ persistence | centers |",
        "|---|---|---|---|---|---|---|",
    ]
    for organ, r in result["headline_earliest_to_latest"].items():
        lines.append(
            f"| {organ} | {r['train']} | {r['test']} | {r['lag_months']} | "
            f"{r['rho_forecast']} | {r['rho_persistence']} | {r['n_centers']} |"
        )
    missing = [o for o in ORGANS if not result["summary"].get(o)]
    if missing:
        lines += [
            "",
            f"**Not covered:** {', '.join(missing)} — fewer than {MIN_PAIRS} centers "
            f"with cohort n ≥ {MIN_N} in overlapping releases, so no correlation is "
            "reportable. This is an explicit data-sparsity exclusion, not an omission.",
        ]
    lines += [
        "",
        "## Honest scope",
        "",
        "- The reduced core (wait factor + competing-risk ratios → closed-form p12)",
        "  produces the same cross-center ranking as the full MC engine for a",
        "  reference patient: patient-level multipliers are center-invariant.",
        "  Acceptance-rate thinning and score drift are excluded (as in the",
        "  calibration harness).",
        "- Ground truth is the SRTR observed 1-yr transplant rate over each center's",
        "  real case mix; predictions are reference-patient probabilities — hence",
        "  rank correlation, not calibration, is the metric.",
        "- Cohorts with n<10 are excluded from ground truth. Centers must appear in",
        "  both train inputs and test outcomes.",
        "- Prediction inputs (B10/B7) and ground-truth outcomes (B7 transplant rate)",
        "  come from the same instrument in different years; the transplant-rate",
        "  column itself is never used as a prediction input.",
        "",
        "See also: `docs/temporal-validation-report.md` (persistence + backward",
        "concordance), `docs/center-calibration-report.md` (within-release",
        "calibration).",
        "",
    ]
    REPORT.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
