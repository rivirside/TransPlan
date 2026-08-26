"""POST /multi-listing — joint transplant probability across 2-5 listings (#321)."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import PatientProfile

logger = logging.getLogger(__name__)
router = APIRouter()


class MultiListingRequest(BaseModel):
    patient: PatientProfile
    center_codes: list[str] = Field(min_length=2, max_length=5,
                                    description="2-5 SRTR center codes; for "
                                    "non-kidney organs the FIRST is the "
                                    "current listing (accrued time applies "
                                    "only there)")
    seed: int | None = Field(None, ge=0, le=2147483647)


@router.post("/multi-listing")
def multi_listing(request: MultiListingRequest) -> dict:
    """Joint P(transplant) for a patient listed at several centers, with the
    listings coupled by their allocation-circle overlap (L-074)."""
    try:
        from services.multi_listing import compute_multi_listing
        return compute_multi_listing(request.patient, request.center_codes,
                                     seed=request.seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Multi-listing failed for %s", request.patient.organ)
        raise HTTPException(status_code=500,
                            detail="Multi-listing analysis failed — see server logs") from e
