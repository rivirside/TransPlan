"""Multi-listing joint-probability analyzer (#321, closes L-074).

Mechanism (OPTN policy, verified 2026-08): every deceased-donor organ
generates ONE national match run. Listing at a second center adds a second
independently-scored entry with proximity measured from the second hospital
— it improves the patient's RANK for donors near that center. Two listings'
offer processes are therefore positively correlated in proportion to their
donor-pool overlap: same-metro centers add almost nothing (OPTN's own
guidance), distant centers approach independence.

Model
-----
Wait times (T_1..T_k) at the k listed centers keep their existing marginal
lognormals (center factors, clinical multipliers, acceptance thinning, and
accrued-time truncation for kidney — qualified time TRAVELS with the
patient). Dependence is a Gaussian copula whose pairwise correlation equals
the 250nm allocation-circle overlap fraction of the two centers (lens
intersection area / circle area). The patient transplants at the FIRST
offer: T_joint = min(T_1..T_k), raced against a single patient-level
competing-risk clock (mortality + delisting exponentials, averaged across
the listed centers — the patient dies once, wherever listed).

Honest limits (register SURV-41):
- circle overlap is a LOWER bound on true correlation (national sharing
  beyond 500nm couples even distant centers a little), so the joint gain is
  an upper-bound estimate;
- the copula's Gaussian shape is an assumption; the marginals and the
  bounds max(p_i) <= p_joint <= 1 - prod(1-p_i) are not.
"""
import logging
import math
import time

import numpy as np
import scipy.stats

from models.schemas import PatientProfile
from services.data_loader import get_data
from services.distributions import get_lognorm_params, get_wait_time_distribution
from services.competing_risks import get_annual_mortality_rate, get_annual_delisting_rate
from services.stats_utils import rate_to_exponential_scale
from utils import haversine_distance_nm

logger = logging.getLogger(__name__)

CIRCLE_NM = 250.0
N_DRAWS = 20_000


def circle_overlap_fraction(distance_nm: float, radius_nm: float = CIRCLE_NM) -> float:
    """Fraction of a 250nm allocation circle shared with another at
    *distance_nm* (lens intersection area / circle area). 1.0 at d=0,
    0.0 at d >= 2r."""
    d = float(distance_nm)
    r = float(radius_nm)
    if d <= 0:
        return 1.0
    if d >= 2 * r:
        return 0.0
    # Lens area for two equal circles
    lens = 2 * r * r * math.acos(d / (2 * r)) - (d / 2) * math.sqrt(4 * r * r - d * d)
    return float(lens / (math.pi * r * r))


def _effective_dist(patient: PatientProfile, code: str):
    """The center's wait lognormal, matching the MC engine's DEFAULT
    semantics: acceptance thinning (F1) is an opt-in engine feature
    (model_acceptance=False by default), so it is NOT applied here — the
    2026-08-26 browser verification caught the mismatch as a visible
    contradiction between the results table (default path) and the
    multi-listing panel (thinned path) for the same patient."""
    dist = get_wait_time_distribution(
        organ=patient.organ, blood_type=patient.blood_type, center_code=code,
        cpra=patient.cpra, meld=patient.meld, las=patient.las,
        age=patient.age, sex=patient.sex,
    )
    s, loc, scale = get_lognorm_params(dist)
    return scipy.stats.lognorm(s=s, loc=loc, scale=scale)


