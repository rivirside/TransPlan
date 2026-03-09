"""POST /equity-analysis — Demographic equity analysis endpoint."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from models.schemas import EquityAnalysisResult, PatientProfile
from services.equity import compute_equity_analysis

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
    return compute_equity_analysis(request.patient, request.iterations_per_profile)
