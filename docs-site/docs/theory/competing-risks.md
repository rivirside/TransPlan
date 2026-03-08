---
sidebar_position: 3
---

# Competing Risks

A transplant patient waiting on the list faces multiple possible outcomes, not just "transplant or keep waiting." TransPlan models three competing events.

## The Problem

Standard survival analysis asks: "How long until the event?" But a transplant patient can experience:

1. **Transplant**: the desired outcome
2. **Mortality**: death while on the waiting list
3. **Delisting**: removal from the list due to clinical deterioration, improvement, or patient choice

These are *competing risks*: experiencing one event precludes the others. A standard Kaplan-Meier estimator would treat mortality and delisting as censored observations, which overestimates transplant probability. Competing risks analysis correctly partitions the probability space.

## Model

At 24 months, the four mutually exclusive outcomes must sum to 1.0:

```
P(transplant) + P(mortality) + P(delisting) + P(still waiting) = 1.0
```

### Mortality Model

Mortality while on the waiting list is modeled as an exponential process:

```
P(mortality by t) = 1 - exp(-λ_mortality × t)
```

where `λ_mortality` is estimated from SRTR Table B7 (waiting list mortality rates) per organ and city.

### Delisting Model

Delisting (removal for reasons other than transplant or death) is similarly modeled:

```
P(delisting by t) = 1 - exp(-λ_delisting × t)
```

`λ_delisting` is estimated from SRTR Table B7 (removal rates for "too sick," "condition improved," "patient decision").

### Integration with Monte Carlo

During each Monte Carlo iteration, all three processes compete:

1. Sample a transplant time `t_tx` from the log-normal wait distribution
2. Sample a mortality time `t_mort` from the exponential mortality distribution
3. Sample a delisting time `t_delist` from the exponential delisting distribution
4. The outcome is whichever event occurs first: `min(t_tx, t_mort, t_delist)`
5. If all three times exceed the horizon (36 months), outcome is "still waiting"

## Output

The competing risks breakdown appears as a stacked horizontal bar in the app:

| Color | Outcome |
|-------|---------|
| Green | Transplant |
| Red | Mortality while waiting |
| Orange | Delisted |
| Gray | Still waiting at 24 months |

And in the API response:

```json
"competing_risks": {
  "p_transplant": 0.61,
  "p_mortality": 0.08,
  "p_delisting": 0.11,
  "p_still_waiting": 0.20
}
```

## Organ-Specific Notes

| Organ | Mortality Risk | Notes |
|-------|---------------|-------|
| Heart | Highest | Status 1A patients have very high short-term mortality risk |
| Liver | High | MELD >25 patients have significant 6-month mortality |
| Lung | High | LAS incorporates mortality risk directly |
| Kidney | Lowest | Dialysis provides a survival bridge |
| Pancreas | Low | Rare; primarily type 1 diabetics with kidney disease |
| Intestine | Moderate | Very small candidate pool; significant morbidity risk |

## Data Sources

Mortality and delisting rates are derived from SRTR Program-Specific Reports (Table B7: Waiting List Removal Reasons). These are parsed annually from SRTR Excel PSR files via `scripts/parse-srtr-reports.py` and stored in `data/competing-risks.json`.

## Limitations

The exponential model assumes constant hazard (memoryless), whereas real mortality risk increases with time on list. City-level variation in mortality/delisting rates is partially captured, but center-specific practices are not modeled. Interaction effects between clinical score trajectories (e.g., rising MELD) and delisting/mortality are also not modeled. Data is updated biannually via SRTR PSR downloads.

See [Wait Time Distributions](/theory/wait-time-distributions) for how the transplant wait model is calibrated.
