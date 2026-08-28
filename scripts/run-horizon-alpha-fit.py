#!/usr/bin/env python3
"""Fit the 12->24 month exponent from SRTR's own three horizons (#233 / L-095).

`_extend_12_to_24` assumes constant cause-specific hazards, S(24) = S(12)**2.
That was carried as untestable because SRTR publishes 12-month outcomes and
the model reports at 24.

It is testable. Table B7 publishes the SAME cohort at 6, 12 and 18 months
(SAL_*_U6 / _U12 / _U18), which is enough to observe the hazard's SHAPE — and
shape is exactly what the exponent encodes.

Method:
  1. National still-waiting share S(t) = 1 - sum(terminal outcomes) at each
     horizon.
  2. Interval hazards lambda = -dlnS/dt over 0-6, 6-12, 12-18.
  3. Extrapolate the 12-18 hazard across 18-24 to get S(24).
  4. Solve S(24) = S(12)**alpha.

The pancreas result is the control: it is the one organ whose hazard is flat,
and the method returns alpha ~ 2.07 there — recovering the shipped assumption
exactly where the shipped assumption holds.

Usage:
    python3 scripts/run-horizon-alpha-fit.py
"""
import json
import math
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))

import xlrd  # noqa: E402

from artifact_meta import stamped_meta  # noqa: E402

RAW = Path(__file__).parent.parent / "data" / "srtr-raw"
ORGANS = [("kidney", "KI"), ("liver", "LI"), ("heart", "HR"),
          ("lung", "LU"), ("pancreas", "PA"), ("intestine", "IN")]
# Every way a candidate leaves the list; the remainder is still waiting.
TERMINAL = ["SAL_TOTTX", "SAL_WLDIED", "SAL_REMDET",
            "SAL_REMREC", "SAL_REFTX", "SAL_REMOTH"]
HORIZONS = (6, 12, 18)


def national_survival(code: str) -> dict[int, float] | None:
    """Still-waiting share at 6/12/18 months, national (the _U columns)."""
    path = RAW / f"csrs_final_tables_2511_{code}.xls"
    if not path.exists():
        return None
    sheet = xlrd.open_workbook(str(path)).sheet_by_name("Table B7")
    header = {str(sheet.cell_value(0, c)): c for c in range(sheet.ncols)}

    def value(name: str) -> float | None:
        col = header.get(name)
        if col is None:
            return None
        try:
            return float(sheet.cell_value(2, col))
        except (TypeError, ValueError):
            return None

    out = {}
    for h in HORIZONS:
        parts = [value(f"{t}_U{h}") for t in TERMINAL]
        if any(p is None for p in parts):
            return None
        out[h] = 1.0 - sum(parts) / 100.0
    return out


def main() -> int:
    rows = []
    for organ, code in ORGANS:
        s = national_survival(code)
        if not s or any(not (0.0 < v < 1.0) for v in s.values()):
            print(f"{organ}: unusable survival vector {s}")
            continue
        lam = {
            "0-6": -math.log(s[6]) / 6.0,
            "6-12": -(math.log(s[12]) - math.log(s[6])) / 6.0,
            "12-18": -(math.log(s[18]) - math.log(s[12])) / 6.0,
        }
        s24 = s[18] * math.exp(-lam["12-18"] * 6.0)
        alpha = math.log(s24) / math.log(s[12])
        falling = lam["0-6"] > lam["6-12"] > lam["12-18"]
        rows.append({
            "organ": organ,
            "survival": {str(h): round(s[h], 4) for h in HORIZONS},
            "interval_hazards": {k: round(v, 4) for k, v in lam.items()},
            "hazard_monotonically_falling": falling,
            "implied_s24": round(s24, 4),
            "implied_alpha": round(alpha, 3),
            "shipped_alpha": 2.0,
        })

    falling = [r["organ"] for r in rows if r["hazard_monotonically_falling"]]
    below = [r["organ"] for r in rows if r["implied_alpha"] < 2.0]
    out = {
        "_meta": stamped_meta(
            description="Fitted 12->24 month horizon exponent from SRTR "
                        "C6/C12/C18 (#233 / L-095)",
            script="scripts/run-horizon-alpha-fit.py",
            method="alpha solves S(24)=S(12)**alpha with S(24) extrapolated "
                   "from the observed 12-18 hazard",
            caveat="18-24 is unobserved. Since the hazard falls at every "
                   "observed step, holding it flat across 18-24 likely still "
                   "OVERSTATES terminal outcomes, so these alphas are "
                   "probably conservative (true alpha lower).",
        ),
        "hazard_falling_for": falling,
        "alpha_below_shipped_for": below,
        "results": rows,
    }
    dest = Path(__file__).parent.parent / "data" / "horizon-alpha-fit.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")

    print(f"{'organ':10s} {'S(6)':>7s} {'S(12)':>7s} {'S(18)':>7s} "
          f"{'implied α':>10s} {'shipped':>8s} {'falling?':>9s}")
    for r in rows:
        s = r["survival"]
        print(f"{r['organ']:10s} {s['6']:7.4f} {s['12']:7.4f} {s['18']:7.4f} "
              f"{r['implied_alpha']:10.3f} {r['shipped_alpha']:8.1f} "
              f"{'yes' if r['hazard_monotonically_falling'] else 'NO':>9s}")
    print(f"\nhazard falls monotonically for {len(falling)}/{len(rows)}: {falling}")
    print(f"implied alpha below the shipped 2.0 for {len(below)}/{len(rows)}: {below}")
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
