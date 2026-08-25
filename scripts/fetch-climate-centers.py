#!/usr/bin/env python3
"""
Per-center climate recovery scores from NASA POWER climatology (#289, epic #285).

Replaces data/manual/climate-scores.json (22 hand-curated city scores, "no API
exists") with an objective derivation for all 248 SRTR centers:

  1. Fetch NASA POWER climatology (monthly T2M °C, RH2M %) at each center's
     coordinates (keyless public API).
  2. Features: mean monthly deviation from 18 °C comfort temperature, seasonal
     temperature range, annual relative humidity.
  3. Calibrate a least-squares linear map from those features to the EXISTING
     22 hand-curated city scores (fetched at the city coordinates), so the
     scale and semantics ("climate recovery score", higher = milder) are
     preserved — then apply it to every center, clamped to [0, 100].
  4. Report the calibration fit (R², Spearman) so the derivation is auditable;
     refuse to write if Spearman < 0.7 (the formula would not reproduce the
     curated semantics).

Output: data/climate-scores-centers.json {"centers": {code: score}, "_meta"}.
Never-shrink guard per the 2026-08-05 incident rule.

Usage:
    cd TransPlan && .venv/bin/python scripts/fetch-climate-centers.py
"""
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).parent.parent
CENTERS_PATH = REPO_ROOT / "data" / "srtr-all-centers.json"
MANUAL_PATH = REPO_ROOT / "data" / "manual" / "climate-scores.json"
OUT_PATH = REPO_ROOT / "data" / "climate-scores-centers.json"
CACHE_PATH = REPO_ROOT / "data" / "srtr-raw" / "power-climatology-cache.json"

POWER_URL = ("https://power.larc.nasa.gov/api/temporal/climatology/point"
             "?parameters=T2M,RH2M&community=RE&longitude={lon}&latitude={lat}&format=JSON")

COMFORT_C = 18.0  # ~65 °F
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# The 22 legacy city coordinates (scripts/utils.js CITIES) — calibration anchors.
CITY_COORDS = {
    "Pittsburgh": (40.4406, -79.9959), "Baltimore": (39.2904, -76.6122),
    "Philadelphia": (39.9526, -75.1652), "New York": (40.7128, -74.0060),
    "Minneapolis": (44.9778, -93.2650), "Madison": (43.0731, -89.4012),
    "Chicago": (41.8781, -87.6298), "Cleveland": (41.4993, -81.6944),
    "St. Louis": (38.6270, -90.1994), "Indianapolis": (39.7684, -86.1581),
    "Omaha": (41.2565, -95.9345), "Rochester": (44.0121, -92.4802),
    "Nashville": (36.1627, -86.7816), "Durham": (35.9940, -78.8986),
    "Miami": (25.7617, -80.1918), "Dallas": (32.7767, -96.7970),
    "Houston": (29.7604, -95.3698), "Portland": (45.5152, -122.6784),
    "Seattle": (47.6062, -122.3321), "San Francisco": (37.7749, -122.4194),
    "Los Angeles": (33.9425, -118.4081), "Palo Alto": (37.4419, -122.1430),
}


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache))


def fetch_climatology(lat: float, lon: float, cache: dict) -> dict | None:
    """Monthly T2M/RH2M climatology at (lat, lon), disk-cached."""
    key = f"{lat:.4f},{lon:.4f}"
    if key in cache:
        return cache[key]
    url = POWER_URL.format(lat=lat, lon=lon)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TransPlan-DataPipeline/1.0"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode())
            params = data["properties"]["parameter"]
            rec = {"T2M": params["T2M"], "RH2M": params["RH2M"]}
            cache[key] = rec
            time.sleep(0.15)
            return rec
        except Exception as e:
            print(f"    retry {attempt + 1} for {key}: {e}")
            time.sleep(2.0 * (attempt + 1))
    return None


