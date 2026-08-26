#!/usr/bin/env python3
"""Interval coverage audit (#311): do the 95% intervals actually cover?

The engines emit 95% intervals; nothing has ever tested their coverage.
Using the 15-release archive: for each (train, test) release pair, build the
closed-form p12 prediction WITH the #226-style binomial data-sampling
interval at each center's observed cohort n (the same construction the BBN
response uses), then measure what fraction of the NEXT release's observed
transplant rates fall inside. Nominal 95% should cover ~95%; material
under-coverage means the intervals are too tight (they ignore real
between-release drift), over-coverage means too loose.

Coverage is reported per organ and per cohort-size band, at lags of one
release (~6 months) and beyond, so the answer distinguishes "the binomial
interval is right for sampling noise" from "drift dominates at longer lags".

Outputs: docs/coverage-audit-report.md, docs-site/static/data/coverage-audit.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
HIST = REPO / "data" / "srtr-observed-rates-historical.json"

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas"]
MIN_N = 10
Z95 = 1.959963984540054


def _rates(releases, rel, organ):
    c = releases[rel]["organs"].get(organ, {}).get("centers", {})
    return {k: v for k, v in c.items()
            if v.get("n", 0) >= MIN_N and v.get("transplant_rate") is not None}


def audit_pair(releases, train, test, organ):
    """Coverage of [p_hat ± z*sqrt(p(1-p)/n)] built on TRAIN, evaluated on
    TEST's observed rate. p_hat is the train rate itself (persistence-style
    predictor — the same information the closed-form model conditions on)."""
    tr = _rates(releases, train, organ)
    te = _rates(releases, test, organ)
    rows = []
    for code in set(tr) & set(te):
        p = tr[code]["transplant_rate"] / 100.0
        n = tr[code]["n"]
        half = Z95 * math.sqrt(max(p * (1 - p), 1e-9) / n)
        obs = te[code]["transplant_rate"] / 100.0
        rows.append({"n": n, "covered": abs(obs - p) <= half,
                     "half_width": half, "abs_err": abs(obs - p)})
    return rows


def main():
    releases = json.loads(HIST.read_text())["releases"]
    rels = sorted(releases)
    result = {"organs": {}, "_meta": {
        "method": "95% binomial interval on train-release rate at cohort n; "
                  "coverage = fraction of test-release observed rates inside. "
                  f"Centers with n>={MIN_N}; lag-1 = adjacent releases.",
    }}
    lines = ["# Interval coverage audit (#311)", "",
             "Do 95% data-sampling intervals cover the next release's observed",
             "rates? Under-coverage = intervals too tight (drift ignored).", "",
             "| organ | lag-1 coverage | lag-2 | lag>=4 | n pairs (lag-1) |",
             "|---|---|---|---|---|"]

    for organ in ORGANS:
        by_lag = {1: [], 2: [], 4: []}
        for i, train in enumerate(rels):
            for j in range(i + 1, len(rels)):
                lag = j - i
                key = 1 if lag == 1 else (2 if lag == 2 else 4 if lag >= 4 else None)
                if key is None:
                    continue
                by_lag[key].extend(audit_pair(releases, train, rels[j], organ))
        cov = {k: (float(np.mean([r["covered"] for r in v])) if v else None)
               for k, v in by_lag.items()}
        # coverage by cohort size at lag 1
        by_size = {}
        for name, lo, hi in (("n<60", 0, 60), ("60-300", 60, 300), ("300+", 300, 10**9)):
            sub = [r for r in by_lag[1] if lo <= r["n"] < hi]
            if len(sub) >= 30:
                by_size[name] = float(np.mean([r["covered"] for r in sub]))
        # Empirical inflation: multiplier on the half-width needed to reach
        # nominal 95% at each lag — the usable correction factor.
        def _inflation(rows):
            if not rows:
                return None
            lo, hi = 1.0, 8.0
            def cov_at(m):
                return np.mean([r["covered_ratio"] <= m for r in rows])
            for r in rows:
                r["covered_ratio"] = r["abs_err"] / r["half_width"] if r["half_width"] > 0 else 99.0
            for _ in range(40):
                mid = (lo + hi) / 2
                if cov_at(mid) >= 0.95:
                    hi = mid
                else:
                    lo = mid
            return round(hi, 2)
        inflation = {k: _inflation(v) for k, v in by_lag.items()}
        result["organs"][organ] = {"coverage_by_lag": cov,
                                   "coverage_lag1_by_size": by_size,
                                   "inflation_to_95_by_lag": inflation,
                                   "n_pairs_lag1": len(by_lag[1])}
        fmt = lambda v: f"{v:.1%}" if v is not None else "—"
        lines.append(f"| {organ} | {fmt(cov[1])} | {fmt(cov[2])} | "
                     f"{fmt(cov[4])} | {len(by_lag[1])} |")
        print(f"{organ}: lag1 {fmt(cov[1])} lag2 {fmt(cov[2])} "
              f"lag>=4 {fmt(cov[4])} | inflation {inflation}")

    lines += ["", "## Empirical inflation factors (multiplier on the",
              "binomial half-width to reach nominal 95%)", "",
              "| organ | lag-1 | lag-2 | lag>=4 |", "|---|---|---|---|"]
    for organ in ORGANS:
        infl = result["organs"][organ]["inflation_to_95_by_lag"]
        lines.append(f"| {organ} | {infl.get(1)} | {infl.get(2)} | {infl.get(4)} |")
    lines += ["", "## Interpretation", "",
              "- Lag-1 coverage near 95% would mean binomial sampling noise",
              "  fully explains release-to-release variation. Coverage BELOW",
              "  95% quantifies the real drift the interval ignores — and the",
              "  gap should WIDEN with lag if drift accumulates.",
              "- Consequence for the product: the #226-style data-sampling",
              "  intervals (BBN CI, rank-stability bootstrap) are honest about",
              "  sampling noise but NOT total predictive uncertainty; a",
              "  drift-inflated interval (scaling with horizon) would be the",
              "  upgrade, tracked with #358's release-effect modeling.", ""]
    (REPO / "docs" / "coverage-audit-report.md").write_text("\n".join(lines))
    (REPO / "docs-site" / "static" / "data" / "coverage-audit.json").write_text(
        json.dumps(result, indent=1))
    print("Wrote report + JSON")


if __name__ == "__main__":
    sys.exit(main())
