"""POST /simulate — Monte Carlo simulation endpoint."""
from fastapi import APIRouter, Query

from models.schemas import PatientProfile, SimulationResult
from services.monte_carlo import simulate

router = APIRouter()


@router.post("/simulate", response_model=SimulationResult)
def run_simulation(
    patient: PatientProfile,
    iterations: int = Query(default=None, ge=100, le=10000, description="Override default iteration count"),
) -> SimulationResult:
    return simulate(patient, n_iterations=iterations)
