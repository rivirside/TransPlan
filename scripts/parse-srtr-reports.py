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

import statistics

import xlrd

import eb_shrinkage

# ---------- paths ----------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
RAW_DIR = os.path.join(DATA_DIR, "srtr-raw")
MAPPING_PATH = os.path.join(DATA_DIR, "srtr-center-mapping.json")
WAIT_TIME_OUT = os.path.join(DATA_DIR, "wait-time-distributions.json")
COMPETING_OUT = os.path.join(DATA_DIR, "competing-risks.json")
OUTCOMES_OUT = os.path.join(DATA_DIR, "post-transplant-outcomes.json")

# Phase 6A: Center-level output files (all ~250 centers, not just 22 cities)
CENTERS_WAIT_OUT = os.path.join(DATA_DIR, "wait-time-distributions-centers.json")
CENTERS_COMPETING_OUT = os.path.join(DATA_DIR, "competing-risks-centers.json")
CENTERS_OUTCOMES_OUT = os.path.join(DATA_DIR, "post-transplant-outcomes-centers.json")

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


# Shared xls helpers (#339): single source in scripts/srtr_xls_utils.py
import importlib.util as _ilu
from pathlib import Path as _Path
_sx_spec = _ilu.spec_from_file_location(
    "srtr_xls_utils", _Path(__file__).parent / "srtr_xls_utils.py")
sx = _ilu.module_from_spec(_sx_spec)
_sx_spec.loader.exec_module(sx)

CENSORED = sx.CENSORED  # sentinel for ">72" censored values
_safe_float = sx.safe_float
_is_valid = sx.is_valid


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

    # Strategy chain + clamps live in srtr_xls_utils.sigma_from_percentiles
    # (#339): the temporal forecast uses the SAME function by construction.
    sigma = sx.sigma_from_percentiles(p10, p25, p50, p75)
    return (mu, sigma)


