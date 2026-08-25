#!/usr/bin/env python3
"""
Generate per-center historical trend series (#288, epic #285).

Replaces the 22-city srtr-historical.json trend basis: builds
data/srtr-trends-centers.json with per-center, per-organ time series across
all 15 archived SRTR releases (2018-2025):

  - median_wait_months  : Table B10 TTT_50_C per release (era-proof parse of
                          data/srtr-archive/*.zip, same helpers as
                          run-temporal-forecast.py)
  - mortality_rate      : observed 1-yr waitlist death rate (fraction), from
                          data/srtr-observed-rates-historical.json
  - delisting_rate      : observed 1-yr delisting rate (fraction)
  - volume              : cohort n (SAL_N_C)

Series shape matches srtr-historical.json city blocks so services/trends.py
regression machinery applies unchanged.

Never-shrink guard: refuses to overwrite an existing file with fewer centers
or fewer organs (2026-08-05 incident rule).

Usage:
    cd TransPlan && .venv/bin/python scripts/generate-center-trends.py
"""
import importlib.util
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import xlrd

REPO_ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = REPO_ROOT / "data" / "srtr-archive"
HIST_PATH = REPO_ROOT / "data" / "srtr-observed-rates-historical.json"
OUT_PATH = REPO_ROOT / "data" / "srtr-trends-centers.json"

# Reuse the era-proof B10 helpers from the forecast script
_spec = importlib.util.spec_from_file_location(
    "temporal_forecast", REPO_ROOT / "scripts" / "run-temporal-forecast.py")
tf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tf)

ORGANS = tf.ORGANS  # {"kidney": "KI", ...}


def release_year(code: str) -> int:
    return 2000 + int(code[:2])


def parse_release_waits(zip_path: Path) -> dict:
    """{organ: {center: median_wait_months}} from a release zip's Table B10."""
    zf = zipfile.ZipFile(zip_path)
    members = {}
    for name in zf.namelist():
        m = re.search(r"_(KI|LI|HR|LU|PA|IN)\.xls$", name, re.I)
        if m and not name.endswith("/"):
            members[m.group(1).upper()] = name

    out = {}
    for organ, oc in ORGANS.items():
        if oc not in members:
            continue
        wb = xlrd.open_workbook(file_contents=zf.read(members[oc]))
        sheet, hdr = tf._find_sheet_with(wb, "TTT_50_C")
        if sheet is None:
            continue
        rows = tf._all_rows(sheet, hdr, {"p50": "TTT_50_C"})
        organ_out = {}
        for code, rec in rows.items():
            v = rec.get("p50")
            if tf._is_valid(v):
                organ_out[code] = round(v, 1)
        if organ_out:
            out[organ] = organ_out
    return out


def main():
    hist = json.loads(HIST_PATH.read_text())
    zips = sorted(ARCHIVE_DIR.glob("csrs_final_tables_*all.zip"))
    codes = [re.search(r"_(\d{4})all", z.name).group(1) for z in zips]

    waits_by_release = {}
    for z, code in zip(zips, codes):
        print(f"  parsing B10 medians from {code} ...")
        waits_by_release[code] = parse_release_waits(z)

    centers: dict[str, dict] = {}
    for code in codes:
        year = release_year(code)
        organs_block = hist["releases"].get(code, {}).get("organs", {})
        for organ in ORGANS:
            obs = organs_block.get(organ, {}).get("centers", {})
            waits = waits_by_release.get(code, {}).get(organ, {})
            for ctr in set(obs) | set(waits):
                series = (centers.setdefault(ctr, {})
                          .setdefault(organ, {"years": [], "median_wait_months": [],
                                              "mortality_rate": [], "delisting_rate": [],
                                              "volume": []}))
                rec = obs.get(ctr, {})
                series["years"].append(year)
                series["median_wait_months"].append(waits.get(ctr))
                mort = rec.get("waitlist_death_rate")
                delist = rec.get("delisting_rate")
                series["mortality_rate"].append(round(mort / 100.0, 4) if mort is not None else None)
                series["delisting_rate"].append(round(delist / 100.0, 4) if delist is not None else None)
                series["volume"].append(rec.get("n"))

    out = {
        "_meta": {
            "source": "SRTR PSR historical archive (Table B10 medians) + srtr-observed-rates-historical.json (B7 rates)",
            "script": "scripts/generate-center-trends.py",
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "releases": codes,
            "units": {"median_wait_months": "months", "mortality_rate": "fraction/yr-cohort",
                      "delisting_rate": "fraction/yr-cohort", "volume": "SAL_N_C cohort size"},
            "note": ("Two releases per year share the release year; the trends "
                     "regression treats them as repeated annual observations, "
                     "matching srtr-historical.json city-series semantics."),
        },
        "centers": centers,
    }

    # Never-shrink guard (2026-08-05 incident rule)
    if OUT_PATH.exists():
        old = json.loads(OUT_PATH.read_text())
        old_centers = len(old.get("centers", {}))
        old_points = sum(len(o.get("years", [])) for c in old.get("centers", {}).values()
                         for o in c.values())
        new_points = sum(len(o.get("years", [])) for c in centers.values() for o in c.values())
        if len(centers) < old_centers or new_points < old_points:
            raise SystemExit(
                f"NEVER-SHRINK GUARD: refusing to write {len(centers)} centers/"
                f"{new_points} points over existing {old_centers}/{old_points}."
            )

    OUT_PATH.write_text(json.dumps(out, indent=1))
    n_organs = sum(1 for c in centers.values() for _ in c)
    print(f"Wrote {OUT_PATH}: {len(centers)} centers, {n_organs} center-organ series, "
          f"{len(codes)} releases")


if __name__ == "__main__":
    main()
