"""Pydantic schemas for TransPlan Phase 2 API."""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class PatientProfile(BaseModel):
    organ: Literal["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
    blood_type: str = Field(
        ...,
        pattern=r"^(A|B|AB|O)[+-]$",
        examples=["O+", "A-", "AB+"],
    )
    age: int = Field(..., ge=1, le=99)
    sex: Literal["male", "female"]
    urgency: int = Field(..., ge=1, le=4)
    insurance: Optional[Literal["medicare", "medicaid", "private", "uninsured"]] = None
    weight_lbs: Optional[float] = Field(None, gt=0, lt=1000)
    height_inches: Optional[float] = Field(None, gt=0, lt=120)
    # Organ-specific scores
    cpra: Optional[int] = Field(None, ge=0, le=100, description="Kidney only: % panel reactive antibodies")
    meld: Optional[int] = Field(None, ge=6, le=40, description="Liver only: MELD 3.0 score (the score in use since 2023; 6-40)")
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
        True,
        description="Use Clayton copula for correlated mortality/delisting draws (recommended; set False for independent exponentials)"
    )
    # Phase 6 #206: BBN region granularity
    bbn_granularity: str = Field(
        "state",
        description="BBN region node granularity: 'state' (~50 states) or 'full' (248 centers)"
    )
    # Phase 4 M1: Configurable scoring weights (frontend concern, passed through for export fidelity)
    custom_weights: Optional[dict[str, float]] = Field(
        None,
        description="Custom scoring weights as { category: decimal_fraction }. 8 keys, all >= 0, sum ~1.0"
    )
    # L-067 (#304): user-defined center set
    center_codes: Optional[list[str]] = Field(
        None,
        max_length=248,
        description="Restrict scoring/simulation to these SRTR center codes "
                    "(a user's shortlist). None/empty = all centers for the organ."
    )

    @model_validator(mode="after")
    def validate_bbn_granularity(self):
        # #293: 'classic' (22 cities) retired — coerce it (and anything
        # unknown) to the state default
        if self.bbn_granularity not in ("state", "full"):
            self.bbn_granularity = "state"
        return self

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
    city: str = Field(description="City or center name (display label)")
    state: str
    center_code: str = Field("", description="SRTR center code (e.g. 'PAPT')")
    center_name: str = Field("", description="Full center name")
    lat: Optional[float] = Field(None, description="Center latitude")
    lon: Optional[float] = Field(None, description="Center longitude")
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
    data_quality: Optional[list[str]] = Field(
        None,
        description="Degraded-input tags for this center (#300): e.g. "
                    "'wait_time_national_default', 'competing_risks_national_default', "
                    "'no_observed_outcomes'. None/empty = fully center-level inputs."
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
    seed_used: int = Field(0, description="RNG seed used for this run (for reproducibility)")
    deterministic_scores: dict = Field(
        default_factory=dict,
        description="Phase 1 suitability scores for comparison (city → score)"
    )
    inference_mode: Literal["monte_carlo", "bayesian", "mcmc"] = Field(
        default="monte_carlo",
        description="Which inference engine produced this result"
    )
    data_quality: Optional[dict] = Field(
        None,
        description="Response-level data-provenance summary (#300): per input "
                    "family, how many centers used center-level data vs fell "
                    "back to national defaults."
    )
    data_vintage: Optional[dict] = Field(
        None,
        description="Which SRTR release the inputs come from (#334) — "
                    "estimates reflect that release's cohorts, not "
                    "real-time allocation behavior",
    )


class CenterScore(BaseModel):
    """Comprehensive suitability score for a single transplant center."""
    code: str = Field(description="SRTR center code")
    name: str = Field(description="Center name")
    state: str = Field(description="Full state name")
    state_abbr: str = Field(description="Two-letter state abbreviation")
    lat: float
    lon: float
    total: float = Field(..., ge=0, le=100, description="Weighted total score")
    breakdown: dict[str, float] = Field(
        description="Per-category scores: medicalCompatibility, waitTime, donorAvailability, "
                    "hospitalQuality, geographic, healthDemographics, policy, socioeconomic"
    )
    rank: int = Field(..., ge=1)


class ScoringResult(BaseModel):
    """Response for POST /score endpoint."""
    patient: PatientProfile
    centers: list[CenterScore]
    total_centers: int
    elapsed_seconds: float
    data_quality: Optional[dict] = Field(
        None,
        description="Data-provenance summary (#219): per-center wait-factor/"
                    "outcomes coverage and any spatial layers that fell back "
                    "to constants."
    )
    data_vintage: Optional[dict] = Field(
        None,
        description="Which SRTR release the inputs come from (#334) — "
                    "estimates reflect that release's cohorts, not "
                    "real-time allocation behavior",
    )


# ── Provenance schemas (for ?explain=true) ──────────────────────────────

class LookupTableEntry(BaseModel):
    """One row of a lookup table used to score a component."""
    label: str = Field(description="What this row matches (e.g. '35-49', 'O+', 'Ohio')")
    value: Any = Field(description="Score, multiplier, or descriptive value (number or string)")
    highlighted: bool = Field(default=False, description="True if this row matched the patient's input")
    note: Optional[str] = Field(default=None, description="Optional context (e.g. 'pediatric premium')")


class ComponentDetails(BaseModel):
    """Detailed rule trail for a single component — answers 'why is the value what it is?'"""
    summary: Optional[str] = Field(default=None, description="One-line explanation of the rule")
    lookup_table: Optional[list[LookupTableEntry]] = Field(
        default=None,
        description="If the value came from a lookup table, the full table",
    )
    formula: Optional[str] = Field(default=None, description="Mathematical formula if applicable")
    notes: Optional[str] = Field(default=None, description="Additional context or caveats")


class ScoreComponent(BaseModel):
    """A single sub-component within a scoring category."""
    name: str = Field(description="Human-readable component name")
    value: float = Field(description="Raw or normalized value (0-100 scale typical)")
    weight_within_category: float = Field(description="Component's weight within its category (0-1)")
    contribution: float = Field(description="value × weight_within_category")
    source: str = Field(description="Where this value came from (data file, rule, fallback, etc.)")
    raw_input: Optional[Any] = Field(default=None, description="Underlying raw input that drove this value")
    details: Optional[ComponentDetails] = Field(
        default=None,
        description="Expanded explanation of the rule/lookup that produced this value",
    )


class CategoryProvenance(BaseModel):
    """Provenance for a single scoring category."""
    category: str = Field(description="Category key: medicalCompatibility, waitTime, etc.")
    score: float = Field(description="Final category score (0-100)")
    weight: float = Field(description="Category's weight in overall score (0-1)")
    contribution: float = Field(description="score × weight (this category's contribution to total)")
    components: list[ScoreComponent] = Field(description="Breakdown of sub-components")
    notes: Optional[str] = Field(default=None, description="Additional context (e.g., fallbacks used)")


class CenterScoreProvenance(BaseModel):
    """Full provenance trail for a single center's score."""
    code: str
    name: str
    total: float
    weights_used: dict[str, float] = Field(description="Final weights after normalization")
    categories: list[CategoryProvenance]
    data_sources: list[str] = Field(description="List of data files consulted")


class ScoringResultWithProvenance(BaseModel):
    """Response for POST /score?explain=true endpoint."""
    patient: PatientProfile
    centers: list[CenterScore]
    provenance: list[CenterScoreProvenance]
    total_centers: int
    elapsed_seconds: float


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
    city: str = Field(description="City or center used for sensitivity analysis")
    center_code: str = Field("", description="SRTR center code (if center-level analysis)")
    impacts: list[ParameterImpact] = Field(description="Sorted by magnitude of impact (largest first)")
    iterations: int
    elapsed_seconds: float
    seed_used: int = Field(0, description="RNG seed used for this run (for reproducibility)")
    data_quality: Optional[list[str]] = Field(
        None, description="Degraded-input tags for the analyzed center (#300)")


class DemographicGroup(BaseModel):
    """A specific demographic dimension + value used in equity analysis."""
    dimension: str = Field(description="e.g., 'blood_type', 'age_bracket', 'sex'")
    value: str = Field(description="e.g., 'O+', '18-34', 'female'")


class CityEquity(BaseModel):
    """Equity metrics for a single center/city across demographic profiles."""
    city: str
    state: str
    center_code: str = ""
    center_name: str = ""
    gini_coefficient: float = Field(ge=0, le=1, description="0=equality, 1=total inequality")
    gini_weighted: Optional[float] = Field(
        None, ge=0, le=1,
        description="Gini with cells population-weighted (US blood-type prevalence × approx OPTN waitlist age/sex mix)"
    )
    gini_between_blood_type: Optional[float] = Field(
        None, ge=0, le=1,
        description="Weighted Gini of the 8 blood-type mean p24s — the ABO-matching (biology) component"
    )
    gini_within_blood_type: Optional[float] = Field(
        None, ge=0, le=1,
        description="Weighted mean of within-blood-type Ginis (age/sex variation) — the non-ABO component"
    )
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
    overall_gini_weighted: Optional[float] = Field(
        None, ge=0, le=1, description="Population-weighted Gini across all profiles x all centers"
    )
    overall_gini_between_blood_type: Optional[float] = Field(
        None, ge=0, le=1, description="ABO-matching (biology) component of overall inequality"
    )
    overall_gini_within_blood_type: Optional[float] = Field(
        None, ge=0, le=1,
        description="Non-ABO component of overall inequality (geography + age/sex within blood type)"
    )
    profiles_simulated: int = Field(description="Total demographic profiles in matrix")
    iterations_per_profile: int
    elapsed_seconds: float
    seed_used: int = Field(0, description="RNG seed used for this run (for reproducibility)")
    disclaimers: list[str] = Field(description="Mandatory limitation disclaimers")


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    data_freshness: dict = Field(
        description="{ file_name: fetched_at_iso } for each loaded data file"
    )
    data_files_loaded: int


# ── What-if / policy-scenario request-response models (#264: moved from
# routers/what_if.py; PolicyScenarioResult stays in the router because it
# embeds the service-defined PolicyScenario type) ─────────────────────────

class WhatIfRequest(BaseModel):
    patient: PatientProfile
    center_code: str = Field(
        min_length=1,
        description="SRTR center code — REQUIRED (the legacy city-name mode "
                    "was retired, #285; requests without it are rejected)",
    )
    city: str = Field(
        default="",
        description="Optional display label only — ignored by the model "
                    "(the location factor comes from center_code)",
    )
    donor_rate_multiplier: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Multiplier for donor availability. >1 = more donors (shorter waits), <1 = fewer donors (longer waits)",
    )
    wait_time_multiplier: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Multiplier for base wait time distribution. >1 = longer waits, <1 = shorter waits",
    )
    iterations: int = Field(default=500, ge=100, le=2000)
    seed: Optional[int] = Field(None, ge=0, le=2147483647, description="RNG seed for reproducibility")


