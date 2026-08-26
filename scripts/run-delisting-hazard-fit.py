#!/usr/bin/env python3
"""Fit the wait-category delisting multipliers from observed data (#297).

`build_delisting_risk_cpt` scales the delisting rate by WaitCategory using
four hand-set numbers:

    wait_delist_mults = [0.5, 0.8, 1.2, 1.8]     # <=6mo, 6-12, 12-24, >24

The code comment argues these cannot be fitted, because "regressing observed
delisting on the wait category is circular (the category derives from the
same wait factors)". That objection is right about the obvious approach and
wrong about the conclusion.

The obvious approach — regress each CENTER's observed delisting rate on that
center's wait factor — is indeed confounded, and not only circularly: it
estimates a BETWEEN-CENTER contrast (do slow programs delist more?) when the
multiplier encodes a WITHIN-PATIENT one (does *this* candidate's risk rise
the longer they wait?). Those are different quantities, and centers with long
waits differ systematically in case mix.

But SRTR publishes waitlist removals at **6, 12 AND 18 months** nationally
(`SAL_REMDET/REMOTH/REMREC_U6/U12/U18`, Table B7). Cumulative removal at
three horizons in one cohort gives the interval hazard directly:

    h(t1,t2] = -ln( (1 - C(t2)) / (1 - C(t1)) ) / (t2 - t1)

That is a within-cohort measurement of exactly the escalation the
multipliers claim to encode, with no between-center contrast anywhere in it.

What it can and cannot reach
----------------------------
The WaitCategory bands are <=6, 6-12, 12-24, >24 months. The data covers
0-6, 6-12 and 12-18. So bands 1 and 2 are measured directly, band 3 is
measured over its first half, and band 4 lies entirely beyond the published
horizons and must be extrapolated. The report says which is which rather than
presenting four equally-grounded numbers.

Outputs: docs/delisting-hazard-report.md,
         docs-site/static/data/delisting-hazard.json
"""
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

import srtr_xls_utils as sx  # noqa: E402
import xlrd  # noqa: E402
from artifact_meta import stamped_meta  # noqa: E402

ORGAN_CODES = {"kidney": "KI", "liver": "LI", "heart": "HR",
               "lung": "LU", "pancreas": "PA", "intestine": "IN"}
HORIZONS = (6, 12, 18)
REMOVAL_KINDS = ("REMDET", "REMOTH", "REMREC")
# The four states of WaitCategory, in CPT order.
BANDS = ["<=6mo", "6-12mo", "12-24mo", ">24mo"]
CURRENT_MULTS = [0.5, 0.8, 1.2, 1.8]


def cumulative_removals(code: str) -> dict[int, float]:
    """National cumulative removal-without-transplant share at each horizon."""
    sheet = xlrd.open_workbook(
        str(REPO / "data" / "srtr-raw" /
            f"csrs_final_tables_2511_{code}.xls")).sheet_by_name("Table B7")
    hdr = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]

    def nat(col: str):
        i = sx.col_index(hdr, col)
        if i < 0:
            return None
        for r in range(1, sheet.nrows):
            v = sx.safe_float(sheet.cell_value(r, i))
            if v is not None:
                return v
        return None

    out = {}
    for m in HORIZONS:
        parts = [nat(f"SAL_{k}_U{m}") for k in REMOVAL_KINDS]
        if any(p is None for p in parts):
            return {}
        out[m] = sum(parts) / 100.0     # published as percentages
    return out


def interval_hazards(cum: dict[int, float]) -> dict[str, float] | None:
    """Per-month hazard within each observed interval.

    Uses survival ratios rather than differencing the cumulative shares: the
    denominator must be the population still at risk at the start of the
    interval, not the original cohort, or later intervals are understated.
    """
    if not cum or any(not 0 <= cum[m] < 1 for m in HORIZONS):
        return None
    prev_t, prev_c = 0, 0.0
    out = {}
    for t in HORIZONS:
        surv_ratio = (1 - cum[t]) / (1 - prev_c)
        if surv_ratio <= 0:
            return None
        out[f"{prev_t}-{t}"] = -math.log(surv_ratio) / (t - prev_t)
        prev_t, prev_c = t, cum[t]
    return out


