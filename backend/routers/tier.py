"""GET /tier -- returns active tier caps for frontend control gating."""
from fastapi import APIRouter

from tier_config import get_tier

router = APIRouter()


@router.get("/tier")
def get_tier_config():
    tier = get_tier()
    return {
        "name": tier.name,
        "caps": {
            "max_iterations": tier.max_iterations,
            "allowed_inference_modes": list(tier.allowed_inference_modes),
            "allowed_bbn_granularity": list(tier.allowed_bbn_granularity),
            "copula_theta_locked": tier.copula_theta_locked,
            "elasticity_locked": tier.elasticity_locked,
            "max_equity_centers": tier.max_equity_centers,
            "max_equity_iterations": tier.max_equity_iterations,
            "max_sensitivity_iterations": tier.max_sensitivity_iterations,
            "max_whatif_iterations": tier.max_whatif_iterations,
            "max_spatial_resolution": tier.max_spatial_resolution,
            "max_trend_years": tier.max_trend_years,
        },
    }
