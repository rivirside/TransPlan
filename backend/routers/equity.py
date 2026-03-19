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
        default=300, ge=100, le=1000,
        description="Monte Carlo iterations per demographic profile (lower = faster, less precise)"
    )


@router.post("/equity-analysis", response_model=EquityAnalysisResult)
def run_equity_analysis(request: EquityAnalysisRequest) -> EquityAnalysisResult:
    """Run equity analysis across demographic profiles for all 22 cities."""
    try:
        return compute_equity_analysis(request.patient, request.iterations_per_profile)
    except Exception as e:
        logger.exception("Equity analysis failed for %s", request.patient.organ)
        raise HTTPException(status_code=500, detail="Equity analysis failed — see server logs") from e