def features(rec: dict) -> tuple[float, float, float] | None:
    t = [rec["T2M"].get(m) for m in MONTHS]
    if any(v is None for v in t):
        return None
    t = np.array(t, dtype=float)
    mean_dev = float(np.mean(np.abs(t - COMFORT_C)))
    t_range = float(np.max(t) - np.min(t))
    rh_ann = float(rec["RH2M"].get("ANN", np.mean([rec["RH2M"].get(m, 70) for m in MONTHS])))
    return mean_dev, t_range, rh_ann


def main():
    manual = {k: v for k, v in json.loads(MANUAL_PATH.read_text()).items()
              if not k.startswith("_")}
    all_centers = json.loads(CENTERS_PATH.read_text())["centers"]
    cache = _load_cache()

    # 1. Calibration anchors: features at the 22 city coordinates
    X, y, names = [], [], []
    print("Fetching climatology for 22 calibration cities ...")
    for city, (lat, lon) in CITY_COORDS.items():
        if city not in manual:
            continue
        rec = fetch_climatology(lat, lon, cache)
        if rec is None:
            continue
        f = features(rec)
        if f is None:
            continue
        X.append(f)
        y.append(manual[city])
        names.append(city)
    _save_cache(cache)

    X = np.array(X)
    y = np.array(y, dtype=float)
    A = np.column_stack([np.ones(len(X)), X])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred22 = A @ coef
    ss_res = float(np.sum((y - pred22) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot
    rho = float(stats.spearmanr(pred22, y)[0])
    print(f"Calibration on {len(y)} cities: R²={r2:.3f}, Spearman={rho:.3f}")
    print(f"Coefficients: intercept={coef[0]:.2f}, mean_dev={coef[1]:.3f}, "
          f"t_range={coef[2]:.3f}, rh_ann={coef[3]:.3f}")
    if rho < 0.7:
        raise SystemExit(
            f"CALIBRATION GATE: Spearman {rho:.3f} < 0.7 — the POWER-feature "
            "formula does not reproduce the curated semantics; not writing."
        )

    # 2. Score every center
    print(f"Fetching climatology for {len(all_centers)} centers ...")
    scores = {}
    for i, (code, c) in enumerate(sorted(all_centers.items())):
        lat, lon = c.get("lat"), c.get("lon")
        if lat is None or lon is None:
            continue
        rec = fetch_climatology(lat, lon, cache)
        if rec is None:
            print(f"    SKIP {code}: no climatology")
            continue
        f = features(rec)
        if f is None:
            continue
        score = float(coef[0] + np.dot(coef[1:], f))
        scores[code] = round(max(0.0, min(100.0, score)), 1)
        if (i + 1) % 50 == 0:
            _save_cache(cache)
            print(f"    {i + 1}/{len(all_centers)} done")
    _save_cache(cache)

    out = {
        "_meta": {
            "source": "NASA POWER climatology (T2M, RH2M) at center coordinates",
            "script": "scripts/fetch-climate-centers.py",
            "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "method": (
                "Linear map from (mean monthly |T-18°C| deviation, seasonal "
                "temperature range, annual RH) calibrated by least squares to "
                "the 22 previously hand-curated city scores; applied to all "
                "centers, clamped [0,100]. Higher = milder recovery climate."
            ),
            "calibration": {"n_cities": len(y), "r2": round(r2, 3),
                            "spearman": round(rho, 3),
                            "coefficients": [round(float(v), 4) for v in coef]},
        },
        "centers": scores,
    }

    if OUT_PATH.exists():
        old = json.loads(OUT_PATH.read_text())
        if len(scores) < len(old.get("centers", {})):
            raise SystemExit(
                f"NEVER-SHRINK GUARD: {len(scores)} < existing "
                f"{len(old.get('centers', {}))} centers; not writing."
            )
    OUT_PATH.write_text(json.dumps(out, indent=1))
    print(f"Wrote {OUT_PATH}: {len(scores)} centers")


if __name__ == "__main__":
    main()
