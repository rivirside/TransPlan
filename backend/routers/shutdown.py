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

# Optional auth token — set SHUTDOWN_TOKEN env var to require it (issue #51)
SHUTDOWN_TOKEN = os.environ.get("SHUTDOWN_TOKEN")


class ShutdownResponse(BaseModel):
    status: str


@router.post("/shutdown", response_model=ShutdownResponse)
def shutdown(authorization: str | None = Header(default=None)) -> ShutdownResponse:
    """Gracefully stop the backend process.

    If SHUTDOWN_TOKEN is set, requires Authorization: Bearer <token>.
    Cleans up the PID file, then sends SIGTERM to own process.
    """
    if SHUTDOWN_TOKEN:
        expected = f"Bearer {SHUTDOWN_TOKEN}"
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
