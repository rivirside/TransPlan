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
OUTCOMES_OUT = os.path.join(DATA_DIR, "post-transplant-outcomes.json")

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

# Sheet name mapping: old-format (pre-2111) → new-format (2111+)
# SRTR renamed Table B9→B10, Table B6→B7 starting with the Jan 2022 release (code 2111).
B10_SHEET_NAMES = ["Table B10", "Table B9"]                 # wait time percentiles
B7_SHEET_NAMES = ["Table B7", "Table B6", "Tables B7-B8 Center <=1yr"]  # waitlist outcomes


def _open_sheet(wb, candidates: list[str]):
    """Try multiple sheet names, return first match or None."""
    for name in candidates:
        try:
            return wb.sheet_by_name(name)
        except xlrd.biffh.XLRDError:
            continue
    return None


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


# Phase 4 M2: Post-transplant graft and patient survival columns
# From "TablesC5-C12 Figures C1-C20" (graft survival)
GRAFT_COLS = {
    "graft_survival_1yr": "GSR_AD_ACT_C1Y",
    "graft_survival_3yr": "GSR_AD_ACT_C3Y",
    "graft_hr_1yr": "GSR_AD_HR_C1Y",
    "graft_hr_lo": "GSR_AD_CREDLO_C1Y",
    "graft_hr_hi": "GSR_AD_CREDHI_C1Y",
    "graft_n_1yr": "GSR_AD_N_C1Y",
}
GRAFT_NAT_COLS = {
    "graft_survival_1yr": "GSR_AD_ACT_U1Y",
    "graft_survival_3yr": "GSR_AD_ACT_U3Y",
}

# From "TablesC11-C20 FiguresC21-C32" (patient survival)
PATIENT_COLS = {
    "patient_survival_1yr": "PSR_AD_ACT_C1Y",
    "patient_survival_3yr": "PSR_AD_ACT_C3Y",
    "patient_hr_1yr": "PSR_AD_HR_C1Y",
    "patient_hr_lo": "PSR_AD_CREDLO_C1Y",
    "patient_hr_hi": "PSR_AD_CREDHI_C1Y",
    "patient_n_1yr": "PSR_AD_N_C1Y",
}
PATIENT_NAT_COLS = {
    "patient_survival_1yr": "PSR_AD_ACT_U1Y",
    "patient_survival_3yr": "PSR_AD_ACT_U3Y",
}

# Graft survival sheet name
GRAFT_SHEET = "TablesC5-C12 Figures C1-C20"
PATIENT_SHEET = "TablesC11-C20 FiguresC21-C32"

# Minimum sample size for reliable survival estimates
MIN_N_OUTCOMES = 10


def _get_first_nonempty_national(sheet, col_indices: dict) -> dict | None:
    """
    Get national-level data by scanning rows until we find non-empty values.
    The C-series tables have national values (_U) populated only on certain rows.
    """
    if not col_indices:
        return None
    first_key = next(iter(col_indices))
    first_col = col_indices[first_key]
    for r in range(2, min(sheet.nrows, 50)):
        val = _safe_float(sheet.cell_value(r, first_col))
        if val is not None:
            result = {}
            for key, col_idx in col_indices.items():
                result[key] = _safe_float(sheet.cell_value(r, col_idx))
            return result
    return None


def _performance_rating(hr: float | None, ci_lo: float | None, ci_hi: float | None) -> str:
    """
    Classify center performance based on hazard ratio and 95% credible interval.
    Matches SRTR's own classification methodology.
    """
    if hr is None or ci_lo is None or ci_hi is None:
        return "insufficient_data"
    if ci_hi < 1.0:
        return "better_than_expected"
    if ci_lo > 1.0:
        return "worse_than_expected"
    return "as_expected"


