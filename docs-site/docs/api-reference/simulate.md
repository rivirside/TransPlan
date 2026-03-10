---
sidebar_position: 1
---

# POST /simulate

Run Monte Carlo transplant location simulation for a patient profile.

## Request

```
POST /simulate
Content-Type: application/json
```

### Request Body

```json
{
  "patient": {
    "organ": "kidney",
    "blood_type": "O+",
    "age": 45,
    "sex": "male",
    "urgency": 2,
    "cpra": 35,
    "weight_lbs": 180,
    "height_inches": 70,
    "home_center": "Chicago",
    "adjust_for_cause_of_death": false
  }
}
```

### PatientProfile Schema

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `organ` | string | ✓ | `kidney` `liver` `heart` `lung` `pancreas` `intestine` | Organ type |
| `blood_type` | string | ✓ | `A+` `A-` `B+` `B-` `AB+` `AB-` `O+` `O-` | ABO blood type |
| `age` | integer | ✓ | 0–99 | Patient age in years |
| `sex` | string | ✓ | `male` `female` | Biological sex |
| `urgency` | integer | ✓ | 1–4 | Urgency level (1=elective, 4=emergency) |
| `insurance` | string | no | `medicare` `medicaid` `private` `uninsured` | Insurance type |
| `weight_lbs` | float | no | 0–1000 | Weight in pounds |
| `height_inches` | float | no | 0–120 | Height in inches |
| `cpra` | integer | no | 0–100 | cPRA % (kidney only) |
| `meld` | integer | no | 6–40 | MELD score (liver only) |
| `las` | float | no | 0–100 | Lung Allocation Score (lung only) |
| `home_center` | string | no | Valid city name | Patient's current transplant listing center |
| `adjust_for_cause_of_death` | boolean | no | default `false` | Apply organ-specific COD donor recovery multiplier |

## Response

```json
{
  "patient": { ... },
  "cities": [
    {
      "city": "Minneapolis",
      "state": "MN",
      "p_transplant_6mo": 0.18,
      "p_transplant_12mo": 0.39,
      "p_transplant_24mo": 0.63,
      "p_transplant_36mo": 0.78,
      "confidence_interval_95": [0.56, 0.70],
      "median_wait_months": 19.4,
      "competing_risks": {
        "p_transplant": 0.63,
        "p_mortality": 0.07,
        "p_delisting": 0.09,
        "p_still_waiting": 0.21
      }
    },
    ...
  ],
  "iterations": 1000,
  "elapsed_seconds": 0.082,
  "deterministic_scores": {
    "Minneapolis": 76.4,
    "Boston": 74.1,
    ...
  }
}
```

### SimulationResult Schema

| Field | Type | Description |
|-------|------|-------------|
| `patient` | PatientProfile | Echo of the request patient profile |
| `cities` | CityProbability[] | Ranked by `p_transplant_24mo` descending |
| `iterations` | integer | Number of Monte Carlo iterations (1000) |
| `elapsed_seconds` | float | Server-side simulation time |
| `deterministic_scores` | object | Phase 1 suitability scores `{ city: score }` |

### CityProbability Schema

| Field | Type | Description |
|-------|------|-------------|
| `city` | string | City name |
| `state` | string | Two-letter state code |
| `p_transplant_6mo` | float [0,1] | Probability of transplant within 6 months |
| `p_transplant_12mo` | float [0,1] | Probability of transplant within 12 months |
| `p_transplant_24mo` | float [0,1] | Probability of transplant within 24 months |
| `p_transplant_36mo` | float [0,1] | Probability of transplant within 36 months |
| `confidence_interval_95` | [float, float] | Bootstrap 95% CI for 24-month probability |
| `median_wait_months` | float | Median wait across all iterations |
| `competing_risks` | object | Outcome probabilities at 24 months (sum to 1.0) |

### competing_risks Object

| Key | Type | Description |
|-----|------|-------------|
| `p_transplant` | float | Transplant probability at 24 months |
| `p_mortality` | float | Mortality while waiting at 24 months |
| `p_delisting` | float | Delisted probability at 24 months |
| `p_still_waiting` | float | Still on list at 24 months |

All four values sum to 1.0.

## Error Responses

### 422 Unprocessable Entity

Returned when the request body fails Pydantic validation:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "patient", "blood_type"],
      "msg": "String should match pattern '^(A|B|AB|O)[+-]$'",
      "input": "O positive"
    }
  ]
}
```

### 500 Internal Server Error

Rare. This occurs only if data files are corrupted or missing. Check `/health` to diagnose.

## Example: Kidney Patient

```bash
curl -X POST http://localhost:8002/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "patient": {
      "organ": "kidney",
      "blood_type": "O-",
      "age": 52,
      "sex": "female",
      "urgency": 2,
      "cpra": 80
    }
  }'
```

## Performance

Typical response time: **60–100ms** for 1,000 iterations × 22 cities. There is no caching; each request recomputes fresh.
