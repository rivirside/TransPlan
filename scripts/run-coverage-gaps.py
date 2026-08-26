#!/usr/bin/env python3
"""What share of the US population lives within reach of a transplant center? (#113)

This is the access question the platform could not answer, because the
repository held no population data at any geography until #336 added county
population. With a county population and a county centroid, the statistic is
a straightforward population-weighted distance computation.

WHAT THIS IS NOT
----------------
Distance here is **great-circle**, not drive time. That understates the real
burden everywhere and understates it unevenly: a mountain or coastal county
can sit 60 straight-line miles from a center and three hours by road, while a
county on an interstate corridor is close to its straight-line figure. Any
number below is therefore an OPTIMISTIC bound on access.

The honest fix is a road-network matrix (#323), which needs a self-hosted OSRM
build. Until that lands, this file reports the bound and says so. It is
deliberately written so the distance function is the only thing that changes:
swap `haversine_miles` for a drive-time lookup and every statistic here
becomes a drive-time statistic.

The county centroid is also a simplification — everyone in a county is placed
at its centroid, which flatters large rural counties whose population often
clusters in one town, and barely matters for small dense ones.

Outputs: docs/coverage-gaps-report.md,
         docs-site/static/data/coverage-gaps.json
"""
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from artifact_meta import stamped_meta  # noqa: E402

from services.data_loader import get_data, load_all  # noqa: E402

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
# Straight-line mile bands. 250 nm (~288 mi) is the current UNOS allocation
# circle for several organs, so it is included as the policy-relevant band.
BANDS = [50, 100, 150, 250, 288, 500]
EARTH_RADIUS_MI = 3959.0


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    return EARTH_RADIUS_MI * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_counties() -> dict:
    """{fips: {name, state, population, lat, lon}} for counties with both."""
    pop_doc = json.loads((REPO / "data" / "county-population.json").read_text())
    centroid_doc = json.loads(
        (REPO / "data" / "health-demographics-counties.json").read_text())
    centroids = centroid_doc.get("counties", {})

    out = {}
    for fips, rec in pop_doc.get("counties", {}).items():
        c = centroids.get(fips)
        if not c or c.get("lat") is None or c.get("lon") is None:
            continue
        out[fips] = {
            "name": rec.get("name"),
            "state": rec.get("state"),
            "population": rec["population"],
            "lat": c["lat"],
            "lon": c["lon"],
        }
    return out


def centers_for(organ: str) -> list[tuple[float, float]]:
    coords = []
    for c in get_data().centers_for_organ(organ):
        lat, lon = c.get("lat"), c.get("lon")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            coords.append((lat, lon))
    return coords


def nearest_miles(lat: float, lon: float,
                  centers: list[tuple[float, float]]) -> float | None:
    if not centers:
        return None
    return min(haversine_miles(lat, lon, clat, clon) for clat, clon in centers)


def analyze(organ: str, counties: dict) -> dict | None:
    centers = centers_for(organ)
    if not centers:
        return None

    total_pop = 0
    covered = {b: 0 for b in BANDS}
    per_county = []
    for fips, c in counties.items():
        d = nearest_miles(c["lat"], c["lon"], centers)
        if d is None:
            continue
        total_pop += c["population"]
        for b in BANDS:
            if d <= b:
                covered[b] += c["population"]
        per_county.append((d, c["population"], c["name"], c["state"], fips))

    if not total_pop:
        return None

    # Population-weighted median distance: the distance at which half the
    # population is closer. More informative than a plain county mean, which
    # would let 3,000 tiny counties outvote the population.
    per_county.sort(key=lambda r: r[0])
    running = 0
    median_distance = None
    for d, pop, *_ in per_county:
        running += pop
        if running >= total_pop / 2:
            median_distance = d
            break

    worst = sorted(per_county, key=lambda r: -r[0])[:10]
    return {
        "organ": organ,
        "n_centers": len(centers),
        "n_counties": len(per_county),
        "total_population": total_pop,
        "share_within": {str(b): round(covered[b] / total_pop, 4) for b in BANDS},
        "population_beyond_250mi": total_pop - covered[250],
        "population_weighted_median_miles": round(median_distance or 0.0, 1),
        "farthest_counties": [
            {"fips": f, "county": name, "state": state,
             "miles_to_nearest": round(d, 1), "population": pop}
            for d, pop, name, state, f in worst
        ],
    }


