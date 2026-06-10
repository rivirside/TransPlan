"""POST /shutdown — graceful server shutdown for local sessions."""
import logging
import os
import signal
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# PID file lives at repo root
PID_FILE = Path(__file__).parent.parent.parent / ".transplan.pid"

class ShutdownResponse(BaseModel):
    status: str


@router.post("/shutdown", response_model=ShutdownResponse)
def shutdown(authorization: str | None = Header(default=None)) -> ShutdownResponse:
    """Gracefully stop the backend process.

    If SHUTDOWN_TOKEN is set, requires Authorization: Bearer <token>.
    Cleans up the PID file, then sends SIGTERM to own process.
    """
    # Read at request time, not import time — so tokens set after import
    # (e.g. by tests, or a late-exported env var) are honored (issue #51).
    shutdown_token = os.environ.get("SHUTDOWN_TOKEN")
    if shutdown_token:
        expected = f"Bearer {shutdown_token}"
        if not authorization or authorization != expected:
            raise HTTPException(status_code=403, detail="Invalid or missing shutdown token")
    else:
        logger.warning("SHUTDOWN_TOKEN not set — endpoint is unauthenticated")

    logger.info("Shutdown requested — stopping server...")
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    os.kill(os.getpid(), signal.SIGTERM)
    return ShutdownResponse(status="shutting_down")
