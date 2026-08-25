"""POST /rank-stability — bootstrap rank intervals for the center ranking (#313)."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import PatientProfile

logger = logging.getLogger(__name__)
router = APIRouter()


class RankStabilityRequest(BaseModel):
    patient: PatientProfile
    n_boot: int = Field(default=500, ge=50, le=2000,
                        description="Bootstrap replicates")
    seed: int | None = Field(None, ge=0, le=2147483647)


@router.post("/rank-stability")
def rank_stability(request: RankStabilityRequest) -> dict:
    """Per-center rank intervals + statistical tie groups.

    Propagates the data-sampling uncertainty of each center's observed SRTR
    cohort into the ranking, so a #5 that is statistically tied with #3-#9
    is presented as such instead of with false precision.
    """
    try:
        from services.rank_stability import compute_rank_stability
        return compute_rank_stability(request.patient, n_boot=request.n_boot,
                                      seed=request.seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Rank stability failed for %s", request.patient.organ)
        raise HTTPException(status_code=500,
                            detail="Rank stability failed — see server logs") from e
