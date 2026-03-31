"""
Model parameter sensitivity analysis — ranking stability across parameter sweeps.

Varies a single parameter across a range, runs Monte Carlo at each value,
and computes Spearman rank correlation between adjacent runs to measure
how stable the city rankings are.
"""
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import stats

from models.schemas import PatientProfile

logger = logging.getLogger(__name__)

# Supported sweep parameters and their valid ranges
SWEEP_PARAMS = {
    "copula_theta": {"min": 0.1, "max": 5.0, "default": 1.0, "label": "Copula θ (Dependency)"},
    "elasticity":   {"min": 0.1, "max": 1.0, "default": 0.65, "label": "Supply-Wait Elasticity"},
    "iterations":   {"min": 100, "max": 2000, "default": 500, "label": "MC Iterations"},
    "cpra":         {"min": 0,   "max": 100,  "default": 0,   "label": "cPRA (kidney only)"},
    "meld":         {"min": 6,   "max": 40,   "default": 15,  "label": "MELD Score (liver only)"},
    "las":          {"min": 0,   "max": 100,  "default": 50,  "label": "Lung Allocation Score"},
    "urgency":      {"min": 1,   "max": 4,    "default": 2,   "label": "Urgency Level"},
}

# Max steps per sweep (tier-capped by the router)
MAX_STEPS = 10


@dataclass
class SweepPoint:
    value: float
    spearman_rho: Optional[float]  # rho vs previous step (None for first)
    top5: list[str]                 # top-5 center codes


@dataclass
class ModelSensitivityResult:
    param: str
    param_label: str
    baseline_value: float
    values: list[float]
    spearman_rhos: list[Optional[float]]
    top5_sets: list[list[str]]
    mean_rho: float             # average stability (1.0 = perfectly stable)
    min_rho: float              # worst-case instability
    baseline_top5: list[str]   # top-5 at baseline value
    top5_overlap_with_baseline: list[float]  # jaccard overlap at each step
    elapsed_seconds: float


def sweep_parameter(
    patient: PatientProfile,
    param: str,
    n_steps: int = 8,
    base_iterations: int = 300,
    seed: Optional[int] = None,
) -> ModelSensitivityResult:
    """
    Sweep *param* across its full range in n_steps evenly-spaced values.
    Returns Spearman ρ between each adjacent pair of city rankings.
    """
    t0 = time.perf_counter()

    if param not in SWEEP_PARAMS:
        raise ValueError(f"Unknown param '{param}'. Valid: {list(SWEEP_PARAMS)}")

    config = SWEEP_PARAMS[param]
    n_steps = min(n_steps, MAX_STEPS)
    values = np.linspace(config["min"], config["max"], n_steps).tolist()

    from services.monte_carlo import simulate

    rankings: list[list[str]] = []  # list of city-code lists ordered by p24mo desc

    for i, v in enumerate(values):
        # Build a patient clone with the modified parameter
        profile_dict = patient.model_dump()
        step_seed = None if seed is None else (seed + i * 997) % 2147483647

        if param == "copula_theta":
            result = simulate(
                patient,
                n_iterations=base_iterations,
                copula_theta_override=v,
                seed=step_seed,
            )
        elif param == "elasticity":
            result = simulate(
                patient,
                n_iterations=base_iterations,
                elasticity_override=v,
                seed=step_seed,
            )
        elif param == "iterations":
            result = simulate(patient, n_iterations=int(v), seed=step_seed)
        elif param in ("cpra", "meld", "las", "urgency"):
            profile_dict[param] = int(v) if param == "urgency" else v
            # Clamp urgency
            if param == "urgency":
                profile_dict["urgency"] = max(1, min(4, int(round(v))))
            modified = PatientProfile(**profile_dict)
            result = simulate(modified, n_iterations=base_iterations, seed=step_seed)
        else:
            result = simulate(patient, n_iterations=base_iterations, seed=step_seed)

        ordered = [c.center_code or c.city for c in result.cities]
        rankings.append(ordered)

    # Compute Spearman rho between each adjacent pair
    spearman_rhos: list[Optional[float]] = [None]
    for i in range(1, len(rankings)):
        prev = rankings[i - 1]
        curr = rankings[i]
        # Build rank arrays for common items
        common = [c for c in prev if c in curr]
        if len(common) < 3:
            spearman_rhos.append(None)
            continue
        prev_ranks = [prev.index(c) for c in common]
        curr_ranks = [curr.index(c) for c in common]
        rho, _ = stats.spearmanr(prev_ranks, curr_ranks)
        spearman_rhos.append(float(rho))

    valid_rhos = [r for r in spearman_rhos if r is not None]
    mean_rho = float(np.mean(valid_rhos)) if valid_rhos else 0.0
    min_rho = float(min(valid_rhos)) if valid_rhos else 0.0

    # Top-5 for each step
    top5_sets = [r[:5] for r in rankings]

    # Baseline: value closest to config["default"]
    baseline_idx = int(np.argmin([abs(v - config["default"]) for v in values]))
    baseline_top5 = top5_sets[baseline_idx]

    # Jaccard overlap with baseline top-5
    def jaccard(a, b):
        sa, sb = set(a), set(b)
        if not sa and not sb:
            return 1.0
        return len(sa & sb) / len(sa | sb)

    overlaps = [jaccard(t5, baseline_top5) for t5 in top5_sets]

    return ModelSensitivityResult(
        param=param,
        param_label=config["label"],
        baseline_value=config["default"],
        values=values,
        spearman_rhos=spearman_rhos,
        top5_sets=top5_sets,
        mean_rho=mean_rho,
        min_rho=min_rho,
        baseline_top5=baseline_top5,
        top5_overlap_with_baseline=overlaps,
        elapsed_seconds=time.perf_counter() - t0,
    )
