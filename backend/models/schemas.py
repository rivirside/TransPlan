"""Pydantic schemas for TransPlan Phase 2 API."""
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


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
    # Organ-specific donor availability adjustment
    adjust_for_cause_of_death: bool = Field(
        False,
        description="Apply organ-specific donor recovery rates based on regional cause-of-death patterns"
    )
    # Phase 5 M2: Correlated competing risks via Clayton copula
    use_copula: bool = Field(
        False,
        description="Use Clayton copula for correlated mortality/delisting draws instead of independent exponentials"
    )
    # Phase 4 M1: Configurable scoring weights (frontend concern, passed through for export fidelity)
    custom_weights: Optional[dict[str, float]] = Field(
        None,
        description="Custom scoring weights as { category: decimal_fraction }. 8 keys, all >= 0, sum ~1.0"
    )

    @model_validator(mode="after")
    def validate_custom_weights(self):
        w = self.custom_weights
        if w is None:
            return self
        expected_keys = {
            "medicalCompatibility", "waitTime", "donorAvailability", "hospitalQuality",
            "geographic", "healthDemographics", "policy", "socioeconomic"
        }
        if set(w.keys()) != expected_keys:
            raise ValueError(
                f"custom_weights must have exactly these keys: {sorted(expected_keys)}; "
                f"got: {sorted(w.keys())}"
            )
        for k, v in w.items():
            if v < 0:
                raise ValueError(f"custom_weights['{k}'] must be >= 0, got {v}")
        total = sum(w.values())
        if total <= 0 or abs(total - 1.0) > 0.05:
            raise ValueError(
                f"custom_weights must sum to ~1.0 (tolerance ±0.05), got {total}"
            )
        return self


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
    outcomes: Optional[dict] = Field(
        None,
        description="Post-transplant: graft/patient survival, hazard ratio, compound success metric"
    )
    trends: Optional[dict] = Field(
        None,
        description="Historical trends: wait_time, volume, graft_survival with direction and sparkline data"
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
    inference_mode: Literal["monte_carlo", "bayesian", "mcmc"] = Field(
        default="monte_carlo",
        description="Which inference engine produced this result"
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


class DemographicGroup(BaseModel):
    """A specific demographic dimension + value used in equity analysis."""
    dimension: str = Field(description="e.g., 'blood_type', 'age_bracket', 'sex'")
    value: str = Field(description="e.g., 'O+', '18-34', 'female'")


class CityEquity(BaseModel):
    """Equity metrics for a single city across demographic profiles."""
    city: str
    state: str
    gini_coefficient: float = Field(ge=0, le=1, description="0=equality, 1=total inequality")
    p24_range: tuple[float, float] = Field(description="(min, max) of p_transplant_24mo across profiles")
    median_wait_range: tuple[float, float] = Field(description="(min, max) median wait months across profiles")
    dimension_disparities: dict[str, list[dict]] = Field(
        description="Per-dimension averages: { 'blood_type': [{value, p24, median_wait}, ...], ... }"
    )


class EquityAnalysisResult(BaseModel):
    """Full equity analysis response across demographic profiles and cities."""
    organ: str
    cities: list[CityEquity] = Field(description="Per-city equity metrics, sorted by gini ascending")
    overall_gini: float = Field(ge=0, le=1, description="Gini across all profiles x all cities")
    profiles_simulated: int = Field(description="Total demographic profiles in matrix")
    iterations_per_profile: int
    elapsed_seconds: float
    disclaimers: list[str] = Field(description="Mandatory limitation disclaimers")


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    data_freshness: dict = Field(
        description="{ file_name: fetched_at_iso } for each loaded data file"
    )
    data_files_loaded: int
