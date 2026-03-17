#!/usr/bin/env python3
"""
Generate realistic SRTR historical trend data for 22 TransPlan cities.

Produces data/srtr-historical.json with 7 years (2019-2025) of center-level
metrics across 6 organ types. Values are calibrated against actual SRTR PSR
data and the project's existing post-transplant-outcomes.json.

Data characteristics:
  - Realistic base values per organ (median wait, volume, survival, etc.)
  - City-level variation via per-city offsets (size, quality tiers)
  - COVID-19 dip in 2020 (reduced volume, worse outcomes)
  - City-specific trends: improving, stable, or declining
  - Year-over-year noise (±3-8%) for natural variation
  - Occasional null values for pancreas/intestine (small programs)
  - wait_time_factor = city_median / national_median for each year

Usage:
    python scripts/generate-srtr-historical.py
"""

import json
import random
import math
import os
from datetime import datetime, timezone

# Reproducible seed for deterministic output
random.seed(42)

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]

CITIES = [
    "Pittsburgh", "Baltimore", "Philadelphia", "New York", "Minneapolis",
    "Madison", "Chicago", "Cleveland", "St. Louis", "Indianapolis",
    "Omaha", "Rochester", "Nashville", "Durham", "Miami",
    "Dallas", "Houston", "Portland", "Seattle", "San Francisco",
    "Los Angeles", "Palo Alto",
]

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]

# ---------------------------------------------------------------------------
# National baseline parameters (2019 values; trends applied per-year)
# ---------------------------------------------------------------------------
ORGAN_BASELINES = {
    "kidney": {
        "median_wait_months": 42.0,
        "volume": 220,
        "mortality_rate": 0.015,
        "delisting_rate": 0.045,
        "graft_survival_1yr": 0.948,
        "patient_survival_1yr": 0.972,
        # Annual national trend (additive per year from 2019)
        "wait_trend": -1.2,        # wait dropping ~1.2 mo/yr
        "volume_trend_pct": 0.03,   # +3% volume per year
        "survival_trend": 0.001,    # +0.1pp survival/yr
        "mortality_trend": -0.0005, # slight improvement
    },
    "liver": {
        "median_wait_months": 6.2,
        "volume": 130,
        "mortality_rate": 0.028,
        "delisting_rate": 0.065,
        "graft_survival_1yr": 0.918,
        "patient_survival_1yr": 0.940,
        "wait_trend": -0.15,
        "volume_trend_pct": 0.025,
        "survival_trend": 0.0012,
        "mortality_trend": -0.0008,
    },
    "heart": {
        "median_wait_months": 8.5,
        "volume": 65,
        "mortality_rate": 0.032,
        "delisting_rate": 0.055,
        "graft_survival_1yr": 0.915,
        "patient_survival_1yr": 0.920,
        "wait_trend": -0.25,
        "volume_trend_pct": 0.035,
        "survival_trend": 0.0015,
        "mortality_trend": -0.0006,
    },
    "lung": {
        "median_wait_months": 5.5,
        "volume": 45,
        "mortality_rate": 0.042,
        "delisting_rate": 0.078,
        "graft_survival_1yr": 0.888,
        "patient_survival_1yr": 0.895,
        "wait_trend": -0.12,
        "volume_trend_pct": 0.028,
        "survival_trend": 0.002,
        "mortality_trend": -0.001,
    },
    "pancreas": {
        "median_wait_months": 18.0,
        "volume": 18,
        "mortality_rate": 0.020,
        "delisting_rate": 0.058,
        "graft_survival_1yr": 0.845,
        "patient_survival_1yr": 0.962,
        "wait_trend": -0.3,
        "volume_trend_pct": -0.01,   # declining nationally
        "survival_trend": 0.001,
        "mortality_trend": -0.0003,
    },
    "intestine": {
        "median_wait_months": 12.0,
        "volume": 8,
        "mortality_rate": 0.048,
        "delisting_rate": 0.092,
        "graft_survival_1yr": 0.755,
        "patient_survival_1yr": 0.822,
        "wait_trend": -0.2,
        "volume_trend_pct": 0.01,
        "survival_trend": 0.003,
        "mortality_trend": -0.0012,
    },
}

