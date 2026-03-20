"""TransPlan Phase 2 — FastAPI application.

Serves both the API and the static frontend on a single port.
This eliminates CORS issues and simplifies the launcher.
"""
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend/ is on sys.path so bare imports (config, routers, etc.)
# work whether running as `backend.main:app` from repo root or
# `main:app` from backend/.
_BACKEND_DIR = str(Path(__file__).parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from config import ALLOWED_ORIGINS, DATA_DIR, VERSION
from routers import centers, equity, health, sensitivity, shutdown, simulate, spatial, trends, what_if
from services.data_loader import load_all

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Repo root is one level above backend/
REPO_ROOT: Path = Path(__file__).parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load data at startup; yield for request handling."""
    load_all()
    logger.info("TransPlan backend ready — version %s", VERSION)
    yield


app = FastAPI(
    title="TransPlan Phase 2 API",
    version=VERSION,
    description=(
        "Probabilistic transplant wait-time forecasting engine. "
        "Monte Carlo simulation with competing risks modeling."
    ),
    lifespan=lifespan,
)

# CORS kept as fallback for separate frontend/backend dev setups
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# --- Global exception handlers (#86) ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured 422 JSON instead of raw Pydantic traces."""
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(loc_part) for loc_part in err["loc"])
        errors.append(f"{loc}: {err['msg']}")
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": "; ".join(errors)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all: log full traceback server-side, return generic 500 to client."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "An internal error occurred. See server logs."},
    )


app.include_router(health.router, tags=["ops"])
app.include_router(shutdown.router, tags=["ops"])
app.include_router(simulate.router, tags=["simulation"])
app.include_router(sensitivity.router, tags=["simulation"])
app.include_router(equity.router, tags=["simulation"])
app.include_router(what_if.router, tags=["simulation"])
app.include_router(trends.router, tags=["trends"])
app.include_router(centers.router, tags=["centers"])
app.include_router(spatial.router, tags=["spatial"])


# ---------------------------------------------------------------------------
# Safe static file serving — blocks access to sensitive paths (issue #50)
# ---------------------------------------------------------------------------

class SafeStaticFiles(StaticFiles):
    """StaticFiles subclass that blocks access to backend code, dotfiles, and secrets."""

    _BLOCKED_DIRS = frozenset({
        "backend", "scripts", "docs", "node_modules",
        "__pycache__", ".venv", ".git", ".github", ".claude",
    })
    _BLOCKED_ROOT_FILES = frozenset({
        "package.json", "package-lock.json",
        ".gitignore", ".env", ".env.local", ".env.production",
    })

    async def get_response(self, path: str, scope: Scope):
        parts = path.strip("/").split("/")
        # Block dotfiles and dotdirs ("." is Starlette's internal path for "/")
        if any(p.startswith(".") for p in parts if p and p != "."):
            return PlainTextResponse("Not Found", status_code=404)
        # Block sensitive directories
        if parts[0] in self._BLOCKED_DIRS:
            return PlainTextResponse("Not Found", status_code=404)
        # Block sensitive root-level files
        if len(parts) == 1 and parts[0] in self._BLOCKED_ROOT_FILES:
            return PlainTextResponse("Not Found", status_code=404)
        # Block Python/YAML/config files anywhere in tree
        if path.endswith((".py", ".pyc", ".yml", ".yaml", ".toml", ".cfg")):
            return PlainTextResponse("Not Found", status_code=404)
        return await super().get_response(path, scope)


# Serve frontend files from repo root with sensitive-path blocking.
# Mounted AFTER API routes so API endpoints take priority.
app.mount("/", SafeStaticFiles(directory=str(REPO_ROOT), html=True), name="static")
