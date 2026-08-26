#!/usr/bin/env python3
"""Parse SRTR pediatric per-center tables (#335 phase 2).

The PSR workbooks carry a full pediatric split that nothing has ever read:

  Tbls B4-B5 & Fig B1-B6 - Peds   TMR_p0_CadTxR_c   observed deceased-donor
                                                    transplant rate
                                  TMR_p0_CadTxER_c  expected rate
                                  TMR_p0_CadTxRatio_c  O/E ratio
                                  TMR_p0_DthR_c     waitlist death rate
                                  TMR_p0_TxN_c      waitlist size
  Table B6 & Fig B7-B9            sfl_p0_hr_c       waitlist-mortality HR
                                  sfl_p0_hr_lb_c/_ub_c   95% credible bounds
  TablesC5-C12 …                  GSR_P0_ACT_C1Y    1-yr graft survival
  TablesC11-C20 …                 PSR_P0_ACT_C1Y    1-yr patient survival

Three parsing hazards, all handled below:
  1. The Peds sheet's key column is `center` and holds CTR_CD+CTR_TY
     concatenated ("ALCHTX1") — every OTHER sheet keys on a bare CTR_CD.
  2. Adult and Peds sheets carry the same fields in DIFFERENT column order,
     so everything is indexed by header name, never position.
  3. B4-B5 uses lowercase `_p0_` while Tiers and the C-tables use uppercase
     `_P0_` — matching is case-insensitive.

A center appearing here with a non-null transplant rate is what defines
"has a pediatric program for this organ" downstream; centers absent from
this file are excluded from pediatric results with an explicit reason
rather than silently scored on adult numbers.

Writes data/pediatric-centers.json (never-shrink guarded).
"""
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import xlrd

REPO = Path(__file__).parent.parent
RAW = REPO / "data" / "srtr-raw"
OUT = REPO / "data" / "pediatric-centers.json"

_sx_spec = importlib.util.spec_from_file_location(
    "srtr_xls_utils", REPO / "scripts" / "srtr_xls_utils.py")
sx = importlib.util.module_from_spec(_sx_spec)
_sx_spec.loader.exec_module(sx)

# Minimum pediatric person-years at risk for a center's rate to be usable.
# Below this the rate is dominated by exposure noise (see extract_organ).
MIN_PERSON_YEARS = 1.0

ORGAN_CODES = {"kidney": "KI", "liver": "LI", "heart": "HR", "lung": "LU",
               "pancreas": "PA", "intestine": "IN"}

# Peds B4-B5: field -> column name (case-insensitive match)
PEDS_B45 = {
    "transplant_rate": "TMR_p0_CadTxR_c",
    "transplant_rate_expected": "TMR_p0_CadTxER_c",
    "transplant_ratio": "TMR_p0_CadTxRatio_c",
    "death_rate": "TMR_p0_DthR_c",
    "death_rate_expected": "TMR_p0_DthER_c",
    "waitlist_n": "TMR_p0_TxN_c",
    "transplants": "TMR_p0_CadTxed_c",
    "person_years": "TMR_p0_CadTxPy_c",
}
PEDS_B6 = {
    "mortality_hr": "sfl_p0_hr_c",
    "mortality_hr_lb": "sfl_p0_hr_lb_c",
    "mortality_hr_ub": "sfl_p0_hr_ub_c",
    "mortality_n": "sfl_p0_n_c",
}
PEDS_SURVIVAL = {
    "graft_survival_1yr": ("TablesC5-C12 Figures C1-C20", "GSR_P0_ACT_C1Y"),
    "patient_survival_1yr": ("TablesC11-C20 FiguresC21-C32", "PSR_P0_ACT_C1Y"),
}

# National rows: the same fields aggregated at the nation level (_u suffix)
NATIONAL_B45 = {k: v[:-2] + "_u" for k, v in PEDS_B45.items()}