def _compute_city_factor(ctr_data: dict, nat_median: float, nat_data: dict) -> float | None:
    """
    Compute city wait time factor relative to national median.

    Uses P50 center/national ratio when both are valid. Falls back to P25 ratio
    when center P50 is censored. Returns None if no valid comparison is possible.
    """
    # Ratio/fallback/clamp logic shared with the forecast (#339); the
    # 2-decimal rounding is a parser output convention kept here.
    factor = sx.wait_factor_from_percentiles(
        {"p50": ctr_data.get("p50"), "p25": ctr_data.get("p25")},
        {"p50": nat_median, "p25": nat_data.get("p25") if nat_data else None},
    )
    if factor is None:
        return None
    return factor if factor == sx.CENSORED_FACTOR else round(factor, 2)


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
            "method": "Log-normal fit from center-level P25/P50/P75 wait time percentiles (Table B10): mu=ln(median), sigma via the IQR method ln(P75/P25)/(2*0.6745) in scripts/parse-srtr-reports.py:fit_lognormal. NOTE (#256): sigma is CLAMPED to [0.3, 1.2]; the identical log_sigma=1.2 across kidney/liver/heart/intestine are long-wait organs hitting that ceiling (their true IQR-implied sigma exceeds 1.2), NOT a placeholder. The 1.2 ceiling likely understates dispersion (hence the right tail / long-wait probabilities) for these organs and should be re-evaluated against the raw percentiles.",
            "references": [
                "https://www.srtr.org/reports/program-specific-reports/",
                "SRTR PSR Technical Methods: https://www.srtr.org/about-the-data/technical-methods-for-the-program-specific-reports/",
            ],
            "fetchedAt": now,
            "notes": "Empirical center-level data from SRTR. Blood type and clinical multipliers retained from literature-derived estimates (Table B10 does not stratify by blood type). (#293: the legacy 22-city block was retired 2026-08-25 \u2014 per-center data lives in the *-centers.json files.)",
        }
    }

    # Preserve existing blood type and clinical multipliers
    existing = _load_existing(WAIT_TIME_OUT)

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

        # Build organ entry.
        #
        # #376/L-080: when SRTR censors the national median (">72 months"),
        # `effective_median` is RECONSTRUCTED from P25 rather than published.
        # Pancreas is the only organ this currently affects. Without a flag the
        # reconstructed figure is indistinguishable from the five organs whose
        # medians SRTR does publish and which are stored verbatim — so a
        # pancreas center's displayed "median wait" reads as a registry figure
        # when it is a model artifact.
        #
        # The value itself is deliberately unchanged: raising it toward the
        # censored bound measurably DEGRADES calibration (p12 vs observed
        # across 78 centers: 1.11x shipped, 1.40x at a median of 72), because
        # sigma must rise with the median and fattens the left tail too. The
        # fix is disclosure, not substitution — see docs/limitations.md L-080.
        median_censored = not _is_valid(nat_median)
        organ_entry = {
            "national_median_months": effective_median,
            "log_sigma": round(nat_sigma, 2),
            "median_censored": median_censored,
        }
        if median_censored:
            organ_entry["median_provenance"] = (
                "RECONSTRUCTED. SRTR Table B10 censors this organ's national "
                "median at '>72 months' and publishes no value. This figure is "
                "derived from P25 under the fitted lognormal and is a model "
                "artifact, not a registry statistic. Treat displayed medians "
                "for this organ as indicative only; the registry's own "
                "statement is that the median exceeds 72 months. See L-080."
            )

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

    # (#293: the 22-city city_wait_time_factors block is no longer emitted —
    # per-center factors live in wait-time-distributions-centers.json.)
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
            "notes": "Center-level rates from SRTR Table B7. Urgency and clinical multipliers retained from literature estimates. (#293: the legacy 22-city block was retired 2026-08-25 \u2014 per-center data lives in the *-centers.json files.)",
        }
    }

    # Preserve existing urgency/clinical multipliers
    existing = _load_existing(COMPETING_OUT)

    # Preserve the manual TOP-LEVEL age blocks (SRTR ADR Table 5.3-sourced).
    # The #104 rewrite dropped them, silently killing the BBN AgeGroup edge
    # and MCMC inference age modulation for months (found 2026-08-25) —
    # every regenerate must carry them forward.
    for manual_key in ("age_mortality_multipliers", "age_organ_overrides"):
        if existing and manual_key in existing:
            result[manual_key] = existing[manual_key]

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

    # (#293: the 22-city city_adjustments block is no longer emitted —
    # per-center factors live in competing-risks-centers.json.)
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
            "notes": "Risk-adjusted Bayesian hierarchical estimates. Performance ratings derived from 1-year hazard ratio 95% credible intervals vs expected. (#293: the legacy 22-city block was retired 2026-08-25 \u2014 per-center data lives in the *-centers.json files.)",
        }
    }

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

    # (#293: the 22-city city_outcomes block is no longer emitted —
    # per-center outcomes live in post-transplant-outcomes-centers.json.)
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


# ---------- Phase 6A: Center-level extraction (all ~250 centers) ----------


def _get_all_center_rows(sheet, col_indices: dict) -> dict:
    """Extract named columns for ALL centers in a sheet. Returns {center_code: {col: value}}."""
    ctr_col = _col_index(sheet, "CTR_CD")
    if ctr_col < 0:
        return {}
    result = {}
    for r in range(2, sheet.nrows):
        code = str(sheet.cell_value(r, ctr_col)).strip()
        if not code:
            continue
        row_data = {}
        for key, col_idx in col_indices.items():
            row_data[key] = _safe_float(sheet.cell_value(r, col_idx))
        result[code] = row_data
    return result


