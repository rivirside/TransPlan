"""Application settings."""
from pathlib import Path

# Absolute path to the repo root's data/ directory (one level above backend/)
DATA_DIR: Path = Path(__file__).parent.parent / "data"

# Monte Carlo default iteration count
SIMULATION_ITERATIONS: int = 1000

# Semantic version
VERSION: str = "2.0.0-alpha"

# CORS origins allowed (expand for production deploy)
ALLOWED_ORIGINS: list[str] = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1",
    # GitHub Pages URL — update before deploy
    # "https://rivirside.github.io",
]
