"""TransPlan Phase 2 — FastAPI application.

Serves both the API and the static frontend on a single port.
This eliminates CORS issues and simplifies the launcher.
"""
import logging
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so bare imports (config, routers, etc.)
# work whether running as `backend.main:app` from repo root or
# `main:app` from backend/.
_BACKEND_DIR = str(Path(__file__).parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import ALLOWED_ORIGINS, DATA_DIR, VERSION
from routers import equity, health, sensitivity, shutdown, simulate, what_if
from services.data_loader import load_all

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Repo root is one level above backend/
REPO_ROOT: Path = Path(__file__).parent.parent

app = FastAPI(
    title="TransPlan Phase 2 API",
    version=VERSION,
    description=(
        "Probabilistic transplant wait-time forecasting engine. "
        "Monte Carlo simulation with competing risks modeling."
    ),
)

# CORS kept as fallback for separate frontend/backend dev setups
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router, tags=["ops"])
app.include_router(shutdown.router, tags=["ops"])
app.include_router(simulate.router, tags=["simulation"])
app.include_router(sensitivity.router, tags=["simulation"])
app.include_router(equity.router, tags=["simulation"])
app.include_router(what_if.router, tags=["simulation"])


@app.on_event("startup")
def startup_event() -> None:
    """Load all data files into memory at startup."""
    load_all()
    logger.info("TransPlan backend ready — version %s", VERSION)


# Serve static frontend files (index.html, JS, CSS, data/) from repo root.
# Mounted AFTER API routes so API endpoints take priority.
# html=True enables serving index.html for the root path.
app.mount("/", StaticFiles(directory=str(REPO_ROOT), html=True), name="static")
