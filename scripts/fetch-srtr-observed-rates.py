#!/usr/bin/env python3
"""
Fetch observed SRTR center-level outcome RATES — ground truth for calibration
and temporal validation.

The main SRTR pipeline (parse-srtr-reports.py) reads Table B7 but converts the
1-year transplant rate (SAL_TOTTX_C12) into a volume count and discards the
rate itself. That rate is exactly the ground truth needed to validate the
model's center-level predictions, so this script extracts and persists it.

For each organ × center it stores the observed 12-month:
  - transplant_rate   (SAL_TOTTX_C12)  — % of listed candidates transplanted
  - waitlist_death_rate (SAL_WLDIED_C12)
  - delisting_rate    (sum of SAL_REMDET/REMREC/REFTX_C12 — worsened / improved / refused)
  - n                 (SAL_N_C)        — cohort size (for sparsity weighting)
and the national baselines (…_U12).

DATA SOURCE (verified 2026-06): SRTR migrated to srtr.hrsa.gov.
  - Current release per-organ xls:
      https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables/csrs_final_tables_2511_<ORG>.xls
  - Historical all-organ zip bundles (one per release):
      https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables_all/csrs_final_tables_<CODE>all.zip
  Release codes end in 05/11 (+ early 06); there is NO January release.

SCHEMA ERAS (handled automatically by scanning for the sheet that contains
SAL_TOTTX_C12 rather than hardcoding a sheet name):
  - 2111 → 2511: column lives in a dedicated "Table B7" sheet.
  - 1811 → 2105: no/empty "Table B7"; column lives in "Table B6".
  - 2006 and older: no SAL_* columns at all → transplant_rate unavailable; the
    release is skipped with a logged warning.

Outputs:
  - data/srtr-observed-rates.json             (current release, used by calibration)
  - data/srtr-observed-rates-historical.json  (all releases, keyed by code; for #237)

Usage:
    cd TransPlan && .venv/bin/python scripts/fetch-srtr-observed-rates.py            # current
    cd TransPlan && .venv/bin/python scripts/fetch-srtr-observed-rates.py --historical  # all releases
    cd TransPlan && .venv/bin/python scripts/fetch-srtr-observed-rates.py --organ lung
"""
import argparse
import io
import json
import re
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import xlrd

REPO_ROOT = Path(__file__).parent.parent
OUT_PATH = REPO_ROOT / "data" / "srtr-observed-rates.json"
OUT_HIST_PATH = REPO_ROOT / "data" / "srtr-observed-rates-historical.json"

CURRENT_CODE = "2511"
CURRENT_BASE = "https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables"
ARCHIVE_BASE = "https://srtr.hrsa.gov/Archives/PSRdownloads/csrs_tables_all"

# Historical release codes → nominal year. 05/11 (+ 06); no January release.
HISTORICAL = {
    "1811": 2018, "1905": 2019, "1911": 2019, "2006": 2020, "2011": 2020,
    "2105": 2021, "2111": 2021, "2205": 2022, "2211": 2022, "2305": 2023,
    "2311": 2023, "2405": 2024, "2411": 2024, "2505": 2025, "2511": 2025,
}

ORGAN_CODES = {
    "kidney": "KI", "liver": "LI", "heart": "HR",
    "lung": "LU", "pancreas": "PA", "intestine": "IN",
}

# Table B7/B6 variable codes (center = _C12, national = _U12)
TX_C, TX_U = "SAL_TOTTX_C12", "SAL_TOTTX_U12"
DIED_C, DIED_U = "SAL_WLDIED_C12", "SAL_WLDIED_U12"
DELIST_C = ["SAL_REMDET_C12", "SAL_REMREC_C12", "SAL_REFTX_C12"]
DELIST_U = ["SAL_REMDET_U12", "SAL_REMREC_U12", "SAL_REFTX_U12"]
N_C = "SAL_N_C"

_UA = {"User-Agent": "Mozilla/5.0 TransPlan/2.0 (research)"}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def current_xls(organ_code: str) -> bytes:
    return _get(f"{CURRENT_BASE}/csrs_final_tables_{CURRENT_CODE}_{organ_code}.xls")


def release_members(code: str) -> dict[str, bytes]:
    """Download a release's all-organ zip; return {organ_code: xls_bytes}."""
    zbytes = _get(f"{ARCHIVE_BASE}/csrs_final_tables_{code}all.zip")
    zf = zipfile.ZipFile(io.BytesIO(zbytes))
    out = {}
    for name in zf.namelist():
        m = re.search(r"_(KI|LI|HR|LU|PA|IN)\.xls$", name, re.I)  # skip HL/KP combos
        if m and not name.endswith("/"):
            out[m.group(1).upper()] = zf.read(name)
    return out


def _num(sheet, row: int, col: int):
    try:
        return float(sheet.cell_value(row, col))
    except (ValueError, TypeError):
        return None


def _find_outcomes_sheet(wb):
    """Return (sheet, header_codes) for the sheet that carries SAL_TOTTX_C12.

    Era-proof: scans every sheet's first row for the column rather than
    assuming a sheet name (Table B7 in newer releases, Table B6 in older).
    Returns (None, None) if no sheet has it (pre-SAL_* vintages like 2006).
    """
    # Prefer the canonical sheets if present, else scan all.
    ordered = ["Table B7", "Table B6"] + [s for s in wb.sheet_names()
                                          if s not in ("Table B7", "Table B6")]
    for name in ordered:
        if name not in wb.sheet_names():
            continue
        sh = wb.sheet_by_name(name)
        if sh.nrows < 3:
            continue
        hdr = [str(sh.cell_value(0, c)) for c in range(sh.ncols)]
        if TX_C in hdr:
            return sh, hdr
    return None, None