class PolicyScenarioRequest(BaseModel):
    patient: PatientProfile
    scenario_id: str = Field(description="ID of the predefined policy scenario")
    center_code: str = Field(
        min_length=1,
        description="SRTR center code — REQUIRED (the legacy city-name mode "
                    "was retired, #285; requests without it are rejected)",
    )
    city: str = Field(
        default="",
        description="Optional display label only — ignored by the model "
                    "(the location factor comes from center_code)",
    )
    iterations: int = Field(default=500, ge=100, le=2000)
    seed: Optional[int] = Field(None, ge=0, le=2147483647, description="RNG seed for reproducibility")


class TravelSubsidyRequest(BaseModel):
    patient: PatientProfile
    cities: list[str] = Field(
        default_factory=list,
        description="DEPRECATED (legacy 22-city filter) — use center_codes.",
    )
    center_codes: list[str] = Field(
        default_factory=list,
        description="SRTR center codes to analyze. Empty = all centers for the organ.",
    )
    iterations: int = Field(default=500, ge=100, le=2000,
                            description="Ignored since the sweep became closed-form (#285); kept for API compatibility.")
    seed: Optional[int] = Field(None, ge=0, le=2147483647, description="RNG seed for reproducibility")


class TravelSubsidyCityResult(BaseModel):
    """Result for one center at one price point."""
    city: str
    state: str
    center_code: str = ""
    baseline_p24: float
    adjusted_p24: float
    delta_p24: float
    baseline_median_wait: float
    adjusted_median_wait: float


class TravelSubsidyTierResult(BaseModel):
    """Result for one price point across all cities."""
    subsidy_amount: int
    label: str
    scenario_id: str
    system_avg_baseline_p24: float = Field(description="Average P(transplant ≤ 24mo) across all cities, no subsidy")
    system_avg_adjusted_p24: float = Field(description="Average P(transplant ≤ 24mo) across all cities, with subsidy")
    system_delta_p24: float = Field(description="System-wide improvement in average P24")
    system_avg_baseline_wait: float
    system_avg_adjusted_wait: float
    cities: list[TravelSubsidyCityResult]


class TravelSubsidyAnalysisResult(BaseModel):
    """Full multi-price-point travel subsidy comparison."""
    organ: str
    tiers: list[TravelSubsidyTierResult]
    total_cities: int
    iterations_per_city: int
    elapsed_seconds: float
    seed_used: int = Field(0, description="RNG seed used for this run (for reproducibility)")
    disclaimers: list[str]
