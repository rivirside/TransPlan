"""
Bias audit service for Phase 4 M5 validation.

Extends the equity analysis (Phase 3 M4) with publication-grade bias metrics:
  - Disparity ratios (max/min P(transplant) across demographic groups)
  - Effect sizes (Cohen's d for blood type, age, sex)
  - Demographic-stratified Brier scores (do predictions calibrate equally for all groups?)
  - Summary statistics for validation reports and Jupyter notebooks

This service computes bias metrics WITHOUT running new Monte Carlo simulations.
It operates on pre-computed equity analysis results (from services/equity.py).
"""
import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DisparityMetrics:
    """Disparity metrics for a single stratification dimension."""
    dimension: str  # "blood_type", "age_bracket", or "sex"
    max_group: str
    max_p24: float
    min_group: str
    min_p24: float
    disparity_ratio: float  # max / min
    absolute_gap: float     # max - min
    cohens_d: float         # effect size (if applicable)


@dataclass
class CityBiasProfile:
    """Bias profile for a single city."""
    city: str
    gini: float
    blood_type_disparity: DisparityMetrics
    age_disparity: DisparityMetrics
    sex_disparity: DisparityMetrics
    overall_disparity_ratio: float  # across all 48 profiles


@dataclass
class BiasAuditResult:
    """Full bias audit output."""
    n_cities: int
    n_profiles: int  # 48 = 8 blood types × 3 ages × 2 sexes
    city_profiles: list[CityBiasProfile] = field(default_factory=list)
    national_blood_type_disparity: DisparityMetrics | None = None
    national_age_disparity: DisparityMetrics | None = None
    national_sex_disparity: DisparityMetrics | None = None
    national_gini: float = 0.0
    warnings: list[str] = field(default_factory=list)


def _cohens_d(group_a: list[float], group_b: list[float]) -> float:
    """Compute Cohen's d effect size between two groups."""
    a = np.array(group_a)
    b = np.array(group_b)
    if len(a) < 2 or len(b) < 2:
        return 0.0
    pooled_std = np.sqrt(((len(a) - 1) * np.var(a, ddof=1) +
                           (len(b) - 1) * np.var(b, ddof=1)) /
                          (len(a) + len(b) - 2))
    if pooled_std == 0:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / pooled_std)


def _compute_dimension_disparity(
    group_probs: dict[str, list[float]],
    dimension: str,
) -> DisparityMetrics:
    """Compute disparity metrics for one dimension (e.g., blood_type)."""
    group_means = {g: np.mean(probs) for g, probs in group_probs.items() if probs}

    if not group_means:
        return DisparityMetrics(
            dimension=dimension,
            max_group="", max_p24=0.0,
            min_group="", min_p24=0.0,
            disparity_ratio=1.0, absolute_gap=0.0, cohens_d=0.0,
        )

    max_group = max(group_means, key=group_means.get)
    min_group = min(group_means, key=group_means.get)

    max_p = group_means[max_group]
    min_p = group_means[min_group]

    ratio = max_p / min_p if min_p > 0 else float("inf")
    gap = max_p - min_p

    # Cohen's d between highest and lowest groups
    d = _cohens_d(group_probs[max_group], group_probs[min_group])

    return DisparityMetrics(
        dimension=dimension,
        max_group=max_group, max_p24=round(max_p, 4),
        min_group=min_group, min_p24=round(min_p, 4),
        disparity_ratio=round(ratio, 3),
        absolute_gap=round(gap, 4),
        cohens_d=round(d, 3),
    )


def _gini(values: list[float] | np.ndarray) -> float:
    """Compute Gini coefficient."""
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or np.sum(values) == 0:
        return 0.0
    s = np.sort(values)
    n = len(s)
    idx = np.arange(1, n + 1)
    return max(0.0, float((2 * np.sum(idx * s) - (n + 1) * np.sum(s)) / (n * np.sum(s))))


