#!/usr/bin/env python3
"""
Build OPO (Organ Procurement Organization) mapping data (L-050, L-009, #122).

OPO boundaries don't align with state lines. This script creates:
  1. Center-to-OPO mapping (which OPO each SRTR center belongs to)
  2. OPO metadata (name, region, states served)

Data sources:
  - OPTN member directory: https://optn.transplant.hrsa.gov/members/member-directory/
  - SRTR PSR reports (OPO-level data in OPO-specific workbooks)
  - CMS OPO Medicare Service Areas (county-level mapping)

Future work:
  - County-to-OPO mapping from CMS (enables county-level COD → OPO aggregation)
  - GeoJSON boundaries for map visualization
  - OPO-level donor statistics from SRTR

Usage:
    python3 scripts/build-opo-mapping.py
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# All 56 US OPOs with their OPTN codes, names, and primary states
# Source: OPTN member directory (optn.transplant.hrsa.gov)
OPO_DIRECTORY = {
    "ALOB": {"name": "Legacy of Hope", "states": ["AL"], "region": 3},
    "AROR": {"name": "Arkansas Regional Organ Recovery Agency", "states": ["AR"], "region": 11},
    "AZOB": {"name": "Donor Network of Arizona", "states": ["AZ"], "region": 5},
    "CADN": {"name": "Donor Network West", "states": ["CA"], "region": 5},
    "CAOP": {"name": "OneLegacy", "states": ["CA"], "region": 5},
    "CASD": {"name": "Lifesharing", "states": ["CA"], "region": 5},
    "CORS": {"name": "Donor Alliance", "states": ["CO", "WY"], "region": 8},
    "CTOP": {"name": "New England Organ Bank", "states": ["CT", "ME", "MA", "NH", "RI", "VT"], "region": 1},
    "DCTC": {"name": "Washington Regional Transplant Community", "states": ["DC", "MD", "VA"], "region": 2},
    "FLMP": {"name": "LifeQuest Organ Recovery Services", "states": ["FL"], "region": 3},
    "FLUF": {"name": "LifeLink of Florida", "states": ["FL"], "region": 3},
    "FLWC": {"name": "Life Alliance Organ Recovery Agency", "states": ["FL"], "region": 3},
    "GALL": {"name": "LifeLink of Georgia", "states": ["GA"], "region": 3},
    "HIOP": {"name": "Legacy of Life Hawaii", "states": ["HI"], "region": 6},
    "IAOP": {"name": "Iowa Donor Network", "states": ["IA"], "region": 8},
    "IDOP": {"name": "Idaho Gift of Life", "states": ["ID", "MT"], "region": 6},
    "ILIP": {"name": "Gift of Hope", "states": ["IL", "IN"], "region": 7},
    "INOP": {"name": "Indiana Donor Network", "states": ["IN"], "region": 10},
    "KYDA": {"name": "Kentucky Organ Donor Affiliates", "states": ["KY"], "region": 10},
    "LAOP": {"name": "Louisiana Organ Procurement Agency", "states": ["LA"], "region": 4},
    "MAOB": {"name": "New England Organ Bank", "states": ["MA"], "region": 1},
    "MDPC": {"name": "The Living Legacy Foundation", "states": ["MD"], "region": 2},
    "MIOP": {"name": "Gift of Life Michigan", "states": ["MI"], "region": 10},
    "MNOP": {"name": "LifeSource", "states": ["MN", "ND", "SD"], "region": 7},
    "MOMA": {"name": "Mid-America Transplant", "states": ["MO", "IL", "AR"], "region": 8},
    "MSOP": {"name": "Mississippi Organ Recovery Agency", "states": ["MS"], "region": 3},
    "NCCM": {"name": "Carolina Donor Services", "states": ["NC"], "region": 11},
    "NCNC": {"name": "LifeShare of the Carolinas", "states": ["NC", "SC"], "region": 11},
    "NEOR": {"name": "Nebraska Organ Recovery", "states": ["NE"], "region": 8},
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
    "OKOP": {"name": "LifeShare Transplant Donor Services", "states": ["OK"], "region": 4},
    "ORUO": {"name": "Pacific Northwest Transplant Bank", "states": ["OR"], "region": 6},
    "PADV": {"name": "Gift of Life Donor Program", "states": ["PA", "NJ", "DE"], "region": 2},
    "PATF": {"name": "Center for Organ Recovery & Education", "states": ["PA", "WV"], "region": 2},
    "PRLL": {"name": "LifeLink of Puerto Rico", "states": ["PR"], "region": 3},
    "SCOP": {"name": "We Are Sharing Hope SC", "states": ["SC"], "region": 11},
    "TNDS": {"name": "Tennessee Donor Services", "states": ["TN", "VA"], "region": 11},
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

# Known center-to-OPO mappings for the 22 focus cities
# Source: SRTR center reports and OPTN member search
CENTER_OPO_MAP = {
    "Pittsburgh": "PATF",       # Center for Organ Recovery & Education (CORE)
    "Philadelphia": "PADV",     # Gift of Life Donor Program
    "Baltimore": "MDPC",        # The Living Legacy Foundation
    "New York": "NYCB",         # LiveOnNY
    "Minneapolis": "MNOP",      # LifeSource
    "Madison": "WIDN",          # UW Organ and Tissue Donation
    "Chicago": "ILIP",          # Gift of Hope
    "Cleveland": "OHLB",        # Lifebanc
    "St. Louis": "MOMA",        # Mid-America Transplant
    "Indianapolis": "INOP",     # Indiana Donor Network
    "Omaha": "NEOR",            # Nebraska Organ Recovery
    "Rochester": "MNOP",        # LifeSource
    "Nashville": "TNDS",        # Tennessee Donor Services
    "Durham": "NCCM",           # Carolina Donor Services
    "Miami": "FLWC",            # Life Alliance Organ Recovery Agency
    "Dallas": "TXSB",           # Southwest Transplant Alliance
    "Houston": "TXGC",          # LifeGift
    "Portland": "ORUO",         # Pacific Northwest Transplant Bank
    "Seattle": "WALC",          # LifeCenter Northwest
    "San Francisco": "CADN",    # Donor Network West
    "Los Angeles": "CAOP",      # OneLegacy
    "Palo Alto": "CADN",        # Donor Network West
}


def main():
    # Build the mapping file
    output = {
        "_meta": {
            "description": "OPO (Organ Procurement Organization) mapping for TransPlan",
            "source": "OPTN member directory + manual center-to-OPO lookup",
            "totalOPOs": len(OPO_DIRECTORY),
            "note": "County-level OPO boundaries not yet available. See L-050.",
        },
        "opos": OPO_DIRECTORY,
        "centerOpoMap": CENTER_OPO_MAP,
    }

    output_path = DATA_DIR / "opo-mapping.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"OPO mapping saved: {output_path}")
    print(f"  {len(OPO_DIRECTORY)} OPOs cataloged")
    print(f"  {len(CENTER_OPO_MAP)} focus cities mapped to OPOs")
    print()
    print("Next steps for full OPO boundary mapping:")
    print("  1. Download CMS OPO Medicare Service Area data (county-to-OPO)")
    print("  2. Map each county FIPS to its serving OPO")
    print("  3. Aggregate COD data at OPO level instead of state level")
    print("  4. Add GeoJSON boundaries for map visualization")


if __name__ == "__main__":
    main()
