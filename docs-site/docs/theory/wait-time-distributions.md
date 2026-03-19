---
sidebar_position: 4
---

# Wait Time Distributions

TransPlan models organ transplant wait times as log-normal distributions parameterized from SRTR data. This approach captures the key statistical properties of real-world transplant waiting periods.

## Why Log-Normal?

Transplant wait times share three properties that make the log-normal distribution a natural fit. They are always positive (bounded below by zero), right-skewed (most waits cluster around a moderate duration but some extend to very long periods), and they follow log-normal distributions in most published analyses of SRTR data. A `LogNormal(mu, sigma)` distribution fits observed wait time histograms well across most organ and blood type combinations.

## Parameterization

For each combination of city, organ, and blood type, the distribution parameters are computed as follows:

```
mu = log(median_wait_months)
sigma = shape parameter estimated from SRTR Table B10 interquartile range
```

### Data Source

Parameters come from **SRTR Program-Specific Reports (PSR)**, specifically **Table B10**: Waiting Time Distributions by Blood Type. These are Excel files published biannually at [srtr.org](https://www.srtr.org).

The pipeline works in four stages. First, `scripts/fetch-srtr-excel.py` downloads PSR Excel files for all 6 organs. Then `scripts/parse-srtr-reports.py` parses Table B10 and extracts the median and IQR for each center and blood type combination. Centers are mapped to TransPlan cities through `data/srtr-center-mapping.json`, and city-level parameters are computed as weighted averages across all centers in each city. The final results are stored in `data/wait-time-distributions.json`.

## Parameter Structure

```json
{
  "kidney": {
    "A+": {
      "Atlanta": { "mu": 2.89, "sigma": 0.72, "city_factor": 1.05 },
      "Boston":  { "mu": 2.34, "sigma": 0.68, "city_factor": 0.87 }
    },
    "O-": { }
  },
  "liver": { }
}
```

The `city_factor` scales wait times up or down relative to the national median. Values greater than 1.0 indicate longer expected waits, while values less than 1.0 indicate shorter waits.

## Sampling in Simulation

During each Monte Carlo iteration, the engine samples a raw wait time from the log-normal distribution, applies the city-specific factor, and then applies any relevant clinical multiplier:

```python
# Sample raw wait time
t_raw = lognormal(mu, sigma)

# Apply city-specific factor
t_city = t_raw * city_factor

# Apply clinical multiplier
t_final = t_city * clinical_multiplier(cpra, meld, las)
```

### Clinical Multipliers

Several clinical conditions modify the base wait time. Kidney patients with a cPRA at or above 80% face a 1.5x to 3.0x longer wait because highly sensitized patients need rare antigen-negative donors. Liver patients with a MELD score at or above 25 see wait times reduced to 0.5x to 0.7x due to higher allocation priority, and those with MELD scores at or above 35 receive emergency allocation priority that shortens waits to roughly 0.3x the baseline. Lung patients with an LAS at or above 50 experience 0.6x shorter waits because high LAS scores indicate high urgency.

## Uncertainty and Sparse Data

Some combinations of city, organ, and blood type have very few historical cases in SRTR data. When this occurs, the system falls back to the national median for that organ. The 95% confidence interval in the simulation output will be wider to reflect the increased uncertainty, and this is captured in the `confidence_interval_95` field of the API response.

## Updating the Distributions

SRTR PSR files are released biannually. To update:

```bash
cd backend
source .venv/bin/activate
python ../scripts/fetch-srtr-excel.py    # downloads ~200MB of Excel files
python ../scripts/parse-srtr-reports.py  # parses into wait-time-distributions.json + competing-risks.json
```

The existing `data/wait-time-distributions.json` serves as a fallback if the download fails.

## Comparison: Phase 1 vs Phase 2

Phase 1 uses city-level SRTR factors (a single number per city) to produce deterministic relative rankings from 0 to 100, with no uncertainty quantification and a simple urgency multiplier for clinical adjustment. Phase 2 uses full log-normal parameters for each combination of city, organ, and blood type, producing probability estimates at each time horizon with 95% confidence intervals from bootstrap resampling and clinical adjustments based on cPRA, MELD, and LAS scores.
