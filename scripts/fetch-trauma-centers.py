#!/usr/bin/env python3
"""
Per-center trauma scores from NHTSA FARS (#290, epic #285).

Replaces the 22-city traumaScores in data/traffic-fatalities.json with a
per-center derivation covering all states:

  1. Download the FARS national accident CSV (public bulk file).
  2. Per-state fatality counts / 2023 Census state population → rate per 100k.
  3. Trauma score = 100 × rate / max_rate (same normalization semantics as the
     legacy city scores: higher = more traffic trauma in the center's state).
  4. Each SRTR center gets its state's score.

State-level is an explicit v1 resolution choice (county-level needs county
population joins; tracked in the output metadata as the refinement path).

Output: data/trauma-scores-centers.json. Never-shrink guard.

Usage:
    cd TransPlan && .venv/bin/python scripts/fetch-trauma-centers.py [--year 2023]
"""
import argparse
import csv
import io
import json
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CENTERS_PATH = REPO_ROOT / "data" / "srtr-all-centers.json"
OUT_PATH = REPO_ROOT / "data" / "trauma-scores-centers.json"

FARS_URL = "https://static.nhtsa.gov/nhtsa/downloads/FARS/{year}/National/FARS{year}NationalCSV.zip"

# US Census Bureau state population estimates — single shared source (#339).
STATE_POP_2023 = {
    k: int(v) for k, v in json.loads(
        (REPO_ROOT / "data" / "manual" / "state-populations.json").read_text()
    )["populations"].items()
}

STATE_NAME_TO_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN",
    "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "Puerto Rico": "PR",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2023)
    args = parser.parse_args()

    url = FARS_URL.format(year=args.year)
    print(f"Downloading {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "TransPlan-DataPipeline/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        zbytes = resp.read()
    zf = zipfile.ZipFile(io.BytesIO(zbytes))
    acc_name = next((n for n in zf.namelist() if n.lower().endswith("accident.csv")), None)
    if not acc_name:
        raise SystemExit(f"accident.csv not found in {sorted(zf.namelist())[:10]}")

    fatals = Counter()
    with zf.open(acc_name) as fh:
        reader = csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"))
        for row in reader:
            state = row.get("STATENAME", "").strip()
            abbr = STATE_NAME_TO_ABBR.get(state)
            if not abbr:
                continue
            try:
                fatals[abbr] += int(row.get("FATALS", 0) or 0)
            except ValueError:
                continue
    print(f"Parsed fatalities for {len(fatals)} states "
          f"(total {sum(fatals.values())})")
    if len(fatals) < 45:
        raise SystemExit(f"COVERAGE GATE: only {len(fatals)} states parsed — schema change?")

    rates = {
        abbr: round(fatals[abbr] / STATE_POP_2023[abbr] * 100000, 2)
        for abbr in fatals if abbr in STATE_POP_2023
    }
    max_rate = max(rates.values())
    state_scores = {abbr: round(100.0 * r / max_rate, 1) for abbr, r in rates.items()}

    all_centers = json.loads(CENTERS_PATH.read_text())["centers"]
    center_scores = {}
    for code, c in all_centers.items():
        abbr = c.get("state_abbr")
        if abbr in state_scores:
            center_scores[code] = state_scores[abbr]

    out = {
        "_meta": {
            "source": f"NHTSA FARS {args.year} national accident CSV + US Census Vintage 2023 state population",
            "script": "scripts/fetch-trauma-centers.py",
            "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "method": (
                "State traffic-fatality rate per 100k, normalized so the "
                "highest-rate state = 100 (same semantics as the legacy 22-city "
                "traumaScores: higher = more traffic trauma). Each center gets "
                "its state's score. Refinement path: county-level FARS + county "
                "population for metro-level resolution."
            ),
        },
        "state_fatality_rates_per_100k": dict(sorted(rates.items())),
        "state_scores": dict(sorted(state_scores.items())),
        "centers": dict(sorted(center_scores.items())),
    }

    if OUT_PATH.exists():
        old = json.loads(OUT_PATH.read_text())
        if len(center_scores) < len(old.get("centers", {})):
            raise SystemExit("NEVER-SHRINK GUARD: fewer centers than existing file; not writing.")

    OUT_PATH.write_text(json.dumps(out, indent=1))
    print(f"Wrote {OUT_PATH}: {len(center_scores)} centers, {len(rates)} states")


if __name__ == "__main__":
    main()
