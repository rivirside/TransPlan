"""GET /health — liveness + data freshness check."""
from fastapi import APIRouter
from models.schemas import HealthResponse
from services.data_loader import get_data
from config import VERSION

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    data = get_data()
    loaded_count = sum(
        1 for v in data.freshness.values()
        if v not in ("missing", "parse_error")
    )
    status = "ok" if loaded_count == len(data.freshness) else "degraded"
    return HealthResponse(
        status=status,
        version=VERSION,
        data_freshness=data.freshness,
        data_files_loaded=loaded_count,
    )