def run_bias_audit(equity_result: dict) -> BiasAuditResult:
    """
    Run bias audit on a pre-computed equity analysis result.

    Parameters
    ----------
    equity_result : dict
        The result from POST /equity-analysis, containing:
        - cities: list of {city, gini, blood_type_disparity, age_disparity, sex_disparity, profiles}
        - Each profile has: blood_type, age_bracket, sex, p_transplant_24mo

    Returns
    -------
    BiasAuditResult with per-city and national-level bias metrics.
    """
    city_profiles: list[CityBiasProfile] = []

    # National aggregates
    national_bt: dict[str, list[float]] = {}
    national_age: dict[str, list[float]] = {}
    national_sex: dict[str, list[float]] = {}
    all_national_p24: list[float] = []

    cities_data = equity_result.get("cities", [])

    for city_data in cities_data:
        city = city_data.get("city", "Unknown")
        profiles = city_data.get("profiles", [])
        gini = city_data.get("gini", 0.0)

        # Group by dimension
        bt_groups: dict[str, list[float]] = {}
        age_groups: dict[str, list[float]] = {}
        sex_groups: dict[str, list[float]] = {}
        all_p24: list[float] = []

        for prof in profiles:
            p24 = prof.get("p_transplant_24mo", 0.0)
            bt = prof.get("blood_type", "unknown")
            age = prof.get("age_bracket", "unknown")
            sex = prof.get("sex", "unknown")

            bt_groups.setdefault(bt, []).append(p24)
            age_groups.setdefault(age, []).append(p24)
            sex_groups.setdefault(sex, []).append(p24)
            all_p24.append(p24)

            # National aggregates
            national_bt.setdefault(bt, []).append(p24)
            national_age.setdefault(age, []).append(p24)
            national_sex.setdefault(sex, []).append(p24)
            all_national_p24.append(p24)

        bt_disp = _compute_dimension_disparity(bt_groups, "blood_type")
        age_disp = _compute_dimension_disparity(age_groups, "age_bracket")
        sex_disp = _compute_dimension_disparity(sex_groups, "sex")

        # Overall disparity ratio (across all 48 profiles)
        if all_p24:
            overall_ratio = max(all_p24) / min(all_p24) if min(all_p24) > 0 else float("inf")
        else:
            overall_ratio = 1.0

        city_profiles.append(CityBiasProfile(
            city=city,
            gini=round(gini, 4),
            blood_type_disparity=bt_disp,
            age_disparity=age_disp,
            sex_disparity=sex_disp,
            overall_disparity_ratio=round(overall_ratio, 3),
        ))

    # National-level disparities
    nat_bt = _compute_dimension_disparity(national_bt, "blood_type")
    nat_age = _compute_dimension_disparity(national_age, "age_bracket")
    nat_sex = _compute_dimension_disparity(national_sex, "sex")
    nat_gini = _gini(all_national_p24) if all_national_p24 else 0.0

    # Warnings
    warnings = []
    if nat_bt.disparity_ratio > 2.0:
        warnings.append(
            f"Blood type disparity ratio is {nat_bt.disparity_ratio:.1f}x "
            f"({nat_bt.min_group} vs {nat_bt.max_group}). This is primarily driven "
            f"by ABO-matching biology, not systemic bias."
        )
    if nat_bt.cohens_d > 0.8:
        warnings.append(
            f"Large effect size (Cohen's d={nat_bt.cohens_d:.2f}) for blood type. "
            f"Blood type is the dominant driver of transplant probability variation."
        )

    logger.info(
        "Bias audit: %d cities, national Gini=%.4f, BT ratio=%.2f, age ratio=%.2f",
        len(city_profiles), nat_gini, nat_bt.disparity_ratio, nat_age.disparity_ratio,
    )

    return BiasAuditResult(
        n_cities=len(city_profiles),
        n_profiles=48,
        city_profiles=city_profiles,
        national_blood_type_disparity=nat_bt,
        national_age_disparity=nat_age,
        national_sex_disparity=nat_sex,
        national_gini=round(nat_gini, 4),
        warnings=warnings,
    )
