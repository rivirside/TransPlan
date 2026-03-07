"""TransPlan Phase 2 — FastAPI application."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import ALLOWED_ORIGINS, VERSION
from routers import health, shutdown, simulate
from services.data_loader import load_all

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TransPlan Phase 2 API",
    version=VERSION,
    description=(
        "Probabilistic transplant wait-time forecasting engine. "
        "Monte Carlo simulation with competing risks modeling."
    ),
)

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


@app.on_event("startup")
def startup_event() -> None:
    """Load all data files into memory at startup."""
    load_all()
    logger.info("TransPlan backend ready — version %s", VERSION)
