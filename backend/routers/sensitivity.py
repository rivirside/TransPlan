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
        description="City to run sensitivity analysis for (use top-ranked city from /simulate)",
    )
    iterations: int = Field(default=300, ge=100, le=2000)


@router.post("/sensitivity", response_model=SensitivityResult)
def run_sensitivity(request: SensitivityRequest) -> SensitivityResult:
    try:
        return compute_sensitivity(request.patient, request.city, request.iterations)
    except Exception as e:
        logger.exception("Sensitivity analysis failed for %s/%s", request.patient.organ, request.city)
        raise HTTPException(status_code=500, detail="Sensitivity analysis failed — see server logs") from e
