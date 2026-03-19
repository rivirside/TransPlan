"""What-if scenario analysis endpoints.

POST /what-if — Raw multiplier-based what-if analysis (Phase 3 M5).
POST /policy-scenario — Policy scenario analysis with literature-backed parameters (Phase 4 M4).
GET /policy-scenarios — List available predefined policy scenarios.
GET /policy-scenarios/{scenario_id} — Get a specific scenario's details.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field

from models.schemas import PatientProfile
from services.what_if import compute_what_if, WhatIfResult
from services.policy_scenarios import (
    PolicyScenario, list_scenarios, get_scenario, get_city_multipliers,
)

router = APIRouter()


# --- Raw multiplier endpoint (unchanged) ---

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
    try:
        return compute_what_if(
            patient=request.patient,
            city=request.city,
            donor_rate_multiplier=request.donor_rate_multiplier,
            wait_time_multiplier=request.wait_time_multiplier,
            n_iterations=request.iterations,
        )
    except Exception as e:
        logger.exception("What-if analysis failed for %s/%s", request.patient.organ, request.city)
        raise HTTPException(status_code=500, detail="What-if analysis failed — see server logs") from e


# --- Policy scenario endpoints (Phase 4 M4) ---

class PolicyScenarioRequest(BaseModel):
    patient: PatientProfile
    scenario_id: str = Field(description="ID of the predefined policy scenario")
    city: str = Field(
        default="Nashville",
        description="City to run scenario analysis for",
    )
    iterations: int = Field(default=500, ge=100, le=2000)


class PolicyScenarioResult(BaseModel):
    """Result of a policy scenario analysis."""
    scenario: PolicyScenario
    city: str
    state: str
    donor_rate_multiplier: float = Field(description="Effective multiplier for this city")
    wait_time_multiplier: float = Field(description="Effective multiplier for this city")
    baseline_p24: float
    adjusted_p24: float
    delta_p24: float
    baseline_ci_95: tuple[float, float]
    adjusted_ci_95: tuple[float, float]
    baseline_median_wait: float
    adjusted_median_wait: float
    iterations: int
    elapsed_seconds: float


@router.get("/policy-scenarios", response_model=list[PolicyScenario])
def get_policy_scenarios(organ: Optional[str] = None) -> list[PolicyScenario]:
    """List available predefined policy scenarios, optionally filtered by organ."""
    return list_scenarios(organ=organ)


@router.get("/policy-scenarios/{scenario_id}", response_model=PolicyScenario)
def get_policy_scenario(scenario_id: str) -> PolicyScenario:
    """Get details of a specific policy scenario."""
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return scenario


@router.post("/policy-scenario", response_model=PolicyScenarioResult)
def run_policy_scenario(request: PolicyScenarioRequest) -> PolicyScenarioResult:
    """
    Run a predefined policy scenario for a specific city.

    Looks up the scenario's per-city multipliers (or global defaults),
    then runs the same paired-seed Monte Carlo as /what-if.
    """
    scenario = get_scenario(request.scenario_id)
    if not scenario:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{request.scenario_id}' not found",
        )

    # Check organ applicability
    if scenario.organs and request.patient.organ not in scenario.organs:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Scenario '{scenario.name}' applies to "
                f"{', '.join(scenario.organs)} only, not {request.patient.organ}"
            ),
        )

    # Get effective multipliers for this city
    donor_mult, wait_mult = get_city_multipliers(scenario, request.city)

    # Run the what-if engine with scenario-derived multipliers
    result = compute_what_if(
        patient=request.patient,
        city=request.city,
        donor_rate_multiplier=donor_mult,
        wait_time_multiplier=wait_mult,
        n_iterations=request.iterations,
    )

    return PolicyScenarioResult(
        scenario=scenario,
        city=result.city,
        state=result.state,
        donor_rate_multiplier=donor_mult,
        wait_time_multiplier=wait_mult,
        baseline_p24=result.baseline_p24,
        adjusted_p24=result.adjusted_p24,
        delta_p24=result.delta_p24,
        baseline_ci_95=result.baseline_ci_95,
        adjusted_ci_95=result.adjusted_ci_95,
        baseline_median_wait=result.baseline_median_wait,
        adjusted_median_wait=result.adjusted_median_wait,
        iterations=result.iterations,
        elapsed_seconds=result.elapsed_seconds,
    )
