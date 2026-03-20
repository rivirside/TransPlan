#!/usr/bin/env python3
"""
Fetch and build OPO-to-center mapping for all 248 SRTR centers (L-050, L-009, #122).

Maps every transplant center to its serving OPO using:
  1. Single-OPO states: automatic (95 centers)
  2. Multi-OPO states: geographic proximity to OPO headquarters (152 centers)
  3. Manual overrides for known edge cases

OPO headquarters coordinates sourced from OPTN member directory.
Outputs: data/opo-mapping.json (updated with centerOpoMap for all 248 centers)

Usage:
    python3 scripts/fetch-opo-service-areas.py
"""

import json
import math
import sys
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent.parent / "data"

# OPO headquarters coordinates (lat, lon)
# Source: OPTN member directory addresses, geocoded
# Only needed for multi-OPO states where disambiguation is required
OPO_HEADQUARTERS = {
    # Arkansas
    "AROR": (34.7465, -92.2896),   # Little Rock, AR
    "MOMA": (38.6270, -90.1994),   # St. Louis, MO (serves some AR counties)
    # California
    "CADN": (37.7749, -122.4194),  # San Francisco (Northern CA)
    "CAOP": (34.0522, -118.2437),  # Los Angeles (Southern CA)
    "CASD": (32.7157, -117.1611),  # San Diego
    # Florida
    "FLMP": (28.5383, -81.3792),   # Orlando (North/Central FL)
    "FLUF": (27.9506, -82.4572),   # Tampa (West/Central FL)
    "FLWC": (25.7617, -80.1918),   # Miami (South FL)
    # Illinois
    "ILIP": (41.8781, -87.6298),   # Chicago (Northern IL + some IN)
    # Indiana
    "INOP": (39.7684, -86.1581),   # Indianapolis
    # Massachusetts — both are New England Organ Bank
    "CTOP": (42.3601, -71.0589),   # Boston (NEOB serves all New England)
    "MAOB": (42.3601, -71.0589),   # Boston (same org, different code)
    # Maryland
    "DCTC": (38.9072, -77.0369),   # Washington DC
    "MDPC": (39.2904, -76.6122),   # Baltimore
    # North Carolina
    "NCCM": (35.9940, -78.8986),   # Durham/RTP (Eastern NC)
    "NCNC": (35.2271, -80.8431),   # Charlotte (Western NC + some SC)
    # New Jersey
    "NJTO": (40.7282, -74.0776),   # New Providence, NJ
    "PADV": (39.9526, -75.1652),   # Philadelphia (serves S. NJ + DE)
    # New York
    "NYAP": (42.6526, -73.7562),   # Albany (Upstate East)
    "NYCB": (40.7128, -74.0060),   # New York City
    "NYFL": (43.1566, -77.6088),   # Rochester (Finger Lakes)
    "NYRT": (42.8864, -78.8784),   # Buffalo (Western NY)
    # Ohio
    "OHLB": (41.4993, -81.6944),   # Cleveland (NE Ohio)
    "OHLC": (41.1003, -80.6495),   # Youngstown area (NW Ohio)
    "OHLP": (39.9612, -82.9988),   # Columbus (Central/S Ohio)
    # Pennsylvania
    "PATF": (40.4406, -79.9959),   # Pittsburgh (Western PA + WV)
    # South Carolina
    "SCOP": (34.0007, -81.0348),   # Columbia, SC
    # Texas
    "TXGC": (29.7604, -95.3698),   # Houston (SE Texas)
    "TXSA": (29.4241, -98.4936),   # San Antonio (S. Central TX)
    "TXSB": (32.7767, -96.7970),   # Dallas (North TX)
    # Virginia
    "TNDS": (36.1627, -86.7816),   # Nashville (serves SW VA)
    "VATB": (36.8529, -75.9780),   # Virginia Beach (Eastern VA)
    # Vermont
    # Wisconsin
    "WIDN": (43.0731, -89.4012),   # Madison
    "WIUW": (43.0389, -87.9065),   # Milwaukee
    # West Virginia
    "WVUO": (39.6295, -79.9559),   # Morgantown, WV
}