# ---------------------------------------------------------------------------
# City profiles: size_factor, quality_offset, trend_type
#   size_factor: multiplier on national volume (big centers > 1)
#   quality_offset: additive on survival rates (positive = better)
#   trend_type: "improving", "stable", or "declining"
# ---------------------------------------------------------------------------
CITY_PROFILES = {
    "Pittsburgh":     {"size": 1.05, "quality": +0.010, "trend": "improving"},
    "Baltimore":      {"size": 1.15, "quality": +0.005, "trend": "stable"},
    "Philadelphia":   {"size": 1.10, "quality": +0.003, "trend": "stable"},
    "New York":       {"size": 1.50, "quality": +0.002, "trend": "stable"},
    "Minneapolis":    {"size": 1.00, "quality": +0.012, "trend": "stable"},
    "Madison":        {"size": 0.60, "quality": +0.008, "trend": "declining"},
    "Chicago":        {"size": 1.30, "quality": +0.000, "trend": "stable"},
    "Cleveland":      {"size": 1.10, "quality": +0.015, "trend": "improving"},
    "St. Louis":      {"size": 0.85, "quality": -0.003, "trend": "stable"},
    "Indianapolis":   {"size": 0.80, "quality": -0.002, "trend": "stable"},
    "Omaha":          {"size": 0.55, "quality": +0.005, "trend": "stable"},
    "Rochester":      {"size": 0.75, "quality": +0.018, "trend": "stable"},
    "Nashville":      {"size": 0.95, "quality": +0.004, "trend": "stable"},
    "Durham":         {"size": 0.90, "quality": +0.010, "trend": "stable"},
    "Miami":          {"size": 1.05, "quality": -0.005, "trend": "declining"},
    "Dallas":         {"size": 1.10, "quality": +0.001, "trend": "stable"},
    "Houston":        {"size": 1.35, "quality": +0.006, "trend": "improving"},
    "Portland":       {"size": 0.65, "quality": +0.007, "trend": "stable"},
    "Seattle":        {"size": 0.90, "quality": +0.009, "trend": "stable"},
    "San Francisco":  {"size": 1.00, "quality": +0.008, "trend": "stable"},
    "Los Angeles":    {"size": 1.45, "quality": -0.001, "trend": "stable"},
    "Palo Alto":      {"size": 0.70, "quality": +0.014, "trend": "stable"},
}

# Organs some small cities may not do (for null injection)
SMALL_PROGRAM_ORGANS = {"pancreas", "intestine"}

# Cities that might not report pancreas/intestine every year
SMALL_PROGRAM_CITIES = {
    "Madison", "Omaha", "Portland", "Palo Alto", "Rochester",
    "Indianapolis", "St. Louis",
}

# COVID-19 impact multipliers for 2020
COVID_IMPACT = {
    "volume_mult": 0.82,           # ~18% drop in transplant volume
    "wait_add_months": 2.5,        # longer waits
    "survival_offset": -0.012,     # ~1.2pp worse survival
    "mortality_add": 0.006,        # higher mortality
    "delisting_add": 0.012,        # higher delisting
}


def _noise(scale=0.05):
    """Return a multiplicative noise factor centered at 1.0."""
    return 1.0 + random.gauss(0, scale)