def parse_post_transplant_outcomes(mapping: dict) -> dict:
    """
    Parse graft and patient survival from C-series tables in all organ Excel files.
    Returns dict structure for post-transplant-outcomes.json.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {
        "_meta": {
            "source": "SRTR PSR National Center-Level Summary Data (January 2025 release)",
            "method": "Center-level post-transplant graft survival (Tables C5-C12) and patient survival (Tables C11-C20). Adult (18+) estimates only.",
            "references": [
                "https://www.srtr.org/reports/program-specific-reports/",
            ],
            "fetchedAt": now,
            "notes": "Risk-adjusted Bayesian hierarchical estimates. Performance ratings derived from 1-year hazard ratio 95% credible intervals vs expected.",
        }
    }

    city_outcomes = {}

    for organ, code in ORGAN_CODES.items():
        excel_path = os.path.join(RAW_DIR, f"csrs_final_tables_2511_{code}.xls")
        if not os.path.exists(excel_path):
            print(f"  WARNING: {excel_path} not found, skipping {organ}")
            continue

        wb = xlrd.open_workbook(excel_path)

        # --- Graft survival ---
        try:
            gs_sheet = wb.sheet_by_name(GRAFT_SHEET)
        except xlrd.biffh.XLRDError:
            print(f"  WARNING: No graft survival sheet for {organ}")
            continue

        gs_ctr_cols = _build_col_map(gs_sheet, GRAFT_COLS)
        gs_nat_cols = _build_col_map(gs_sheet, GRAFT_NAT_COLS)
        gs_nat = _get_first_nonempty_national(gs_sheet, gs_nat_cols)

        # --- Patient survival ---
        try:
            ps_sheet = wb.sheet_by_name(PATIENT_SHEET)
        except xlrd.biffh.XLRDError:
            print(f"  WARNING: No patient survival sheet for {organ}")
            ps_sheet = None

        ps_ctr_cols = _build_col_map(ps_sheet, PATIENT_COLS) if ps_sheet else {}
        ps_nat_cols = _build_col_map(ps_sheet, PATIENT_NAT_COLS) if ps_sheet else {}
        ps_nat = _get_first_nonempty_national(ps_sheet, ps_nat_cols) if ps_sheet else None

        # Store national baselines
        nat_gs_1yr = gs_nat.get("graft_survival_1yr") if gs_nat else None
        nat_gs_3yr = gs_nat.get("graft_survival_3yr") if gs_nat else None
        nat_ps_1yr = ps_nat.get("patient_survival_1yr") if ps_nat else None
        nat_ps_3yr = ps_nat.get("patient_survival_3yr") if ps_nat else None

        result[organ] = {
            "national_graft_survival_1yr": round(nat_gs_1yr, 1) if nat_gs_1yr else None,
            "national_graft_survival_3yr": round(nat_gs_3yr, 1) if nat_gs_3yr else None,
            "national_patient_survival_1yr": round(nat_ps_1yr, 1) if nat_ps_1yr else None,
            "national_patient_survival_3yr": round(nat_ps_3yr, 1) if nat_ps_3yr else None,
        }

        print(f"  {organ}: national graft 1yr={nat_gs_1yr}, patient 1yr={nat_ps_1yr}")

        # --- Per-city extraction ---
        for city, info in mapping["cities"].items():
            # Look up graft survival for this center
            gs_data = _get_row_by_code(gs_sheet, info["primary"], gs_ctr_cols)
            if not gs_data:
                for alt_code in info.get("alternates", []):
                    gs_data = _get_row_by_code(gs_sheet, alt_code, gs_ctr_cols)
                    if gs_data:
                        break

            # Look up patient survival
            ps_data = None
            if ps_sheet:
                ps_data = _get_row_by_code(ps_sheet, info["primary"], ps_ctr_cols)
                if not ps_data:
                    for alt_code in info.get("alternates", []):
                        ps_data = _get_row_by_code(ps_sheet, alt_code, ps_ctr_cols)
                        if ps_data:
                            break

            if not gs_data:
                continue

            # Check sample size
            n_1yr = gs_data.get("graft_n_1yr")
            if n_1yr is not None and n_1yr < MIN_N_OUTCOMES:
                print(f"    {city} {organ}: N={n_1yr} < {MIN_N_OUTCOMES}, skipping")
                continue

            # Build city outcome entry
            entry = {}
            gs_1yr = gs_data.get("graft_survival_1yr")
            gs_3yr = gs_data.get("graft_survival_3yr")
            gs_hr = gs_data.get("graft_hr_1yr")
            gs_hr_lo = gs_data.get("graft_hr_lo")
            gs_hr_hi = gs_data.get("graft_hr_hi")

            if gs_1yr is not None:
                entry["graft_survival_1yr"] = round(gs_1yr, 1)
            if gs_3yr is not None:
                entry["graft_survival_3yr"] = round(gs_3yr, 1)
            if gs_hr is not None:
                entry["graft_hr_1yr"] = round(gs_hr, 3)
            if gs_hr_lo is not None and gs_hr_hi is not None:
                entry["graft_hr_1yr_ci"] = [round(gs_hr_lo, 3), round(gs_hr_hi, 3)]
            if n_1yr is not None:
                entry["n_1yr"] = int(n_1yr)

            # Patient survival
            if ps_data:
                ps_1yr = ps_data.get("patient_survival_1yr")
                ps_3yr = ps_data.get("patient_survival_3yr")
                ps_hr = ps_data.get("patient_hr_1yr")
                ps_hr_lo = ps_data.get("patient_hr_lo")
                ps_hr_hi = ps_data.get("patient_hr_hi")

                if ps_1yr is not None:
                    entry["patient_survival_1yr"] = round(ps_1yr, 1)
                if ps_3yr is not None:
                    entry["patient_survival_3yr"] = round(ps_3yr, 1)
                if ps_hr is not None:
                    entry["patient_hr_1yr"] = round(ps_hr, 3)
                if ps_hr_lo is not None and ps_hr_hi is not None:
                    entry["patient_hr_1yr_ci"] = [round(ps_hr_lo, 3), round(ps_hr_hi, 3)]

            # Performance rating based on graft survival HR
            entry["performance_rating"] = _performance_rating(gs_hr, gs_hr_lo, gs_hr_hi)

            if city not in city_outcomes:
                city_outcomes[city] = {}
            city_outcomes[city][organ] = entry

    result["city_outcomes"] = city_outcomes
    return result


# ---------- Phase 4 M3: Historical trend parsing ----------

# Auto-discover historical releases from extracted directories on disk.
# SRTR file codes use YYMM format (2-digit year + 2-digit month), so the
# release year can be derived: add 2 months to get the approximate release
# date, then use that year (e.g. "1811" → Nov 2018 + 2mo → Jan 2019 → 2019).
def _discover_historical_releases(hist_dir: str) -> dict:
    """Scan historical/ for extracted release directories and infer years."""
    releases = {}
    if not os.path.isdir(hist_dir):
        return releases
    for entry in sorted(os.listdir(hist_dir)):
        entry_path = os.path.join(hist_dir, entry)
        if not os.path.isdir(entry_path) or len(entry) != 4 or not entry.isdigit():
            continue
        # Check it actually contains .xls files
        if not any(f.endswith(".xls") for f in os.listdir(entry_path)):
            continue
        yy, mm = int(entry[:2]), int(entry[2:])
        # Approximate release date: data code + ~2 months
        release_month = mm + 2
        release_year = 2000 + yy + (1 if release_month > 12 else 0)
        releases[entry] = release_year
    return releases

CURRENT_RELEASE = ("2511", 2025)

HISTORICAL_DIR = os.path.join(RAW_DIR, "historical")
HISTORICAL_OUT = os.path.join(DATA_DIR, "srtr-historical.json")


def _extract_b10_metrics(sheet, center_code: str, ctr_cols: dict, nat_cols: dict) -> dict | None:
    """Extract wait time metrics from Table B10 for a single center."""
    nat_data = _get_national_row(sheet, nat_cols)
    nat_median = nat_data["p50"] if nat_data else None
    nat_fit = fit_lognormal(
        nat_data.get("p10") if nat_data else None,
        nat_data.get("p25") if nat_data else None,
        nat_median,
        nat_data.get("p75") if nat_data else None,
    )
    effective_median = round(math.exp(nat_fit[0]), 1) if nat_fit else None

    ctr_data = _get_row_by_code(sheet, center_code, ctr_cols)
    if not ctr_data:
        return None

    ctr_p50 = ctr_data.get("p50")
    median_wait = round(ctr_p50, 1) if _is_valid(ctr_p50) else None
    factor = _compute_city_factor(ctr_data, effective_median, nat_data) if effective_median else None

    return {
        "median_wait_months": median_wait,
        "wait_time_factor": factor,
        "national_median_months": effective_median,
    }


def _extract_b7_metrics(sheet, center_code: str, ctr_cols: dict, nat_cols: dict) -> dict | None:
    """Extract volume and outcome metrics from Table B7 for a single center."""
    nat_data = _get_national_row(sheet, nat_cols)
    if not nat_data:
        return None

    ctr_data = _get_row_by_code(sheet, center_code, ctr_cols)
    if not ctr_data:
        return None

    # Volume: total transplants in the 12-month cohort
    volume = ctr_data.get("removed_transplant")
    if volume is not None:
        volume = int(round(volume / 100.0 * (ctr_data.get("n") or 0))) if ctr_data.get("n") else None

    # Mortality and delisting rates
    mortality_rate = (ctr_data.get("died_waitlist") or 0) / 100.0
    delisting_rate = sum(
        (ctr_data.get(k) or 0) for k in ["removed_worsened", "removed_improved", "removed_refused", "removed_other"]
    ) / 100.0

    return {
        "volume": volume,
        "mortality_rate": round(mortality_rate, 4),
        "delisting_rate": round(delisting_rate, 4),
    }


def _extract_survival_metrics(wb, center_code: str) -> dict:
    """Extract graft and patient survival from C-series tables."""
    result = {}
    try:
        gs_sheet = wb.sheet_by_name(GRAFT_SHEET)
        gs_ctr_cols = _build_col_map(gs_sheet, GRAFT_COLS)
        gs_data = _get_row_by_code(gs_sheet, center_code, gs_ctr_cols)
        if gs_data and gs_data.get("graft_survival_1yr") is not None:
            result["graft_survival_1yr"] = round(gs_data["graft_survival_1yr"], 1)
    except (xlrd.biffh.XLRDError, Exception):
        pass  # Sheet may not exist in older releases

    try:
        ps_sheet = wb.sheet_by_name(PATIENT_SHEET)
        ps_ctr_cols = _build_col_map(ps_sheet, PATIENT_COLS)
        ps_data = _get_row_by_code(ps_sheet, center_code, ps_ctr_cols)
        if ps_data and ps_data.get("patient_survival_1yr") is not None:
            result["patient_survival_1yr"] = round(ps_data["patient_survival_1yr"], 1)
    except (xlrd.biffh.XLRDError, Exception):
        pass

    return result


def _extract_national_survival(wb) -> dict:
    """Extract national survival baselines from C-series tables."""
    result = {}
    try:
        gs_sheet = wb.sheet_by_name(GRAFT_SHEET)
        gs_nat_cols = _build_col_map(gs_sheet, GRAFT_NAT_COLS)
        gs_nat = _get_first_nonempty_national(gs_sheet, gs_nat_cols)
        if gs_nat and gs_nat.get("graft_survival_1yr") is not None:
            result["graft_survival_1yr"] = round(gs_nat["graft_survival_1yr"], 1)
    except (xlrd.biffh.XLRDError, Exception):
        pass

    try:
        ps_sheet = wb.sheet_by_name(PATIENT_SHEET)
        ps_nat_cols = _build_col_map(ps_sheet, PATIENT_NAT_COLS)
        ps_nat = _get_first_nonempty_national(ps_sheet, ps_nat_cols)
        if ps_nat and ps_nat.get("patient_survival_1yr") is not None:
            result["patient_survival_1yr"] = round(ps_nat["patient_survival_1yr"], 1)
    except (xlrd.biffh.XLRDError, Exception):
        pass

    return result


def parse_historical_trends(mapping: dict) -> dict:
    """
    Parse multiple SRTR releases to build a time-series dataset.

    For each release × organ × city, extracts:
    - median_wait_months (Table B10)
    - volume (Table B7)
    - mortality_rate, delisting_rate (Table B7)
    - graft_survival_1yr, patient_survival_1yr (C-series, when available)

    Output: dict structure for data/srtr-historical.json
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Collect all available releases (auto-discovered from disk + current)
    discovered = _discover_historical_releases(HISTORICAL_DIR)
    releases = {}
    for code, year in discovered.items():
        release_dir = os.path.join(HISTORICAL_DIR, code)
        releases[code] = {"year": year, "dir": release_dir, "pattern": "csrs_final_tables_{code}_{organ_code}.xls"}

    # Current release (in srtr-raw/ root)
    cur_code, cur_year = CURRENT_RELEASE
    releases[cur_code] = {"year": cur_year, "dir": RAW_DIR, "pattern": "csrs_final_tables_{code}_{organ_code}.xls"}

    if not releases:
        print("  WARNING: No SRTR releases found. Run fetch-srtr-excel.py --historical first.")
        return {}

    sorted_releases = sorted(releases.items(), key=lambda x: x[1]["year"])
    years = [info["year"] for _, info in sorted_releases]
    print(f"  Found {len(releases)} releases: {years}")

    cities_data = {}
    national_data = {}

    for organ, organ_code in ORGAN_CODES.items():
        national_data[organ] = {
            "years": [],
            "median_wait_months": [],
            "graft_survival_1yr": [],
        }

        for release_code, info in sorted_releases:
            year = info["year"]
            release_dir = info["dir"]

            # Find the Excel file for this organ
            filename = f"csrs_final_tables_{release_code}_{organ_code}.xls"
            excel_path = os.path.join(release_dir, filename)
            if not os.path.exists(excel_path):
                # Try without the release code in the filename (some zips use different naming)
                alt_files = [f for f in os.listdir(release_dir) if f.lower().endswith(".xls") and f"_{organ_code}." in f.upper()]
                if alt_files:
                    excel_path = os.path.join(release_dir, alt_files[0])
                else:
                    continue

            try:
                wb = xlrd.open_workbook(excel_path)
            except Exception as e:
                print(f"    WARNING: Could not open {excel_path}: {e}")
                continue

            # Parse B10 and B7 sheets (handles old sheet names: B9→B10, B6→B7)
            b10_sheet = _open_sheet(wb, B10_SHEET_NAMES)
            if b10_sheet:
                b10_ctr_cols = _build_col_map(b10_sheet, B10_COLS)
                b10_nat_cols = _build_col_map(b10_sheet, B10_NAT_COLS)
            else:
                b10_ctr_cols = {}
                b10_nat_cols = {}

            b7_sheet = _open_sheet(wb, B7_SHEET_NAMES)
            if b7_sheet:
                b7_ctr_cols = _build_col_map(b7_sheet, B7_COLS)
                b7_nat_cols = _build_col_map(b7_sheet, B7_NAT_COLS)
            else:
                b7_ctr_cols = {}
                b7_nat_cols = {}

            # National baselines
            nat_median = None
            if b10_sheet:
                nat_row = _get_national_row(b10_sheet, b10_nat_cols)
                if nat_row:
                    nat_p50 = nat_row.get("p50")
                    if _is_valid(nat_p50):
                        nat_median = round(nat_p50, 1)

            nat_survival = _extract_national_survival(wb)

            national_data[organ]["years"].append(year)
            national_data[organ]["median_wait_months"].append(nat_median)
            national_data[organ]["graft_survival_1yr"].append(
                nat_survival.get("graft_survival_1yr")
            )

            # Per-city extraction
            for city, city_info in mapping["cities"].items():
                if city not in cities_data:
                    cities_data[city] = {}
                if organ not in cities_data[city]:
                    cities_data[city][organ] = {
                        "years": [],
                        "median_wait_months": [],
                        "volume": [],
                        "mortality_rate": [],
                        "delisting_rate": [],
                        "graft_survival_1yr": [],
                        "patient_survival_1yr": [],
                        "wait_time_factor": [],
                    }

                entry = cities_data[city][organ]
                entry["years"].append(year)

                # Try primary center, then alternates
                codes_to_try = [city_info["primary"]] + city_info.get("alternates", [])
                b10_metrics = None
                b7_metrics = None
                surv_metrics = {}

                for code in codes_to_try:
                    if b10_sheet and not b10_metrics:
                        b10_metrics = _extract_b10_metrics(b10_sheet, code, b10_ctr_cols, b10_nat_cols)
                    if b7_sheet and not b7_metrics:
                        b7_metrics = _extract_b7_metrics(b7_sheet, code, b7_ctr_cols, b7_nat_cols)
                    if not surv_metrics:
                        surv_metrics = _extract_survival_metrics(wb, code)
                    if b10_metrics and b7_metrics:
                        break

                entry["median_wait_months"].append(b10_metrics["median_wait_months"] if b10_metrics else None)
                entry["wait_time_factor"].append(b10_metrics["wait_time_factor"] if b10_metrics else None)
                entry["volume"].append(b7_metrics["volume"] if b7_metrics else None)
                entry["mortality_rate"].append(b7_metrics["mortality_rate"] if b7_metrics else None)
                entry["delisting_rate"].append(b7_metrics["delisting_rate"] if b7_metrics else None)
                entry["graft_survival_1yr"].append(surv_metrics.get("graft_survival_1yr"))
                entry["patient_survival_1yr"].append(surv_metrics.get("patient_survival_1yr"))

        print(f"  {organ}: parsed {len(national_data[organ]['years'])} releases")

    return {
        "_meta": {
            "source": "SRTR PSR National Center-Level Summary Data (multiple releases)",
            "method": "Per-year extraction from Table B10 (wait times), B7 (volumes/outcomes), C-series (survival)",
            "releases": [code for code, _ in sorted_releases],
            "years": years,
            "fetchedAt": now,
            "notes": "One entry per city per organ per release year. null values indicate center did not report or data was unavailable.",
        },
        "cities": cities_data,
        "national": national_data,
    }


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

    print("\n=== Parsing SRTR Post-Transplant Outcomes (Tables C5-C12, C11-C20) ===")
    pt_outcomes = parse_post_transplant_outcomes(mapping)

    # Phase 4 M3: Parse historical trends if data is available
    has_historical = bool(_discover_historical_releases(HISTORICAL_DIR))

    if has_historical or "--historical" in sys.argv:
        print("\n=== Parsing Historical Trends (Phase 4 M3) ===")
        historical_data = parse_historical_trends(mapping)
        if historical_data:
            with open(HISTORICAL_OUT, "w") as f:
                json.dump(historical_data, f, indent=2)
                f.write("\n")
            print(f"Wrote {HISTORICAL_OUT}")
    else:
        print("\n  Skipping historical trends (no historical data in srtr-raw/historical/)")
        print("  Run: python scripts/fetch-srtr-excel.py --historical to download")

    # Write output files
    with open(WAIT_TIME_OUT, "w") as f:
        json.dump(wait_data, f, indent=2)
        f.write("\n")
    print(f"\nWrote {WAIT_TIME_OUT}")

    with open(COMPETING_OUT, "w") as f:
        json.dump(outcome_data, f, indent=2)
        f.write("\n")
    print(f"Wrote {COMPETING_OUT}")

    with open(OUTCOMES_OUT, "w") as f:
        json.dump(pt_outcomes, f, indent=2)
        f.write("\n")
    print(f"Wrote {OUTCOMES_OUT}")

    # Summary
    n_organs = len([k for k in wait_data if not k.startswith("_") and k != "city_wait_time_factors"])
    n_cities = len([k for k in wait_data.get("city_wait_time_factors", {}) if not k.startswith("_")])
    n_outcomes_cities = len(pt_outcomes.get("city_outcomes", {}))
    print(f"\nSummary: {n_organs} organs, {n_cities} cities with wait time factors, {n_outcomes_cities} cities with post-transplant outcomes")


if __name__ == "__main__":
    main()
