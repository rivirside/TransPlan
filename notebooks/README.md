# TransPlan Validation Notebooks

Reproducible Jupyter notebooks documenting each major model component of the TransPlan transplant location optimizer. These notebooks serve as:

1. **Model documentation** — visual explanation of every assumption and parameter
2. **Self-consistency validation** — Brier scores, calibration curves, sensitivity analysis
3. **Publication artifacts** — figures and tables for supplementary materials

## Notebooks

| # | Notebook | Model Component | Status |
|---|----------|-----------------|--------|
| 01 | `01-wait-time-distributions.ipynb` | Log-normal wait time model | Done |
| 02 | `02-competing-risks.ipynb` | Mortality/delisting competing events | Done |
| 03 | `03-cod-multiplier.ipynb` | COD donor availability model (Beta-distributed recovery rates, state proportions, elasticity) | Done |
| 04 | `04-post-transplant-outcomes.ipynb` | Graft/patient survival, compound success metric, performance ratings | Done |
| 05 | `05-historical-trends.ipynb` | Multi-year SRTR trends (2019-2025), regression quality, COVID impact | Done |
| 06 | `06-equity-analysis.ipynb` | Demographic equity (48-profile matrix, Gini, Cohen's d, disparity decomposition) | Done |

## Setup

```bash
# From the repo root
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# Launch Jupyter
cd ../notebooks
jupyter notebook
```

## Reproducibility

- All notebooks use fixed random seeds (`np.random.default_rng(42)`)
- Data file hashes are logged at the top of each notebook
- Python/package versions recorded via `%watermark` where available
- Figures are saved to `notebooks/figures/` for paper inclusion

## Data Dependencies

Notebooks 01-04 import from the TransPlan backend services and data files. The `sys.path` setup at the top of each notebook adds `backend/` to the Python path so that `from services.distributions import ...` works directly. Notebooks 05-06 are fully standalone (no backend imports) — they load JSON data directly and reimplement computations locally for maximum reproducibility.
