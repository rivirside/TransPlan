"""POST /score — Comprehensive center-level suitability scoring."""
import time

from fastapi import APIRouter, Query

from models.schemas import (
    CenterScore,
    CenterScoreProvenance,
    PatientProfile,
    ScoringResult,
    ScoringResultWithProvenance,
)
from services.scoring import score_all_centers
from services.scoring_explain import explain_all_centers

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


@router.post("/score/explain", response_model=ScoringResultWithProvenance)
async def score_centers_with_provenance(
    patient: PatientProfile,
    limit: int = Query(
        default=20,
        ge=1,
        le=248,
        description="Limit provenance to top-N centers (default 20). Set to 248 for all.",
    ),
):
    """Score all centers AND return full per-center calculation provenance.

    Use this endpoint to audit exactly how each score was derived: which data
    files were consulted, which multipliers were applied, and how each
    sub-component contributed to the final category and total scores.

    `limit` controls how many top-ranked centers receive provenance trails
    (computing provenance for all 248 centers is ~10x slower than scoring alone).
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

    # Run the production scoring path (preserves ranking + tests)
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

    # Run the explain path for the top N
    provenance_dicts = explain_all_centers(
        patient_dict, patient.custom_weights, limit=limit
    )
    provenance = [CenterScoreProvenance(**p) for p in provenance_dicts]

    elapsed = time.perf_counter() - t0
    return ScoringResultWithProvenance(
        patient=patient,
        centers=centers,
        provenance=provenance,
        total_centers=len(centers),
        elapsed_seconds=round(elapsed, 3),
    )
