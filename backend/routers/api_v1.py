"""Public REST API v1 — versioned wrapper around existing endpoints.

Mounts all existing routers under /api/v1/ with rate limiting.
The existing non-prefixed routes remain for frontend backward compatibility.
"""

from fastapi import APIRouter, Depends

from config import VERSION
from middleware.rate_limit import rate_limit

# Meta-only router for the /api/v1/ info endpoint
router = APIRouter(prefix="/api/v1")


@router.get("/", tags=["meta"])
async def api_info():
    """API information, available endpoints, and rate limit details."""
    return {
        "api_version": "1.0",
        "engine_version": VERSION,
        "documentation": "/docs",
        "endpoints": {
            "meta": ["GET /api/v1/", "GET /api/v1/health"],
            "simulation": [
                "POST /api/v1/simulate",
                "POST /api/v1/sensitivity",
                "POST /api/v1/equity-analysis",
                "POST /api/v1/what-if",
                "POST /api/v1/policy-scenario",
            ],
            "data": [
                "GET /api/v1/centers",
                "GET /api/v1/policy-scenarios",
                "GET /api/v1/trends/{organ}",
                "GET /api/v1/trends/{city}/{organ}",
            ],
            "spatial": [
                "GET /api/v1/spatial-layers",
                "GET /api/v1/interpolated-value",
                "GET /api/v1/interpolated-profile",
                "GET /api/v1/allocation-circles",
                "GET /api/v1/distance-score",
            ],
        },
        "rate_limits": {
            "unauthenticated": {"simulation": "30/min", "data": "120/min", "spatial": "60/min"},
            "authenticated": {"simulation": "150/min", "data": "600/min", "spatial": "300/min"},
            "auth_header": "X-Api-Key",
            "env_var": "TRANSPLAN_API_KEYS (comma-separated)",
        },
    }


def include_v1_routers(app):
    """Include all existing routers under /api/v1/ with rate limiting.

    Called from main.py after the unprefixed routers are mounted.
    This re-mounts each router with a prefix and rate-limiting dependency.
    """
    from routers import centers, equity, health, sensitivity, simulate, spatial, trends, what_if

    # Mount the meta endpoint
    app.include_router(router, tags=["meta"])

    # Data endpoints — high rate limit (read-only, fast)
    data_deps = [Depends(rate_limit("data"))]
    app.include_router(health.router, prefix="/api/v1", tags=["v1-ops"], dependencies=data_deps)
    app.include_router(centers.router, prefix="/api/v1", tags=["v1-data"], dependencies=data_deps)
    app.include_router(trends.router, prefix="/api/v1", tags=["v1-data"], dependencies=data_deps)

    # Simulation endpoints — low rate limit (compute-heavy)
    sim_deps = [Depends(rate_limit("simulation"))]
    app.include_router(simulate.router, prefix="/api/v1", tags=["v1-simulation"], dependencies=sim_deps)
    app.include_router(sensitivity.router, prefix="/api/v1", tags=["v1-simulation"], dependencies=sim_deps)
    app.include_router(equity.router, prefix="/api/v1", tags=["v1-simulation"], dependencies=sim_deps)
    app.include_router(what_if.router, prefix="/api/v1", tags=["v1-simulation"], dependencies=sim_deps)

    # Spatial endpoints — medium rate limit
    spatial_deps = [Depends(rate_limit("spatial"))]
    app.include_router(spatial.router, prefix="/api/v1", tags=["v1-spatial"], dependencies=spatial_deps)
