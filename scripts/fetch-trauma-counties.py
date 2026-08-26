#!/usr/bin/env python3
"""County-level trauma scores for each transplant center (#336).

data/trauma-scores-centers.json gives every center in a state the SAME score,
and names its own refinement path: "county-level FARS + county population".
That was blocked because the repository held no population at any geography
until #336 added it. It is now possible.

Why the state score is too coarse to leave alone: within Texas the county
traffic-fatality rate spans an order of magnitude, so a center in urban Dallas
and one in a rural county currently receive an identical trauma figure even
though the local organ-donor injury pattern differs substantially.

Two things this has to get right, or it is worse than the state score:

1. SMALL-COUNTY NOISE. A county with 4,000 residents and two fatal crashes
   computes to 50 per 100k — four times the worst state. Those are real
   deaths but a meaningless rate. County rates are therefore shrunk toward
   the state rate with an empirical-Bayes weight pop/(pop + K), so a small
   county's score is mostly its state's until it has enough exposure to
   speak for itself.

2. COUNTY ASSIGNMENT. Centers carry lat/lon, not a county FIPS, and no county
   boundary polygons are in the repository — so a center is matched to the
   NEAREST county centroid. That is exact for a center well inside a large
   county and can be wrong near a boundary or in dense small-county regions
   (a Manhattan center may match a neighbouring borough's centroid). The
   distance to the matched centroid is recorded per center so the error is
   visible rather than assumed away, and any center further than
   MAX_MATCH_MILES from every centroid keeps its state score.

Writes data/trauma-scores-counties.json. The existing state-level file is
left untouched, so this is additive: consumers can adopt the finer scores
without a flag day.
"""
import argparse
import collections
import csv
import io
import json
import math
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent
POP_FILE = REPO / "data" / "county-population.json"
CENTROID_FILE = REPO / "data" / "health-demographics-counties.json"
CENTERS_FILE = REPO / "data" / "srtr-all-centers.json"
STATE_FILE = REPO / "data" / "trauma-scores-centers.json"
OUT_FILE = REPO / "data" / "trauma-scores-counties.json"

FARS_URL = ("https://static.nhtsa.gov/nhtsa/downloads/FARS/{year}/National/"
            "FARS{year}NationalCSV.zip")

# Shrinkage constant: a county reaches half its own weight at this population.
# NOTE the median US county is ~26,000 people, NOT 100,000 — so at this
# constant roughly 80% of counties sit below half weight and read mostly as
# their state. That is deliberate for a fatality COUNT denominator (a county
# needs real exposure before its rate is anything but noise), but it does mean
# the county signal is concentrated in populous counties — which is where the
# transplant centers are, and where the resolution was wanted.
SHRINK_POP = 100_000
# Beyond this, "nearest centroid" stops being a plausible county assignment.
MAX_MATCH_MILES = 60.0
# FARS uses these county codes for unknown / not-applicable.
SENTINEL_COUNTIES = {0, 997, 998, 999}
MIN_COUNTIES_WITH_DATA = 2000
EARTH_RADIUS_MI = 3959.0