# Manual overrides for centers where geographic proximity is wrong
# (center is closer to one OPO HQ but actually served by another)
MANUAL_OVERRIDES = {
    # Indiana: Gift of Hope (ILIP) serves NW Indiana (Gary, South Bend area)
    # but most IN centers are served by Indiana Donor Network (INOP)
    "INLU": "ILIP",     # Loyola area — actually in IL, served by Gift of Hope
    # Massachusetts: Both CTOP and MAOB are New England Organ Bank
    # CTOP is the primary code; map all MA centers to CTOP
    # New Jersey: Southern NJ is served by PADV (Gift of Life, Philadelphia)
    # Northern NJ is served by NJTO (NJ Sharing Network)
    # Kansas has no OPO in our directory — served by Midwest Transplant Network
    "KSUK": "MOMA",     # University of Kansas — closest match is Mid-America
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def find_nearest_opo(lat: float, lon: float, candidate_opos: list[str]) -> tuple[str, float]:
    """Find nearest OPO by headquarters distance."""
    best_opo = None
    best_dist = float("inf")
    for opo_code in candidate_opos:
        if opo_code not in OPO_HEADQUARTERS:
            continue
        hq_lat, hq_lon = OPO_HEADQUARTERS[opo_code]
        dist = haversine_km(lat, lon, hq_lat, hq_lon)
        if dist < best_dist:
            best_dist = dist
            best_opo = opo_code
    return best_opo, best_dist


def main():
    # Load existing data
    with open(DATA_DIR / "srtr-all-centers.json") as f:
        centers = json.load(f)["centers"]

    with open(DATA_DIR / "opo-mapping.json") as f:
        opo_data = json.load(f)

    opos = opo_data["opos"]

    # Build state → OPO lookup
    state_opos: dict[str, list[str]] = {}
    for code, info in opos.items():
        for st in info["states"]:
            state_opos.setdefault(st, []).append(code)

    single_opo_states = {st: codes[0] for st, codes in state_opos.items() if len(codes) == 1}
    multi_opo_states = {st: codes for st, codes in state_opos.items() if len(codes) > 1}

    # Map all 248 centers
    center_opo_map = {}
    stats = {"single_state": 0, "geographic": 0, "manual": 0, "unmapped": 0}
    distances = []

    for ctr_code, ctr_info in sorted(centers.items()):
        state = ctr_info["state_abbr"]
        lat = ctr_info.get("lat")
        lon = ctr_info.get("lon")

        # 1. Manual override?
        if ctr_code in MANUAL_OVERRIDES:
            center_opo_map[ctr_code] = {
                "opo": MANUAL_OVERRIDES[ctr_code],
                "method": "manual",
                "distance_km": None,
            }
            stats["manual"] += 1
            continue

        # 2. Single-OPO state?
        if state in single_opo_states:
            center_opo_map[ctr_code] = {
                "opo": single_opo_states[state],
                "method": "single_state",
                "distance_km": None,
            }
            stats["single_state"] += 1
            continue

        # 3. Multi-OPO state — use geographic proximity
        if state in multi_opo_states and lat and lon:
            candidates = multi_opo_states[state]
            # For MA, both CTOP and MAOB are the same org — prefer CTOP
            if state == "MA":
                nearest_opo = "CTOP"
                dist = 0.0
            else:
                nearest_opo, dist = find_nearest_opo(lat, lon, candidates)

            if nearest_opo:
                center_opo_map[ctr_code] = {
                    "opo": nearest_opo,
                    "method": "geographic",
                    "distance_km": round(dist, 1),
                }
                stats["geographic"] += 1
                distances.append(dist)
                continue

        # 4. Unmapped
        center_opo_map[ctr_code] = {
            "opo": None,
            "method": "unmapped",
            "distance_km": None,
        }
        stats["unmapped"] += 1
        print(f"  WARNING: Could not map {ctr_code} ({ctr_info.get('name', '?')}) in {state}")

    # Build simplified center→OPO map (just code → OPO code)
    simple_map = {ctr: info["opo"] for ctr, info in center_opo_map.items() if info["opo"]}

    # Count centers per OPO
    opo_center_counts: dict[str, int] = {}
    for info in center_opo_map.values():
        if info["opo"]:
            opo_center_counts[info["opo"]] = opo_center_counts.get(info["opo"], 0) + 1

    # Update opo-mapping.json
    opo_data["_meta"]["description"] = "OPO mapping for TransPlan — all 248 SRTR centers mapped to OPOs"
    opo_data["_meta"]["source"] = (
        "OPTN member directory (OPO catalog) + geographic proximity to OPO HQ "
        "(center-to-OPO assignment for multi-OPO states)"
    )
    opo_data["_meta"]["totalOPOs"] = len(opos)
    opo_data["_meta"]["totalCentersMapped"] = len(simple_map)
    opo_data["_meta"]["mappingMethods"] = stats
    opo_data["_meta"]["generatedAt"] = datetime.now(timezone.utc).isoformat()
    opo_data["_meta"]["note"] = (
        "Centers in single-OPO states are auto-assigned. Centers in multi-OPO states "
        "are assigned to the nearest OPO by headquarters distance. This is approximate — "
        "actual OPO service areas are defined at county level by CMS (42 CFR Part 486 Appendix). "
        "County-level mapping not yet available as structured data."
    )

    # Replace the old 22-city map with the full center map
    opo_data["centerOpoMap"] = simple_map
    opo_data["centerOpoDetails"] = center_opo_map
    opo_data["opoCenterCounts"] = dict(sorted(opo_center_counts.items()))

    with open(DATA_DIR / "opo-mapping.json", "w") as f:
        json.dump(opo_data, f, indent=2)

    # Print summary
    print(f"OPO mapping updated: {DATA_DIR / 'opo-mapping.json'}")
    print(f"  {len(simple_map)}/{len(centers)} centers mapped to OPOs")
    print(f"  Methods: {stats}")
    if distances:
        distances.sort()
        median = distances[len(distances) // 2]
        print(f"  Geographic distances: median {median:.1f} km, "
              f"max {max(distances):.1f} km, mean {sum(distances)/len(distances):.1f} km")
    print()
    print("Centers per OPO:")
    for opo_code, count in sorted(opo_center_counts.items(), key=lambda x: -x[1]):
        name = opos.get(opo_code, {}).get("name", "?")
        print(f"  {opo_code} ({name}): {count} centers")


if __name__ == "__main__":
    main()
