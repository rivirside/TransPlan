#!/usr/bin/env python3
"""
Build OPO mapping from authoritative HRSA county-to-OPO data (#138).

Replaces the proximity-based (haversine) center-to-OPO assignments with
authoritative county-level mappings from HRSA's "Organ Donation and
Transplantation Data" Excel workbook.

Data source:
  https://data.hrsa.gov/DataDownload/DD_Files/Organ_Donation_and_Transplantation_Data.xlsx
  Sheet: "OPO Service Area by County"

Process:
  1. Parse HRSA Excel → county FIPS → OPO name mapping
  2. For each of 248 SRTR centers, look up county FIPS via FCC Census API
  3. Map center's county FIPS → OPO name → OPO code
  4. Output updated opo-mapping.json with HRSA-sourced assignments

Usage:
    python3 scripts/build-opo-mapping-hrsa.py [--excel /path/to/file.xlsx]

    If --excel is not provided, downloads from HRSA automatically.
"""

import json
import sys
import time
import argparse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl required. Install with: pip install openpyxl")
    sys.exit(1)

try:
    import requests
except ImportError:
    requests = None  # Fall back to urllib

DATA_DIR = Path(__file__).parent.parent / "data"

HRSA_URL = "https://data.hrsa.gov/DataDownload/DD_Files/Organ_Donation_and_Transplantation_Data.xlsx"
HRSA_SHEET = "OPO Service Area by County"

# Mapping from HRSA OPO names → OPTN 4-letter codes
# Built by matching HRSA names against the existing OPO directory
HRSA_NAME_TO_CODE = {
    "Legacy of Hope": "ALOB",
    "Southern Legacy of Life": "AROR",  # HRSA name for AR OPO
    "Donor Network of Arizona": "AZOB",
    "Donor Network West": "CADN",
    "OneLegacy": "CAOP",
    "Lifesharing - A Donate Life Organization": "CASD",
    "Sierra Donor Services": "CAGS",  # 4th CA OPO (not in original 55)
    "Donor Alliance": "CORS",
    "New England Organ Bank": "CTOP",
    # Note: DCTC doesn't appear directly in HRSA; DC/MD/VA counties
    # are split among multiple OPOs. We handle this below.
    "LifeQuest Organ Recovery Services": "FLMP",
    "LifeLink of Florida": "FLUF",
    "Life Alliance Organ Recovery Agency": "FLWC",
    "OurLegacy": "FLOP",  # 4th FL OPO
    "LifeLink of Georgia": "GALL",
    "Legacy of Life Hawaii": "HIOP",
    "Iowa Donor Network": "IAOP",
    # IDOP (Idaho/Montana) - not present in HRSA, may be listed differently
    "Gift of Hope Organ & Tissue Donor Network": "ILIP",
    "Indiana Donor Network": "INOP",
    "Network for Hope": "KYDA",  # HRSA name for KY OPO
    "Louisiana Organ Procurement Agency": "LAOP",
    "Infinite Legacy": "MDPC",  # HRSA name for MD OPO (was "The Living Legacy Foundation")
    "Gift of Life Michigan": "MIOP",
    "LifeSource Upper Midwest Organ Procurement Organization": "MNOP",
    "Mid-America Transplant Services": "MOMA",
    "Mississippi Organ Recovery Agency": "MSOP",
    "HonorBridge": "NCCM",  # HRSA name for NC OPO (was "Carolina Donor Services")
    "LifeShare Carolinas": "NCNC",  # HRSA name (was "LifeShare of the Carolinas")
    "Live On Nebraska": "NEOR",  # HRSA name (was "Nebraska Organ Recovery")
    "New Jersey Organ and Tissue Sharing Network OPO": "NJTO",
    "New Mexico Donor Services": "NMOP",
    "Nevada Donor Network": "NVLV",
    "Center for Donation and Transplant": "NYAP",
    "LiveOnNY": "NYCB",
    "Finger Lakes Donor Recovery Network": "NYFL",
    "Upstate New York Transplant Services Inc": "NYRT",  # HRSA name (was "ConnectLife")
    "Lifebanc": "OHLB",
    "Life Connection of Ohio": "OHLC",
    "Lifeline of Ohio": "OHLP",
    "LifeCenter Organ Donor Network": "OHLR",  # 4th OH OPO
    "LifeShare Transplant Donor Services of Oklahoma": "OKOP",
    "Pacific Northwest Transplant Bank/Cascade Life Alliance": "ORUO",
    "Gift of Life Donor Program": "PADV",
    "Center for Organ Recovery and Education": "PATF",
    "LifeLink of Puerto Rico": "PRLL",
    "We Are Sharing Hope SC": "SCOP",
    "Tennessee Donor Services": "TNDS",
    "Mid-South Transplant Foundation": "TNMS",  # 2nd TN OPO
    "LifeGift Organ Donation Center": "TXGC",
    "Texas Organ Sharing Alliance": "TXSA",
    "Southwest Transplant Alliance": "TXSB",
    "DonorConnect": "UTOP",
    "LifeNet Health": "VATB",
    "LifeCenter Northwest": "WALC",
    "UW Health Organ and Tissue Donation": "WIDN",
    "Versiti Wisconsin, Inc": "WIUW",  # HRSA name (was "Versiti")
    "Midwest Transplant Network": "MWOB",  # KS OPO
}