def haversine_miles(lat1, lon1, lat2, lon2):
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    return EARTH_RADIUS_MI * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_county_fatalities(year: int) -> dict[str, int]:
    url = FARS_URL.format(year=year)
    print(f"Downloading {url} …")
    req = urllib.request.Request(
        url, headers={"User-Agent": "TransPlan-DataPipeline/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        zf = zipfile.ZipFile(io.BytesIO(resp.read()))
    name = next((n for n in zf.namelist()
                 if n.lower().endswith("accident.csv")), None)
    if not name:
        raise SystemExit("accident.csv not found in the FARS archive")

    counts: collections.Counter = collections.Counter()
    with zf.open(name) as fh:
        for row in csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1")):
            try:
                state = int(row["STATE"])
                county = int(row["COUNTY"])
                fatals = int(row.get("FATALS", 0) or 0)
            except (KeyError, ValueError, TypeError):
                continue
            if county in SENTINEL_COUNTIES:
                continue
            counts[f"{state:02d}{county:03d}"] += fatals
    return dict(counts)


def _state_score_on_county_scale(state_rate: float, max_county_rate: float) -> float:
    """Put a state fallback score on the COUNTY scale.

    The state file normalizes so the worst STATE = 100 (max rate 24.93/100k);
    county scores normalize so the worst COUNTY = 100 (max 36.39/100k). Mixing
    the two in one dict put a center in the worst state at 100 on the fallback
    path but 68.5 on the county path for identical underlying risk — a
    31.5-point discontinuity decided purely by whether a centroid happened to
    match. Rescaling the state rate against the county maximum makes every
    score in this file mean the same thing.
    """
    return round(100.0 * state_rate / max_county_rate, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023)
    args = ap.parse_args()

    population = json.loads(POP_FILE.read_text())["counties"]
    centroids = json.loads(CENTROID_FILE.read_text())["counties"]
    centers = json.loads(CENTERS_FILE.read_text())["centers"]
    state_doc = json.loads(STATE_FILE.read_text())
    state_rates = state_doc["state_fatality_rates_per_100k"]
    state_scores = state_doc["state_scores"]

    fatalities = fetch_county_fatalities(args.year)
    print(f"{len(fatalities)} counties with recorded fatalities")
    if len(fatalities) < MIN_COUNTIES_WITH_DATA:
        print(f"ERROR: only {len(fatalities)} counties (floor "
              f"{MIN_COUNTIES_WITH_DATA}) — FARS schema change?", file=sys.stderr)
        return 1

    # ── county rates, shrunk toward the state rate ──────────────────────────
    county_rate = {}
    for fips, rec in population.items():
        pop = rec.get("population") or 0
        if pop <= 0:
            continue
        state_abbr = None
        c = centroids.get(fips)
        if c:
            state_abbr = c.get("state")
        prior = state_rates.get(state_abbr)
        if prior is None:
            continue
        raw = fatalities.get(fips, 0) / pop * 100_000
        w = pop / (pop + SHRINK_POP)
        county_rate[fips] = {
            "raw_rate_per_100k": round(raw, 2),
            "shrunk_rate_per_100k": round(w * raw + (1 - w) * prior, 2),
            "weight_on_own_data": round(w, 3),
            "fatalities": fatalities.get(fips, 0),
            "population": pop,
            "state": state_abbr,
        }

    if not county_rate:
        print("ERROR: no county rates computed", file=sys.stderr)
        return 1

    # Normalize so the worst COUNTY = 100.
    max_county_rate = max(r["shrunk_rate_per_100k"] for r in county_rate.values())
    for rec in county_rate.values():
        rec["score"] = round(100.0 * rec["shrunk_rate_per_100k"] / max_county_rate, 1)

    # ── assign each center its nearest county centroid ──────────────────────
    centroid_list = [(f, c["lat"], c["lon"]) for f, c in centroids.items()
                     if c.get("lat") is not None and c.get("lon") is not None]
    center_scores = {}
    fallbacks = 0
    unscorable = []
    match_distances = []
    for code, c in centers.items():
        lat, lon = c.get("lat"), c.get("lon")
        abbr = c.get("state_abbr")
        if lat is None or lon is None:
            if abbr in state_scores:
                center_scores[code] = {"score": state_scores[abbr],
                                       "resolution": "state",
                                       "reason": "center has no coordinates"}
                fallbacks += 1
            else:
                # Neither coordinates nor a state rate. Record it: silently
                # continuing meant the output held 246 of 248 centers with
                # nothing anywhere saying two were discarded (Puerto Rico has
                # no FARS state rate and no county centroids).
                unscorable.append({"code": code, "state_abbr": abbr,
                                   "reason": "no coordinates and no state rate"})
            continue
        best_fips, best_d = None, float("inf")
        for fips, clat, clon in centroid_list:
            d = haversine_miles(lat, lon, clat, clon)
            if d < best_d:
                best_fips, best_d = fips, d
        rec = county_rate.get(best_fips)
        if rec is None or best_d > MAX_MATCH_MILES:
            if abbr in state_scores:
                center_scores[code] = {
                    "score": _state_score_on_county_scale(
                        state_rates[abbr], max_county_rate),
                    "resolution": "state",
                    "reason": (f"nearest county centroid {best_d:.0f} mi away"
                               if best_fips else "no county centroid nearby")}
                fallbacks += 1
            else:
                unscorable.append({
                    "code": code, "state_abbr": abbr,
                    "reason": (f"nearest county centroid {best_d:.0f} mi away "
                               f"and no state rate for {abbr}")})
            continue
        match_distances.append(best_d)
        center_scores[code] = {
            "score": rec["score"],
            "resolution": "county",
            "county_fips": best_fips,
            "county": (centroids.get(best_fips) or {}).get("name"),
            "match_distance_miles": round(best_d, 1),
            "weight_on_own_data": rec["weight_on_own_data"],
        }

    county_res = sum(1 for v in center_scores.values()
                     if v["resolution"] == "county")
    median_match = (sorted(match_distances)[len(match_distances) // 2]
                    if match_distances else None)
    print(f"{county_res} centers at county resolution, {fallbacks} on the "
          f"state fallback; median centroid match {median_match:.1f} mi"
          if median_match is not None else
          f"{county_res} county / {fallbacks} state")

    # Never-shrink guard.
    if OUT_FILE.exists():
        try:
            prev = json.loads(OUT_FILE.read_text())
            prev_n = len(prev.get("center_scores", {}))
            if len(center_scores) < prev_n:
                print(f"ERROR: {len(center_scores)} centers vs {prev_n} "
                      f"previously — never-shrink guard", file=sys.stderr)
                return 1
        except json.JSONDecodeError:
            pass

    out = {
        "_meta": {
            "source": f"NHTSA FARS {args.year} national accident CSV "
                      f"(county-level) + US Census county population",
            "script": "scripts/fetch-trauma-counties.py",
            "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "method": (
                f"County traffic-fatality rate per 100k, shrunk toward the "
                f"state rate with weight pop/(pop+{SHRINK_POP:,}) so small "
                f"counties are not dominated by noise, then normalized so the "
                f"highest county = 100 (same semantics as the state file). "
                f"Centers are matched to the nearest county centroid; a center "
                f"further than {MAX_MATCH_MILES:.0f} mi from any centroid "
                f"keeps its state score."),
            "limitations": (
                "Nearest-centroid matching has no county boundaries behind it, "
                "so a center near a county line may be attributed to its "
                "neighbour. match_distance_miles is recorded per center so "
                "that error is visible."),
            "counties_scored": len(county_rate),
            "centers_county_resolution": county_res,
            "centers_state_fallback": fallbacks,
            "centers_unscorable": unscorable,
            "median_match_distance_miles": (round(median_match, 1)
                                            if median_match is not None else None),
        },
        "county_scores": {f: {"score": r["score"],
                              "shrunk_rate_per_100k": r["shrunk_rate_per_100k"],
                              "raw_rate_per_100k": r["raw_rate_per_100k"],
                              "fatalities": r["fatalities"],
                              "population": r["population"]}
                          for f, r in county_rate.items()},
        "center_scores": center_scores,
    }
    OUT_FILE.write_text(json.dumps(out, indent=1) + "\n")
    print(f"Wrote {OUT_FILE.relative_to(REPO)} — {len(county_rate)} counties, "
          f"{len(center_scores)} centers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
