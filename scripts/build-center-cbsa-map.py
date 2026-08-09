#!/usr/bin/env python3
"""Build the static center → CBSA (metro/micro area) mapping.

One-time build script (re-run only if centers move or new centers are added).
For each of the 248 SRTR centers, reverse-geocodes (lat, lon) against the
Census Bureau geocoder to find the containing CBSA. Output is committed to
data/center-cbsa-map.json and consumed by backend cost-of-living lookups
(exact MSA match instead of 22-city spatial interpolation — #205).

BEA Regional Price Parities (MARPP) cover *metropolitan* areas only, so
centers in micropolitan areas or outside any CBSA fall back to their state
RPP at lookup time. We still record the micro CBSA for transparency.

Source: https://geocoding.geo.census.gov/ (free, no API key)
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GEOCODER = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
LAYERS = "Metropolitan Statistical Areas,Micropolitan Statistical Areas"
DELAY_S = 0.15
RETRIES = 3


def lookup_cbsa(lat: float, lon: float) -> dict | None:
    params = urllib.parse.urlencode({
        "x": lon, "y": lat,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "layers": LAYERS,
        "format": "json",
    })
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(f"{GEOCODER}?{params}", timeout=30) as resp:
                payload = json.load(resp)
            geos = payload["result"]["geographies"]
            for layer, cbsa_type in (
                ("Metropolitan Statistical Areas", "metro"),
                ("Micropolitan Statistical Areas", "micro"),
            ):
                entries = geos.get(layer) or []
                if entries:
                    e = entries[0]
                    return {
                        "cbsa": e["GEOID"],
                        "cbsa_name": e["NAME"],
                        "cbsa_type": cbsa_type,
                    }
            return {"cbsa": None, "cbsa_name": None, "cbsa_type": "none"}
        except Exception as exc:  # noqa: BLE001 — retry on any transport error
            if attempt == RETRIES - 1:
                print(f"  FAILED after {RETRIES} tries: {exc}", file=sys.stderr)
                return None
            time.sleep(2 ** attempt)
    return None


def main() -> int:
    centers = json.loads((DATA_DIR / "srtr-all-centers.json").read_text())["centers"]
    out, failures = {}, []

    for i, (code, c) in enumerate(sorted(centers.items()), 1):
        lat, lon = c.get("lat"), c.get("lon")
        if lat is None or lon is None:
            failures.append(code)
            print(f"[{i}/{len(centers)}] {code}: no coordinates, skipped")
            continue
        result = lookup_cbsa(lat, lon)
        if result is None:
            failures.append(code)
            continue
        out[code] = {"state_abbr": c.get("state_abbr"), **result}
        print(f"[{i}/{len(centers)}] {code}: {result['cbsa_type']} {result['cbsa_name']}")
        time.sleep(DELAY_S)

    if failures:
        print(f"\nERROR: {len(failures)} centers unresolved: {failures}", file=sys.stderr)
        print("Not writing partial mapping.", file=sys.stderr)
        return 1

    n_metro = sum(1 for v in out.values() if v["cbsa_type"] == "metro")
    n_micro = sum(1 for v in out.values() if v["cbsa_type"] == "micro")
    n_none = sum(1 for v in out.values() if v["cbsa_type"] == "none")

    payload = {
        "_meta": {
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": "Census Bureau geocoder (Public_AR_Current / Current_Current)",
            "counts": {"metro": n_metro, "micro": n_micro, "outside_cbsa": n_none},
        },
        "centers": out,
    }
    (DATA_DIR / "center-cbsa-map.json").write_text(json.dumps(payload, indent=1) + "\n")
    print(f"\nWrote {len(out)} centers → data/center-cbsa-map.json "
          f"({n_metro} metro, {n_micro} micro, {n_none} outside any CBSA)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
