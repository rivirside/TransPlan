#!/usr/bin/env python3
"""
Geocode all SRTR transplant centers to add lat/lon coordinates.

Reads data/srtr-all-centers.json and geocodes each center using its hospital
name + state. Uses Nominatim (free, no API key) with rate limiting.

Updates data/srtr-all-centers.json in-place with lat/lon fields.
Also adds coordinates to the 22 focus cities in scripts/utils.js city list.

Phase 6A issue #116.
"""

import json
import math
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
CENTERS_PATH = os.path.join(DATA_DIR, "srtr-all-centers.json")

# Known coordinates for the 22 TransPlan focus cities (from traffic-fatalities.json)
CITY_COORDS = {
    "Pittsburgh": (40.4406, -79.9959),
    "Baltimore": (39.2904, -76.6122),
    "Philadelphia": (39.9526, -75.1652),
    "New York": (40.7128, -74.0060),
    "Minneapolis": (44.9778, -93.2650),
    "Madison": (43.0731, -89.4012),
    "Chicago": (41.8781, -87.6298),
    "Cleveland": (41.4993, -81.6944),
    "St. Louis": (38.6270, -90.1994),
    "Indianapolis": (39.7684, -86.1581),
    "Omaha": (41.2565, -95.9345),
    "Rochester": (44.0121, -92.4802),
    "Nashville": (36.1627, -86.7816),
    "Durham": (35.9940, -78.8986),
    "Miami": (25.7617, -80.1918),
    "Dallas": (32.7767, -96.7970),
    "Houston": (29.7604, -95.3698),
    "Portland": (45.5152, -122.6784),
    "Seattle": (47.6062, -122.3321),
    "San Francisco": (37.7749, -122.4194),
    "Los Angeles": (33.9425, -118.4081),
    "Palo Alto": (37.4419, -122.1430),
}

# Map SRTR center codes → their 22-city assignment (from srtr-center-mapping.json)
# This lets us assign city coordinates as a starting point for mapped centers
CENTER_TO_CITY = {}


def load_center_mapping():
    """Load center-to-city mapping for the 22 focus cities."""
    mapping_path = os.path.join(DATA_DIR, "srtr-center-mapping.json")
    try:
        with open(mapping_path) as f:
            data = json.load(f)
        for city, info in data["cities"].items():
            CENTER_TO_CITY[info["primary"]] = city
            for alt in info.get("alternates", []):
                CENTER_TO_CITY[alt] = city
    except FileNotFoundError:
        pass


def geocode_with_nominatim(query: str) -> tuple[float, float] | None:
    """Geocode a single query using Nominatim. Returns (lat, lon) or None."""
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderServiceError

        geolocator = Nominatim(user_agent="transplan-geocoder/1.0")
        time.sleep(1.1)  # Nominatim requires 1 request per second
        location = geolocator.geocode(query, country_codes="us", timeout=10)
        if location:
            return (round(location.latitude, 4), round(location.longitude, 4))
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"    Geocoder error for '{query}': {e}")
    except Exception as e:
        print(f"    Unexpected error for '{query}': {e}")
    return None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute haversine distance in miles between two points."""
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def main():
    load_center_mapping()

    with open(CENTERS_PATH) as f:
        data = json.load(f)

    centers = data["centers"]
    total = len(centers)
    geocoded = 0
    from_city = 0
    from_nominatim = 0
    failed = []

    print(f"=== Geocoding {total} SRTR Centers ===\n")

    for code, center in centers.items():
        # Skip if already has coordinates
        if center.get("lat") is not None and center.get("lon") is not None:
            geocoded += 1
            continue

        # Strategy 1: Use known city coordinates for mapped centers
        if code in CENTER_TO_CITY:
            city = CENTER_TO_CITY[code]
            if city in CITY_COORDS:
                lat, lon = CITY_COORDS[city]
                center["lat"] = lat
                center["lon"] = lon
                center["geocode_source"] = "city_mapping"
                geocoded += 1
                from_city += 1
                continue

        # Strategy 2: Geocode using hospital name + state
        name = center.get("name", "")
        state = center.get("state", "")
        query = f"{name}, {state}, USA"

        coords = geocode_with_nominatim(query)
        if coords:
            center["lat"] = coords[0]
            center["lon"] = coords[1]
            center["geocode_source"] = "nominatim"
            geocoded += 1
            from_nominatim += 1
            print(f"  [{geocoded}/{total}] {code}: {name} → ({coords[0]}, {coords[1]})")
        else:
            # Fallback: try just the state capital area
            state_query = f"{name}, {center.get('state_abbr', '')}, USA"
            coords = geocode_with_nominatim(state_query)
            if coords:
                center["lat"] = coords[0]
                center["lon"] = coords[1]
                center["geocode_source"] = "nominatim_fallback"
                geocoded += 1
                from_nominatim += 1
                print(f"  [{geocoded}/{total}] {code}: {name} (fallback) → ({coords[0]}, {coords[1]})")
            else:
                failed.append(code)
                print(f"  [{geocoded}/{total}] {code}: FAILED — {name}")

    # Update metadata
    data["_meta"]["geocodedCount"] = geocoded
    data["_meta"]["geocodeFailures"] = len(failed)
    if failed:
        data["_meta"]["failedCenters"] = failed

    # Write back
    with open(CENTERS_PATH, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"\n=== Geocoding Complete ===")
    print(f"  Total: {total}")
    print(f"  Geocoded: {geocoded} ({geocoded/total*100:.0f}%)")
    print(f"    From city mapping: {from_city}")
    print(f"    From Nominatim: {from_nominatim}")
    print(f"  Failed: {len(failed)}")
    if failed:
        print(f"  Failed codes: {failed}")


if __name__ == "__main__":
    main()
