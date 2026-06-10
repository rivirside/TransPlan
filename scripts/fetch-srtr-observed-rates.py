#!/usr/bin/env python3
"""
Fetch observed SRTR center-level outcome RATES — ground truth for calibration.

The main SRTR pipeline (parse-srtr-reports.py) reads Table B7 but converts the
1-year transplant rate (SAL_TOTTX_C12) into a volume count and discards the
rate itself. That rate is exactly the ground truth needed to validate the
model's center-level predictions, so this script extracts and persists it.

For each organ × center it stores the observed 12-month:
  - transplant_rate   (SAL_TOTTX_C12)  — % of listed candidates transplanted
  - waitlist_death_rate (SAL_WLDIED_C12)
  - delisting_rate    (sum of SAL_REMDET/REMREC/REFTX_C12 — too sick / improved / refused)
  - n                 (SAL_N_C)        — cohort size (for sparsity weighting)
and the national baselines (…_U12).

Source: SRTR PSR National Center-Level Summary Data.
NOTE: SRTR migrated from srtr.org to srtr.hrsa.gov; the file path is now
  https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables/csrs_final_tables_{REL}_{ORG}.xls
This differs from the (now-stale) URL in fetch-srtr-excel.py — see issue tracker.

Output: data/srtr-observed-rates.json

Usage:
    cd TransPlan && .venv/bin/python scripts/fetch-srtr-observed-rates.py
    cd TransPlan && .venv/bin/python scripts/fetch-srtr-observed-rates.py --organ lung
"""
import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import xlrd

REPO_ROOT = Path(__file__).parent.parent
OUT_PATH = REPO_ROOT / "data" / "srtr-observed-rates.json"

# January 2025 release — matches the prefix the model data was parameterized from
# (data/*-centers.json _meta says "January 2025 release"), so observed rates and
# model parameters come from the same cohort (no temporal mismatch).
RELEASE_PREFIX = "2511"
BASE_URL = "https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables"

ORGAN_CODES = {
    "kidney": "KI", "liver": "LI", "heart": "HR",
    "lung": "LU", "pancreas": "PA", "intestine": "IN",
}

# Table B7 variable codes (center = _C12, national = _U12)
TX_C, TX_U = "SAL_TOTTX_C12", "SAL_TOTTX_U12"
DIED_C, DIED_U = "SAL_WLDIED_C12", "SAL_WLDIED_U12"
DELIST_C = ["SAL_REMDET_C12", "SAL_REMREC_C12", "SAL_REFTX_C12"]
DELIST_U = ["SAL_REMDET_U12", "SAL_REMREC_U12", "SAL_REFTX_U12"]
N_C = "SAL_N_C"


def download_xls(organ_code: str) -> bytes:
    url = f"{BASE_URL}/csrs_final_tables_{RELEASE_PREFIX}_{organ_code}.xls"
    req = urllib.request.Request(url, headers={"User-Agent": "TransPlan/2.0 (research)"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _num(sheet, row: int, col: int):
    v = sheet.cell_value(row, col)
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def extract_rates(xls_bytes: bytes) -> dict:
    """Extract per-center observed rates from Table B7. Rates are percentages."""
    wb = xlrd.open_workbook(file_contents=xls_bytes)
    sh = wb.sheet_by_name("Table B7")
    hdr = [str(sh.cell_value(0, c)) for c in range(sh.ncols)]

    def col(code: str) -> int | None:
        return hdr.index(code) if code in hdr else None

    code_col = col("CTR_CD")
    tx_c, died_c = col(TX_C), col(DIED_C)
    delist_cols = [col(c) for c in DELIST_C if col(c) is not None]
    n_col = col(N_C)

    centers = {}
    for r in range(2, sh.nrows):  # rows 0-1 are headers
        ctr = str(sh.cell_value(r, code_col)).strip()
        if not ctr:
            continue
        tx = _num(sh, r, tx_c) if tx_c is not None else None
        if tx is None:
            continue  # no transplant rate → unusable as ground truth
        delist = sum((_num(sh, r, c) or 0.0) for c in delist_cols)
        centers[ctr] = {
            "transplant_rate": round(tx, 4),
            "waitlist_death_rate": round(_num(sh, r, died_c) or 0.0, 4) if died_c is not None else None,
            "delisting_rate": round(delist, 4),
            "n": int(_num(sh, r, n_col)) if (n_col is not None and _num(sh, r, n_col)) else None,
        }

    # National baselines (first data row carries the _U12 values, constant per file)
    national = {}
    for label, code in [("transplant_rate", TX_U), ("waitlist_death_rate", DIED_U)]:
        ci = col(code)
        if ci is not None:
            national[label] = round(_num(sh, 2, ci) or 0.0, 4)
    du = [col(c) for c in DELIST_U if col(c) is not None]
    if du:
        national["delisting_rate"] = round(sum((_num(sh, 2, c) or 0.0) for c in du), 4)

    return {"centers": centers, "national": national}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--organ", choices=list(ORGAN_CODES), help="Fetch one organ (default: all)")
    args = ap.parse_args()

    organs = [args.organ] if args.organ else list(ORGAN_CODES)
    out = {
        "_meta": {
            "source": f"SRTR PSR Table B7, release {RELEASE_PREFIX} (srtr.hrsa.gov)",
            "fields": "12-month observed rates (%): transplant_rate=SAL_TOTTX_C12, "
                      "waitlist_death_rate=SAL_WLDIED_C12, delisting_rate=sum(REMDET,REMREC,REFTX)",
            "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    }
    for organ in organs:
        print(f"Fetching {organ} ({ORGAN_CODES[organ]})...", flush=True)
        try:
            data = extract_rates(download_xls(ORGAN_CODES[organ]))
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            continue
        out[organ] = data
        print(f"  {len(data['centers'])} centers, national tx rate {data['national'].get('transplant_rate')}%")

    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
