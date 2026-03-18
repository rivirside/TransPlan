"""POST /simulate — Monte Carlo or Bayesian inference endpoint."""
from typing import Literal

from fastapi import APIRouter, Query

from models.schemas import PatientProfile, SimulationResult
from services.monte_carlo import simulate

router = APIRouter()


@router.post("/simulate", response_model=SimulationResult)
def run_simulation(
    patient: PatientProfile,
    iterations: int = Query(default=None, ge=100, le=10000, description="Override default iteration count"),
    inference_mode: Literal["monte_carlo", "bayesian"] = Query(
        default="monte_carlo",
        description="Inference engine: 'monte_carlo' (default, stochastic) or 'bayesian' (exact, faster)",
    ),
) -> SimulationResult:
    if inference_mode == "bayesian":
        from services.bayesian_network import simulate_bbn
        return simulate_bbn(patient)
    return simulate(patient, n_iterations=iterations)
