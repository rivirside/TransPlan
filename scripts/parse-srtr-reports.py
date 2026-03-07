#!/usr/bin/env python3
"""
Parse SRTR PSR National Center-Level Summary Data Excel files.

Reads Excel files downloaded by fetch-srtr-excel.py and extracts:
  1. Wait time percentiles (Table B10) → data/wait-time-distributions.json
  2. Waitlist outcomes (Table B7) → data/competing-risks.json

Uses center-to-city mapping from data/srtr-center-mapping.json.
Falls back to national-level data when a center lacks data for an organ.

Output JSON files are consumed by the backend Monte Carlo engine.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone

import xlrd

# ---------- paths ----------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
RAW_DIR = os.path.join(DATA_DIR, "srtr-raw")
MAPPING_PATH = os.path.join(DATA_DIR, "srtr-center-mapping.json")
WAIT_TIME_OUT = os.path.join(DATA_DIR, "wait-time-distributions.json")
COMPETING_OUT = os.path.join(DATA_DIR, "competing-risks.json")

ORGAN_CODES = {
    "kidney": "KI",
    "liver": "LI",
    "heart": "HR",
    "lung": "LU",
    "pancreas": "PA",
    "intestine": "IN",
}

# Column name → index mappings built at parse time
# Table B10 center-level wait time percentile columns
B10_COLS = {
    "p5": "TTT_5_C",
    "p10": "TTT_10_C",
    "p25": "TTT_25_C",
    "p50": "TTT_50_C",   # median
    "p75": "TTT_75_C",
}
# National-level columns (fallback)
B10_NAT_COLS = {
    "p5": "TTT_5_U",
    "p10": "TTT_10_U",
    "p25": "TTT_25_U",
    "p50": "TTT_50_U",
    "p75": "TTT_75_U",
}

# Table B7 outcome columns (center, 12-month)
B7_COLS = {
    "died_waitlist": "SAL_WLDIED_C12",
    "removed_transplant": "SAL_TOTTX_C12",
    "removed_worsened": "SAL_REMDET_C12",
    "removed_improved": "SAL_REMREC_C12",
    "removed_refused": "SAL_REFTX_C12",
    "removed_other": "SAL_REMOTH_C12",
    "alive_waitlist": "SAL_WLLIVE_C12",
    "total": "SAL_TOTAL_C12",
    "n": "SAL_N_C",
}
# National 12-month columns (fallback)
B7_NAT_COLS = {
    "died_waitlist": "SAL_WLDIED_U12",
    "removed_transplant": "SAL_TOTTX_U12",
    "removed_worsened": "SAL_REMDET_U12",
    "removed_improved": "SAL_REMREC_U12",
    "removed_refused": "SAL_REFTX_U12",
    "removed_other": "SAL_REMOTH_U12",
    "alive_waitlist": "SAL_WLLIVE_U12",
    "total": "SAL_TOTAL_U12",
    "n": "SAL_N_U",
}


# ---------- helpers ----------


def _col_index(sheet, col_name: str) -> int:
    """Find column index by header name (row 0)."""
    for c in range(sheet.ncols):
        if sheet.cell_value(0, c) == col_name:
            return c
    return -1


CENSORED = -999.0  # sentinel for ">72" censored values


def _safe_float(val) -> float | None:
    """Parse a cell value as float, handling '>72' style strings and blanks."""
    if isinstance(val, (int, float)):
        return float(val) if val != "" else None
    s = str(val).strip()
    if not s:
        return None
    # SRTR uses ">72" for censored values (didn't reach percentile within 72 months)
    if s.startswith(">"):
        return CENSORED
    try:
        return float(s)
    except ValueError:
        return None


def _is_valid(val: float | None) -> bool:
    """Check if a percentile value is valid (not None, not censored, positive)."""
    return val is not None and val != CENSORED and val > 0


def _get_row_by_code(sheet, center_code: str, col_indices: dict) -> dict | None:
    """Extract named columns for a given center code from a sheet."""
    ctr_col = _col_index(sheet, "CTR_CD")
    if ctr_col < 0:
        return None
    for r in range(2, sheet.nrows):
        if str(sheet.cell_value(r, ctr_col)).strip() == center_code:
            result = {}
            for key, col_idx in col_indices.items():
                result[key] = _safe_float(sheet.cell_value(r, col_idx))
            return result
    return None


def _build_col_map(sheet, col_names: dict) -> dict:
    """Map logical names → column indices for a sheet."""
    result = {}
    for key, header in col_names.items():
        idx = _col_index(sheet, header)
        if idx >= 0:
            result[key] = idx
    return result


def _get_national_row(sheet, col_indices: dict) -> dict | None:
    """Get national-level data from the first data row (all rows share same U values)."""
    if sheet.nrows < 3:
        return None
    result = {}
    for key, col_idx in col_indices.items():
        result[key] = _safe_float(sheet.cell_value(2, col_idx))
    return result


def fit_lognormal(
    p10: float | None, p25: float | None, p50: float | None, p75: float | None
) -> tuple[float, float] | None:
    """
    Fit log-normal parameters (mu, sigma) from percentiles.

    mu = ln(median)  — for log-normal, median = exp(mu)

    Sigma estimation strategy:
    SRTR data has very heavy upper tails because P75 is frequently censored at ">72"
    months. Our Monte Carlo model handles the heavy tail via competing risks (mortality,
    delisting), so we estimate sigma from the *lower* quantiles (P10, P25) which are
    more reliable and better represent the transplant-conditional distribution shape.

    Strategies (in preference order):
    1. P10-P25 method: sigma = ln(P25/P10) / (z_25 - z_10) = ln(P25/P10) / 1.9561
       Uses only lower quantiles, unaffected by censoring. Best for SRTR data.
    2. IQR method: sigma = ln(P75/P25) / (2 * 0.6745) — when P75 is valid
    3. Fallback: sigma = 0.8
    """
    if not _is_valid(p50):
        # Median is censored — use P25 to approximate mu
        if _is_valid(p25):
            sigma_est = 0.8
            mu = math.log(p25) + 0.6745 * sigma_est
            return (mu, sigma_est)
        return None

    mu = math.log(p50)

    # Strategy 1: P10-P25 spread (most reliable for SRTR data)
    # z_25 = -0.6745, z_10 = -1.2816, difference = 0.6071
    # But we use P10/P25 to infer the local spread in the lower tail
    if _is_valid(p10) and _is_valid(p25) and p25 > p10:
        sigma = (math.log(p25) - math.log(p10)) / (1.2816 - 0.6745)  # 0.6071
    # Strategy 2: IQR (when P75 is not censored)
    elif _is_valid(p25) and _is_valid(p75) and p75 > p25:
        sigma = (math.log(p75) - math.log(p25)) / (2 * 0.6745)
    # Strategy 3: P10-P50 (wider range)
    elif _is_valid(p10) and p50 > p10:
        sigma = (math.log(p50) - math.log(p10)) / 1.2816
    # Strategy 4: fallback
    else:
        sigma = 0.8

    # Clamp sigma to reasonable range for transplant wait times
    sigma = max(0.3, min(sigma, 1.2))
    return (mu, sigma)


def _compute_city_factor(ctr_data: dict, nat_median: float, nat_data: dict) -> float | None:
    """
    Compute city wait time factor relative to national median.

    Uses P50 center/national ratio when both are valid. Falls back to P25 ratio
    when center P50 is censored. Returns None if no valid comparison is possible.
    """
    ctr_p50 = ctr_data.get("p50")
    ctr_p25 = ctr_data.get("p25")
    nat_p25 = nat_data.get("p25") if nat_data else None

    # Best case: both medians valid
    if _is_valid(ctr_p50) and _is_valid(nat_median):
        factor = ctr_p50 / nat_median
        return round(max(0.3, min(factor, 3.0)), 2)

    # Center P50 is censored but P25 is valid — use P25 ratio
    if _is_valid(ctr_p25) and _is_valid(nat_p25) and nat_p25 > 0:
        factor = ctr_p25 / nat_p25
        return round(max(0.3, min(factor, 3.0)), 2)

    # Both censored — this center has extremely long waits
    if ctr_p50 == CENSORED and _is_valid(nat_median):
        return 2.5  # conservative high factor

    return None


# ---------- main parse functions ----------


def parse_wait_times(mapping: dict) -> dict:
    """
    Parse Table B10 from all organ Excel files.
    Returns dict structure for wait-time-distributions.json.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {
        "_meta": {
            "source": "SRTR PSR National Center-Level Summary Data (January 2025 release)",
            "method": "Log-normal fit from center-level P25/P50/P75 wait time percentiles (Table B10)",
            "references": [
                "https://www.srtr.org/reports/program-specific-reports/",
                "SRTR PSR Technical Methods: https://www.srtr.org/about-the-data/technical-methods-for-the-program-specific-reports/",
            ],
            "fetchedAt": now,
            "notes": "Empirical center-level data from SRTR. Blood type and clinical multipliers retained from literature-derived estimates (Table B10 does not stratify by blood type).",
        }
    }

    # Preserve existing blood type and clinical multipliers
    existing = _load_existing(WAIT_TIME_OUT)

    city_factors = {}

    for organ, code in ORGAN_CODES.items():
        excel_path = os.path.join(RAW_DIR, f"csrs_final_tables_2511_{code}.xls")
        if not os.path.exists(excel_path):
            print(f"  WARNING: {excel_path} not found, skipping {organ}")
            continue

        wb = xlrd.open_workbook(excel_path)
        sheet = wb.sheet_by_name("Table B10")

        # Build column index maps
        ctr_cols = _build_col_map(sheet, B10_COLS)
        nat_cols = _build_col_map(sheet, B10_NAT_COLS)

        # Get national baseline
        nat_data = _get_national_row(sheet, nat_cols)
        nat_median = nat_data["p50"] if nat_data else None
        nat_fit = fit_lognormal(
            nat_data.get("p10") if nat_data else None,
            nat_data.get("p25") if nat_data else None,
            nat_median,
            nat_data.get("p75") if nat_data else None,
        )

        if not nat_fit:
            print(f"  WARNING: Could not fit national baseline for {organ}")
            continue

        nat_mu, nat_sigma = nat_fit
        # For display and storage, use exp(mu) as the effective median
        effective_median = round(math.exp(nat_mu), 1)
        print(f"  {organ}: national median={effective_median}mo, sigma={nat_sigma:.2f}")

        # Build organ entry
        organ_entry = {
            "national_median_months": effective_median,
            "log_sigma": round(nat_sigma, 2),
        }

        # Carry forward blood type / clinical multipliers from existing data
        if existing and organ in existing:
            if "blood_type_multipliers" in existing[organ]:
                organ_entry["blood_type_multipliers"] = existing[organ]["blood_type_multipliers"]
            if "clinical_multipliers" in existing[organ]:
                organ_entry["clinical_multipliers"] = existing[organ]["clinical_multipliers"]
        else:
            organ_entry["blood_type_multipliers"] = _default_blood_type_multipliers()
            organ_entry["clinical_multipliers"] = {}

        result[organ] = organ_entry

        # Extract city-level wait time factors from center percentiles
        # Use effective_median (derived from mu, handles censored national P50)
        for city, info in mapping["cities"].items():
            ctr_data = _get_row_by_code(sheet, info["primary"], ctr_cols)
            if not ctr_data:
                for alt_code in info.get("alternates", []):
                    ctr_data = _get_row_by_code(sheet, alt_code, ctr_cols)
                    if ctr_data:
                        break

            if ctr_data:
                factor = _compute_city_factor(ctr_data, effective_median, nat_data)
                if factor is not None:
                    if city not in city_factors:
                        city_factors[city] = {}
                    city_factors[city][organ] = factor
                    continue

            print(f"  WARNING: No {organ} data for {city} ({info['primary']}), using 1.0")

    # Compute average city factor across organs (for the aggregate city_wait_time_factors)
    city_wait_time_factors = {
        "_notes": "Relative to national average (1.0). Computed as average center-median / national-median across available organs. Source: SRTR Table B10."
    }
    for city in mapping["cities"]:
        if city in city_factors and city_factors[city]:
            factors = list(city_factors[city].values())
            avg = sum(factors) / len(factors)
            city_wait_time_factors[city] = round(avg, 2)
        else:
            # Fall back to existing value
            if existing and "city_wait_time_factors" in existing:
                city_wait_time_factors[city] = existing["city_wait_time_factors"].get(city, 1.0)
            else:
                city_wait_time_factors[city] = 1.0

    result["city_wait_time_factors"] = city_wait_time_factors
    return result


