#!/usr/bin/env python3
"""Extract per-center Offer Acceptance Rate Ratios from SRTR PSR Table B11
(#320, the L-075 observed-discretion covariate).

The OARR is SRTR's risk-adjusted measure of center offer-acceptance
behavior: observed acceptances / model-expected acceptances, with 95%
credible bounds. It is the DIRECT measurement of the discretion the model
previously inferred from volume proxies (SURV-28), and it spans the whole
archive (2018-2025), enabling a time panel.

Reads the current release from data/srtr-raw/*.xls (staged from the archive
zips) and writes data/offer-acceptance-centers.json:

  {organ: {centers: {code: {oar, ci95: [lb, ub], offers, accepts,
                            expected, lowrisk_oar, hardtoplace_oar}},
           national_oar}}

Never-shrink guarded; validate-data.js enforces coverage floors.
"""
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import xlrd

REPO = Path(__file__).parent.parent
RAW = REPO / "data" / "srtr-raw"
OUT = REPO / "data" / "offer-acceptance-centers.json"

_sx_spec = importlib.util.spec_from_file_location(
    "srtr_xls_utils", REPO / "scripts" / "srtr_xls_utils.py")
sx = importlib.util.module_from_spec(_sx_spec)
_sx_spec.loader.exec_module(sx)

ORGAN_CODES = {"kidney": "KI", "liver": "LI", "heart": "HR", "lung": "LU",
               "pancreas": "PA", "intestine": "IN"}

# Subset prefixes present in Table B11 (2511): OVERALL always; the others
# where published for the organ
SUBSETS = {"oar": "OA_OVERALL", "lowrisk_oar": "OA_LOWRISK",
           "hardtoplace_oar": "OA_HARDTOPLACE"}


def extract_organ(path: Path) -> dict | None:
    wb = xlrd.open_workbook(str(path))
    sheet, hdr = sx.find_sheet_with(wb, "OA_OVERALL_HR_MN_CENTER",
                                    preferred=("Table B11 & Figures B10-B14",))
    if sheet is None:
        return None
    cols = {}
    for key, prefix in SUBSETS.items():
        cols[key] = sx.col_index(hdr, f"{prefix}_HR_MN_CENTER")
        cols[f"{key}_lb"] = sx.col_index(hdr, f"{prefix}_HR_LB_CENTER")
        cols[f"{key}_ub"] = sx.col_index(hdr, f"{prefix}_HR_UB_CENTER")
    for k, c in (("offers", "OA_OVERALL_OFFERS_CENTER"),
                 ("accepts", "OA_OVERALL_ACCEPTS_CENTER"),
                 ("expected", "OA_OVERALL_EXP_ACCEPTS_CENTER")):
        cols[k] = sx.col_index(hdr, c)
    nat_col = sx.col_index(hdr, "OA_OVERALL_HR_MN_NATION")

    ctr_col = sx.col_index(hdr, "CTR_CD")
    centers = {}
    national = None
    for r in range(1, sheet.nrows):
        code = str(sheet.cell_value(r, ctr_col)).strip()
        if not sx.is_center_code(code):
            continue
        rec = {}
        oar = sx.safe_float(sheet.cell_value(r, cols["oar"]))
        if oar is None or oar == sx.CENSORED:
            continue
        rec["oar"] = round(oar, 3)
        lb = sx.safe_float(sheet.cell_value(r, cols["oar_lb"]))
        ub = sx.safe_float(sheet.cell_value(r, cols["oar_ub"]))
        if sx.is_valid(lb) and sx.is_valid(ub):
            rec["ci95"] = [round(lb, 3), round(ub, 3)]
        for k in ("offers", "accepts", "expected"):
            v = sx.safe_float(sheet.cell_value(r, cols[k]))
            if v is not None and v != sx.CENSORED:
                rec[k] = round(v, 2)
        for sub in ("lowrisk_oar", "hardtoplace_oar"):
            if cols[sub] >= 0:
                v = sx.safe_float(sheet.cell_value(r, cols[sub]))
                if sx.is_valid(v):
                    rec[sub] = round(v, 3)
        centers[code] = rec
        if national is None and nat_col >= 0:
            nv = sx.safe_float(sheet.cell_value(r, nat_col))
            if sx.is_valid(nv):
                national = round(nv, 3)
    return {"centers": centers, "national_oar": national}


def extract_panel() -> dict:
    """OARR time panel over every archived release (#320 remainder / #358).

    {organ: {code: {release: oar}}} — the per-release risk-adjusted ratios,
    giving the discretion covariate a time dimension (drift, stability, and
    the release-effects modeling #358 needs).
    """
    import re
    import zipfile
    archive = REPO / "data" / "srtr-archive"
    panel: dict = {o: {} for o in ORGAN_CODES}
    for z in sorted(archive.glob("csrs_final_tables_*all.zip")):
        rel = re.search(r"_(\d{4})all", z.name).group(1)
        zf = zipfile.ZipFile(z)
        for organ, oc in ORGAN_CODES.items():
            names = [n for n in zf.namelist() if n.endswith(f"_{oc}.xls")]
            if not names:
                continue
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".xls") as tmp:
                tmp.write(zf.read(names[0]))
                tmp.flush()
                block = extract_organ(Path(tmp.name))
            if not block:
                continue
            for code, rec in block["centers"].items():
                panel[organ].setdefault(code, {})[rel] = rec["oar"]
        print(f"  panel: release {rel} done")
    return panel


def main():
    result = {"_meta": {
        "source": "SRTR PSR Table B11 (offer acceptance), release 2511",
        "method": "OARR = risk-adjusted acceptances/expected (SRTR Bayesian "
                  "model) with 95% credible bounds; OVERALL plus LOWRISK/"
                  "HARDTOPLACE subsets where published. #320: the observed "
                  "center-discretion covariate L-075 called for.",
        "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }}
    total = 0
    for organ, code in ORGAN_CODES.items():
        path = RAW / f"csrs_final_tables_2511_{code}.xls"
        if not path.exists():
            print(f"  {organ}: raw file missing — skipped")
            continue
        block = extract_organ(path)
        if block:
            result[organ] = block
            total += len(block["centers"])
            print(f"  {organ}: {len(block['centers'])} centers "
                  f"(national OARR {block['national_oar']})")

    # Never-shrink guard (2026-08-05 incident rule)
    if OUT.exists():
        old = json.loads(OUT.read_text())
        old_total = sum(len(old.get(o, {}).get("centers", {}))
                        for o in ORGAN_CODES)
        if total < 0.9 * old_total:
            print(f"REFUSING to shrink: {total} < 90% of {old_total}")
            return 1
    OUT.write_text(json.dumps(result, indent=1))
    print(f"Wrote {OUT} ({total} center-organ OARRs)")

    if "--panel" in sys.argv:
        panel = extract_panel()
        panel_out = REPO / "data" / "offer-acceptance-panel.json"
        n_series = sum(len(v) for v in panel.values())
        if panel_out.exists():
            old_n = sum(len(v) for v in json.loads(panel_out.read_text())
                        .get("panel", {}).values())
            if n_series < 0.9 * old_n:
                print(f"REFUSING to shrink panel: {n_series} < 90% of {old_n}")
                return 1
        panel_out.write_text(json.dumps({
            "_meta": {"source": "SRTR PSR Table B11 across all archived "
                                "releases", "fetchedAt": datetime.now(
                                    timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
            "panel": panel,
        }, indent=1))
        print(f"Wrote {panel_out} ({n_series} center-organ series)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
