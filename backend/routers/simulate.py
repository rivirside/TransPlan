"""POST /simulate — Monte Carlo, Bayesian, or MCMC inference endpoint."""
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from models.schemas import PatientProfile, SimulationResult
from services.monte_carlo import simulate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/simulate", response_model=SimulationResult)
def run_simulation(
    patient: PatientProfile,
    iterations: int = Query(default=None, ge=100, le=10000, description="Override default iteration count"),
    inference_mode: Literal["monte_carlo", "bayesian", "mcmc"] = Query(
        default="monte_carlo",
        description="Inference engine: 'monte_carlo' (default), 'bayesian' (exact), or 'mcmc' (posterior sampling)",
    ),
) -> SimulationResult:
    try:
        if inference_mode == "bayesian":
            from services.bayesian_network import simulate_bbn
            return simulate_bbn(patient)
        if inference_mode == "mcmc":
            from services.mcmc_inference import is_available, simulate_mcmc
            if not is_available(patient.organ):
                raise HTTPException(
                    status_code=503,
                    detail=f"MCMC trace not available for {patient.organ}. "
                           f"Run scripts/fit-mcmc-model.py --organ {patient.organ} to generate it.",
                )
            return simulate_mcmc(patient, n_iterations=iterations)
        return simulate(patient, n_iterations=iterations)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Simulation failed for %s/%s", patient.organ, inference_mode)
        raise HTTPException(status_code=500, detail="Simulation failed — see server logs") from e