# Updated OPO directory incorporating HRSA names and any new OPOs
# This preserves the original codes but updates names where HRSA differs
OPO_DIRECTORY = {
    "ALOB": {"name": "Legacy of Hope", "states": ["AL"], "region": 3},
    "AROR": {"name": "Southern Legacy of Life", "states": ["AR"], "region": 11},
    "AZOB": {"name": "Donor Network of Arizona", "states": ["AZ"], "region": 5},
    "CADN": {"name": "Donor Network West", "states": ["CA", "NV"], "region": 5},
    "CAOP": {"name": "OneLegacy", "states": ["CA"], "region": 5},
    "CASD": {"name": "Lifesharing", "states": ["CA"], "region": 5},
    "CAGS": {"name": "Sierra Donor Services", "states": ["CA"], "region": 5},
    "CORS": {"name": "Donor Alliance", "states": ["CO", "WY"], "region": 8},
    "CTOP": {"name": "New England Organ Bank", "states": ["CT", "ME", "MA", "NH", "RI", "VT"], "region": 1},
    "DCTC": {"name": "Washington Regional Transplant Community", "states": ["DC", "MD", "VA"], "region": 2},
    "FLMP": {"name": "LifeQuest Organ Recovery Services", "states": ["FL"], "region": 3},
    "FLUF": {"name": "LifeLink of Florida", "states": ["FL"], "region": 3},
    "FLWC": {"name": "Life Alliance Organ Recovery Agency", "states": ["FL"], "region": 3},
    "FLOP": {"name": "OurLegacy", "states": ["FL"], "region": 3},
    "GALL": {"name": "LifeLink of Georgia", "states": ["GA"], "region": 3},
    "HIOP": {"name": "Legacy of Life Hawaii", "states": ["HI"], "region": 6},
    "IAOP": {"name": "Iowa Donor Network", "states": ["IA"], "region": 8},
    "IDOP": {"name": "Idaho Gift of Life", "states": ["ID", "MT"], "region": 6},
    "ILIP": {"name": "Gift of Hope", "states": ["IL", "IN"], "region": 7},
    "INOP": {"name": "Indiana Donor Network", "states": ["IN"], "region": 10},
    "KYDA": {"name": "Network for Hope", "states": ["KY"], "region": 10},
    "LAOP": {"name": "Louisiana Organ Procurement Agency", "states": ["LA"], "region": 4},
    "MAOB": {"name": "New England Organ Bank", "states": ["MA"], "region": 1},
    "MDPC": {"name": "Infinite Legacy", "states": ["MD"], "region": 2},
    "MIOP": {"name": "Gift of Life Michigan", "states": ["MI"], "region": 10},
    "MNOP": {"name": "LifeSource", "states": ["MN", "ND", "SD"], "region": 7},
    "MOMA": {"name": "Mid-America Transplant", "states": ["MO", "IL", "AR"], "region": 8},
    "MSOP": {"name": "Mississippi Organ Recovery Agency", "states": ["MS"], "region": 3},
    "MWOB": {"name": "Midwest Transplant Network", "states": ["KS"], "region": 8},
    "NCCM": {"name": "HonorBridge", "states": ["NC"], "region": 11},
    "NCNC": {"name": "LifeShare Carolinas", "states": ["NC", "SC"], "region": 11},
    "NEOR": {"name": "Live On Nebraska", "states": ["NE"], "region": 8},
    "NJTO": {"name": "NJ Sharing Network", "states": ["NJ"], "region": 2},
    "NMOP": {"name": "New Mexico Donor Services", "states": ["NM"], "region": 5},
    "NVLV": {"name": "Nevada Donor Network", "states": ["NV"], "region": 5},
    "NYAP": {"name": "Center for Donation & Transplant", "states": ["NY", "VT"], "region": 9},
    "NYCB": {"name": "LiveOnNY", "states": ["NY"], "region": 9},
    "NYFL": {"name": "Finger Lakes Donor Recovery Network", "states": ["NY"], "region": 2},
    "NYRT": {"name": "ConnectLife", "states": ["NY"], "region": 2},
    "OHLB": {"name": "Lifebanc", "states": ["OH"], "region": 10},
    "OHLC": {"name": "Life Connection of Ohio", "states": ["OH"], "region": 10},
    "OHLP": {"name": "Lifeline of Ohio", "states": ["OH"], "region": 10},
    "OHLR": {"name": "LifeCenter Organ Donor Network", "states": ["OH"], "region": 10},
    "OKOP": {"name": "LifeShare Transplant Donor Services", "states": ["OK"], "region": 5},
    "ORUO": {"name": "Pacific Northwest Transplant Bank", "states": ["OR"], "region": 6},
    "PADV": {"name": "Gift of Life Donor Program", "states": ["PA", "NJ", "DE"], "region": 2},
    "PATF": {"name": "Center for Organ Recovery & Education", "states": ["PA", "WV"], "region": 2},
    "PRLL": {"name": "LifeLink of Puerto Rico", "states": ["PR"], "region": 3},
    "SCOP": {"name": "We Are Sharing Hope SC", "states": ["SC"], "region": 11},
    "TNDS": {"name": "Tennessee Donor Services", "states": ["TN", "VA"], "region": 11},
    "TNMS": {"name": "Mid-South Transplant Foundation", "states": ["TN"], "region": 11},
    "TXGC": {"name": "LifeGift", "states": ["TX"], "region": 4},
    "TXSA": {"name": "Texas Organ Sharing Alliance", "states": ["TX"], "region": 4},
    "TXSB": {"name": "Southwest Transplant Alliance", "states": ["TX"], "region": 4},
    "UTOP": {"name": "DonorConnect", "states": ["UT"], "region": 5},
    "VATB": {"name": "LifeNet Health", "states": ["VA"], "region": 11},
    "WALC": {"name": "LifeCenter Northwest", "states": ["WA", "AK"], "region": 6},
    "WIDN": {"name": "UW Organ and Tissue Donation", "states": ["WI"], "region": 7},
    "WIUW": {"name": "Versiti", "states": ["WI"], "region": 7},
    "WVUO": {"name": "CORE (WV)", "states": ["WV"], "region": 2},
}


