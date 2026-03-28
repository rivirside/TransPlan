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
# Values derived from clinical literature on waitlist competing event co-occurrence.
# Kendall's τ ≈ θ/(θ+2): kidney 0.29, liver 0.37, heart 0.47, lung 0.43, pancreas 0.31, intestine 0.43.
ORGAN_COPULA_THETA: dict[str, float] = {
    "kidney": 0.8,     # τ ≈ 0.29 — low acuity, long stable waitlist periods
    "liver": 1.2,      # τ ≈ 0.37 — MELD-driven, moderate mort↔delist coupling
    "heart": 1.8,      # τ ≈ 0.47 — high acuity, strong adverse event clustering
    "lung": 1.5,       # τ ≈ 0.43 — high acuity, LAS-driven
    "pancreas": 0.9,   # τ ≈ 0.31 — similar to kidney
    "intestine": 1.5,  # τ ≈ 0.43 — highest acuity, small volume
}

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
