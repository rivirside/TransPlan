"""Tier-based caps for web vs local deployment.

Set TRANSPLAN_TIER=local to unlock all caps (default: web).
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TierConfig:
    name: str
    max_iterations: int
    allowed_inference_modes: tuple[str, ...]
    allowed_bbn_granularity: tuple[str, ...]
    copula_theta_locked: bool
    elasticity_locked: bool
    max_equity_centers: int
    max_equity_iterations: int
    max_sensitivity_iterations: int
    max_whatif_iterations: int
    max_spatial_resolution: int
    # Validation tool caps
    max_validation_iterations: int
    max_validation_sweep_steps: int
    max_validation_train_years: int
    # Trend projection cap
    max_trend_years: float


WEB_TIER = TierConfig(
    name="web",
    max_iterations=1000,
    allowed_inference_modes=("monte_carlo", "bayesian"),
    allowed_bbn_granularity=("classic", "state"),
    copula_theta_locked=True,
    elasticity_locked=True,
    # Equity p24 is now closed-form (#216), so the full center set runs in <1s
    # even on serverless — no need to cap the web tier at 30 anymore.
    max_equity_centers=248,
    max_equity_iterations=200,
    max_sensitivity_iterations=500,
    max_whatif_iterations=500,
    max_spatial_resolution=30,
    max_validation_iterations=300,
    max_validation_sweep_steps=6,
    max_validation_train_years=3,
    max_trend_years=2.0,
)

LOCAL_TIER = TierConfig(
    name="local",
    max_iterations=10000,
    allowed_inference_modes=("monte_carlo", "bayesian", "mcmc"),
    allowed_bbn_granularity=("classic", "state", "full"),
    copula_theta_locked=False,
    elasticity_locked=False,
    max_equity_centers=248,
    max_equity_iterations=5000,
    max_sensitivity_iterations=5000,
    max_whatif_iterations=2000,
    max_spatial_resolution=100,
    max_validation_iterations=1000,
    max_validation_sweep_steps=10,
    max_validation_train_years=6,
    max_trend_years=5.0,
)


def get_tier() -> TierConfig:
    """Return the active tier config based on TRANSPLAN_TIER env var."""
    tier_name = os.environ.get("TRANSPLAN_TIER", "web").lower()
    if tier_name == "local":
        return LOCAL_TIER
    return WEB_TIER