def parse_hrsa_opo_name(raw_name: str) -> tuple[str, str]:
    """Extract OPO name and state from 'OPO Name (ST)' format."""
    # e.g. "Legacy of Hope (AL)" → ("Legacy of Hope", "AL")
    if raw_name and "(" in raw_name:
        idx = raw_name.rindex("(")
        name = raw_name[:idx].strip()
        state = raw_name[idx + 1 : raw_name.rindex(")")]
        return name, state
    return raw_name, ""


def parse_hrsa_excel(excel_path: str) -> dict:
    """
    Parse the HRSA Excel file and return:
      - county_to_opos: {fips: [opo_name, ...]}  (primary + overlap)
      - county_to_primary_opo: {fips: opo_name}   (primary only)
      - county_info: {fips: {state, county_name}}
    """
    print(f"Reading HRSA Excel: {excel_path}")
    wb = openpyxl.load_workbook(excel_path, read_only=True)
    ws = wb[HRSA_SHEET]

    county_to_primary_opo = {}  # FIPS → primary OPO name
    county_to_opos = {}  # FIPS → list of all OPO names (primary + overlap)
    county_info = {}  # FIPS → {state, county_name}

    row_count = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        opo_raw = row[0]
        if opo_raw is None:
            break

        fips = str(row[1]).zfill(5)  # Ensure 5-digit FIPS
        state_name = row[2]
        county_name = row[3]
        overlap_with = row[4]

        opo_name, opo_state = parse_hrsa_opo_name(opo_raw)

        county_info[fips] = {"state": state_name, "county_name": county_name}

        # Primary assignment
        if fips not in county_to_primary_opo:
            county_to_primary_opo[fips] = opo_name
        # Build list of all OPOs for this county
        if fips not in county_to_opos:
            county_to_opos[fips] = []
        if opo_name not in county_to_opos[fips]:
            county_to_opos[fips].append(opo_name)

        # Add overlap OPO if present
        if overlap_with and overlap_with != "N/A":
            if overlap_with not in county_to_opos[fips]:
                county_to_opos[fips].append(overlap_with)

        row_count += 1

    wb.close()
    print(f"  Parsed {row_count} rows, {len(county_to_primary_opo)} unique counties")
    return county_to_primary_opo, county_to_opos, county_info


