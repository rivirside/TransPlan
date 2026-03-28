---
sidebar_position: 1
---

# POST /simulate

Run transplant location simulation for a patient profile across all SRTR centers that perform the requested organ.

## Request

```
POST /simulate?iterations=1000&inference_mode=monte_carlo&copula_theta=1.0&elasticity=0.65
Content-Type: application/json
```

### Query Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `iterations` | int | 1000 | Monte Carlo iterations per center (100-10000) |
| `inference_mode` | string | `monte_carlo` | Engine: `monte_carlo`, `bayesian`, or `mcmc` |
| `copula_theta` | float | per-organ | Override Clayton copula theta (0.1-5.0; requires `use_copula: true`) |
| `elasticity` | float | 0.65 | Override supply-wait elasticity (0.1-1.0) |

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
| `organ` | string | yes | `kidney` `liver` `heart` `lung` `pancreas` `intestine` | Organ type |
| `blood_type` | string | yes | `A+` `A-` `B+` `B-` `AB+` `AB-` `O+` `O-` | ABO blood type |
| `age` | integer | yes | 1-99 | Patient age in years |
| `sex` | string | yes | `male` `female` | Biological sex |
| `urgency` | integer | yes | 1-4 | Urgency level (1=elective, 4=emergency) |
| `insurance` | string | no | `medicare` `medicaid` `private` `uninsured` | Insurance type |
| `weight_lbs` | float | no | 0-1000 | Weight in pounds |
| `height_inches` | float | no | 0-120 | Height in inches |
| `cpra` | integer | no | 0-100 | cPRA % (kidney only) |
| `meld` | integer | no | 6-40 | MELD score (liver only) |
| `las` | float | no | 0-100 | Lung Allocation Score (lung only) |
| `home_center` | string | no | Valid city name | Patient's current transplant listing center |
| `adjust_for_cause_of_death` | boolean | no | default `false` | Apply organ-specific COD donor recovery multiplier |

## Response

```json
{
  "patient": { ... },
  "cities": [
    {
      "city": "University of Minnesota Medical Center",
      "state": "Minnesota",
      "center_code": "MNMC",
      "center_name": "University of Minnesota Medical Center",
      "lat": 44.9727,
      "lon": -93.2354,
      "p_transplant_6mo": 0.18,
      "p_transplant_12mo": 0.39,
      "p_transplant_24mo": 0.63,
      "p_transplant_36mo": 0.78,
      "confidence_interval_95": [0.56, 0.70],
      "median_wait_months": 19.4,
      "competing_risks": {
        "p_transplant_24mo": 0.63,
        "p_mortality_24mo": 0.07,
        "p_delisting_24mo": 0.09,
        "p_still_waiting_24mo": 0.21
      },
      "outcomes": { ... },
      "trends": { ... }
    },
    ...
  ],
  "iterations": 1000,
  "elapsed_seconds": 2.34,
  "inference_mode": "monte_carlo"
}
```

### SimulationResult Schema

| Field | Type | Description |
|-------|------|-------------|
| `patient` | PatientProfile | Echo of the request patient profile |
| `cities` | CityProbability[] | Ranked by `p_transplant_24mo` descending |
| `iterations` | integer | Number of Monte Carlo iterations per center |
| `elapsed_seconds` | float | Server-side simulation time |
| `inference_mode` | string | Engine used: `monte_carlo`, `bayesian`, or `mcmc` |

### CityProbability Schema

| Field | Type | Description |
|-------|------|-------------|
| `city` | string | Center or city name (display label) |
| `state` | string | Full state name |
| `center_code` | string | SRTR center code (e.g., `PAPT`) |
| `center_name` | string | Full center name |
| `lat` | float | Center latitude |
| `lon` | float | Center longitude |
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

Returned when the request body fails Pydantic validation.

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

This is rare and occurs only if data files are corrupted or missing. Check `/health` to diagnose.

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

Response time depends on the organ (number of centers) and iteration count:

| Organ | Centers | ~Time (1000 iter) |
|-------|---------|-------------------|
| Kidney | 233 | 10-15s |
| Heart | 149 | 7-10s |
| Liver | 148 | 7-10s |
| Pancreas | 99 | 4-6s |
| Lung | 74 | 3-5s |
| Intestine | 21 | ~1s |

Reduce iterations (e.g., `?iterations=300`) for faster responses with wider confidence intervals. There is no caching; each request recomputes fresh.
