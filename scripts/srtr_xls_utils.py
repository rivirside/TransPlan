"""Shared SRTR xls parsing/derivation helpers (#339).

Single source for the cell parsing, sheet scanning, and lognormal/factor
derivations that parse-srtr-reports.py, run-temporal-forecast.py, and
fetch-srtr-observed-rates.py previously carried as drifting copies — the
temporal forecast's validity claim is "exactly the parser's derivation",
and this module makes that true by construction.

Load from a sibling script via the established importlib idiom:

    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "srtr_xls_utils", Path(__file__).parent / "srtr_xls_utils.py")
    sx = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(sx)
"""
import math
import re

CENSORED = -999.0  # sentinel for ">72" censored values

# Sigma clamp for wait-time lognormals (#256/#274: the 1.2 ceiling binds for
# long-wait organs and is tracked for re-evaluation — change it HERE only).
SIGMA_CLAMP = (0.3, 1.2)
# Center wait-factor clamps + the factor assigned when the center median is
# censored (">72") but the national median is valid.
FACTOR_CLAMP = (0.3, 3.0)
CENSORED_FACTOR = 2.5


def safe_float(val) -> float | None:
    """Parse a cell value as float, handling '>72' style strings and blanks."""
    if isinstance(val, (int, float)):
        return float(val) if val != "" else None
    s = str(val).strip()
    if not s:
        return None
    if s.startswith(">"):
        return CENSORED
    try:
        return float(s)
    except ValueError:
        return None


def is_valid(val: float | None) -> bool:
    """True for a usable percentile value (not None/censored, positive)."""
    return val is not None and val != CENSORED and val > 0


def is_center_code(v) -> bool:
    """True for SRTR center-code cells (3-5 uppercase alphanumerics)."""
    s = str(v).strip()
    return bool(re.fullmatch(r"[A-Z0-9]{3,5}", s)) and s != "CTR_CD"


def col_index(header_or_sheet, name: str) -> int:
    """Column index by header name; accepts a header list or an xlrd sheet
    (row 0 headers). -1 when absent."""
    if hasattr(header_or_sheet, "cell_value"):
        sheet = header_or_sheet
        for c in range(sheet.ncols):
            if str(sheet.cell_value(0, c)).strip() == name:
                return c
        return -1
    try:
        return [str(h).strip() for h in header_or_sheet].index(name)
    except ValueError:
        return -1


def find_sheet_with(wb, required_col: str, preferred: tuple[str, ...] = ()):
    """(sheet, header list) for the first sheet whose row 0 carries
    *required_col*; *preferred* sheet names are tried first. Era-proof:
    SRTR renamed sheets (B9->B10, B6->B7 at release 2111) but kept columns.
    Returns (None, None) when no sheet qualifies."""
    ordered = [n for n in preferred if n in wb.sheet_names()]
    ordered += [n for n in wb.sheet_names() if n not in ordered]
    for name in ordered:
        sh = wb.sheet_by_name(name)
        if sh.nrows < 3 or sh.ncols < 2:
            continue
        hdr = [str(sh.cell_value(0, c)).strip() for c in range(sh.ncols)]
        if required_col in hdr:
            return sh, hdr
    return None, None


def all_center_rows(sheet, hdr, cols: dict) -> dict:
    """{center_code: {key: parsed value}} for every center row of a sheet."""
    ctr = col_index(hdr, "CTR_CD")
    if ctr < 0:
        return {}
    idx = {k: col_index(hdr, c) for k, c in cols.items()}
    out = {}
    for r in range(1, sheet.nrows):
        code = str(sheet.cell_value(r, ctr)).strip()
        if not is_center_code(code):
            continue
        out[code] = {k: (safe_float(sheet.cell_value(r, i)) if i >= 0 else None)
                     for k, i in idx.items()}
    return out


def sigma_from_percentiles(p10, p25, p50, p75) -> float:
    """Lognormal sigma from wait-time percentiles — the canonical strategy
    chain (see parse-srtr-reports.py fit_lognormal for the rationale:
    lower quantiles are censoring-robust for SRTR data):
      1. P10-P25 spread   2. IQR   3. P10-P50   4. fallback 0.8
    Clamped to SIGMA_CLAMP."""
    if is_valid(p10) and is_valid(p25) and p25 > p10:
        sigma = (math.log(p25) - math.log(p10)) / (1.2816 - 0.6745)
    elif is_valid(p25) and is_valid(p75) and p75 > p25:
        sigma = (math.log(p75) - math.log(p25)) / (2 * 0.6745)
    elif is_valid(p10) and is_valid(p50) and p50 > p10:
        sigma = (math.log(p50) - math.log(p10)) / 1.2816
    else:
        sigma = 0.8
    return max(SIGMA_CLAMP[0], min(sigma, SIGMA_CLAMP[1]))


def wait_factor_from_percentiles(ctr: dict, nat: dict) -> float | None:
    """Center wait factor vs national — P50 ratio, P25 fallback, and the
    CENSORED_FACTOR when the center median is '>72'. Clamped to
    FACTOR_CLAMP. Keys: p25/p50 in both dicts."""
    p50_c, p25_c = ctr.get("p50"), ctr.get("p25")
    p50_n, p25_n = nat.get("p50"), nat.get("p25")
    if is_valid(p50_c) and is_valid(p50_n):
        return max(FACTOR_CLAMP[0], min(p50_c / p50_n, FACTOR_CLAMP[1]))
    if is_valid(p25_c) and is_valid(p25_n):
        return max(FACTOR_CLAMP[0], min(p25_c / p25_n, FACTOR_CLAMP[1]))
    if p50_c == CENSORED and is_valid(p50_n):
        return CENSORED_FACTOR
    return None
