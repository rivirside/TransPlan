"""Rank-stability bootstrap (#313).

The simulator's core output is a ranking, but a rank is an estimate: each
center's numbers rest on a finite SRTR cohort, and center #5 may be
statistically indistinguishable from #3-#9. This service quantifies that.

Method: compute each center's closed-form p24 (the deterministic
competing-risks integral — no Monte Carlo noise), then bootstrap it with
binomial sampling noise at the center's OBSERVED cohort size n (SRTR Table
B7) — the same data-sampling uncertainty philosophy as the BBN's #226
interval. Each replicate re-ranks all centers; per-center rank quantiles and
"statistical tie groups" (maximal runs of centers whose rank intervals
overlap the group) summarize the result.

Honest scope: this propagates DATA-SAMPLING uncertainty in the observed
rates only — not model-form uncertainty (assumption sweep, #295 report) nor
parameter uncertainty (MCMC engine). Centers with no observed cohort get a
wide, honest effective n (register SURV-39).
"""
import logging
import time

import numpy as np

from models.schemas import PatientProfile
from services.data_loader import get_data
from services.what_if import closed_form_baseline

logger = logging.getLogger(__name__)

# Effective cohort for centers with NO observed outcome record: small enough
# to give a deliberately wide interval (the honest answer for a center whose
# rates are national fallbacks). Register: SURV-39.
_FALLBACK_N = 8


def compute_rank_stability(patient: PatientProfile, n_boot: int = 500,
                           seed: int | None = None) -> dict:
    """Bootstrap rank intervals for every center performing patient.organ."""
    start = time.perf_counter()
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 2**31))

    data = get_data()
    rows = []
    for center in data.centers_for_organ(patient.organ):
        code = center.get("code", "")
        try:
            base = closed_form_baseline(patient, code)
        except ValueError:
            continue
        rec = data.observed_outcome(patient.organ, code)
        n_obs = int(rec["n"]) if rec and rec.get("n") else 0
        rows.append({
            "center_code": code,
            "center_name": base["city"],
            "state": base["state"],
            "p24": float(base["baseline_p24"]),
            "n_obs": n_obs,
        })

    if not rows:
        raise ValueError(f"No centers with usable data for {patient.organ}")

    # Point ranking (descending p24; deterministic tiebreak by code)
    rows.sort(key=lambda r: (-r["p24"], r["center_code"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1

    p24 = np.array([r["p24"] for r in rows])
    n_eff = np.array([r["n_obs"] if r["n_obs"] > 0 else _FALLBACK_N
                      for r in rows], dtype=float)

    # Beta noise around p24 at effective cohort size: Beta(p*n, (1-p)*n) has
    # mean p and sd ~ sqrt(p(1-p)/n) — the binomial SE of an observed
    # proportion (same as bayesian_network._data_uncertainty_ci, #226).
    # +1 on each shape keeps degenerate p24 in {0,1} sampleable.
    rng = np.random.default_rng(seed)
    a = np.clip(p24 * n_eff, 0.0, None) + 1.0
    b = np.clip((1.0 - p24) * n_eff, 0.0, None) + 1.0
    draws = rng.beta(a[None, :].repeat(n_boot, 0), b[None, :].repeat(n_boot, 0))

    # Per-replicate ranks (1 = best). argsort of descending values.
    order = np.argsort(-draws, axis=1)
    ranks = np.empty_like(order)
    boot_idx = np.arange(n_boot)[:, None]
    ranks[boot_idx, order] = np.arange(1, len(rows) + 1)[None, :]

    lo = np.percentile(ranks, 5, axis=0)
    med = np.percentile(ranks, 50, axis=0)
    hi = np.percentile(ranks, 95, axis=0)
    for i, r in enumerate(rows):
        r["rank_lo"] = int(np.floor(lo[i]))
        r["rank_median"] = int(round(med[i]))
        r["rank_hi"] = int(np.ceil(hi[i]))
        # coverage guarantee for the point rank (quantile rounding can
        # otherwise exclude it at the margins)
        r["rank_lo"] = min(r["rank_lo"], r["rank"])
        r["rank_hi"] = max(r["rank_hi"], r["rank"])

    # Statistical tie groups: walk the point ranking; extend the current
    # group while the next center's interval overlaps the group's span.
    groups = []
    current = [rows[0]]
    span_hi = rows[0]["rank_hi"]
    for r in rows[1:]:
        if r["rank_lo"] <= span_hi:
            current.append(r)
            span_hi = max(span_hi, r["rank_hi"])
        else:
            groups.append(current)
            current = [r]
            span_hi = r["rank_hi"]
    groups.append(current)

    elapsed = time.perf_counter() - start
    logger.info("Rank stability: %s, %d centers x %d replicates, %.2fs",
                patient.organ, len(rows), n_boot, elapsed)
    return {
        "organ": patient.organ,
        "n_boot": n_boot,
        "seed_used": seed,
        "centers": rows,
        "tie_groups": [
            {"rank_from": g[0]["rank"], "rank_to": g[-1]["rank"],
             "center_codes": [r["center_code"] for r in g]}
            for g in groups
        ],
        "elapsed_seconds": round(elapsed, 3),
        "note": (
            "Rank intervals propagate data-sampling uncertainty in the "
            "observed SRTR cohorts (binomial at each center's n). Centers in "
            "the same tie group are statistically indistinguishable at this "
            "uncertainty level. Model-form and parameter uncertainty are "
            "assessed separately (assumption sweep; MCMC engine)."
        ),
    }
