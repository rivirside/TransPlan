"""POST /equity-analysis and /bias-audit — demographic equity endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import EquityAnalysisResult, PatientProfile
from services.equity import compute_equity_analysis, compute_bias_audit

logger = logging.getLogger(__name__)
router = APIRouter()


class EquityAnalysisRequest(BaseModel):
    patient: PatientProfile
    iterations_per_profile: int = Field(
        default=200, ge=50, le=5000,
        description="Monte Carlo iterations per demographic profile (lower = faster, less precise)"
    )
    max_centers: Optional[int] = Field(
        default=None, ge=5, le=300,
        description="Optional cap on centers analyzed. Default None = all centers "
                    "(feasible since p24 is closed-form, #216)."
    )
    seed: Optional[int] = Field(None, ge=0, le=2147483647, description="RNG seed for reproducibility")


@router.post("/equity-analysis", response_model=EquityAnalysisResult)
def run_equity_analysis(request: EquityAnalysisRequest) -> EquityAnalysisResult:
    """Run equity analysis across demographic profiles for transplant centers."""
    try:
        from tier_config import get_tier
        tier = get_tier()
        iterations = min(request.iterations_per_profile, tier.max_equity_iterations)
        # Default: analyze all centers (None), bounded by the tier ceiling. An
        # explicit request cap is honored, also bounded by the tier.
        if request.max_centers is None:
            centers = tier.max_equity_centers
        else:
            centers = min(request.max_centers, tier.max_equity_centers)
        return compute_equity_analysis(
            request.patient,
            n_iterations=iterations,
            seed=request.seed,
            max_centers=centers,
        )
    except Exception as e:
        logger.exception("Equity analysis failed for %s", request.patient.organ)
        raise HTTPException(status_code=500, detail="Equity analysis failed — see server logs") from e


@router.post("/bias-audit")
def run_bias_audit_endpoint(request: EquityAnalysisRequest):
    """Publication-grade bias metrics (disparity ratios, Cohen's d) computed
    from the equity analysis' per-profile results (#254 — previously unwired)."""
    try:
        from tier_config import get_tier
        tier = get_tier()
        if request.max_centers is None:
            centers = tier.max_equity_centers
        else:
            centers = min(request.max_centers, tier.max_equity_centers)
        return compute_bias_audit(
            request.patient,
            seed=request.seed,
            max_centers=centers,
        )
    except Exception as e:
        logger.exception("Bias audit failed for %s", request.patient.organ)
        raise HTTPException(status_code=500, detail="Bias audit failed — see server logs") from e