def parse_all_centers_wait_times() -> dict:
    """
    Parse Table B10 for ALL centers (not just 22 cities).
    Returns center-level wait time factors for every center in SRTR data.
    Phase 6A issue #117.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {
        "_meta": {
            "source": "SRTR PSR National Center-Level Summary Data (January 2025 release)",
            "method": "Center-level wait time factors from Table B10 (all centers)",
            "fetchedAt": now,
        }
    }
    center_factors = {}

    for organ, code in ORGAN_CODES.items():
        excel_path = os.path.join(RAW_DIR, f"csrs_final_tables_2511_{code}.xls")
        if not os.path.exists(excel_path):
            continue

        wb = xlrd.open_workbook(excel_path)
        sheet = _open_sheet(wb, B10_SHEET_NAMES)
        if not sheet:
            continue

        ctr_cols = _build_col_map(sheet, B10_COLS)
        nat_cols = _build_col_map(sheet, B10_NAT_COLS)
        nat_data = _get_national_row(sheet, nat_cols)
        nat_fit = fit_lognormal(
            nat_data.get("p10") if nat_data else None,
            nat_data.get("p25") if nat_data else None,
            nat_data.get("p50") if nat_data else None,
            nat_data.get("p75") if nat_data else None,
        )
        if not nat_fit:
            continue
        effective_median = round(math.exp(nat_fit[0]), 1)

        all_rows = _get_all_center_rows(sheet, ctr_cols)
        count = 0
        for ctr_code, ctr_data in all_rows.items():
            factor = _compute_city_factor(ctr_data, effective_median, nat_data)
            if factor is not None:
                if ctr_code not in center_factors:
                    center_factors[ctr_code] = {}
                center_factors[ctr_code][organ] = factor
                count += 1
        print(f"  {organ}: {count} centers with wait time factors")

    result["center_wait_time_factors"] = center_factors
    result["_meta"]["totalCenters"] = len(center_factors)
    return result


def parse_all_centers_outcomes() -> dict:
    """
    Parse Table B7 for ALL centers (not just 22 cities).
    Returns center-level mortality and delisting factors.
    Phase 6A issue #117.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {
        "_meta": {
            "source": "SRTR PSR National Center-Level Summary Data (January 2025 release)",
            "method": "Center-level competing risks from Table B7 (all centers)",
            "fetchedAt": now,
        }
    }
    center_adjustments = {}
    shrinkage_meta = {}

    for organ, code in ORGAN_CODES.items():
        excel_path = os.path.join(RAW_DIR, f"csrs_final_tables_2511_{code}.xls")
        if not os.path.exists(excel_path):
            continue

        wb = xlrd.open_workbook(excel_path)
        sheet = _open_sheet(wb, B7_SHEET_NAMES)
        if not sheet:
            continue

        ctr_cols = _build_col_map(sheet, B7_COLS)
        nat_cols = _build_col_map(sheet, B7_NAT_COLS)
        nat_data = _get_national_row(sheet, nat_cols)
        if not nat_data:
            continue

        nat_mortality = (nat_data.get("died_waitlist") or 0) / 100.0
        nat_delisting = sum(
            (nat_data.get(k) or 0) for k in ["removed_worsened", "removed_improved", "removed_refused", "removed_other"]
        ) / 100.0

        all_rows = _get_all_center_rows(sheet, ctr_cols)

        # --- Pass 1: raw, UNCLAMPED ratios plus each center's cohort size ---
        # #268/L-086: a factor from a 3-patient cohort is noise, lands at an
        # extreme, and the clamp below pins it to the most favourable value —
        # so the center ranks near the top of the recommendation list. Every
        # center with n <= 10 was pinned to a bound. Shrink toward the organ
        # mean in proportion to cohort size, BEFORE clamping; shrinking after
        # is useless because the clamp has already replaced the estimate.
        raw = {}
        for ctr_code, ctr_data in all_rows.items():
            ctr_mortality = (ctr_data.get("died_waitlist") or 0) / 100.0
            ctr_delisting = sum(
                (ctr_data.get(k) or 0) for k in ["removed_worsened", "removed_improved", "removed_refused", "removed_other"]
            ) / 100.0
            raw[ctr_code] = {
                "mort": (ctr_mortality / nat_mortality) if nat_mortality > 0 else 1.0,
                "delist": (ctr_delisting / nat_delisting) if nat_delisting > 0 else 1.0,
                "mort_rate": ctr_mortality,
                "delist_rate": ctr_delisting,
                "n": ctr_data.get("n") or 0,
            }

        # --- Estimate shrinkage strength from THIS organ's data ---
        # Derived by method of moments, not chosen. estimate_k declines when
        # the model does not hold (too few centers, no spread in cohort size,
        # or no recoverable between-center signal) — pancreas and intestine
        # hit that for real, and are then left unshrunk rather than flattened.
        ns = [r["n"] for r in raw.values()]
        if organ not in eb_shrinkage.SHRINKABLE_ORGANS:
            # Measured to degrade calibration, or not estimable — see the
            # allowlist in eb_shrinkage.py for the numbers.
            k_mort = k_delist = None
        else:
            k_mort = eb_shrinkage.estimate_k(
                [r["mort_rate"] for r in raw.values()], ns, nat_mortality)
            k_delist = eb_shrinkage.estimate_k(
                [r["delist_rate"] for r in raw.values()], ns, nat_delisting)
        med_n = statistics.median([n for n in ns if n]) if any(ns) else 0
        shrinkage_meta[organ] = {
            "prior_strength_mortality": round(k_mort, 1) if k_mort else None,
            "prior_strength_delisting": round(k_delist, 1) if k_delist else None,
            # the interpretable form: what a median-sized center retains
            "median_cohort": med_n,
            "median_weight_mortality": round(eb_shrinkage.implied_weight(k_mort, med_n), 3) if k_mort else 1.0,
            "median_weight_delisting": round(eb_shrinkage.implied_weight(k_delist, med_n), 3) if k_delist else 1.0,
            "shrunk": bool(k_mort or k_delist),
        }

        # --- Pass 2: shrink, then clamp ---
        count = 0
        for ctr_code, r in raw.items():
            n = r["n"]
            mort_factor = round(max(0.3, min(eb_shrinkage.shrink(r["mort"], n, k_mort), 3.0)), 2)
            delist_factor = round(max(0.3, min(eb_shrinkage.shrink(r["delist"], n, k_delist), 3.0)), 2)

            if ctr_code not in center_adjustments:
                center_adjustments[ctr_code] = {}
            center_adjustments[ctr_code][organ] = {
                "mortality_factor": mort_factor,
                "delisting_factor": delist_factor,
            }
            count += 1
        ks = shrinkage_meta[organ]
        note = (f"shrunk: median center keeps {ks['median_weight_mortality']:.0%} "
                f"mortality / {ks['median_weight_delisting']:.0%} delisting"
                if ks["shrunk"] else "NOT shrunk — prior strength not estimable")
        print(f"  {organ}: {count} centers with competing risk factors [{note}]")

    result["center_adjustments"] = center_adjustments
    result["_meta"]["totalCenters"] = len(center_adjustments)
    result["_meta"]["shrinkage"] = shrinkage_meta
    result["_meta"]["method"] += (
        "; per-center factors shrunk toward the organ mean by empirical Bayes "
        "before clamping (#268/L-086), strength estimated by method of moments "
        "per organ — see _meta.shrinkage")
    return result