def main() -> int:
    load_all()
    counties = load_counties()
    if len(counties) < 3000:
        print(f"ERROR: only {len(counties)} counties have both population and "
              f"a centroid — refusing to report a national statistic",
              file=sys.stderr)
        return 1
    print(f"{len(counties)} counties with population + centroid")

    result = {"organs": {}, "_meta": stamped_meta(
        script="scripts/run-coverage-gaps.py",
        distance_metric="great-circle (haversine) miles, county centroid to "
                        "nearest transplant center",
        caveat="Straight-line distance UNDERSTATES real travel burden, and does "
               "so unevenly by terrain and road network. Every share below is "
               "an optimistic bound. Drive-time replacement is tracked as #323.",
        population_source="data/county-population.json (US Census, vintage 2024)",
        centroid_source="data/health-demographics-counties.json",
    )}

    lines = ["# Population coverage of transplant centers (#113)", "",
             "Share of the US population living within a given straight-line",
             "distance of a center performing each organ.", "",
             "| organ | centers | within 50mi | 100mi | 250mi | 288mi (250nm) | "
             "pop-weighted median | population beyond 250mi |",
             "|---|---|---|---|---|---|---|---|"]

    for organ in ORGANS:
        res = analyze(organ, counties)
        if not res:
            continue
        result["organs"][organ] = res
        s = res["share_within"]
        lines.append(
            f"| {organ} | {res['n_centers']} | {s['50']:.1%} | {s['100']:.1%} | "
            f"{s['250']:.1%} | {s['288']:.1%} | "
            f"{res['population_weighted_median_miles']:.0f} mi | "
            f"{res['population_beyond_250mi']:,} |")
        print(f"{organ:10s} centers={res['n_centers']:3d} "
              f"within50={s['50']:.1%} within250={s['250']:.1%} "
              f"median={res['population_weighted_median_miles']:.0f}mi")

    kidney = result["organs"].get("kidney", {})
    lines += ["", "## Reading these numbers", "",
              "**Distance here is great-circle, not drive time.** That is not a",
              "detail. A county 60 straight-line miles from a center across a",
              "mountain range is a three-hour drive; a county the same distance",
              "along an interstate is under an hour. So every share above is an",
              "OPTIMISTIC bound on real access, and it is optimistic *unevenly* —",
              "rural and mountainous populations are flattered most, which is",
              "exactly the population an access analysis most needs to get right.",
              "",
              "Replacing the distance function with a road-network matrix (#323)",
              "turns every statistic here into a drive-time statistic without",
              "changing anything else in this script.", "",
              "**County centroids are a second simplification.** Everyone in a",
              "county is placed at its centroid, which flatters large rural",
              "counties whose population usually clusters in one town.", "",
              "**Alaska and Hawaii break the framing entirely.** Every one of the",
              "ten farthest counties is in Alaska, whose nearest program is in",
              "Seattle. For those populations the straight-line figure is not an",
              "optimistic bound on a drive — there is no drive. Access is a",
              "flight, and the relevant burden is cost and scheduling rather than",
              "road distance. A drive-time matrix will not fix this; it will",
              "report no route at all. These counties need to be described",
              "separately rather than folded into a national distance figure.", "",
              "**Organ coverage differs because program counts differ.** Kidney is",
              "performed at far more centers than intestine, so the intestine",
              "figures describe genuine geographic scarcity rather than a",
              "modelling artifact.", ""]
    if kidney:
        lines += [
            f"For kidney — the most widely performed organ — "
            f"{kidney['share_within']['250']:.1%} of the population lives within "
            f"250 straight-line miles of a program, leaving "
            f"{kidney['population_beyond_250mi']:,} people beyond it even on this "
            f"optimistic measure.", ""]

    (REPO / "docs" / "coverage-gaps-report.md").write_text("\n".join(lines))
    (REPO / "docs-site" / "static" / "data" / "coverage-gaps.json").write_text(
        json.dumps(result, indent=1) + "\n")
    print("\nWrote docs/coverage-gaps-report.md + "
          "docs-site/static/data/coverage-gaps.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
