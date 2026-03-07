"""POST /shutdown — graceful server shutdown for local sessions."""
import logging
import os
import signal

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class ShutdownResponse(BaseModel):
    status: str


@router.post("/shutdown", response_model=ShutdownResponse)
def shutdown() -> ShutdownResponse:
    """Gracefully stop the backend process.

    Only works on localhost (CORS restricts remote callers).
    Sends SIGTERM to own process, which uvicorn handles gracefully.
    The start.command trap then cleans up the frontend server too.
    """
    logger.info("Shutdown requested — stopping server...")
    # Schedule SIGTERM after response is sent
    os.kill(os.getpid(), signal.SIGTERM)
    return ShutdownResponse(status="shutting_down")
