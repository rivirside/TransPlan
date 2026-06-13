"""Security helpers: CORS origin policy, docs gating, and response headers.

Kept as small pure functions + one middleware so the policy is unit-testable
independently of the FastAPI app wiring (#247, #248, #250).
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


# Allowed CORS origins (#248): localhost dev, the production domain, and
# THIS project's Vercel previews only — not any *.vercel.app deployment.
# Vercel project name is "transplan", so previews are transplan(-<slug>).vercel.app.
CORS_ORIGIN_REGEX = (
    r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    r"|^https://transplan(-[a-z0-9-]+)?\.vercel\.app$"
    r"|^https://(www\.)?transplant\.today$"
)


def docs_urls(is_prod: bool) -> tuple[str | None, str | None, str | None]:
    """Return (docs_url, redoc_url, openapi_url). All disabled in production so
    neither the interactive console NOR the raw OpenAPI schema (which enumerates
    every endpoint and parameter) is publicly exposed (#247)."""
    if is_prod:
        return (None, None, None)
    return ("/docs", "/redoc", "/openapi.json")


_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers to every response (#250)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for key, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response