def parse_outcomes(mapping: dict) -> dict:
    """
    Parse Table B7 from all organ Excel files.
    Returns dict structure for competing-risks.json.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {
        "_meta": {
            "source": "SRTR PSR National Center-Level Summary Data (January 2025 release)",
            "method": "12-month waitlist outcomes from Table B7 — died-on-waitlist as annual mortality proxy, removals (worsened + other + refused) as delisting proxy",
            "references": [
                "https://www.srtr.org/reports/program-specific-reports/",
            ],
            "fetchedAt": now,
            "notes": "Center-level rates from SRTR Table B7. Urgency and clinical multipliers retained from literature estimates.",
        }
    }

    # Preserve existing urgency/clinical multipliers
    existing = _load_existing(COMPETING_OUT)

    city_adjustments = {
        "_notes": "Center-level mortality and delisting factors relative to national average. Source: SRTR Table B7."
    }

    for organ, code in ORGAN_CODES.items():
        excel_path = os.path.join(RAW_DIR, f"csrs_final_tables_2511_{code}.xls")
        if not os.path.exists(excel_path):
            continue

        wb = xlrd.open_workbook(excel_path)
        sheet = wb.sheet_by_name("Table B7")

        ctr_cols = _build_col_map(sheet, B7_COLS)
        nat_cols = _build_col_map(sheet, B7_NAT_COLS)

        # National baseline rates (12-month %, used as annual proxy)
        nat_data = _get_national_row(sheet, nat_cols)
        if not nat_data:
            print(f"  WARNING: No national B7 data for {organ}")
            continue

        nat_mortality = (nat_data.get("died_waitlist") or 0) / 100.0
        nat_delisting = sum(
            (nat_data.get(k) or 0) for k in ["removed_worsened", "removed_improved", "removed_refused", "removed_other"]
        ) / 100.0

        print(f"  {organ}: national mortality={nat_mortality:.3f}, delisting={nat_delisting:.3f}")

        organ_entry = {
            "annual_mortality_rate": round(nat_mortality, 4),
            "annual_delisting_rate": round(nat_delisting, 4),
        }

        # Carry forward urgency/MELD multipliers from existing data
        if existing and organ in existing:
            if "urgency_mortality_multipliers" in existing[organ]:
                organ_entry["urgency_mortality_multipliers"] = existing[organ]["urgency_mortality_multipliers"]
            if "meld_mortality_multipliers" in existing[organ]:
                organ_entry["meld_mortality_multipliers"] = existing[organ]["meld_mortality_multipliers"]
        else:
            organ_entry["urgency_mortality_multipliers"] = {"1": 0.7, "2": 1.0, "3": 1.4, "4": 2.0}

        result[organ] = organ_entry

        # City-level adjustment factors
        for city, info in mapping["cities"].items():
            primary_code = info["primary"]
            ctr_data = _get_row_by_code(sheet, primary_code, ctr_cols)

            if not ctr_data:
                for alt_code in info.get("alternates", []):
                    ctr_data = _get_row_by_code(sheet, alt_code, ctr_cols)
                    if ctr_data:
                        break

            if ctr_data:
                ctr_mortality = (ctr_data.get("died_waitlist") or 0) / 100.0
                ctr_delisting = sum(
                    (ctr_data.get(k) or 0) for k in ["removed_worsened", "removed_improved", "removed_refused", "removed_other"]
                ) / 100.0

                mort_factor = (ctr_mortality / nat_mortality) if nat_mortality > 0 else 1.0
                delist_factor = (ctr_delisting / nat_delisting) if nat_delisting > 0 else 1.0

                # Clamp to reasonable range
                mort_factor = round(max(0.3, min(mort_factor, 3.0)), 2)
                delist_factor = round(max(0.3, min(delist_factor, 3.0)), 2)

                if city not in city_adjustments or not isinstance(city_adjustments.get(city), dict):
                    city_adjustments[city] = {}
                if not isinstance(city_adjustments[city], dict) or "_notes" in city_adjustments.get(city, {}):
                    city_adjustments[city] = {}

                # Average across organs for this city
                if "mortality_factors" not in city_adjustments[city]:
                    city_adjustments[city]["mortality_factors"] = []
                    city_adjustments[city]["delisting_factors"] = []
                city_adjustments[city]["mortality_factors"].append(mort_factor)
                city_adjustments[city]["delisting_factors"].append(delist_factor)

    # Average the per-organ factors into single city adjustments
    final_adjustments = {
        "_notes": "Center-level mortality and delisting factors relative to national average. Averaged across available organs. Source: SRTR Table B7."
    }
    for city in mapping["cities"]:
        if city in city_adjustments and isinstance(city_adjustments[city], dict):
            ca = city_adjustments[city]
            if "mortality_factors" in ca and ca["mortality_factors"]:
                mort = sum(ca["mortality_factors"]) / len(ca["mortality_factors"])
                delist = sum(ca["delisting_factors"]) / len(ca["delisting_factors"])
                final_adjustments[city] = {
                    "mortality_factor": round(mort, 2),
                    "delisting_factor": round(delist, 2),
                }
            else:
                final_adjustments[city] = {"mortality_factor": 1.0, "delisting_factor": 1.0}
        else:
            # Fall back to existing
            if existing and "city_adjustments" in existing:
                final_adjustments[city] = existing["city_adjustments"].get(
                    city, {"mortality_factor": 1.0, "delisting_factor": 1.0}
                )
            else:
                final_adjustments[city] = {"mortality_factor": 1.0, "delisting_factor": 1.0}

    result["city_adjustments"] = final_adjustments
    return result


def _load_existing(path: str) -> dict | None:
    """Load existing JSON file, or None if it doesn't exist."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _default_blood_type_multipliers() -> dict:
    """Default blood type multipliers when no existing data."""
    return {
        "O+": 1.25, "O-": 1.30, "A+": 0.90, "A-": 0.95,
        "B+": 1.10, "B-": 1.15, "AB+": 0.70, "AB-": 0.75,
    }


def main():
    # Load center mapping
    with open(MAPPING_PATH) as f:
        mapping = json.load(f)

    print("=== Parsing SRTR Wait Time Data (Table B10) ===")
    wait_data = parse_wait_times(mapping)

    print("\n=== Parsing SRTR Outcome Data (Table B7) ===")
    outcome_data = parse_outcomes(mapping)

    # Write output files
    with open(WAIT_TIME_OUT, "w") as f:
        json.dump(wait_data, f, indent=2)
        f.write("\n")
    print(f"\nWrote {WAIT_TIME_OUT}")

    with open(COMPETING_OUT, "w") as f:
        json.dump(outcome_data, f, indent=2)
        f.write("\n")
    print(f"Wrote {COMPETING_OUT}")

    # Summary
    n_organs = len([k for k in wait_data if not k.startswith("_") and k != "city_wait_time_factors"])
    n_cities = len([k for k in wait_data.get("city_wait_time_factors", {}) if not k.startswith("_")])
    print(f"\nSummary: {n_organs} organs, {n_cities} cities with wait time factors")


if __name__ == "__main__":
    main()