def lookup_county_fips_fcc(lat: float, lon: float) -> str | None:
    """Look up county FIPS code from lat/lon using FCC Census Area API."""
    url = "https://geo.fcc.gov/api/census/area"
    params = {"lat": lat, "lon": lon, "format": "json"}

    try:
        if requests:
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
        else:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            full_url = f"{url}?{query}"
            req = urllib.request.Request(full_url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

        results = data.get("results", [])
        if results:
            return results[0]["county_fips"]
    except Exception as e:
        print(f"  FCC API error for ({lat}, {lon}): {e}")

    return None


def resolve_opo_code(opo_name: str) -> str | None:
    """Resolve HRSA OPO name to OPTN 4-letter code."""
    if opo_name in HRSA_NAME_TO_CODE:
        return HRSA_NAME_TO_CODE[opo_name]

    # Try fuzzy matching by checking if name is contained
    name_lower = opo_name.lower()
    for hrsa_name, code in HRSA_NAME_TO_CODE.items():
        if hrsa_name.lower() in name_lower or name_lower in hrsa_name.lower():
            return code

    return None


def build_center_to_opo(
    centers: dict,
    county_to_primary_opo: dict,
    county_to_opos: dict,
    county_info: dict,
) -> tuple[dict, dict, list]:
    """
    Map each SRTR center to its OPO using county FIPS lookup.

    Returns:
      - center_opo_map: {center_code: opo_code}
      - center_opo_details: {center_code: {opo, method, county_fips, county_name}}
      - warnings: list of warning strings
    """
    center_opo_map = {}
    center_opo_details = {}
    warnings = []

    total = len(centers)
    print(f"\nMapping {total} centers to OPOs via county FIPS lookup...")

    # Cache for FCC API results to avoid redundant calls
    fips_cache = {}

    for i, (code, center) in enumerate(centers.items()):
        lat = center.get("lat")
        lon = center.get("lon")

        if lat is None or lon is None:
            warnings.append(f"{code}: No coordinates available")
            continue

        # Look up county FIPS from coordinates
        cache_key = f"{lat},{lon}"
        if cache_key in fips_cache:
            county_fips = fips_cache[cache_key]
        else:
            county_fips = lookup_county_fips_fcc(lat, lon)
            fips_cache[cache_key] = county_fips
            # Rate limit: FCC API is free but be polite
            time.sleep(0.15)

        if i % 25 == 0:
            print(f"  Progress: {i}/{total} centers processed...")

        if not county_fips:
            warnings.append(f"{code} ({center['name']}): FCC API returned no county FIPS for ({lat}, {lon})")
            continue

        # Look up OPO for this county
        opo_name = county_to_primary_opo.get(county_fips)
        if not opo_name:
            # Check if there's an overlapping OPO
            if county_fips in county_to_opos:
                opo_name = county_to_opos[county_fips][0]
            else:
                warnings.append(
                    f"{code} ({center['name']}): County FIPS {county_fips} not found in HRSA data"
                )
                continue

        # Resolve to OPTN code
        opo_code = resolve_opo_code(opo_name)
        if not opo_code:
            warnings.append(
                f"{code} ({center['name']}): Cannot resolve OPO name '{opo_name}' to OPTN code"
            )
            continue

        info = county_info.get(county_fips, {})
        center_opo_map[code] = opo_code
        center_opo_details[code] = {
            "opo": opo_code,
            "method": "hrsa_county",
            "county_fips": county_fips,
            "county_name": info.get("county_name", ""),
            "opo_name": opo_name,
        }

    print(f"  Done: {len(center_opo_map)}/{total} centers mapped")
    return center_opo_map, center_opo_details, warnings


def build_county_to_opo_section(
    county_to_primary_opo: dict,
    county_to_opos: dict,
    county_info: dict,
) -> dict:
    """
    Build the countyToOpo section: FIPS → {opo, opoCode, county, state, overlaps}.
    Used by the spatial interpolation engine.
    """
    result = {}
    for fips, opo_name in sorted(county_to_primary_opo.items()):
        opo_code = resolve_opo_code(opo_name)
        info = county_info.get(fips, {})
        all_opos = county_to_opos.get(fips, [opo_name])

        entry = {
            "opo": opo_code or opo_name,
            "opoName": opo_name,
            "county": info.get("county_name", ""),
            "state": info.get("state", ""),
        }

        # Only include overlaps if there's more than one OPO
        if len(all_opos) > 1:
            overlap_codes = []
            for name in all_opos[1:]:
                c = resolve_opo_code(name)
                overlap_codes.append(c or name)
            entry["overlaps"] = overlap_codes

        result[fips] = entry

    return result


def main():
    parser = argparse.ArgumentParser(description="Build OPO mapping from HRSA data")
    parser.add_argument(
        "--excel",
        default="/tmp/hrsa_organ_donation.xlsx",
        help="Path to HRSA Excel file (default: /tmp/hrsa_organ_donation.xlsx)",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the Excel file from HRSA before processing",
    )
    args = parser.parse_args()

    excel_path = args.excel

    # Download if requested or file doesn't exist
    if args.download or not Path(excel_path).exists():
        print(f"Downloading HRSA data from {HRSA_URL}...")
        urllib.request.urlretrieve(HRSA_URL, excel_path)
        print(f"  Saved to {excel_path}")

    # 1. Parse HRSA Excel
    county_to_primary_opo, county_to_opos, county_info = parse_hrsa_excel(excel_path)

    # Validate HRSA OPO name → code mapping
    print("\nValidating OPO name → code mapping...")
    all_opo_names = set(county_to_primary_opo.values())
    for name in sorted(all_opo_names):
        code = resolve_opo_code(name)
        status = f"→ {code}" if code else "→ UNMAPPED!"
        print(f"  {name}: {status}")

    unmapped_names = [n for n in all_opo_names if not resolve_opo_code(n)]
    if unmapped_names:
        print(f"\nWARNING: {len(unmapped_names)} OPO names could not be mapped to codes:")
        for n in unmapped_names:
            print(f"  - {n}")
        print("Please add these to HRSA_NAME_TO_CODE in the script.")

    # 2. Load SRTR centers
    centers_path = DATA_DIR / "srtr-all-centers.json"
    print(f"\nLoading centers from {centers_path}")
    with open(centers_path) as f:
        centers_data = json.load(f)
    centers = centers_data["centers"]
    print(f"  Loaded {len(centers)} centers")

    # 3. Map centers to OPOs
    center_opo_map, center_opo_details, warnings = build_center_to_opo(
        centers, county_to_primary_opo, county_to_opos, county_info
    )

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")

    # 4. Build county-to-OPO section
    print("\nBuilding countyToOpo section...")
    county_to_opo_section = build_county_to_opo_section(
        county_to_primary_opo, county_to_opos, county_info
    )
    print(f"  {len(county_to_opo_section)} counties mapped")

    # 5. Compute OPO center counts
    opo_center_counts = {}
    for opo_code in center_opo_map.values():
        opo_center_counts[opo_code] = opo_center_counts.get(opo_code, 0) + 1

    # 6. Count mapping methods
    method_counts = {}
    for detail in center_opo_details.values():
        m = detail["method"]
        method_counts[m] = method_counts.get(m, 0) + 1

    # 7. Build output
    # Only include OPOs that actually have counties or centers assigned
    active_opo_codes = set(center_opo_map.values()) | {
        entry["opo"] for entry in county_to_opo_section.values()
        if isinstance(entry["opo"], str) and len(entry["opo"]) == 4
    }
    opos_section = {}
    for code in sorted(OPO_DIRECTORY.keys()):
        if code in active_opo_codes or code in {
            v for v in center_opo_map.values()
        }:
            opos_section[code] = OPO_DIRECTORY[code]
        elif code in OPO_DIRECTORY:
            # Include all known OPOs even if no centers assigned
            opos_section[code] = OPO_DIRECTORY[code]

    output = {
        "_meta": {
            "description": "OPO mapping for TransPlan — all 248 SRTR centers mapped to OPOs via HRSA county data",
            "source": "HRSA Organ Donation and Transplantation Data (county-to-OPO) + FCC Census Area API (center lat/lon to county FIPS)",
            "hrsaDataUrl": HRSA_URL,
            "hrsaSheet": HRSA_SHEET,
            "totalOPOs": len(opos_section),
            "totalCounties": len(county_to_opo_section),
            "totalCentersMapped": len(center_opo_map),
            "mappingMethods": method_counts,
            "note": "Center-to-OPO assignments are authoritative, based on HRSA county-level OPO service areas. Each center is mapped to the OPO serving the county where the center is located (via FCC Census Area API for lat/lon → county FIPS lookup).",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        },
        "opos": opos_section,
        "centerOpoMap": center_opo_map,
        "centerOpoDetails": center_opo_details,
        "opoCenterCounts": dict(sorted(opo_center_counts.items())),
        "countyToOpo": county_to_opo_section,
    }

    # Write output
    output_path = DATA_DIR / "opo-mapping.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote {output_path}")
    print(f"  OPOs: {len(opos_section)}")
    print(f"  Centers mapped: {len(center_opo_map)}")
    print(f"  Counties: {len(county_to_opo_section)}")

    # Summary of changes vs old mapping
    old_path = DATA_DIR / "opo-mapping.json.bak"
    if old_path.exists():
        with open(old_path) as f:
            old_data = json.load(f)
        old_map = old_data.get("centerOpoMap", {})
        changes = 0
        for code in center_opo_map:
            if code in old_map and old_map[code] != center_opo_map[code]:
                changes += 1
                print(f"  CHANGED: {code}: {old_map[code]} → {center_opo_map[code]}")
        print(f"\n  Total OPO assignment changes: {changes}/{len(center_opo_map)}")


if __name__ == "__main__":
    main()
