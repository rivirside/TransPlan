"""POST /score — Comprehensive center-level suitability scoring."""
import time

from fastapi import APIRouter, HTTPException, Query

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


def _patient_to_dict(patient: PatientProfile) -> dict:
    """Project a PatientProfile to the plain dict the scoring services expect."""
    return {
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
        "peld": patient.peld,
        "las": patient.las,
        "adjust_for_cause_of_death": patient.adjust_for_cause_of_death,
        "center_codes": patient.center_codes,
    }


def _to_center_scores(results, tag_lists: list[list[str]] | None = None) -> list[CenterScore]:
    """Project scoring results to the wire schema (#262: was copy-pasted).

    `tag_lists` is positional-by-index against `results`; omitted on /score/
    explain, whose consumers audit the calculation directly.
    """
    return [
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
            # Empty means "nothing degraded" — send None so the field is
            # absent rather than an empty array on 240-odd clean centers.
            data_quality=(tag_lists[i] or None) if tag_lists else None,
        )
        for i, r in enumerate(results)
    ]


@router.post("/score", response_model=ScoringResult)
async def score_centers(patient: PatientProfile):
    """Score all transplant centers for a patient profile.

    Returns centers ranked by weighted suitability score (8 categories).
    Uses center-level SRTR data + spatial interpolation for geographic factors.
    """
    t0 = time.perf_counter()

    patient_dict = _patient_to_dict(patient)

    try:
        results = score_all_centers(patient_dict, patient.custom_weights)
    except ValueError as e:
        # Caller-input problems (an empty center shortlist, or a pediatric
        # request for an organ with no pediatric program data) are 400s, and
        # must match how /simulate answers the same request (#335).
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Per-center provenance (#227), computed once and used twice: the summary
    # rolls these same lists up, so a second 248-center sweep would only be a
    # chance for the two to disagree.
    from services.provenance import scoring_summary, scoring_tags
    tag_lists = scoring_tags(patient.organ, [r.code for r in results])
    centers = _to_center_scores(results, tag_lists)

    # Data-provenance summary (#219/#340): one scoring-specific builder —
    # no more mutating the shared summary dict
    from services.scoring import unavailable_spatial_layers
    dq = scoring_summary(patient.organ, [c.code for c in centers],
                         spatial_layers_unavailable=unavailable_spatial_layers(),
                         tag_lists=tag_lists)

    from services.data_loader import get_data
    elapsed = time.perf_counter() - t0
    return ScoringResult(
        patient=patient,
        centers=centers,
        total_centers=len(centers),
        elapsed_seconds=round(elapsed, 3),
        data_quality=dq,
        data_vintage=get_data().srtr_vintage(),
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
    The active tier caps the effective limit (#249).
    """
    t0 = time.perf_counter()

    from tier_config import get_tier
    limit = min(limit, get_tier().max_score_explain_limit)

    patient_dict = _patient_to_dict(patient)  # single source of truth (#262)

    # Run the production scoring path (preserves ranking + tests)
    try:
        results = score_all_centers(patient_dict, patient.custom_weights)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    centers = _to_center_scores(results)

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
