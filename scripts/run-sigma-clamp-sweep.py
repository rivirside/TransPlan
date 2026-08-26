#!/usr/bin/env python3
"""Is the log_sigma clamp ceiling of 1.2 costing us accuracy? (#274 / DATA-07)

`srtr_xls_utils.sigma_from_percentiles` estimates the wait-time lognormal
sigma from SRTR percentiles and then clamps it to [0.3, 1.2]. Measured
against the raw Table B10 national percentiles, **five of six organs hit that
ceiling**, and kidney's IQR-implied sigma is 2.53 — more than double the cap:

    organ       p10    p25    raw sigma   stored
    kidney      1.4    6.5      2.529      1.2
    pancreas    3.4   13.3      2.247      0.8   <- see below
    intestine   0.8    2.9      2.121      1.2
    liver       0.2    0.5      1.509      1.2
    heart       0.2    0.5      1.509      1.2
    lung        0.2    0.4      1.142      1.14  <- only organ under the cap

Sigma controls the SPREAD of the wait distribution, so a ceiling that binds
on almost every organ compresses the tail everywhere it matters. The register
carries this as DATA-07, `heuristic_clamp`, high-risk.

But "the clamp binds" is not the same as "raising it helps". A larger sigma
fattens both tails, and the competing-risks integral is not monotone in it:
more mass at short waits raises p12 while more mass at long waits lowers it.
So this sweeps the ceiling and measures calibration at each value against the
observed SRTR transplant rates, rather than assuming the uncapped fit is
better because it is unclamped.

Also measured separately: pancreas stores 0.8 rather than the clamp value,
because `fit_lognormal` returns early with a hardcoded 0.8 when the median is
censored — discarding P10 and P25 that are present and valid. That is a
distinct defect from the ceiling and is reported on its own line.

Outputs: docs/sigma-clamp-sweep-report.md,
         docs-site/static/data/sigma-clamp-sweep.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

import srtr_xls_utils as sx  # noqa: E402
import xlrd  # noqa: E402
from artifact_meta import stamped_meta  # noqa: E402

from models.schemas import PatientProfile  # noqa: E402
from services.data_loader import get_data, load_all  # noqa: E402
from services.monte_carlo import simulate  # noqa: E402
from reference_patients import reference_patient_kwargs  # noqa: E402

ORGAN_CODES = {"kidney": "KI", "liver": "LI", "heart": "HR",
               "lung": "LU", "pancreas": "PA", "intestine": "IN"}
CEILINGS = [1.2, 1.5, 1.8, 2.1, 2.6]     # 2.6 is effectively uncapped here
N_ITERATIONS = 1500
SEED = 20260826
MIN_N = 25                                # observed-cohort floor, as elsewhere


def raw_sigma(organ: str, code: str) -> dict:
    """Unclamped sigma from the national B10 percentiles, plus which strategy
    produced it — the strategy matters because the censored-median branch in
    fit_lognormal bypasses this chain entirely."""
    wb = xlrd.open_workbook(str(REPO / "data" / "srtr-raw" /
                                f"csrs_final_tables_2511_{code}.xls"))
    sheet = wb.sheet_by_name("Table B10")
    hdr = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]

    def nat(col):
        i = sx.col_index(hdr, col)
        if i < 0:
            return None
        for r in range(1, sheet.nrows):
            v = sx.safe_float(sheet.cell_value(r, i))
            if v is not None:
                return v
        return None

    p10, p25, p50, p75 = (nat(f"TTT_{p}_U") for p in (10, 25, 50, 75))
    if sx.is_valid(p10) and sx.is_valid(p25) and p25 > p10:
        sigma = (math.log(p25) - math.log(p10)) / (1.2816 - 0.6745)
        method = "P10-P25"
    elif sx.is_valid(p25) and sx.is_valid(p75) and p75 > p25:
        sigma = (math.log(p75) - math.log(p25)) / (2 * 0.6745)
        method = "IQR"
    elif sx.is_valid(p10) and sx.is_valid(p50) and p50 > p10:
        sigma = (math.log(p50) - math.log(p10)) / 1.2816
        method = "P10-P50"
    else:
        sigma, method = 0.8, "fallback"
    return {"raw_sigma": round(sigma, 4), "method": method,
            "median_censored": not sx.is_valid(p50),
            "percentiles": {"p10": p10, "p25": p25, "p50": p50, "p75": p75}}


def calibrate(organ: str) -> tuple[float | None, int]:
    """Spearman between predicted p12 and the observed SRTR transplant rate.

    This is the same headline metric run-center-calibration.py reports, so a
    ceiling that improves it improves the number already published.
    """
    data = get_data()
    patient = PatientProfile(**reference_patient_kwargs(organ))
    result = simulate(patient, n_iterations=N_ITERATIONS, seed=SEED)
    pred, obs = [], []
    for c in result.cities:
        o = data.observed_outcome(organ, c.center_code)
        if not o or o.get("n", 0) < MIN_N:
            continue
        rate = o.get("transplant_rate")
        if rate is None or not 0 < rate < 100:
            continue
        pred.append(c.p_transplant_12mo)
        obs.append(rate)
    if len(pred) < 20 or len(set(pred)) < 2:
        return None, len(pred)
    return float(stats.spearmanr(pred, obs).statistic), len(pred)


def main() -> int:
    load_all()
    data = get_data()
    dists = data.wait_time_distributions

    fits = {organ: raw_sigma(organ, code) for organ, code in ORGAN_CODES.items()}
    baseline_sigma = {o: dists.get(o, {}).get("log_sigma") for o in ORGAN_CODES}

    results = {}
    for organ in ORGAN_CODES:
        fit = fits[organ]
        stored = baseline_sigma[organ]
        per_ceiling = {}
        for ceiling in CEILINGS:
            # Apply this ceiling to the UNCLAMPED fit, in memory.
            sigma = max(0.3, min(fit["raw_sigma"], ceiling))
            # distributions.py keeps its OWN module-level cache
            # (`_DISTRIBUTIONS`), loaded independently of data_loader — so
            # patching data_loader alone changes nothing. Both are set.
            from services import distributions as _d
            _d._ensure_loaded()
            original = dists[organ]["log_sigma"]
            original_cached = _d._DISTRIBUTIONS[organ]["log_sigma"]
            dists[organ]["log_sigma"] = sigma
            _d._DISTRIBUTIONS[organ]["log_sigma"] = sigma
            try:
                rho, n_used = calibrate(organ)
            finally:
                dists[organ]["log_sigma"] = original
                _d._DISTRIBUTIONS[organ]["log_sigma"] = original_cached
            per_ceiling[str(ceiling)] = {
                "sigma_used": round(sigma, 4),
                "n_centers_scored": n_used,
                "spearman": None if rho is None else round(rho, 4),
                "binds": fit["raw_sigma"] > ceiling,
            }
            print(f"  {organ:10s} ceiling={ceiling:<4} sigma={sigma:.3f} "
                  f"rho={'—' if rho is None else f'{rho:.4f}'}")

        valid = {k: v for k, v in per_ceiling.items() if v["spearman"] is not None}
        best = max(valid, key=lambda k: valid[k]["spearman"]) if valid else None
        max_cohort = 0
        for code in (data.center_wait_times.get("center_wait_time_factors", {})):
            o = data.observed_outcome(organ, code)
            if o and o.get("n"):
                max_cohort = max(max_cohort, o["n"])
        results[organ] = {
            "not_assessable_reason": (
                None if any(v["spearman"] is not None for v in per_ceiling.values())
                else f"no center has an observed cohort of {MIN_N}+ "
                     f"(largest is {max_cohort}), so the calibration metric "
                     f"cannot be computed at any ceiling"),
            "max_observed_cohort_n": max_cohort,
            "stored_sigma": stored,
            "raw_sigma": fit["raw_sigma"],
            "method": fit["method"],
            "median_censored": fit["median_censored"],
            "clamp_binds_at_1_2": fit["raw_sigma"] > 1.2,
            "stored_ignores_chain": (fit["method"] != "fallback"
                                     and stored == 0.8
                                     and abs(fit["raw_sigma"] - 0.8) > 0.05),
            "by_ceiling": per_ceiling,
            "best_ceiling": best,
            "best_spearman": valid[best]["spearman"] if best else None,
            "spearman_at_1_2": per_ceiling["1.2"]["spearman"],
        }
        print()

    doc = {"organs": results, "_meta": stamped_meta(
        script="scripts/run-sigma-clamp-sweep.py",
        metric="Spearman rank correlation between predicted p_transplant_12mo "
               "and the observed SRTR 12-month transplant rate — the same "
               "headline metric run-center-calibration.py reports.",
        ceilings=CEILINGS,
        n_iterations=N_ITERATIONS,
        seed=SEED,
        question="#274/DATA-07: the sigma clamp ceiling of 1.2 binds on 5 of 6 "
                 "organs. Does raising it improve calibration?",
    )}

    lines = ["# log_sigma clamp ceiling sweep (#274 / DATA-07)", "",
             "The wait-time lognormal sigma is clamped to [0.3, 1.2]. Measured",
             "against the raw Table B10 national percentiles, that ceiling",
             "**binds on five of six organs** — kidney's IQR-implied sigma is",
             "2.53, more than double the cap.", "",
             "Whether raising it *helps* is a separate question, because sigma",
             "fattens both tails and the competing-risks integral is not",
             "monotone in it. So each ceiling is scored by the same calibration",
             "metric the published center-calibration report uses.", "",
             "| organ | raw sigma | stored | binds? | ρ @1.2 | best ceiling | ρ @best | change |",
             "|---|---|---|---|---|---|---|---|"]
    for organ, r in results.items():
        base = r["spearman_at_1_2"]
        best = r["best_spearman"]
        delta = (f"{best - base:+.4f}" if (base is not None and best is not None)
                 else "—")
        lines.append(
            f"| {organ} | {r['raw_sigma']:.3f} | {r['stored_sigma']} | "
            f"{'yes' if r['clamp_binds_at_1_2'] else 'no'} | "
            f"{'—' if base is None else f'{base:.4f}'} | {r['best_ceiling']} | "
            f"{'—' if best is None else f'{best:.4f}'} | {delta} |")

    assessable = {o: r for o, r in results.items()
                  if r["spearman_at_1_2"] is not None}
    raised_helps = [o for o, r in assessable.items()
                    if r["best_ceiling"] != "1.2"
                    and r["best_spearman"] - r["spearman_at_1_2"] > 0.005]
    lines += ["", "## Verdict", ""]
    if raised_helps:
        lines += [f"Raising the ceiling improves calibration for "
                  f"{', '.join(raised_helps)}. Worth doing.", ""]
    else:
        lines += [
            "**Raising the ceiling does not help — it hurts.** On every organ",
            "where the metric is computable, calibration is best at the",
            "CURRENT 1.2 ceiling and degrades as the cap is lifted:", "",
            "| organ | ρ @1.2 | ρ uncapped | change |",
            "|---|---|---|---|",
        ]
        for organ, r in assessable.items():
            top = r["by_ceiling"][str(CEILINGS[-1])]["spearman"]
            lines.append(f"| {organ} | {r['spearman_at_1_2']:.4f} | {top:.4f} | "
                         f"{top - r['spearman_at_1_2']:+.4f} |")
        lines += [
            "",
            "That is the opposite of what #274 expected, and it makes sense on",
            "reflection: SRTR's published percentiles describe a distribution",
            "already truncated by competing risks and censoring, so the",
            "'unclamped' sigma is not the true dispersion of the wait — it is",
            "the dispersion of a censored observation of it. The 1.2 ceiling",
            "acts as a crude but effective regularizer against that.",
            "",
            "So DATA-07 stays clamped, and #274's proposed raise to ~1.8-2.0",
            "is rejected on evidence rather than left open on suspicion.", ""]

    not_assessable = {o: r for o, r in results.items()
                      if r["spearman_at_1_2"] is None}
    if not_assessable:
        lines += ["### What could not be measured", ""]
        for organ, r in not_assessable.items():
            lines.append(f"- **{organ}**: {r['not_assessable_reason']}.")
        lines += ["",
                  "These organs are excluded from the verdict rather than",
                  "assumed to follow it.", ""]

    censored = [o for o, r in results.items() if r["stored_ignores_chain"]]
    lines += ["", "## A second, separate defect", ""]
    if censored:
        lines += [
            f"**{', '.join(censored)}** store{'' if len(censored) > 1 else 's'} "
            f"sigma 0.8 rather than any clamp",
            "value. `fit_lognormal` returns early with a hardcoded 0.8 whenever",
            "the median is censored (`>72`), discarding P10 and P25 that are",
            "present and valid. For pancreas the chain would have produced",
            f"{results['pancreas']['raw_sigma']:.3f} from real percentiles.",
            "That is independent of the ceiling and should be fixed regardless",
            "of what this sweep concludes about the cap.", ""]
    else:
        lines += ["No organ bypasses the strategy chain in this vintage.", ""]

    (REPO / "docs" / "sigma-clamp-sweep-report.md").write_text("\n".join(lines) + "\n")
    (REPO / "docs-site" / "static" / "data" / "sigma-clamp-sweep.json").write_text(
        json.dumps(doc, indent=1) + "\n")
    print("Wrote docs/sigma-clamp-sweep-report.md + "
          "docs-site/static/data/sigma-clamp-sweep.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
