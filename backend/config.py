"""Application settings."""
from pathlib import Path

# Absolute path to the repo root's data/ directory (one level above backend/)
DATA_DIR: Path = Path(__file__).parent.parent / "data"

# Monte Carlo default iteration count
SIMULATION_ITERATIONS: int = 1000

# Supply-wait elasticity: how much a change in donor supply affects wait times.
# wait_adjustment = supply_multiplier ^ SUPPLY_WAIT_ELASTICITY
# Value of 1.0 = linear (old behavior). Value of 0.65 = sublinear (more realistic).
# Empirical range from queuing theory + SRTR data: 0.5–0.8.
# 0.65 means 10% more donors → ~6.5% shorter waits (not 10%).
SUPPLY_WAIT_ELASTICITY: float = 0.65

# Clayton copula dependence parameter for correlated competing risks (Phase 5 M2).
# θ > 0; higher values = stronger lower-tail dependence between mortality & delisting.
# θ = 1.0 ≈ Kendall's τ 0.33 (moderate, conservative default from SRTR analyses).
COPULA_THETA: float = 1.0

# Per-organ copula θ (L-059 fix). High-acuity organs (heart, lung, intestine) have
# stronger mortality↔delisting correlation; low-acuity (kidney) have weaker.
# NOTE: these are a clinical-acuity HEURISTIC ordering, not yet calibrated to
# patient-level data — no specific citation backs the exact magnitudes (#255,
# ADR-025). They encode the qualitative ranking only; treat absolute τ values
# as illustrative until fit from SRTR microdata.
# Kendall's τ ≈ θ/(θ+2): kidney 0.29, liver 0.37, heart 0.47, lung 0.43, pancreas 0.31, intestine 0.43.
ORGAN_COPULA_THETA: dict[str, float] = {
    "kidney": 0.8,     # τ ≈ 0.29 — low acuity, long stable waitlist periods
    "liver": 1.2,      # τ ≈ 0.37 — MELD-driven, moderate mort↔delist coupling
    "heart": 1.8,      # τ ≈ 0.47 — high acuity, strong adverse event clustering
    "lung": 1.5,       # τ ≈ 0.43 — high acuity, LAS-driven
    "pancreas": 0.9,   # τ ≈ 0.31 — similar to kidney
    "intestine": 1.5,  # τ ≈ 0.43 — highest acuity, small volume
}

# Score drift rates (annual) for dynamic MELD/LAS progression (Feature 3).
# Liver MELD: ~2.5 points/year (Volk et al. Hepatology 2006; Bambha et al. Gastro 2008).
# Lung LAS: ~-1.0 points/year (Davis Square & LAS Working Group estimates).
SCORE_DRIFT_RATES: dict[str, dict[str, float]] = {
    "liver": {"meld": 2.5},
    "lung": {"las": -1.0},
}
SCORE_DRIFT_CAPS: dict[str, float] = {
    "meld": 40,   # MELD caps at 40
    "las": 0,     # LAS floor
}

# Piecewise drift interval boundaries (months) for per-sample score drift (F3).
# The lookup table is built at monthly resolution from 0 to 60 months.
PIECEWISE_DRIFT_INTERVALS: list[int] = [0, 6, 12, 18, 24, 36]

# Semantic version
VERSION: str = "2.0.0-alpha"

# CORS origins allowed
ALLOWED_ORIGINS: list[str] = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1",
    "https://transplant.today",
    "https://www.transplant.today",
]
