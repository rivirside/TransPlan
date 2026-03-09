"""Pydantic schemas for TransPlan Phase 2 API."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class PatientProfile(BaseModel):
    organ: Literal["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
    blood_type: str = Field(
        ...,
        pattern=r"^(A|B|AB|O)[+-]$",
        examples=["O+", "A-", "AB+"],
    )
    age: int = Field(..., ge=0, le=99)
    sex: Literal["male", "female"]
    urgency: int = Field(..., ge=1, le=4)
    insurance: Optional[Literal["medicare", "medicaid", "private", "uninsured"]] = None
    weight_lbs: Optional[float] = Field(None, gt=0, lt=1000)
    height_inches: Optional[float] = Field(None, gt=0, lt=120)
    # Organ-specific scores
    cpra: Optional[int] = Field(None, ge=0, le=100, description="Kidney only: % panel reactive antibodies")
    meld: Optional[int] = Field(None, ge=6, le=40, description="Liver only: MELD score")
    las: Optional[float] = Field(None, ge=0, le=100, description="Lung only: Lung Allocation Score")
    # Relocation comparison
    home_center: Optional[str] = Field(None, description="Patient's current transplant listing center (city name)")


class CityProbability(BaseModel):
    city: str
    state: str
    p_transplant_6mo: float = Field(..., ge=0, le=1)
    p_transplant_12mo: float = Field(..., ge=0, le=1)
    p_transplant_24mo: float = Field(..., ge=0, le=1)
    p_transplant_36mo: float = Field(..., ge=0, le=1)
    confidence_interval_95: tuple[float, float] = Field(
        ..., description="95% CI for 24-month probability"
    )
    median_wait_months: float = Field(..., gt=0)
    competing_risks: Optional[dict] = Field(
        None,
        description="{ p_transplant, p_mortality, p_delisting, p_still_waiting } at 24 months"
    )


class SimulationResult(BaseModel):
    patient: PatientProfile
    cities: list[CityProbability]  # Ranked by p_transplant_24mo descending
    iterations: int
    elapsed_seconds: float
    deterministic_scores: dict = Field(
        default_factory=dict,
        description="Phase 1 suitability scores for comparison (city → score)"
    )


class ParameterImpact(BaseModel):
    parameter: str = Field(description="Parameter key: 'cpra', 'meld', 'las', 'urgency'")
    label: str = Field(description="Human-readable parameter name")
    baseline_value: float = Field(description="Patient's current value")
    low_value: float = Field(description="Most favorable extreme tested")
    high_value: float = Field(description="Least favorable extreme tested")
    p24_baseline: float = Field(..., ge=0, le=1, description="p_transplant_24mo at patient's actual value")
    p24_at_low: float = Field(..., ge=0, le=1, description="p_transplant_24mo at low_value")
    p24_at_high: float = Field(..., ge=0, le=1, description="p_transplant_24mo at high_value")


class SensitivityResult(BaseModel):
    patient: PatientProfile
    city: str = Field(description="City used for sensitivity analysis")
    impacts: list[ParameterImpact] = Field(description="Sorted by magnitude of impact (largest first)")
    iterations: int
    elapsed_seconds: float


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    data_freshness: dict = Field(
        description="{ file_name: fetched_at_iso } for each loaded data file"
    )
    data_files_loaded: int
