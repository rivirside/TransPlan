#!/usr/bin/env python3
"""
Extract comprehensive SRTR transplant center list from PSR Excel files.

Reads all organ-specific Excel files and builds a complete catalog of
all US transplant centers with their codes, names, states, and organ programs.

Output: data/srtr-all-centers.json

Phase 6A issue #115.
"""

import json
import os
import sys
from datetime import datetime, timezone

import xlrd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
RAW_DIR = os.path.join(DATA_DIR, "srtr-raw")
OUTPUT_PATH = os.path.join(DATA_DIR, "srtr-all-centers.json")

ORGAN_CODES = {
    "kidney": "KI",
    "liver": "LI",
    "heart": "HR",
    "lung": "LU",
    "pancreas": "PA",
    "intestine": "IN",
}

# B10 sheet names across SRTR release eras
B10_SHEET_NAMES = ["Table B10", "Table B9"]

# US state abbreviations → full names
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "PR": "Puerto Rico",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}


def _open_sheet(wb, candidates: list[str]):
    """Try multiple sheet names, return first match or None."""
    for name in candidates:
        try:
            return wb.sheet_by_name(name)
        except xlrd.biffh.XLRDError:
            continue
    return None


def _extract_city_from_name(entire_name: str) -> str | None:
    """
    Try to extract city from ENTIRE_NAME.
    SRTR names are like "Hospital Name (CODE)" — city info isn't explicit.
    We rely on known hospital locations or return None.
    """
    # The ENTIRE_NAME field doesn't contain city — we'll need geocoding later.
    return None


def extract_all_centers() -> dict:
    """Extract all centers from SRTR Excel files across all organs."""
    centers = {}

    for organ, organ_code in ORGAN_CODES.items():
        excel_path = os.path.join(RAW_DIR, f"csrs_final_tables_2511_{organ_code}.xls")
        if not os.path.exists(excel_path):
            print(f"  WARNING: {excel_path} not found, skipping {organ}")
            continue

        wb = xlrd.open_workbook(excel_path)
        sheet = _open_sheet(wb, B10_SHEET_NAMES)
        if not sheet:
            print(f"  WARNING: No B10/B9 sheet in {organ} file")
            continue

        headers = [sheet.cell_value(0, c) for c in range(sheet.ncols)]

        # Find required columns
        ctr_col = headers.index("CTR_CD") if "CTR_CD" in headers else -1
        name_col = headers.index("ENTIRE_NAME") if "ENTIRE_NAME" in headers else -1

        if ctr_col < 0:
            print(f"  WARNING: No CTR_CD column in {organ} B10")
            continue

        count = 0
        for r in range(2, sheet.nrows):
            code = str(sheet.cell_value(r, ctr_col)).strip()
            if not code:
                continue

            name = str(sheet.cell_value(r, name_col)).strip() if name_col >= 0 else ""

            if code not in centers:
                # Parse name: "Hospital Name (CODE)" → "Hospital Name"
                clean_name = name.replace(f"({code})", "").strip()

                # Infer state from first 2 characters of SRTR code
                state_abbr = code[:2]
                state_name = STATE_NAMES.get(state_abbr, state_abbr)

                centers[code] = {
                    "code": code,
                    "name": clean_name,
                    "state_abbr": state_abbr,
                    "state": state_name,
                    "organs": [],
                }

            if organ not in centers[code]["organs"]:
                centers[code]["organs"].append(organ)
            count += 1

        print(f"  {organ}: {count} centers found")

    return centers


def main():
    print("=== Extracting SRTR Center List ===")
    centers = extract_all_centers()

    if not centers:
        print("ERROR: No centers found. Run fetch-srtr-excel.py first.")
        sys.exit(1)

    # Sort by code for stable output
    sorted_centers = dict(sorted(centers.items()))

    # Build output
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {
        "_meta": {
            "description": "Complete catalog of US transplant centers from SRTR PSR data",
            "source": "SRTR PSR National Center-Level Summary Data",
            "totalCenters": len(sorted_centers),
            "organCounts": {},
            "extractedAt": now,
            "notes": "Center codes use 2-letter state prefix + 2-letter institution code. "
                     "Coordinates (lat/lon) to be added in issue #116.",
        },
        "centers": sorted_centers,
    }

    # Compute organ counts for metadata
    for organ in ORGAN_CODES:
        count = sum(1 for c in sorted_centers.values() if organ in c["organs"])
        output["_meta"]["organCounts"][organ] = count

    # Write output
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(f"\nWrote {OUTPUT_PATH}")
    print(f"Total: {len(sorted_centers)} unique centers")
    for organ, count in output["_meta"]["organCounts"].items():
        print(f"  {organ}: {count}")

    # Stats
    by_organ_count = {}
    for c in sorted_centers.values():
        n = len(c["organs"])
        by_organ_count[n] = by_organ_count.get(n, 0) + 1
    print(f"\nCenters by # of organ programs: {by_organ_count}")

    # State distribution
    by_state = {}
    for c in sorted_centers.values():
        st = c["state_abbr"]
        by_state[st] = by_state.get(st, 0) + 1
    top_states = sorted(by_state.items(), key=lambda x: -x[1])[:10]
    print(f"Top 10 states: {top_states}")


if __name__ == "__main__":
    main()