def compute_multi_listing(patient: PatientProfile, center_codes: list[str],
                          seed: int | None = None,
                          n_draws: int = N_DRAWS) -> dict:
    """Joint transplant probability for a patient listed at 2-5 centers."""
    start = time.perf_counter()
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 2**31))
    if len(set(center_codes)) != len(center_codes):
        raise ValueError("Duplicate center codes in the multi-listing set")
    if not 2 <= len(center_codes) <= 5:
        raise ValueError("Multi-listing analysis takes 2-5 center codes")

    data = get_data()
    centers = [data.resolve_center(c, organ=patient.organ) for c in center_codes]

    # Marginals: effective wait distribution per listing. Kidney qualified
    # time travels with the patient — accrued-time truncation applies at
    # EVERY listing. For other organs the clock is per-program: a NEW
    # listing starts at zero, so t0 applies only to the first (current)
    # center in the list.
    t0 = float(patient.months_waiting or 0.0)
    dists = [_effective_dist(patient, c) for c in center_codes]
    t0s = [t0] * len(center_codes) if patient.organ == "kidney" \
        else [t0] + [0.0] * (len(center_codes) - 1)

    # Patient-level competing hazard: the patient dies/delists once —
    # average the listed centers' hazards (they describe the same patient
    # under slightly different center-mix adjustments).
    inv_totals = []
    for c in center_codes:
        mort = get_annual_mortality_rate(organ=patient.organ, center_code=c,
                                         urgency=patient.urgency, meld=patient.meld)
        delist = get_annual_delisting_rate(organ=patient.organ, center_code=c)
        inv_totals.append(1.0 / rate_to_exponential_scale(mort, "mortality", c)
                          + 1.0 / rate_to_exponential_scale(delist, "delisting", c))
    hazard = float(np.mean(inv_totals))

    # Pairwise correlation from allocation-circle overlap
    k = len(center_codes)
    corr = np.eye(k)
    overlap = {}
    for i in range(k):
        for j in range(i + 1, k):
            d_nm = haversine_distance_nm(
                centers[i]["lat"], centers[i]["lon"],
                centers[j]["lat"], centers[j]["lon"])
            f = circle_overlap_fraction(d_nm)
            corr[i, j] = corr[j, i] = f
            overlap[f"{center_codes[i]}-{center_codes[j]}"] = {
                "distance_nm": round(float(d_nm), 1),
                "overlap_fraction": round(f, 4),
            }
    # Ensure positive semidefinite (tiny jitter for near-singular sets)
    eigmin = float(np.linalg.eigvalsh(corr).min())
    if eigmin < 1e-8:
        corr += np.eye(k) * (1e-8 - eigmin)

    # Gaussian copula draws -> per-listing conditional wait times
    rng = np.random.default_rng(seed)
    z = rng.multivariate_normal(np.zeros(k), corr, size=n_draws,
                                method="cholesky")
    u = scipy.stats.norm.cdf(z)
    waits = np.empty_like(u)
    for i, (dist, t0_i) in enumerate(zip(dists, t0s)):
        if t0_i > 0:
            f0 = min(float(dist.cdf(t0_i)), 1.0 - 1e-12)
            waits[:, i] = np.maximum(dist.ppf(f0 + u[:, i] * (1.0 - f0)) - t0_i,
                                     1e-9)
        else:
            waits[:, i] = dist.ppf(np.clip(u[:, i], 1e-12, 1 - 1e-12))

    t_joint = waits.min(axis=1)
    competing = rng.exponential(scale=1.0 / hazard, size=n_draws) \
        if hazard > 0 else np.full(n_draws, np.inf)

    def p_within(months: float) -> float:
        return float(np.mean((t_joint <= months) & (t_joint < competing)))

    # Marginal p24 per listing under the SAME competing clock, for a
    # like-for-like comparison
    listings = []
    for i, code in enumerate(center_codes):
        p24_i = float(np.mean((waits[:, i] <= 24.0) & (waits[:, i] < competing)))
        listings.append({
            "center_code": code,
            "center_name": centers[i].get("name", code),
            "state": centers[i].get("state_abbr", ""),
            "p24": round(p24_i, 4),
            "median_remaining_wait_months": round(float(np.median(waits[:, i])), 2),
        })

    joint = {h: round(p_within(m), 4)
             for h, m in (("joint_p6", 6.0), ("joint_p12", 12.0),
                          ("joint_p24", 24.0), ("joint_p36", 36.0))}
    best_single = max(l["p24"] for l in listings)

    elapsed = time.perf_counter() - start
    return {
        "organ": patient.organ,
        "listings": listings,
        **joint,
        "joint_median_wait_months": round(float(np.median(t_joint)), 2),
        "gain_over_best_single": round(joint["joint_p24"] - best_single, 4),
        "pairwise_overlap": overlap,
        "seed_used": seed,
        "n_draws": n_draws,
        "accrued_time_note": (
            "Kidney qualified waiting time travels with the patient — the "
            "accrued-time conditioning applies at every listing."
            if patient.organ == "kidney" and t0 > 0 else
            ("For non-kidney organs waiting time is per-program: accrued time "
             "applies only to the first (current) listing; new listings start "
             "at zero." if t0 > 0 else "")),
        "note": (
            "One national match run per donor; a second listing adds a second "
            "independently-scored entry. Correlation between listings is the "
            "250nm allocation-circle overlap — a LOWER bound on true coupling "
            "(national sharing links even distant centers), so the joint gain "
            "is an upper-bound estimate. Same-metro second listings add "
            "almost nothing, per OPTN guidance."),
        "elapsed_seconds": round(elapsed, 3),
    }
