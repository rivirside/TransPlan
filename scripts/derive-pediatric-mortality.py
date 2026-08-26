#!/usr/bin/env python3
"""Derive the BBN pediatric age-group mortality multipliers from SRTR (#335).

The BBN's `age_to_group` used to clamp every child to the "18-34" bucket
(bbn_parameterizer.py:961, BBN-22 / #298). That clamp is not merely coarse —
it points the wrong way for some organs and badly the wrong way for others:

    kidney  pediatric waitlist hazard 0.57x adult  (children die less)
    heart   pediatric waitlist hazard 3.35x adult  (congenital disease)

Clamping to the youngest ADULT bucket (multiplier 0.4, or 0.3 for heart)
therefore understates pediatric heart waitlist mortality by roughly an order
of magnitude. This script replaces the clamp's implied constant with a ratio
measured from the data we already parse.

Method
------
Pediatric hazard: person-year-weighted mean of the per-center pediatric
waitlist death RATE (`TMR_p0_DthR_c`, already per person-year) over
`data/pediatric-centers.json`.

Adult hazard: cohort-weighted mean of -ln(1 - p) over the adult 12-month
waitlist death percentage from Table B7, i.e. the percentage converted to a
constant annual hazard so the two are on the same scale.

The per-organ ratio is then shrunk toward the pooled all-organ ratio by
w = py / (py + SHRINK_PY), the same empirical-Bayes form used for pediatric
per-center estimates in monte_carlo._pediatric_dist. This matters: pediatric
lung has 39 person-years nationally, so its raw 2.21 is mostly noise.

Anchor: the ratio is measured against the ALL-LISTED-ADULT hazard, and the
`annual_mortality_rate` these multipliers scale is itself an all-ages rate,
so multiplier 1.0 means "the average listed adult" — the same convention the
existing table approximates by pinning 50-64 to 1.0.

Writes into the manual age blocks of data/competing-risks.json, which
scripts/parse-srtr-reports.py explicitly carries forward across regenerations.
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "backend"))

from services.data_loader import get_data, load_all  # noqa: E402

PEDS_FILE = REPO / "data" / "pediatric-centers.json"
CR_FILE = REPO / "data" / "competing-risks.json"
REPORT = REPO / "docs" / "pediatric-mortality-derivation.md"

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas"]
PEDS_GROUP = "0-17"
SHRINK_PY = 200.0   # person-years at which a per-organ estimate gets half weight
MIN_ADULT_N = 25    # same cohort floor the inversion gate uses
# Sanity band. A multiplier outside this is a parsing or units error, not a
# clinical finding — fail loudly rather than shipping it (2026-08-05 rule).
PLAUSIBLE = (0.05, 20.0)


def pediatric_hazard(organ: str, peds: dict) -> tuple[float | None, float]:
    """(person-year-weighted pediatric hazard per year, total person-years)."""
    num = den = 0.0
    for rec in peds.get(organ, {}).get("centers", {}).values():
        py = rec.get("person_years") or 0.0
        rate = rec.get("death_rate")
        if py > 0 and rate is not None:
            num += rate * py
            den += py
    return (num / den if den else None), den


def adult_hazard(organ: str) -> float | None:
    """Cohort-weighted adult annual hazard from the Table B7 12-month rate."""
    data = get_data()
    factors = data.center_wait_times.get("center_wait_time_factors", {})
    num = den = 0.0
    for code in factors:
        obs = data.observed_outcome(organ, code)
        if not obs or obs.get("n", 0) < MIN_ADULT_N:
            continue
        pct = obs.get("waitlist_death_rate")
        if pct is None or not 0.0 <= pct < 100.0:
            continue
        num += -math.log(max(1e-9, 1.0 - pct / 100.0)) * obs["n"]
        den += obs["n"]
    return (num / den) if den else None


def main() -> int:
    load_all()
    peds = json.loads(PEDS_FILE.read_text())

    raw = {}
    for organ in ORGANS:
        ped_h, py = pediatric_hazard(organ, peds)
        adult_h = adult_hazard(organ)
        if ped_h is None or not adult_h:
            continue
        raw[organ] = {"ratio": ped_h / adult_h, "py": py,
                      "ped_hazard": ped_h, "adult_hazard": adult_h}

    if not raw:
        print("ERROR: no organ had both pediatric and adult hazards", file=sys.stderr)
        return 1

    # Pooled prior: person-year-weighted mean of the per-organ ratios.
    tot_py = sum(r["py"] for r in raw.values())
    pooled = sum(r["ratio"] * r["py"] for r in raw.values()) / tot_py

    rows = []
    for organ, r in sorted(raw.items()):
        w = r["py"] / (r["py"] + SHRINK_PY)
        shrunk = w * r["ratio"] + (1.0 - w) * pooled
        if not PLAUSIBLE[0] <= shrunk <= PLAUSIBLE[1]:
            print(f"ERROR: {organ} multiplier {shrunk:.3f} outside "
                  f"{PLAUSIBLE} — refusing to write", file=sys.stderr)
            return 1
        r["shrunk"] = round(shrunk, 3)
        r["weight"] = round(w, 3)
        rows.append((organ, r))

    cr = json.loads(CR_FILE.read_text())
    cr.setdefault("age_mortality_multipliers", {})[PEDS_GROUP] = round(pooled, 3)
    overrides = cr.setdefault("age_organ_overrides", {})
    for organ, r in rows:
        overrides.setdefault(organ, {})[PEDS_GROUP] = r["shrunk"]
    cr["age_mortality_multipliers"]["_pediatric_notes"] = (
        f"'{PEDS_GROUP}' derived by scripts/derive-pediatric-mortality.py from "
        f"SRTR pediatric waitlist death rates vs adult Table B7, shrunk toward "
        f"the pooled ratio at {SHRINK_PY:.0f} person-years. Anchored to the "
        f"all-listed-adult hazard (multiplier 1.0 = average listed adult).")

    CR_FILE.write_text(json.dumps(cr, indent=2) + "\n")

    lines = [
        "# Pediatric waitlist-mortality multipliers (#335)", "",
        "The BBN previously clamped every pediatric candidate into the",
        "`18-34` bucket. These are the measured ratios that replace it.", "",
        "| organ | ped hazard/yr | adult hazard/yr | raw ratio | ped person-yrs |"
        " weight | shipped multiplier |",
        "|---|---|---|---|---|---|---|",
    ]
    for organ, r in rows:
        lines.append(
            f"| {organ} | {r['ped_hazard']:.4f} | {r['adult_hazard']:.4f} | "
            f"{r['ratio']:.3f} | {r['py']:.0f} | {r['weight']:.2f} | "
            f"**{r['shrunk']:.3f}** |")
    lines += [
        "", f"Pooled (default for organs with no pediatric data): "
        f"**{pooled:.3f}**", "",
        "## Reading these", "",
        "The direction reverses by organ, which is why a single pediatric",
        "constant would have been wrong no matter how it was chosen:",
        "pediatric kidney candidates die on the waitlist at roughly half the",
        "adult rate, while pediatric heart candidates die at several times the",
        "adult rate — the congenital-disease population listed as infants. The",
        "old clamp assigned heart children the 18-34 heart multiplier of 0.3,",
        "understating their waitlist mortality by about an order of magnitude.",
        "",
        "Lung's raw ratio rests on 39 national pediatric person-years and is",
        "mostly noise, which is what the shrinkage is for; its shipped value",
        "sits close to the pooled prior. Treat lung and pancreas pediatric",
        "mortality as prior-dominated, not measured.", "",
        f"Generated by `scripts/derive-pediatric-mortality.py` on "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.", "",
    ]
    REPORT.write_text("\n".join(lines))

    for organ, r in rows:
        print(f"{organ:9s} raw={r['ratio']:.3f} py={r['py']:7.0f} "
              f"w={r['weight']:.2f} -> {r['shrunk']:.3f}")
    print(f"pooled default = {pooled:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
