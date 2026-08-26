#!/usr/bin/env python3
"""Per-organ waitlist composition from SRTR Tables B8-B9 (#337).

Equity analysis weights its 48 demographic cells by how common each profile
actually is. Until now those weights were:

  * blood type — US GENERAL-POPULATION prevalence, and
  * age and sex — a single all-organ approximation (11/38/51, 60/40 M/F),
    recorded in the register as EQSP-31 `assumed`, high risk.

Both are measurably wrong, and wrong in a direction that matters. SRTR
publishes the actual national waitlist composition per organ, and it differs
from the general population precisely where inequity lives:

  kidney waitlist  50.0% type O, 15.1% type B
  US population    44.0% type O, 10.0% type B

Type B is over-represented on the kidney waitlist (B is more common among
Black and Asian candidates) and faces among the longest waits. Weighting that
cell by general-population prevalence therefore UNDERSTATES the disparity the
analysis exists to measure.

Age and sex vary by organ too, so one global figure cannot fit any of them:

  pancreas  23.5% aged 18-34   kidney 9.7%   lung 5.4%
  heart     71% male           pancreas 51% male

One documented assumption remains. SRTR reports ABO group (O/A/B/AB) without
Rh, while the equity matrix uses eight Rh-qualified types, so each group is
split by the US Rh-positive share. Rh is not associated with the ABO groups,
and the split is the same for every cell, so it cannot move the between-group
comparison — unlike the ABO figures it replaces.

Writes data/waitlist-composition.json.
"""
import json
import sys
from pathlib import Path

import xlrd

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "scripts"))

RAW_DIR = REPO / "data" / "srtr-raw"
OUT = REPO / "data" / "waitlist-composition.json"
SHEET = "Tables B8-B9 Counts Nation"

ORGAN_CODES = {"kidney": "KI", "liver": "LI", "heart": "HR",
               "lung": "LU", "pancreas": "PA", "intestine": "IN"}

# SRTR's published adult age bands. The equity brackets are defined as exact
# UNIONS of these, so no apportionment assumption is needed anywhere.
AGE_BANDS = {
    "18-34": ["TPC_A34_NU"],
    "35-64": ["TPC_A49_NU", "TPC_A64_NU"],
    "65+": ["TPC_A69_NU", "TPC_A70P_NU"],
}
SEX_COLS = {"female": "TPC_GF_NU", "male": "TPC_GM_NU"}
ABO_COLS = {"O": "TPC_BO_NU", "A": "TPC_BA_NU",
            "B": "TPC_BB_NU", "AB": "TPC_BAB_NU"}

# US Rh-positive share (American Red Cross). Applied uniformly to every ABO
# group; see the module docstring for why this cannot bias the comparison.
RH_POSITIVE = 0.84

# Never-shrink / sanity guards (2026-08-05 rule).
MIN_ORGANS = 4
MIN_LISTED = 100          # an organ with fewer listed candidates is not usable
TOLERANCE = 0.02          # shares must sum to 1 within this


class MissingColumn(Exception):
    """A configured SRTR column is absent — a layout change, not a zero."""


def read_national_row(sheet, header: list[str], columns: list[str]) -> float:
    """Sum the national counts for *columns*.

    Raises MissingColumn if any requested column is absent. It previously
    returned None, which `shares()` then dropped — so a renamed SRTR column
    produced a distribution NORMALIZED OVER WHATEVER SURVIVED. A dropped
    `TPC_GF_NU` would have shipped "the kidney waitlist is 100% male" and
    passed every downstream check, because a vector normalized over its own
    survivors always sums to 1. The guard could not fire.

    A column that is present but genuinely zero returns 0.0 — a real
    observation, kept.
    """
    idx = {h: i for i, h in enumerate(header)}
    total = 0.0
    for col in columns:
        i = idx.get(col)
        if i is None:
            raise MissingColumn(col)
        for r in range(1, sheet.nrows):
            v = sheet.cell_value(r, i)
            if isinstance(v, (int, float)) and v > 0:
                total += float(v)
                break
    return total


