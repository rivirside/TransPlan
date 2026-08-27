"""POST /weight-range — rank span across the app's weighting presets (#386)."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.schemas import PatientProfile
from routers.score import _patient_to_dict
from services.weight_range import compute_weight_range

logger = logging.getLogger(__name__)
router = APIRouter()


class WeightRangeRequest(BaseModel):
    patient: PatientProfile


@router.post("/weight-range")
def run_weight_range(request: WeightRangeRequest):
    """How much does each center's rank move across the shipped weightings?

    Deliberately a separate endpoint rather than a field on /score: it costs
    four extra scoring passes, and adding that to every scoring call would
    slow the default path for a figure most callers do not request. The
    frontend fetches it in the background after the table renders, the same
    way rank stability (#313) does.
    """
    try:
        return compute_weight_range(_patient_to_dict(request.patient))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("weight-range failed for %s", request.patient.organ)
        raise HTTPException(
            status_code=500,
            detail="Weight-range analysis failed — see server logs") from e
