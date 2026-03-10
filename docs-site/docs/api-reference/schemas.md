---
sidebar_position: 3
---

# Schemas

Complete Pydantic schema reference for the TransPlan API. Source: `backend/models/schemas.py`.

## PatientProfile

Input schema for simulation requests.

```python
class PatientProfile(BaseModel):
    organ: Literal["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
    blood_type: str  # pattern: ^(A|B|AB|O)[+-]$
    age: int         # 0–99
    sex: Literal["male", "female"]
    urgency: int     # 1–4
    insurance: Optional[Literal["medicare", "medicaid", "private", "uninsured"]]
    weight_lbs: Optional[float]    # > 0, < 1000
    height_inches: Optional[float] # > 0, < 120
    cpra: Optional[int]    # 0–100 (kidney only)
    meld: Optional[int]    # 6–40  (liver only)
    las: Optional[float]   # 0–100 (lung only)
    home_center: Optional[str]     # Patient's current listing center (city name)
    adjust_for_cause_of_death: bool  # default False; apply COD donor multiplier
```

### Field Details

#### `organ`
One of six transplantable solid organs. Determines which wait time distribution, competing risks model, and clinical score multiplier are used.

#### `blood_type`
ABO type with Rh factor. Must match the regex `^(A|B|AB|O)[+-]$`. Valid values:
`A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-`

#### `urgency`
Urgency level on a 1–4 scale:

| Value | Meaning |
|-------|---------|
| 1 | Elective / stable |
| 2 | Moderate urgency |
| 3 | High urgency |
| 4 | Emergency (Status 1A/1B equivalent) |

#### `cpra`
Calculated Panel Reactive Antibody percentage (kidney only). Range 0–100.
At 0%, the patient has no sensitization and will accept most donors. At 80%+, the patient is highly sensitized and needs a rare compatible donor, significantly extending wait time. At 99%+, only extremely rare matches exist.

#### `meld`
Model for End-Stage Liver Disease score (liver only). Range 6–40.
Scores of 6–14 indicate low urgency. Scores of 15–24 indicate moderate urgency with expedited allocation. Scores of 25–35 carry high urgency with significant mortality risk. Scores above 35 trigger emergency allocation with the shortest expected wait.

#### `las`
Lung Allocation Score (lung only). Range 0–100.
Higher scores indicate greater urgency and receive allocation priority.

---

## CityProbability

Per-city simulation output.

```python
class CityProbability(BaseModel):
    city: str
    state: str
    p_transplant_6mo: float   # [0, 1]
    p_transplant_12mo: float  # [0, 1]
    p_transplant_24mo: float  # [0, 1]
    p_transplant_36mo: float  # [0, 1]
    confidence_interval_95: tuple[float, float]  # for 24-month probability
    median_wait_months: float  # > 0
    competing_risks: Optional[dict]
    # competing_risks = {
    #   "p_transplant": float,
    #   "p_mortality": float,
    #   "p_delisting": float,
    #   "p_still_waiting": float
    # }  ← all sum to 1.0
```

---

## SimulationResult

Top-level response schema.

```python
class SimulationResult(BaseModel):
    patient: PatientProfile
    cities: list[CityProbability]  # ranked by p_transplant_24mo descending
    iterations: int
    elapsed_seconds: float
    deterministic_scores: dict  # { city_name: float }
```

#### `deterministic_scores`
Phase 1 suitability scores (0–100) for all 22 cities, computed in parallel with the Monte Carlo simulation. Useful for side-by-side comparison.

---

## HealthResponse

`GET /health` response.

```python
class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    data_freshness: dict  # { filename: iso_timestamp_string }
    data_files_loaded: int
```

---

## ParameterImpact

Per-parameter sensitivity data (part of SensitivityResult).

```python
class ParameterImpact(BaseModel):
    parameter: str        # e.g., 'cpra', 'meld', 'las', 'urgency'
    label: str            # Human-readable name
    baseline_value: float # Patient's current value
    low_value: float      # Most favorable extreme tested
    high_value: float     # Least favorable extreme tested
    p24_baseline: float   # p_transplant_24mo at patient's actual value
    p24_at_low: float     # p_transplant_24mo at low_value
    p24_at_high: float    # p_transplant_24mo at high_value
```

---

## SensitivityResult

`POST /sensitivity` response.

```python
class SensitivityResult(BaseModel):
    patient: PatientProfile
    city: str                       # City used for analysis
    impacts: list[ParameterImpact]  # Sorted by magnitude (largest first)
    iterations: int
    elapsed_seconds: float
```

---

## CityEquity

Per-city equity metrics (part of EquityAnalysisResult).

```python
class CityEquity(BaseModel):
    city: str
    state: str
    gini_coefficient: float                # 0 = equality, 1 = total inequality
    p24_range: tuple[float, float]         # (min, max) p_transplant_24mo across profiles
    median_wait_range: tuple[float, float] # (min, max) median wait across profiles
    dimension_disparities: dict[str, list[dict]]
    # e.g., { 'blood_type': [{value, p24, median_wait}, ...], ... }
```

---

## EquityAnalysisResult

`POST /equity-analysis` response.

```python
class EquityAnalysisResult(BaseModel):
    organ: str
    cities: list[CityEquity]       # Sorted by gini ascending (most equitable first)
    overall_gini: float            # Gini across all profiles × all cities
    profiles_simulated: int        # Total demographic profiles (48)
    iterations_per_profile: int
    elapsed_seconds: float
    disclaimers: list[str]         # Mandatory limitation disclaimers
```

---

## Frontend Field Mapping

The frontend form uses camelCase. `api-client.js` normalizes to snake_case before sending:

| Form field | API field |
|-----------|-----------|
| `bloodType` | `blood_type` |
| `weightLbs` | `weight_lbs` |
| `heightInches` | `height_inches` |
| `cpra` | `cpra` |
| `meld` | `meld` |
| `las` | `las` |
| `urgency` | `urgency` |
| `organ` | `organ` |
| `age` | `age` |
| `sex` | `sex` |
| `homeCenter` | `home_center` |
| `adjustForCauseOfDeath` | `adjust_for_cause_of_death` |