def shares(counts: dict) -> dict:
    """Normalize, KEEPING every configured key.

    Dropping zero-valued keys meant a genuinely empty band vanished from the
    output, so downstream saw a missing key rather than a zero.
    """
    total = sum(counts.values())
    if not total:
        return {}
    return {k: round(v / total, 4) for k, v in counts.items()}


def extract(organ: str, code: str) -> dict | None:
    path = RAW_DIR / f"csrs_final_tables_2511_{code}.xls"
    if not path.exists():
        print(f"  {organ}: {path.name} absent — skipped")
        return None
    sheet = xlrd.open_workbook(str(path)).sheet_by_name(SHEET)
    header = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]

    try:
        ages = {band: read_national_row(sheet, header, cols)
                for band, cols in AGE_BANDS.items()}
        sexes = {name: read_national_row(sheet, header, [col])
                 for name, col in SEX_COLS.items()}
        abo = {name: read_national_row(sheet, header, [col])
               for name, col in ABO_COLS.items()}
    except MissingColumn as e:
        raise SystemExit(
            f"{organ}: SRTR column {e} is missing — the workbook layout has "
            f"changed. Refusing to write a distribution normalized over the "
            f"columns that happen to remain.")

    listed = sum(v for v in abo.values() if v)
    if listed < MIN_LISTED:
        print(f"  {organ}: only {listed:.0f} listed candidates — skipped")
        return None

    # Split each ABO group by Rh into the eight types the equity matrix uses.
    abo_shares = shares(abo)
    blood_type = {}
    for group, share in abo_shares.items():
        blood_type[f"{group}+"] = round(share * RH_POSITIVE, 4)
        blood_type[f"{group}-"] = round(share * (1.0 - RH_POSITIVE), 4)

    return {
        "n_listed": int(listed),
        "age_brackets": shares(ages),
        "sex": shares(sexes),
        "abo_group": abo_shares,
        "blood_type": blood_type,
        "age_band_counts": {k: int(v) for k, v in ages.items() if v},
    }


def main() -> int:
    result = {"_meta": {
        "source": "SRTR PSR National Center-Level Summary Data (January 2025 "
                  "release), Tables B8-B9 national candidate counts",
        "script": "scripts/parse-waitlist-composition.py",
        "method": "National waitlist composition per organ. Age brackets are "
                  "exact unions of SRTR's published bands (18-34; 35-49 + "
                  "50-64; 65-69 + 70+), so no apportionment is involved.",
        "rh_assumption": f"SRTR reports ABO group without Rh, so each group is "
                         f"split {RH_POSITIVE:.0%}/{1 - RH_POSITIVE:.0%} "
                         f"positive/negative using the US Rh share. Applied "
                         f"uniformly, so it cannot shift between-group "
                         f"comparisons.",
        "references": ["https://www.srtr.org/reports/program-specific-reports/"],
    }}

    for organ, code in ORGAN_CODES.items():
        rec = extract(organ, code)
        if not rec:
            continue
        # Every distribution must be a distribution.
        for field in ("age_brackets", "sex", "abo_group", "blood_type"):
            total = sum(rec[field].values())
            if abs(total - 1.0) > TOLERANCE:
                print(f"ERROR: {organ}.{field} sums to {total:.4f}, not 1.0",
                      file=sys.stderr)
                return 1
        result[organ] = rec
        print(f"  {organ:10s} n={rec['n_listed']:6d} "
              f"age={rec['age_brackets']} sex={rec['sex']}")

    organs = [k for k in result if k != "_meta"]
    if len(organs) < MIN_ORGANS:
        print(f"ERROR: only {len(organs)} organs parsed (floor {MIN_ORGANS}) — "
              f"refusing to write", file=sys.stderr)
        return 1

    # Never-shrink guard against the previous file.
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text())
            prev_organs = len([k for k in prev if k != "_meta"])
            if len(organs) < prev_organs:
                print(f"ERROR: {len(organs)} organs vs {prev_organs} previously "
                      f"— never-shrink guard", file=sys.stderr)
                return 1
        except json.JSONDecodeError:
            pass

    OUT.write_text(json.dumps(result, indent=1) + "\n")
    print(f"\nWrote {OUT.relative_to(REPO)} — {len(organs)} organs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
