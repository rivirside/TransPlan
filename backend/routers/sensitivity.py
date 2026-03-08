"""POST /sensitivity — Input parameter sensitivity analysis endpoint."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from models.schemas import PatientProfile, SensitivityResult
from services.sensitivity import compute_sensitivity

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
    return compute_sensitivity(request.patient, request.city, request.iterations)