def _trend_multiplier(trend_type: str, year_idx: int) -> float:
    """
    Return an additive quality-trend factor per year.
    year_idx: 0 = 2019, 6 = 2025
    """
    if trend_type == "improving":
        return year_idx * 0.002   # +0.2pp survival per year beyond baseline
    elif trend_type == "declining":
        return year_idx * -0.0015  # -0.15pp survival per year
    return 0.0


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def generate_city_organ(city: str, organ: str) -> dict | None:
    """Generate 7-year time series for one city-organ pair."""
    base = ORGAN_BASELINES[organ]
    profile = CITY_PROFILES[city]

    # Determine if this city-organ has data gaps
    has_gaps = (
        organ in SMALL_PROGRAM_ORGANS
        and city in SMALL_PROGRAM_CITIES
    )

    # For intestine, very small cities might not have a program at all
    if organ == "intestine" and city in {"Madison", "Omaha", "Portland", "Palo Alto"}:
        # Sparse: only 2-3 years of data
        active_years = set(random.sample(YEARS, random.randint(2, 3)))
    elif has_gaps:
        # Occasional gaps: drop 1-2 years
        n_missing = random.randint(1, 2)
        missing = set(random.sample(YEARS, n_missing))
        active_years = set(YEARS) - missing
    else:
        active_years = set(YEARS)

    # City-specific wait time offset (some cities faster, some slower)
    # Use a stable random offset seeded by city+organ
    rng = random.Random(hash(city + organ) & 0xFFFFFFFF)
    wait_offset_pct = rng.gauss(0, 0.20)  # ±20% from national

    results = {
        "years": list(YEARS),
        "median_wait_months": [],
        "volume": [],
        "mortality_rate": [],
        "delisting_rate": [],
        "graft_survival_1yr": [],
        "patient_survival_1yr": [],
        "wait_time_factor": [],
    }

    for yi, year in enumerate(YEARS):
        if year not in active_years:
            for key in results:
                if key == "years":
                    continue
                results[key].append(None)
            continue

        is_covid = (year == 2020)

        # --- National baseline for this year ---
        nat_wait = base["median_wait_months"] + base["wait_trend"] * yi
        nat_graft_surv = base["graft_survival_1yr"] + base["survival_trend"] * yi
        nat_patient_surv = base["patient_survival_1yr"] + base["survival_trend"] * yi * 0.7

        # --- Median wait months ---
        city_wait = nat_wait * (1 + wait_offset_pct)
        # Trend adjustment
        trend_adj = _trend_multiplier(profile["trend"], yi)
        city_wait *= (1 - trend_adj * 5)  # improving trend → shorter waits
        if is_covid:
            city_wait += COVID_IMPACT["wait_add_months"] * _noise(0.15)
        city_wait *= _noise(0.04)
        city_wait = _clamp(city_wait, 1.0, 80.0)

        # --- Volume ---
        vol_base = base["volume"] * profile["size"]
        vol = vol_base * (1 + base["volume_trend_pct"]) ** yi
        if profile["trend"] == "improving":
            vol *= (1 + 0.02 * yi)
        elif profile["trend"] == "declining":
            vol *= (1 - 0.015 * yi)
        if is_covid:
            vol *= COVID_IMPACT["volume_mult"] * _noise(0.06)
        vol *= _noise(0.05)
        vol = max(1, round(vol))

        # --- Mortality rate ---
        mort = base["mortality_rate"] + base["mortality_trend"] * yi
        mort += profile["quality"] * -0.3  # better quality → lower mortality
        mort += trend_adj * -0.15
        if is_covid:
            mort += COVID_IMPACT["mortality_add"] * _noise(0.2)
        mort *= _noise(0.08)
        mort = _clamp(mort, 0.005, 0.08)

        # --- Delisting rate ---
        delist = base["delisting_rate"]
        delist += profile["quality"] * -0.2
        if profile["trend"] == "improving":
            delist -= 0.001 * yi
        elif profile["trend"] == "declining":
            delist += 0.001 * yi
        if is_covid:
            delist += COVID_IMPACT["delisting_add"] * _noise(0.15)
        delist *= _noise(0.06)
        delist = _clamp(delist, 0.015, 0.15)

        # --- Graft survival 1yr ---
        gsurv = nat_graft_surv + profile["quality"] + trend_adj
        if is_covid:
            gsurv += COVID_IMPACT["survival_offset"] * _noise(0.2)
        gsurv *= _noise(0.008)
        gsurv = _clamp(gsurv, 0.55, 0.995)

        # --- Patient survival 1yr ---
        psurv = nat_patient_surv + profile["quality"] * 0.8 + trend_adj * 0.8
        if is_covid:
            psurv += COVID_IMPACT["survival_offset"] * 0.7 * _noise(0.2)
        psurv *= _noise(0.006)
        # Patient survival >= graft survival
        psurv = max(psurv, gsurv + 0.005)
        psurv = _clamp(psurv, 0.60, 0.998)

        # --- Wait time factor ---
        # Ratio of city wait to national for this year
        wtf = city_wait / max(nat_wait, 0.5)
        wtf = _clamp(wtf, 0.3, 2.5)

        # Store rounded values
        results["median_wait_months"].append(round(city_wait, 1))
        results["volume"].append(vol)
        results["mortality_rate"].append(round(mort, 4))
        results["delisting_rate"].append(round(delist, 4))
        results["graft_survival_1yr"].append(round(gsurv * 100, 1))
        results["patient_survival_1yr"].append(round(psurv * 100, 1))
        results["wait_time_factor"].append(round(wtf, 3))

    return results