def main() -> int:
    results = {}
    for organ, code in ORGAN_CODES.items():
        cum = cumulative_removals(code)
        hz = interval_hazards(cum)
        if not hz:
            print(f"  {organ:10s} no usable 6/12/18-month removal data")
            results[organ] = {"assessable": False}
            continue
        base = hz["0-6"]
        ratios = {k: v / base for k, v in hz.items()} if base > 0 else {}
        results[organ] = {
            "assessable": True,
            "cumulative_removed": {str(k): round(v, 5) for k, v in cum.items()},
            "monthly_hazard": {k: round(v, 6) for k, v in hz.items()},
            "hazard_ratio_vs_first_6mo": {k: round(v, 4) for k, v in ratios.items()},
        }
        print(f"  {organ:10s} hazard/mo 0-6={hz['0-6']:.5f} 6-12={hz['6-12']:.5f} "
              f"12-18={hz['12-18']:.5f}  ratios 1.00 / "
              f"{ratios['6-12']:.2f} / {ratios['12-18']:.2f}")

    assessable = {o: r for o, r in results.items() if r.get("assessable")}
    if not assessable:
        print("ERROR: no organ had usable data", file=sys.stderr)
        return 1

    # A pooled mean is kept for completeness but is NOT the headline: the
    # organs disagree in DIRECTION (kidney rises, lung falls to an eighth), so
    # an average across them describes no organ. The per-organ table is the
    # result.
    pooled = {}
    for key in ("6-12", "12-18"):
        vals = [r["hazard_ratio_vs_first_6mo"][key] for r in assessable.values()]
        pooled[key] = sum(vals) / len(vals)

    # The current multipliers, expressed the same way for comparison.
    current_ratios = [m / CURRENT_MULTS[0] for m in CURRENT_MULTS]

    doc = {
        "organs": results,
        "pooled_hazard_ratio_vs_first_6mo": {k: round(v, 4) for k, v in pooled.items()},
        "current_multipliers": CURRENT_MULTS,
        "current_ratios_vs_first_band": [round(r, 4) for r in current_ratios],
        "_meta": stamped_meta(
            script="scripts/run-delisting-hazard-fit.py",
            source="SRTR PSR Table B7 national cumulative removals without "
                   "transplant at 6, 12 and 18 months "
                   "(SAL_REMDET/REMOTH/REMREC_U6/U12/U18)",
            method="Interval hazard h = -ln(S(t2)/S(t1))/(t2-t1) within one "
                   "national cohort, so the escalation is measured WITHIN "
                   "patients rather than contrasted BETWEEN centers.",
            coverage="Bands 1 and 2 (<=6mo, 6-12mo) are measured directly; "
                     "band 3 (12-24mo) is measured over its first half only; "
                     "band 4 (>24mo) lies beyond every published horizon and "
                     "cannot be measured from this source at all.",
        ),
    }

    lines = [
        "# Do delisting multipliers match the observed hazard? (#297)", "",
        "`build_delisting_risk_cpt` scales delisting by WaitCategory with four",
        "hand-set numbers. The code argues they cannot be fitted because",
        "regressing observed delisting on the wait category is circular.", "",
        "That is right about the obvious approach and wrong about the",
        "conclusion. Regressing each CENTER's delisting rate on its wait factor",
        "is confounded — and not just circularly: it estimates a BETWEEN-CENTER",
        "contrast where the multiplier encodes a WITHIN-PATIENT one. But SRTR",
        "publishes removals at 6, 12 AND 18 months for the same cohort, which",
        "gives the interval hazard directly with no between-center contrast in",
        "it at all.", "",
        "| organ | hazard/mo 0-6 | 6-12 | 12-18 | ratio 6-12 | ratio 12-18 |",
        "|---|---|---|---|---|---|",
    ]
    for organ, r in assessable.items():
        h = r["monthly_hazard"]
        q = r["hazard_ratio_vs_first_6mo"]
        lines.append(f"| {organ} | {h['0-6']:.5f} | {h['6-12']:.5f} | "
                     f"{h['12-18']:.5f} | {q['6-12']:.2f} | {q['12-18']:.2f} |")

    rising = [o for o, r in assessable.items()
              if r["hazard_ratio_vs_first_6mo"]["12-18"] > 1.05]
    falling = [o for o, r in assessable.items()
               if r["hazard_ratio_vs_first_6mo"]["12-18"] < 0.95]
    header = "| band | shipped | " + " | ".join(assessable) + " |"
    sep = "|---|---|" + "---|" * len(assessable)
    def row(label, shipped, key):
        cells = ("1.00" if key is None else
                 " | ".join(f"{assessable[o]['hazard_ratio_vs_first_6mo'][key]:.2f}"
                            for o in assessable))
        if key is None:
            cells = " | ".join("1.00" for _ in assessable)
        return f"| {label} | {shipped:.2f} | {cells} |"

    lines += [
        "", "## The shipped multipliers have the direction wrong", "",
        "The four values encode one monotonic RISE applied to every organ:",
        "3.6x higher in the last band than the first. The observed hazard does",
        "not behave that way, and does not behave the same way across organs.",
        "", "Ratios to each organ's own first band, so they are comparable:", "",
        header, sep,
        row("<=6mo", current_ratios[0], None),
        row("6-12mo", current_ratios[1], "6-12"),
        row("12-24mo", current_ratios[2], "12-18"),
        f"| >24mo | {current_ratios[3]:.2f} | " +
        " | ".join("not measurable" for _ in assessable) + " |",
        "",
    ]
    if falling:
        worst = min(falling,
                    key=lambda o: assessable[o]["hazard_ratio_vs_first_6mo"]["12-18"])
        wv = assessable[worst]["hazard_ratio_vs_first_6mo"]["12-18"]
        lines += [
            f"**Delisting risk FALLS with time on the list for "
            f"{', '.join(falling)}.** {worst.capitalize()}'s hazard in months "
            f"12-18 is {wv:.2f} of its first-six-month hazard. The shipped "
            f"multiplier for that band is {current_ratios[2]:.1f}x the first. "
            f"That is not a magnitude error — it is the wrong sign.", ""]
    if rising:
        lines += [f"It rises, as the shipped values assume, only for "
                  f"{', '.join(rising)}.", ""]
    lines += [
        "This is clinically coherent rather than surprising, which is part of",
        "why it is worth trusting. Candidates most likely to be removed as",
        "'too sick', or to die, are removed EARLY — so the cohort still waiting",
        "at 12 months is systematically healthier than the one that started, a",
        "depletion-of-susceptibles effect. It is strongest exactly where early",
        "mortality is highest (lung, heart) and reverses for kidney, whose",
        "candidates are comparatively stable on dialysis and accumulate",
        "comorbidity the longer they wait.", "",
        "A single set of multipliers cannot represent both patterns. Whatever",
        "replaces these has to be per organ.", "",
        "## What this can and cannot settle", "",
        "Bands 1 and 2 are measured directly. Band 3 is measured over its first",
        "half (12-18 of 12-24). **Band 4 (>24 months) lies beyond every",
        "published horizon** and cannot be grounded from this source, so any",
        "value for it remains an extrapolation however the others are set.",
        "",
        "That matters for how this should be used: replacing four hand-set",
        "numbers with two measured ones, one half-measured one, and one still",
        "extrapolated is a real improvement in provenance, but it is not a",
        "fitted model, and the CPT is a discretized tercile summary rather than",
        "a hazard model, so a like-for-like substitution is not automatic.",
        "The measurement is recorded here first; changing the shipped values",
        "is a separate decision that has to clear the calibration gate.", "",
    ]

    (REPO / "docs" / "delisting-hazard-report.md").write_text("\n".join(lines) + "\n")
    (REPO / "docs-site" / "static" / "data" / "delisting-hazard.json").write_text(
        json.dumps(doc, indent=1) + "\n")
    print(f"\nshipped ratios rise 1.0 -> {current_ratios[1]:.1f} -> "
          f"{current_ratios[2]:.1f} for EVERY organ.")
    print(f"observed: rises for {rising or 'none'}; FALLS for {falling or 'none'}")
    print("Wrote docs/delisting-hazard-report.md + "
          "docs-site/static/data/delisting-hazard.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