def parse_all_centers_post_transplant() -> dict:
    """
    Parse C-series tables for ALL centers (not just 22 cities).
    Returns center-level graft/patient survival.
    Phase 6A issue #117.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {
        "_meta": {
            "source": "SRTR PSR National Center-Level Summary Data (January 2025 release)",
            "method": "Center-level post-transplant outcomes from C-series tables (all centers)",
            "fetchedAt": now,
        }
    }
    center_outcomes = {}

    for organ, code in ORGAN_CODES.items():
        excel_path = os.path.join(RAW_DIR, f"csrs_final_tables_2511_{code}.xls")
        if not os.path.exists(excel_path):
            continue

        wb = xlrd.open_workbook(excel_path)

        # Graft survival
        try:
            gs_sheet = wb.sheet_by_name(GRAFT_SHEET)
        except xlrd.biffh.XLRDError:
            continue

        gs_ctr_cols = _build_col_map(gs_sheet, GRAFT_COLS)

        # Patient survival
        try:
            ps_sheet = wb.sheet_by_name(PATIENT_SHEET)
            ps_ctr_cols = _build_col_map(ps_sheet, PATIENT_COLS)
        except xlrd.biffh.XLRDError:
            ps_sheet = None
            ps_ctr_cols = {}

        gs_all = _get_all_center_rows(gs_sheet, gs_ctr_cols)
        ps_all = _get_all_center_rows(ps_sheet, ps_ctr_cols) if ps_sheet else {}

        count = 0
        for ctr_code, gs_data in gs_all.items():
            n_1yr = gs_data.get("graft_n_1yr")
            if n_1yr is not None and n_1yr < MIN_N_OUTCOMES:
                continue

            entry = {}
            gs_1yr = gs_data.get("graft_survival_1yr")
            gs_3yr = gs_data.get("graft_survival_3yr")
            gs_hr = gs_data.get("graft_hr_1yr")
            gs_hr_lo = gs_data.get("graft_hr_lo")
            gs_hr_hi = gs_data.get("graft_hr_hi")

            # 0.0% survival is an empty/censored SRTR cell, not an observed
            # rate — emitting it would show "0% survival" in the UI (found by
            # the 2026-08 range-sanity test: OHCM lung 3yr).
            if gs_1yr:
                entry["graft_survival_1yr"] = round(gs_1yr, 1)
            if gs_3yr:
                entry["graft_survival_3yr"] = round(gs_3yr, 1)
            if gs_hr is not None:
                entry["graft_hr_1yr"] = round(gs_hr, 3)
            if gs_hr_lo is not None and gs_hr_hi is not None:
                entry["graft_hr_1yr_ci"] = [round(gs_hr_lo, 3), round(gs_hr_hi, 3)]
            if n_1yr is not None:
                entry["n_1yr"] = int(n_1yr)

            ps_data = ps_all.get(ctr_code)
            if ps_data:
                ps_1yr = ps_data.get("patient_survival_1yr")
                ps_3yr = ps_data.get("patient_survival_3yr")
                ps_hr = ps_data.get("patient_hr_1yr")
                ps_hr_lo = ps_data.get("patient_hr_lo")
                ps_hr_hi = ps_data.get("patient_hr_hi")
                if ps_1yr:
                    entry["patient_survival_1yr"] = round(ps_1yr, 1)
                if ps_3yr:
                    entry["patient_survival_3yr"] = round(ps_3yr, 1)
                if ps_hr is not None:
                    entry["patient_hr_1yr"] = round(ps_hr, 3)
                if ps_hr_lo is not None and ps_hr_hi is not None:
                    entry["patient_hr_1yr_ci"] = [round(ps_hr_lo, 3), round(ps_hr_hi, 3)]

            entry["performance_rating"] = _performance_rating(gs_hr, gs_hr_lo, gs_hr_hi)

            if ctr_code not in center_outcomes:
                center_outcomes[ctr_code] = {}
            center_outcomes[ctr_code][organ] = entry
            count += 1

        print(f"  {organ}: {count} centers with post-transplant outcomes")

    result["center_outcomes"] = center_outcomes
    result["_meta"]["totalCenters"] = len(center_outcomes)
    return result


_ORGAN_KEYS = frozenset(ORGAN_CODES)


def _data_keys(d: dict) -> set:
    """Substantive top-level keys of an output dict (ignores _meta)."""
    return {k for k in d if k != "_meta"}


def _organ_count(d: dict) -> int:
    return len(_ORGAN_KEYS & _data_keys(d))


def _write_guarded(path: str, new_data: dict) -> None:
    """Write *new_data* to *path* only if it doesn't lose data vs. what's there.

    Guards (same snapshot-first philosophy as fetch-cost-of-living.js):
      - never write fewer organ blocks than the existing file has;
      - never drop a substantive top-level section the existing file has;
      - a section that exists in both must not shrink to empty.
    On guard failure the existing file is left untouched and a warning is
    printed — the parse output is treated as degraded, not authoritative.
    """
    # Deliberately retired sections (#293): the 22-city blocks are no longer
    # emitted — dropping them is the intended migration, not data loss.
    _RETIRED_SECTIONS = {"city_wait_time_factors", "city_adjustments", "city_outcomes"}

    existing = _load_existing(path)
    if existing:
        problems = []
        if _organ_count(new_data) < _organ_count(existing):
            problems.append(
                f"organ blocks would shrink {_organ_count(existing)} → {_organ_count(new_data)}"
            )
        for key in _data_keys(existing) - _data_keys(new_data) - _RETIRED_SECTIONS:
            problems.append(f"section '{key}' would be dropped")
        for key in _data_keys(existing) & _data_keys(new_data):
            old_v, new_v = existing[key], new_data[key]
            if isinstance(old_v, dict) and isinstance(new_v, dict):
                n_old = len({k for k in old_v if not k.startswith("_")})
                n_new = len({k for k in new_v if not k.startswith("_")})
                if n_old > 0 and n_new == 0:
                    problems.append(f"section '{key}' would become empty")
                # Partial shrink. The emptiness check above cannot see this,
                # and for the center-level files it is the ONLY dimension that
                # moves: their top level is _meta plus one container of 248
                # center codes, so organ blocks and section names are both
                # unchanged while the contents collapse (#444 follow-up).
                #
                # No tolerance band, matching the organ-block rule directly
                # above: ANY shrink refuses. A percentage would have to be
                # invented — the archive's workbooks can't be parsed for real
                # churn without reworking the release-pinned reader — and a
                # threshold nobody can source is the kind of constant this
                # project keeps having to justify later. A genuine release
                # that retires a center is handled by --allow-shrink, which
                # makes the loss a decision someone recorded rather than a
                # silent write.
                elif n_new < n_old:
                    lost = sorted({k for k in old_v if not k.startswith("_")} -
                                  {k for k in new_v if not k.startswith("_")})
                    problems.append(
                        f"section '{key}' would shrink {n_old} → {n_new} "
                        f"entries (dropping {', '.join(lost[:8])}"
                        f"{f' and {len(lost) - 8} more' if len(lost) > 8 else ''})"
                    )
        # srtr-historical's coverage lives in _meta, not in a data section:
        # the parse always appends the current release, so a run with
        # srtr-raw/historical/ absent produces a *truthy* 1-release dict that
        # would otherwise overwrite all 15.
        old_rel = existing.get("_meta", {}).get("releases")
        new_rel = new_data.get("_meta", {}).get("releases")
        if isinstance(old_rel, list) and isinstance(new_rel, list) and \
                len(new_rel) < len(old_rel):
            problems.append(
                f"SRTR releases would shrink {len(old_rel)} → {len(new_rel)}"
            )
        if problems and "--allow-shrink" in sys.argv:
            print(f"  Allowing shrink on {path} (--allow-shrink):")
            for p in problems:
                print(f"    - {p}")
            problems = []
        if problems:
            print(f"  REFUSING to write {path} (degraded parse):")
            for p in problems:
                print(f"    - {p}")
            print("    Existing file kept. Ensure data/srtr-raw/ has the current release Excels.")
            print("    If the loss is real (a center genuinely left the SRTR report),")
            print("    re-run with --allow-shrink to record it deliberately.")
            return
    with open(path, "w") as f:
        json.dump(new_data, f, indent=2)
        f.write("\n")
    print(f"Wrote {path}")


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
            _write_guarded(HISTORICAL_OUT, historical_data)
    else:
        print("\n  Skipping historical trends (no historical data in srtr-raw/historical/)")
        print("  Run: python scripts/fetch-srtr-excel.py --historical to download")

    # Write city-level output files — guarded so a degraded parse (e.g. CI,
    # where data/srtr-raw/ is gitignored and the current-release Excels are
    # absent) can never clobber good committed data. The 2026-08-05 workflow
    # run did exactly that: every organ hit "not found, skipping" and the
    # organ-less shells overwrote all three files on main.
    _write_guarded(WAIT_TIME_OUT, wait_data)
    _write_guarded(COMPETING_OUT, outcome_data)
    _write_guarded(OUTCOMES_OUT, pt_outcomes)

    # Phase 6A: Center-level extraction (all ~250 centers)
    if "--all-centers" in sys.argv or "--all" in sys.argv:
        print("\n=== Phase 6A: Parsing ALL Center Wait Times (Table B10) ===")
        centers_wait = parse_all_centers_wait_times()
        _write_guarded(CENTERS_WAIT_OUT, centers_wait)

        print("\n=== Phase 6A: Parsing ALL Center Competing Risks (Table B7) ===")
        centers_competing = parse_all_centers_outcomes()
        _write_guarded(CENTERS_COMPETING_OUT, centers_competing)

        print("\n=== Phase 6A: Parsing ALL Center Post-Transplant Outcomes ===")
        centers_outcomes = parse_all_centers_post_transplant()
        _write_guarded(CENTERS_OUTCOMES_OUT, centers_outcomes)

    # Summary
    n_organs = len([k for k in wait_data if not k.startswith("_")])
    print(f"\nSummary: {n_organs} organs (city_* blocks retired, #293)")
    if "--all-centers" in sys.argv or "--all" in sys.argv:
        print(f"  Center-level: wait={centers_wait['_meta']['totalCenters']}, competing={centers_competing['_meta']['totalCenters']}, outcomes={centers_outcomes['_meta']['totalCenters']} centers")


if __name__ == "__main__":
    main()
