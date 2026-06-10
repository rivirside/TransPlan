"""In-memory rate limiting middleware for the public API.

Uses a sliding window counter per IP address. No external dependencies required.
Configurable per-endpoint limits via the `rate_limit` dependency.

Limits:
  - Unauthenticated: 30 req/min for simulation endpoints, 120 req/min for data endpoints
  - Authenticated (API key): 5× higher limits
"""

import os
import time
from collections import defaultdict
from threading import Lock
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request


class RateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, remaining)."""
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            # Trim expired entries
            timestamps = self._windows[key]
            self._windows[key] = [t for t in timestamps if t > cutoff]

            if len(self._windows[key]) >= limit:
                return False, 0

            self._windows[key].append(now)
            return True, limit - len(self._windows[key])

    def cleanup(self, max_age_seconds: int = 300):
        """Remove stale entries to prevent memory growth."""
        now = time.monotonic()
        cutoff = now - max_age_seconds
        with self._lock:
            stale_keys = [k for k, v in self._windows.items() if not v or v[-1] < cutoff]
            for k in stale_keys:
                del self._windows[k]


# Singleton instance
_limiter = RateLimiter()


# Rate limit tiers (requests per minute)
RATE_LIMITS = {
    "simulation": {"default": 30, "authenticated": 150},
    "data": {"default": 120, "authenticated": 600},
    "spatial": {"default": 60, "authenticated": 300},
}


def _trust_proxy_headers() -> bool:
    """Whether X-Forwarded-For can be trusted (#218).

    The header is client-spoofable, so it is only honored when the app is
    known to sit behind a proxy that sanitizes it:
      - Vercel sets VERCEL=1 in its runtime and overwrites X-Forwarded-For
        with the real client IP (client-supplied values are stripped).
      - Other deployments opt in explicitly via TRANSPLAN_TRUST_PROXY=1.
    """
    if os.environ.get("VERCEL"):
        return True
    return os.environ.get("TRANSPLAN_TRUST_PROXY", "").lower() in ("1", "true", "yes")


def _get_client_ip(request: Request) -> str:
    """Extract client IP.

    X-Forwarded-For is only consulted behind a trusted proxy; otherwise a
    client could spoof the header to dodge rate limits (#218). The rightmost
    entry is used because it is the one appended by the trusted proxy —
    leftmost entries can be forged by the client.
    """
    if _trust_proxy_headers():
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _get_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """Extract API key from header."""
    return x_api_key


def rate_limit(tier: str = "data"):
    """Create a rate-limiting dependency for the given tier.

    Usage:
        @router.get("/endpoint", dependencies=[Depends(rate_limit("simulation"))])
    """
    async def _check(request: Request, api_key: Optional[str] = Depends(_get_api_key)):
        import os
        valid_keys = os.environ.get("TRANSPLAN_API_KEYS", "").split(",")
        valid_keys = [k.strip() for k in valid_keys if k.strip()]

        is_authenticated = api_key and api_key in valid_keys
        tier_config = RATE_LIMITS.get(tier, RATE_LIMITS["data"])
        limit = tier_config["authenticated"] if is_authenticated else tier_config["default"]

        client_ip = _get_client_ip(request)
        key = f"{client_ip}:{tier}"

        allowed, remaining = _limiter.check(key, limit)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded ({limit} req/min for {tier} tier). "
                               "Provide X-Api-Key header for higher limits.",
                    "retry_after_seconds": 60,
                },
                headers={"Retry-After": "60"},
            )

        # Set rate limit headers on the response
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = limit

    return _check
