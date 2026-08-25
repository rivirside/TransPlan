#!/usr/bin/env python3
"""
Per-center living-donor program strength from SRTR Table D1 (#292, epic #285).

Replaces the 22-city hand-curated livingDonorProgramStrength block in
data/donor-registration.json — which was ALSO dead at runtime: scoring.py
matched city names as substrings of state names ("Minneapolis" in
"Minnesota"), which never hits, so the 28% living-donor component was a
constant 75 for every center.

Derivation: LD_CT_1C ("Number of Living Donors", 1-year center count) from the
current release's Table D1, for the organs where living donation exists
(kidney, liver). Score = 100 x log1p(count) / log1p(max_count) within each
organ — log-scaled so the huge programs don't flatten everyone else, anchored
at 0 for zero living donors.

Output: data/living-donor-centers.json. Never-shrink guard.

Usage:
    cd TransPlan && .venv/bin/python scripts/fetch-living-donor-centers.py [--release 2511]
"""
import argparse
import json
import math
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import xlrd

REPO_ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = REPO_ROOT / "data" / "srtr-archive"
OUT_PATH = REPO_ROOT / "data" / "living-donor-centers.json"

LIVING_ORGANS = {"kidney": "KI", "liver": "LI"}


def _is_center_code(v) -> bool:
    s = str(v).strip()
    return bool(re.fullmatch(r"[A-Z0-9]{3,5}", s)) and s != "CTR_CD"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", default="2511")
    args = parser.parse_args()

    zip_path = ARCHIVE_DIR / f"csrs_final_tables_{args.release}all.zip"
    zf = zipfile.ZipFile(zip_path)

    counts: dict[str, dict[str, int]] = {}
    for organ, oc in LIVING_ORGANS.items():
        name = next(n for n in zf.namelist() if re.search(rf"_{oc}\.xls$", n, re.I))
        wb = xlrd.open_workbook(file_contents=zf.read(name))
        if "Table D1" not in wb.sheet_names():
            raise SystemExit(f"{organ}: Table D1 missing — schema change?")
        sh = wb.sheet_by_name("Table D1")
        hdr = [str(sh.cell_value(0, c)) for c in range(sh.ncols)]
        ctr, ld = hdr.index("CTR_CD"), hdr.index("LD_CT_1C")
        organ_counts = {}
        for r in range(1, sh.nrows):
            code = str(sh.cell_value(r, ctr)).strip()
            if not _is_center_code(code):
                continue
            try:
                organ_counts[code] = int(float(sh.cell_value(r, ld)))
            except (ValueError, TypeError):
                continue
        counts[organ] = organ_counts
        print(f"{organ}: {len(organ_counts)} centers, "
              f"total living donors {sum(organ_counts.values())}")

    scores = {}
    for organ, oc_counts in counts.items():
        max_log = math.log1p(max(oc_counts.values())) if oc_counts else 1.0
        scores[organ] = {
            code: round(100.0 * math.log1p(n) / max_log, 1)
            for code, n in oc_counts.items()
        }

    out = {
        "_meta": {
            "source": f"SRTR PSR release {args.release}, Table D1 LD_CT_1C (1-yr living donor count per center)",
            "script": "scripts/fetch-living-donor-centers.py",
            "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "method": ("score = 100·log1p(count)/log1p(max count) within organ; "
                       "living donation exists only for kidney and liver — other "
                       "organs have no entry and scoring uses a neutral value."),
        },
        "counts": counts,
        "scores": scores,
    }

    if OUT_PATH.exists():
        old = json.loads(OUT_PATH.read_text())
        old_n = sum(len(v) for v in old.get("scores", {}).values())
        new_n = sum(len(v) for v in scores.values())
        if new_n < old_n:
            raise SystemExit(f"NEVER-SHRINK GUARD: {new_n} < {old_n} center-organ scores.")

    OUT_PATH.write_text(json.dumps(out, indent=1))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
