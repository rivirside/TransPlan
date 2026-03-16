"""POST /what-if — What-if scenario analysis with assumption multipliers.

Runs Monte Carlo simulation for a single city with adjusted model assumptions
(donor availability multiplier, wait time multiplier) to show how results
change under different scenarios. Returns both baseline and adjusted p24 values.

Unlike /sensitivity (which varies patient parameters), this endpoint varies
*model assumptions* — things like "what if donor availability were 20% higher?"
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from models.schemas import PatientProfile
from services.what_if import compute_what_if, WhatIfResult

router = APIRouter()


class WhatIfRequest(BaseModel):
    patient: PatientProfile
    city: str = Field(
        default="Nashville",
        description="City to run what-if analysis for",
    )
    donor_rate_multiplier: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Multiplier for donor availability. >1 = more donors (shorter waits), <1 = fewer donors (longer waits)",
    )
    wait_time_multiplier: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Multiplier for base wait time distribution. >1 = longer waits, <1 = shorter waits",
    )
    iterations: int = Field(default=500, ge=100, le=2000)


@router.post("/what-if", response_model=WhatIfResult)
def run_what_if(request: WhatIfRequest) -> WhatIfResult:
    return compute_what_if(
        patient=request.patient,
        city=request.city,
        donor_rate_multiplier=request.donor_rate_multiplier,
        wait_time_multiplier=request.wait_time_multiplier,
        n_iterations=request.iterations,
    )
