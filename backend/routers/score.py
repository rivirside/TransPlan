"""POST /score — Comprehensive center-level suitability scoring."""
import time

from fastapi import APIRouter

from models.schemas import CenterScore, PatientProfile, ScoringResult
from services.scoring import score_all_centers

router = APIRouter()


@router.post("/score", response_model=ScoringResult)
async def score_centers(patient: PatientProfile):
    """Score all transplant centers for a patient profile.

    Returns centers ranked by weighted suitability score (8 categories).
    Uses center-level SRTR data + spatial interpolation for geographic factors.
    """
    t0 = time.perf_counter()

    patient_dict = {
        "organ": patient.organ,
        "blood_type": patient.blood_type,
        "age": patient.age,
        "sex": patient.sex,
        "urgency": patient.urgency,
        "insurance": patient.insurance,
        "weight_lbs": patient.weight_lbs,
        "height_inches": patient.height_inches,
        "cpra": patient.cpra,
        "meld": patient.meld,
        "las": patient.las,
        "adjust_for_cause_of_death": patient.adjust_for_cause_of_death,
    }

    results = score_all_centers(patient_dict, patient.custom_weights)

    centers = [
        CenterScore(
            code=r.code,
            name=r.name,
            state=r.state,
            state_abbr=r.state_abbr,
            lat=r.lat,
            lon=r.lon,
            total=r.total,
            breakdown=r.breakdown,
            rank=r.rank,
        )
        for r in results
    ]

    elapsed = time.perf_counter() - t0
    return ScoringResult(
        patient=patient,
        centers=centers,
        total_centers=len(centers),
        elapsed_seconds=round(elapsed, 3),
    )
