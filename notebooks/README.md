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
| 03 | `03-cod-multiplier.ipynb` | Cause-of-death donor availability | Planned |
| 04 | `04-post-transplant-outcomes.ipynb` | Graft/patient survival model | Planned |
| 05 | `05-calibration-validation.ipynb` | Brier scores & calibration curves | Planned |
| 06 | `06-full-validation-report.ipynb` | Capstone: all metrics + bias audit | Planned |

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

Notebooks import from the TransPlan backend services and data files. The `sys.path` setup at the top of each notebook adds `backend/` to the Python path so that `from services.distributions import ...` works directly.
