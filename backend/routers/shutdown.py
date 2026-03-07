"""POST /shutdown — graceful server shutdown for local sessions."""
import logging
import os
import signal
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# PID file lives at repo root
PID_FILE = Path(__file__).parent.parent.parent / ".transplan.pid"


class ShutdownResponse(BaseModel):
    status: str


@router.post("/shutdown", response_model=ShutdownResponse)
def shutdown() -> ShutdownResponse:
    """Gracefully stop the backend process.

    Only works on localhost (CORS restricts remote callers).
    Cleans up the PID file, then sends SIGTERM to own process.
    """
    logger.info("Shutdown requested — stopping server...")
    # Clean up PID file before terminating
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    # Schedule SIGTERM after response is sent
    os.kill(os.getpid(), signal.SIGTERM)
    return ShutdownResponse(status="shutting_down")
