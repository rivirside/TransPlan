#!/usr/bin/env python3
"""Extract SRTR's official 5-tier center ratings from the PSR 'Tiers' sheet.

These are the patient-facing ratings SRTR itself publishes (1-5, 5 best):
graft survival (adult/pediatric, deceased/living), 'getting a deceased donor
transplant faster', and 'survival on the waitlist'. They are external,
recognizable reference points — and the pediatric tiers are a first
per-center pediatric data source for #335 phase 2.

Writes data/srtr-tiers-centers.json:
  {organ: {code: {adult_graft_survival, adult_transplant_faster,
                  adult_waitlist_survival, pediatric_graft_survival,
                  pediatric_transplant_faster, pediatric_waitlist_survival}}}
"""
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import xlrd

REPO = Path(__file__).parent.parent
RAW = REPO / "data" / "srtr-raw"
OUT = REPO / "data" / "srtr-tiers-centers.json"

_sx_spec = importlib.util.spec_from_file_location(
    "srtr_xls_utils", REPO / "scripts" / "srtr_xls_utils.py")
sx = importlib.util.module_from_spec(_sx_spec)
_sx_spec.loader.exec_module(sx)

ORGAN_CODES = {"kidney": "KI", "liver": "LI", "heart": "HR", "lung": "LU",
               "pancreas": "PA", "intestine": "IN"}

FIELDS = {
    "adult_graft_survival": "GSR_AD_RATING_C1Y",
    "adult_transplant_faster": "TMR_AD_CADTXRTIER_C",
    "adult_waitlist_survival": "TMR_AD_DTHRTIER_C",
    "pediatric_graft_survival": "GSR_P0_RATING_C1Y",
    "pediatric_transplant_faster": "TMR_P0_CADTXRTIER_C",
    "pediatric_waitlist_survival": "TMR_P0_DTHRTIER_C",
}


def extract(path: Path) -> dict:
    wb = xlrd.open_workbook(str(path))
    sheet, hdr = sx.find_sheet_with(wb, "GSR_AD_RATING_C1Y", preferred=("Tiers",))
    if sheet is None:
        return {}
    ctr = sx.col_index(hdr, "CTR_CD")
    cols = {k: sx.col_index(hdr, c) for k, c in FIELDS.items()}
    out = {}
    for r in range(1, sheet.nrows):
        code = str(sheet.cell_value(r, ctr)).strip()
        if not sx.is_center_code(code):
            continue
        rec = {}
        for k, c in cols.items():
            if c < 0:
                continue
            v = sx.safe_float(sheet.cell_value(r, c))
            if v is not None and v != sx.CENSORED and 1 <= v <= 5:
                rec[k] = int(v)
        if rec:
            out[code] = rec
    return out


def main():
    result = {"_meta": {
        "source": "SRTR PSR 'Tiers' sheet, release 2511",
        "method": "SRTR's official 5-tier ratings (1-5, 5 best): 1-year graft "
                  "survival, deceased-donor transplant rate ('faster'), and "
                  "waitlist survival — adult and pediatric. External published "
                  "ratings, not TransPlan-derived. Pediatric tiers are the "
                  "first per-center pediatric source (#335 phase 2).",
        "scale_note": "1 = worse than expected ... 5 = better than expected, "
                      "per SRTR's Bayesian tier assignment",
        "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }}
    total = 0
    for organ, code in ORGAN_CODES.items():
        path = RAW / f"csrs_final_tables_2511_{code}.xls"
        if not path.exists():
            continue
        block = extract(path)
        if block:
            result[organ] = block
            total += len(block)
            n_peds = sum(1 for r in block.values()
                         if any(k.startswith("pediatric") for k in r))
            print(f"  {organ}: {len(block)} centers ({n_peds} with pediatric tiers)")

    if OUT.exists():
        old = json.loads(OUT.read_text())
        old_total = sum(len(old.get(o, {})) for o in ORGAN_CODES)
        if total < 0.9 * old_total:
            print(f"REFUSING to shrink: {total} < 90% of {old_total}")
            return 1
    OUT.write_text(json.dumps(result, indent=1))
    print(f"Wrote {OUT} ({total} center-organ tier records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
