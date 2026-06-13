"""
Temporal walk-forward analysis — train on years 1..Y, test on year Y+1.

Uses historical_trends data from data/historical-srtr-trends.json (if available).

CAVEAT (#270 MCMC-24): when real historical data is limited this FALLS BACK to a
synthetic check that perturbs the model's own trend assumptions and then scores
the model against those perturbations — near-tautological, a persistence/
self-consistency signal, NOT a true out-of-sample temporal holdout. The genuine
out-of-sample work (fit on a prior SRTR release, test on the next) is tracked in
docs/temporal-validation-report.md / #237; treat the synthetic fallback's rho as
a sanity check only, not evidence of forecast accuracy.

Computes Spearman rank correlation between predicted and "actual"
(next-year observed) rankings.
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import stats

from models.schemas import PatientProfile

logger = logging.getLogger(__name__)

# Year range available in historical data
YEAR_RANGE = (2019, 2025)


@dataclass
class TemporalFold:
    train_end_year: int
    test_year: int
    spearman_rho: float
    top5_overlap: float          # Jaccard between predicted and "actual" top-5
    n_centers: int
    elapsed_seconds: float


@dataclass
class TemporalValidationResult:
    organ: str
    folds: list[TemporalFold]
    mean_spearman_rho: float
    mean_top5_overlap: float
    train_years: tuple[int, int]
    test_years: tuple[int, int]
    elapsed_seconds: float
    notes: list[str]


def run_temporal_validation(
    patient: PatientProfile,
    train_start: int = 2019,
    train_end: int = 2022,
    test_end: int = 2024,
    iterations: int = 300,
    seed: Optional[int] = None,
) -> TemporalValidationResult:
    """
    Walk-forward validation: for each year Y in [train_end, test_end-1]:
      1. "Train" = simulate with data as of year Y (approximated by scaling wait factors)
      2. "Test" = simulate with data as of year Y+1
      3. Compute Spearman ρ between the two rankings

    Since we don't retrain models year-over-year, we simulate temporal
    sensitivity by perturbing wait time factors with year-over-year trend
    slopes from historical_trends data.
    """
    t0 = time.perf_counter()
    notes: list[str] = []

    # Clamp to available range
    train_start = max(train_start, YEAR_RANGE[0])
    test_end = min(test_end, YEAR_RANGE[1])
    train_end = max(train_start, min(train_end, test_end - 1))

    # Load trend slopes from historical data
    trend_slopes = _get_trend_slopes(patient.organ)

    from services.monte_carlo import simulate

    folds: list[TemporalFold] = []

    for y in range(train_end, test_end):
        t_fold = time.perf_counter()
        fold_seed_a = None if seed is None else (seed + y * 7919) % 2147483647
        fold_seed_b = None if seed is None else (seed + y * 7919 + 1) % 2147483647

        # Year Y baseline run
        result_y = simulate(patient, n_iterations=iterations, seed=fold_seed_a)

        # Year Y+1 run: apply trend perturbation to wait time scale
        # This approximates "if wait times grew/shrank per historical trend"
        try:
            result_y1 = _simulate_with_trend_shift(
                patient,
                trend_slopes=trend_slopes,
                year_delta=1,
                iterations=iterations,
                seed=fold_seed_b,
            )
        except Exception:
            # Fallback: re-run with slight seed offset to get natural variance
            result_y1 = simulate(patient, n_iterations=iterations, seed=fold_seed_b)
            notes.append(f"Year {y}→{y+1}: used seed-offset fallback (trend data unavailable)")

        # Extract rankings
        rank_y  = [c.center_code or c.city for c in result_y.cities]
        rank_y1 = [c.center_code or c.city for c in result_y1.cities]

        common = [c for c in rank_y if c in rank_y1]
        if len(common) < 3:
            continue

        prev_ranks = [rank_y.index(c) for c in common]
        next_ranks = [rank_y1.index(c) for c in common]
        rho, _ = stats.spearmanr(prev_ranks, next_ranks)

        top5_y  = set(rank_y[:5])
        top5_y1 = set(rank_y1[:5])
        jaccard = len(top5_y & top5_y1) / len(top5_y | top5_y1) if (top5_y | top5_y1) else 1.0

        folds.append(TemporalFold(
            train_end_year=y,
            test_year=y + 1,
            spearman_rho=float(rho),
            top5_overlap=float(jaccard),
            n_centers=len(common),
            elapsed_seconds=time.perf_counter() - t_fold,
        ))

    mean_rho = float(np.mean([f.spearman_rho for f in folds])) if folds else 0.0
    mean_overlap = float(np.mean([f.top5_overlap for f in folds])) if folds else 0.0

    if not folds:
        notes.append("No valid folds produced — train_end must be < test_end")

    return TemporalValidationResult(
        organ=patient.organ,
        folds=folds,
        mean_spearman_rho=mean_rho,
        mean_top5_overlap=mean_overlap,
        train_years=(train_start, train_end),
        test_years=(train_end + 1, test_end),
        elapsed_seconds=time.perf_counter() - t0,
        notes=notes,
    )


def _get_trend_slopes(organ: str) -> dict[str, float]:
    """
    Load per-city wait time trend slopes (change per year, as a multiplier).
    Returns empty dict if historical data unavailable.
    """
    try:
        from services.data_loader import get_data
        data = get_data()
        trends = data.historical_trends
        city_trends = trends.get("city_trends", {})

        slopes: dict[str, float] = {}
        for city, info in city_trends.items():
            organ_data = info.get(organ, {})
            wait_slope = organ_data.get("wait_time_slope", 0.0)  # monthly change per year
            # Convert to multiplicative factor per year
            baseline = organ_data.get("baseline_median_months", 24.0)
            if baseline > 0:
                slopes[city] = 1.0 + (wait_slope / baseline)
            else:
                slopes[city] = 1.0
        return slopes
    except Exception:
        return {}


def _simulate_with_trend_shift(
    patient: PatientProfile,
    trend_slopes: dict[str, float],
    year_delta: int,
    iterations: int,
    seed: Optional[int],
):
    """
    Run simulation with wait-time distributions shifted by trend_slopes^year_delta.
    Since distributions.py doesn't have a year_range param, we approximate by
    temporarily patching _CITY_FACTORS in distributions module.
    """
    import services.distributions as dist_module

    dist_module._ensure_loaded()
    original_factors = dict(dist_module._CITY_FACTORS)

    try:
        # Apply year-over-year shift
        shifted = {}
        for city, factor in original_factors.items():
            slope = trend_slopes.get(city, 1.0)
            shifted[city] = factor * (slope ** year_delta)

        dist_module._CITY_FACTORS = shifted

        from services.monte_carlo import simulate
        return simulate(patient, n_iterations=iterations, seed=seed)
    finally:
        dist_module._CITY_FACTORS = original_factors
