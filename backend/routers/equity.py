"""POST /equity-analysis — Demographic equity analysis endpoint."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import EquityAnalysisResult, PatientProfile
from services.equity import compute_equity_analysis

logger = logging.getLogger(__name__)
router = APIRouter()


class EquityAnalysisRequest(BaseModel):
    patient: PatientProfile
    iterations_per_profile: int = Field(
        default=200, ge=50, le=5000,
        description="Monte Carlo iterations per demographic profile (lower = faster, less precise)"
    )
    max_centers: int = Field(
        default=30, ge=5, le=300,
        description="Maximum number of transplant centers to include (caps simulation size)"
    )


@router.post("/equity-analysis", response_model=EquityAnalysisResult)
def run_equity_analysis(request: EquityAnalysisRequest) -> EquityAnalysisResult:
    """Run equity analysis across demographic profiles for all 22 cities."""
    try:
        from tier_config import get_tier
        tier = get_tier()
        iterations = min(request.iterations_per_profile, tier.max_equity_iterations)
        centers = min(request.max_centers, tier.max_equity_centers)
        return compute_equity_analysis(
            request.patient,
            n_iterations=iterations,
            max_centers=centers,
        )
    except Exception as e:
        logger.exception("Equity analysis failed for %s", request.patient.organ)
        raise HTTPException(status_code=500, detail="Equity analysis failed — see server logs") from e