def _find_ci(wb, needle: str, preferred: tuple = ()):
    """find_sheet_with, but case-insensitive on the column name (B4-B5 uses
    lowercase _p0_ while the C-tables use uppercase _P0_)."""
    target = needle.lower()
    ordered = [n for n in preferred if n in wb.sheet_names()]
    ordered += [n for n in wb.sheet_names() if n not in ordered]
    for name in ordered:
        sh = wb.sheet_by_name(name)
        if sh.nrows < 3 or sh.ncols < 2:
            continue
        hdr = [str(sh.cell_value(0, c)).strip() for c in range(sh.ncols)]
        if any(h.lower() == target for h in hdr):
            return sh, hdr
    return None, None


def _col_ci(hdr, name: str) -> int:
    target = name.lower()
    for i, h in enumerate(hdr):
        if str(h).strip().lower() == target:
            return i
    return -1


def _bare_code(raw) -> str | None:
    """'ALCHTX1' -> 'ALCH'. The Peds sheet concatenates CTR_CD + CTR_TY."""
    s = str(raw).strip().upper()
    for suffix in ("TX1", "TX2", "TX3", "TX4"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    return s if sx.is_center_code(s) else None


def _rows_by_center(sheet, hdr, cols: dict, key_col: str,
                    strip_type: bool) -> dict:
    ci = _col_ci(hdr, key_col)
    if ci < 0:
        return {}
    idx = {k: _col_ci(hdr, c) for k, c in cols.items()}
    out = {}
    for r in range(1, sheet.nrows):
        raw = sheet.cell_value(r, ci)
        code = _bare_code(raw) if strip_type else (
            str(raw).strip() if sx.is_center_code(str(raw).strip()) else None)
        if not code:
            continue
        rec = {}
        for k, i in idx.items():
            if i < 0:
                continue
            v = sx.safe_float(sheet.cell_value(r, i))
            if v is not None and v != sx.CENSORED:
                rec[k] = round(v, 4)
        if rec:
            out[code] = rec
    return out


def extract_organ(path: Path) -> dict | None:
    wb = xlrd.open_workbook(str(path))
    block: dict = {"centers": {}, "national": {}}

    sheet, hdr = _find_ci(wb, "TMR_p0_CadTxR_c",
                          preferred=("Tbls B4-B5 & Fig B1-B6 - Peds",))
    if sheet is None:
        return None
    b45 = _rows_by_center(sheet, hdr, PEDS_B45, "center", strip_type=True)
    for code, rec in b45.items():
        block["centers"][code] = rec
    # National pediatric baseline (any row carries the _u columns)
    nat_idx = {k: _col_ci(hdr, c) for k, c in NATIONAL_B45.items()}
    for r in range(1, sheet.nrows):
        rec = {}
        for k, i in nat_idx.items():
            if i < 0:
                continue
            v = sx.safe_float(sheet.cell_value(r, i))
            if v is not None and v != sx.CENSORED:
                rec[k] = round(v, 4)
        if rec.get("transplant_rate"):
            block["national"] = rec
            break

    sheet6, hdr6 = _find_ci(wb, "sfl_p0_hr_c", preferred=("Table B6 & Fig B7-B9",))
    if sheet6 is not None:
        for code, rec in _rows_by_center(sheet6, hdr6, PEDS_B6, "CTR_CD",
                                         strip_type=False).items():
            block["centers"].setdefault(code, {}).update(rec)

    for field, (pref, colname) in PEDS_SURVIVAL.items():
        sh, h = _find_ci(wb, colname, preferred=(pref,))
        if sh is None:
            continue
        for code, rec in _rows_by_center(sh, h, {field: colname}, "CTR_CD",
                                         strip_type=False).items():
            block["centers"].setdefault(code, {}).update(rec)

    # A pediatric PROGRAM requires an observed transplant rate AND enough
    # exposure for that rate to mean anything. Person-years below the floor
    # produce arithmetically-correct but statistically meaningless rates:
    # ALUA liver showed 1 transplant over 0.011 person-years = 91.3/py, which
    # would convert to "certain transplant within 12 months". The observed
    # p10 of exposure is 0.68 py, so a 1.0 floor removes exactly that tail.
    kept, dropped = {}, 0
    for c, r in block["centers"].items():
        if r.get("transplant_rate") is None:
            continue
        if (r.get("person_years") or 0.0) < MIN_PERSON_YEARS:
            dropped += 1
            continue
        kept[c] = r
    block["centers"] = kept
    block["excluded_low_exposure"] = dropped
    block["national_age_mix"] = _national_age_mix(wb)
    return block


# SRTR's own pediatric age bands (Tables B8-B9 counts, national columns).
# These give the real pediatric case mix, so equity's pediatric brackets are
# weighted by observed composition rather than a guessed split.
AGE_MIX_COLS = {"0-1": "TPC_A2_NU", "2-11": "TPC_A10_NU", "12-17": "TPC_A17_NU"}


def _national_age_mix(wb) -> dict:
    """National pediatric waitlist age composition as fractions summing to 1."""
    sheet, hdr = _find_ci(wb, "TPC_A2_NU",
                          preferred=("Tables B8-B9 Counts Nation",))
    if sheet is None:
        return {}
    counts = {}
    for label, col in AGE_MIX_COLS.items():
        i = _col_ci(hdr, col)
        if i < 0:
            continue
        for r in range(1, sheet.nrows):
            v = sx.safe_float(sheet.cell_value(r, i))
            if v is not None and v != sx.CENSORED and v > 0:
                counts[label] = v
                break
    total = sum(counts.values())
    if not total:
        return {}
    return {"counts": {k: int(v) for k, v in counts.items()},
            "weights": {k: round(v / total, 4) for k, v in counts.items()}}


def fit_exposure_calibration(organ: str, code: str) -> dict | None:
    """Fit the rate-per-person-year -> 12-month probability conversion on
    ADULTS, where both forms are published (#335).

    B4-B5 reports a rate per person-year AT RISK; B7 reports the 12-month
    proportion of a listed cohort. They differ because the risk set shrinks
    as people are transplanted, die, or are delisted, so person-years are
    less than cohort-years. A naive 1-exp(-rate) is therefore biased LOW
    (kidney: 0.198 predicted vs 0.346 observed).

    One free parameter absorbs that exposure difference:
        P(12mo) = 1 - exp(-k * rate)
    fitted per organ by minimizing median absolute error against the
    observed adult proportions. Residuals are reported so the pediatric
    intervals can carry them.
    """
    import numpy as np
    from scipy.optimize import minimize_scalar
    from scipy.stats import spearmanr
    from services.data_loader import get_data

    path = RAW / f"csrs_final_tables_2511_{code}.xls"
    if not path.exists():
        return None
    wb = xlrd.open_workbook(str(path))
    sheet, hdr = _find_ci(wb, f"TMR_Ad_CadTxR_c",
                          preferred=("Tbls B4-B5 & Fig B1-B6 - Adult",))
    if sheet is None:
        return None
    data = get_data()
    ci = _col_ci(hdr, "center")
    ri = _col_ci(hdr, "TMR_Ad_CadTxR_c")
    pairs = []
    for r in range(1, sheet.nrows):
        cd = _bare_code(sheet.cell_value(r, ci))
        v = sx.safe_float(sheet.cell_value(r, ri))
        if not cd or v is None or v <= 0:
            continue
        obs = data.observed_outcome(organ, cd)
        if obs and obs.get("n", 0) >= 25 and obs.get("transplant_rate"):
            pairs.append((v, obs["transplant_rate"] / 100.0))
    if len(pairs) < 20:
        return None
    a = np.array(pairs)
    err = lambda k: float(np.median(np.abs((1 - np.exp(-k * a[:, 0])) - a[:, 1])))
    res = minimize_scalar(err, bounds=(0.2, 5.0), method="bounded")
    k = float(res.x)
    pred = 1 - np.exp(-k * a[:, 0])
    return {
        "k": round(k, 4),
        "n_adult_centers": len(a),
        "median_abs_error": round(err(k), 4),
        "spearman": round(float(spearmanr(pred, a[:, 1]).statistic), 4),
    }


def main():
    sys.path.insert(0, str(REPO / "backend"))
    from services.data_loader import load_all
    load_all()
    result = {"_meta": {
        "source": "SRTR PSR pediatric tables (B4-B5 Peds, B6 sfl_p0_*, "
                  "GSR_P0_/PSR_P0_ survival), release 2511",
        "script": "scripts/parse-srtr-pediatric.py",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "Per-center pediatric (age <18) transplant/death rates with "
                  "SRTR's own expected values and O/E ratios, waitlist-"
                  "mortality hazard ratios with credible bounds, and 1-year "
                  "graft/patient survival. Presence of transplant_rate defines "
                  "a pediatric program for that organ (#335).",
        "note": "transplant_rate / death_rate are SRTR RATES PER PERSON-YEAR at "
                "risk (transplants / person_years), NOT percentages and NOT "
                "probabilities. Use the adult-fitted exposure calibration in "
                "_calibration to convert to a 12-month probability.",
    }}
    total = 0
    for organ, code in ORGAN_CODES.items():
        path = RAW / f"csrs_final_tables_2511_{code}.xls"
        if not path.exists():
            print(f"  {organ}: raw file missing — skipped")
            continue
        block = extract_organ(path)
        if block and block["centers"]:
            cal = fit_exposure_calibration(organ, code)
            if cal:
                block["calibration"] = cal
                print(f"    calibration k={cal['k']} "
                      f"(adult fit, median abs err {cal['median_abs_error']}, "
                      f"n={cal['n_adult_centers']})")
            result[organ] = block
            total += len(block["centers"])
            nat = block["national"].get("transplant_rate")
            print(f"  {organ}: {len(block['centers'])} pediatric programs "
                  f"(national rate {nat}; {block['excluded_low_exposure']} "
                  f"dropped below {MIN_PERSON_YEARS} person-years)")

    # Cross-check against the center registry: a pediatric program we cannot
    # join is a registry GAP, not a parse error — report it loudly.
    from services.data_loader import get_data
    registry = set(get_data().all_centers.get("centers", {}))
    unjoinable = {}
    for organ in ORGAN_CODES:
        miss = [c for c in result.get(organ, {}).get("centers", {})
                if c not in registry]
        if miss:
            unjoinable[organ] = miss
    if unjoinable:
        result["_meta"]["unjoinable_centers"] = unjoinable
        print(f"  NOTE: {sum(len(v) for v in unjoinable.values())} pediatric "
              f"program(s) missing from the center registry: {unjoinable}")

    if OUT.exists():
        old = json.loads(OUT.read_text())
        old_total = sum(len(old.get(o, {}).get("centers", {}))
                        for o in ORGAN_CODES)
        if total < 0.9 * old_total and "--allow-shrink" not in sys.argv:
            print(f"REFUSING to shrink: {total} < 90% of {old_total}. "
                  f"If this drop is INTENTIONAL (e.g. a new exclusion rule), "
                  f"re-run with --allow-shrink and record why in _meta.")
            return 1
        if total < old_total:
            result["_meta"]["intentional_shrink"] = (
                f"{old_total} -> {total} records: the {MIN_PERSON_YEARS} "
                f"person-year exposure floor removed centers whose pediatric "
                f"rates were dominated by near-zero exposure (see "
                f"extract_organ)."
            )
    OUT.write_text(json.dumps(result, indent=1))
    print(f"Wrote {OUT} ({total} center-organ pediatric records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