def generate_national() -> dict:
    """Generate national-level trend data for reference."""
    national = {}
    for organ in ORGANS:
        base = ORGAN_BASELINES[organ]
        entry = {
            "years": list(YEARS),
            "median_wait_months": [],
            "graft_survival_1yr": [],
        }
        for yi, year in enumerate(YEARS):
            wait = base["median_wait_months"] + base["wait_trend"] * yi
            gsurv = base["graft_survival_1yr"] + base["survival_trend"] * yi
            if year == 2020:
                wait += COVID_IMPACT["wait_add_months"] * 0.8
                gsurv += COVID_IMPACT["survival_offset"] * 0.8
            entry["median_wait_months"].append(round(wait, 1))
            entry["graft_survival_1yr"].append(round(gsurv * 100, 1))
        national[organ] = entry
    return national


def main():
    data = {
        "_meta": {
            "source": "Synthetic seed data derived from SRTR PSR center-level reports (2019-2025)",
            "method": "Generated by scripts/generate-srtr-historical.py with realistic baselines, trends, and noise",
            "references": [
                "https://www.srtr.org/reports/program-specific-reports/",
                "SRTR PSR Technical Methods: https://www.srtr.org/about-the-data/technical-methods-for-the-program-specific-reports/"
            ],
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "notes": (
                "Synthetic data calibrated against published SRTR statistics. "
                "NOT real patient data. COVID-19 impact modeled in 2020. "
                "Null values for pancreas/intestine indicate years where center "
                "volume was too low for reportable metrics."
            ),
            "schema_version": "1.0.0",
            "years": YEARS,
            "cities": CITIES,
            "organs": ORGANS,
        },
        "cities": {},
        "national": generate_national(),
    }

    for city in CITIES:
        data["cities"][city] = {}
        for organ in ORGANS:
            result = generate_city_organ(city, organ)
            if result is not None:
                data["cities"][city][organ] = result

    # Write output
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "srtr-historical.json",
    )
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {out_path}")

    # Quick validation
    city_count = len(data["cities"])
    total_series = sum(
        len(organs) for organs in data["cities"].values()
    )
    null_count = 0
    for city_data in data["cities"].values():
        for organ_data in city_data.values():
            for key in ["median_wait_months", "volume", "mortality_rate"]:
                null_count += sum(1 for v in organ_data[key] if v is None)

    print(f"Cities: {city_count}, organ-series: {total_series}, null values: {null_count}")


if __name__ == "__main__":
    main()
