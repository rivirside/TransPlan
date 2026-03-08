---
sidebar_position: 4
---

# Wait Time Distributions

TransPlan models organ transplant wait times as log-normal distributions parameterized from SRTR data.

## Why Log-Normal?

Transplant wait times are always positive (bounded below by 0), right-skewed (most waits are moderate but some are very long), and log-normally distributed in most published analyses of SRTR data. A log-normal distribution `LogNormal(μ, σ)` fits observed wait time histograms well across most organ/blood-type combinations.

## Parameterization

For each (city, organ, blood_type) combination:

```
μ = log(median_wait_months)
σ = shape parameter estimated from SRTR Table B10 interquartile range
```

### Data Source

Parameters are extracted from **SRTR Program-Specific Reports (PSR)**, specifically **Table B10**: Waiting Time Distributions by Blood Type.

These are Excel files published biannually at [srtr.org](https://www.srtr.org). The pipeline:

1. `scripts/fetch-srtr-excel.py`: downloads PSR Excel files for all 6 organs
2. `scripts/parse-srtr-reports.py`: parses Table B10 and extracts median and IQR by (center, blood_type)
3. Centers are mapped to TransPlan cities via `data/srtr-center-mapping.json`
4. City-level parameters are computed as weighted averages across centers in that city

The results are stored in `data/wait-time-distributions.json`.

## Parameter Structure

```json
{
  "kidney": {
    "A+": {
      "Atlanta": { "mu": 2.89, "sigma": 0.72, "city_factor": 1.05 },
      "Boston":  { "mu": 2.34, "sigma": 0.68, "city_factor": 0.87 },
      ...
    },
    "O-": { ... }
  },
  "liver": { ... }
}
```

The `city_factor` scales wait times up or down relative to national median. Values > 1.0 mean longer waits; < 1.0 means shorter.

## Sampling in Simulation

During each Monte Carlo iteration:

```python
# Sample raw wait time
t_raw = lognormal(mu, sigma)

# Apply city-specific factor
t_city = t_raw * city_factor

# Apply clinical multiplier
t_final = t_city * clinical_multiplier(cpra, meld, las)
```

### Clinical Multipliers

| Condition | Effect | Rationale |
|-----------|--------|-----------|
| cPRA ≥ 80% (kidney) | 1.5× to 3.0× longer | Highly sensitized patients need rare antigen-negative donors |
| MELD ≥ 25 (liver) | 0.5× to 0.7× shorter | High MELD gets priority allocation |
| MELD ≥ 35 (liver) | 0.3× shorter | Emergency allocation rules kick in |
| LAS ≥ 50 (lung) | 0.6× shorter | High LAS = high urgency priority |

## Uncertainty and Sparse Data

Some (city, organ, blood_type) combinations have very few historical cases in SRTR data. In these cases, parameters fall back to the national median for that organ, the 95% CI in the simulation output will be wider to reflect higher uncertainty, and this uncertainty is captured in the `confidence_interval_95` field of the API response.

## Updating the Distributions

SRTR PSR files are released biannually. To update:

```bash
cd backend
source .venv/bin/activate
python ../scripts/fetch-srtr-excel.py    # downloads ~200MB of Excel files
python ../scripts/parse-srtr-reports.py  # parses → wait-time-distributions.json + competing-risks.json
```

The existing `data/wait-time-distributions.json` serves as a fallback if the download fails.

## Comparison: Phase 1 vs Phase 2

| Aspect | Phase 1 (Scoring) | Phase 2 (Distributions) |
|--------|------------------|------------------------|
| Data | City-level SRTR factors (single number per city) | Full log-normal parameters per (city, organ, blood_type) |
| Output | Relative rank (0–100) | Probability at each time horizon |
| Uncertainty | None (deterministic) | 95% CI from bootstrap |
| Clinical adjustment | Urgency multiplier | cPRA / MELD / LAS multipliers |