def _is_center_code(v) -> bool:
    s = str(v).strip()
    return bool(re.fullmatch(r"[A-Z0-9]{3,5}", s)) and s != "CTR_CD"


def extract_rates(xls_bytes: bytes) -> dict | None:
    """Extract per-center observed rates (percentages). None if no SAL_TOTTX_C12."""
    wb = xlrd.open_workbook(file_contents=xls_bytes)
    sh, hdr = _find_outcomes_sheet(wb)
    if sh is None:
        return None  # pre-SAL_* schema (e.g. 2006)

    def col(code: str):
        return hdr.index(code) if code in hdr else None

    code_col = col("CTR_CD")
    if code_col is None:
        return None
    tx_c, died_c = col(TX_C), col(DIED_C)
    delist_cols = [col(c) for c in DELIST_C if col(c) is not None]
    n_col = col(N_C)

    centers = {}
    for r in range(1, sh.nrows):
        if not _is_center_code(sh.cell_value(r, code_col)):
            continue  # skips the label row and any footer rows
        ctr = str(sh.cell_value(r, code_col)).strip()
        tx = _num(sh, r, tx_c) if tx_c is not None else None
        if tx is None:
            continue
        delist = sum((_num(sh, r, c) or 0.0) for c in delist_cols)
        centers[ctr] = {
            "transplant_rate": round(tx, 4),
            "waitlist_death_rate": round(_num(sh, r, died_c) or 0.0, 4) if died_c is not None else None,
            "delisting_rate": round(delist, 4),
            "n": int(_num(sh, r, n_col)) if (n_col is not None and _num(sh, r, n_col)) else None,
        }

    # First data row carries the constant _U12 national baselines.
    first = next((r for r in range(1, sh.nrows) if _is_center_code(sh.cell_value(r, code_col))), 2)
    national = {}
    for label, code in [("transplant_rate", TX_U), ("waitlist_death_rate", DIED_U)]:
        ci = col(code)
        if ci is not None:
            national[label] = round(_num(sh, first, ci) or 0.0, 4)
    du = [col(c) for c in DELIST_U if col(c) is not None]
    if du:
        national["delisting_rate"] = round(sum((_num(sh, first, c) or 0.0) for c in du), 4)

    return {"centers": centers, "national": national, "source_sheet": sh.name}


def fetch_one_release(code: str, organs: list[str], from_zip: bool) -> dict:
    """Return {organ: {centers, national, ...}} for one release."""
    members = release_members(code) if from_zip else None
    out = {}
    for organ in organs:
        oc = ORGAN_CODES[organ]
        try:
            xls = members[oc] if from_zip else current_xls(oc)
        except KeyError:
            print(f"    {organ}: not in bundle", file=sys.stderr)
            continue
        except Exception as e:
            print(f"    {organ}: download error {e}", file=sys.stderr)
            continue
        data = extract_rates(xls)
        if data is None:
            print(f"    {organ}: no SAL_TOTTX_C12 (pre-SAL schema) — skipped")
            continue
        out[organ] = data
        print(f"    {organ}: {len(data['centers'])} centers "
              f"(sheet {data['source_sheet']}, national {data['national'].get('transplant_rate')}%)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--organ", choices=list(ORGAN_CODES), help="One organ (default: all)")
    ap.add_argument("--historical", action="store_true",
                    help="Fetch all releases -> srtr-observed-rates-historical.json")
    args = ap.parse_args()
    organs = [args.organ] if args.organ else list(ORGAN_CODES)

    if not args.historical:
        # Current release only (per-organ xls) — preserves the calibration input.
        out = {"_meta": {
            "source": f"SRTR PSR Table B7, release {CURRENT_CODE} (srtr.hrsa.gov)",
            "fields": "12-month observed rates (%): transplant_rate=SAL_TOTTX_C12, "
                      "waitlist_death_rate=SAL_WLDIED_C12, "
                      "delisting_rate=sum(REMDET,REMREC,REFTX)",
            "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }}
        print(f"Current release {CURRENT_CODE}:")
        out.update(fetch_one_release(CURRENT_CODE, organs, from_zip=False))
        OUT_PATH.write_text(json.dumps(out, indent=2))
        print(f"\nWrote {OUT_PATH.relative_to(REPO_ROOT)}")
        return

    # Historical: every release via zip bundles → keyed by release code.
    out = {"_meta": {
        "source": "SRTR PSR Table B7/B6 all-organ zip bundles (srtr.hrsa.gov)",
        "fields": "12-month observed rates (%) per center; see srtr-observed-rates.json",
        "schema_note": "SAL_TOTTX_C12 in 'Table B7' for 2111+, 'Table B6' for "
                       "1811-2105; absent in 2006 and older (those releases skipped).",
        "releases": list(HISTORICAL.keys()),
        "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, "releases": {}}
    for code, year in HISTORICAL.items():
        print(f"Release {code} (year {year}):")
        rel = fetch_one_release(code, organs, from_zip=True)
        if rel:
            out["releases"][code] = {"year": year, "organs": rel}
    OUT_HIST_PATH.write_text(json.dumps(out, indent=2))
    got = sum(len(v["organs"]) for v in out["releases"].values())
    print(f"\nWrote {OUT_HIST_PATH.relative_to(REPO_ROOT)} "
          f"({len(out['releases'])} releases, {got} release×organ tables)")


if __name__ == "__main__":
    main()
