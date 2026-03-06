"""POST /simulate — Monte Carlo simulation endpoint (Milestone 3)."""
from fastapi import APIRouter, HTTPException
from models.schemas import PatientProfile, SimulationResult

router = APIRouter()


@router.post("/simulate", response_model=SimulationResult)
def simulate(patient: PatientProfile) -> SimulationResult:
    # FIXME (Milestone 3): Replace stub with full Monte Carlo engine.
    raise HTTPException(
        status_code=501,
        detail="Simulation engine not yet implemented — coming in Milestone 3.",
    )
