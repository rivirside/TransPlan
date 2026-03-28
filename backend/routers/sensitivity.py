"""POST /sensitivity — Input parameter sensitivity analysis endpoint."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import PatientProfile, SensitivityResult
from services.sensitivity import compute_sensitivity

logger = logging.getLogger(__name__)
router = APIRouter()


class SensitivityRequest(BaseModel):
    patient: PatientProfile
    city: str = Field(
        default="Nashville",
        description="City name (legacy) or display label for the center",
    )
    center_code: str = Field(
        default="",
        description="SRTR center code (preferred over city name)",
    )
    iterations: int = Field(default=1000, ge=100, le=5000)


@router.post("/sensitivity", response_model=SensitivityResult)
def run_sensitivity(request: SensitivityRequest) -> SensitivityResult:
    try:
        from tier_config import get_tier
        tier = get_tier()
        iterations = min(request.iterations, tier.max_sensitivity_iterations)
        return compute_sensitivity(
            request.patient, request.city, iterations,
            center_code=request.center_code,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Sensitivity analysis failed for %s/%s", request.patient.organ, request.city)
        raise HTTPException(status_code=500, detail="Sensitivity analysis failed — see server logs") from e
