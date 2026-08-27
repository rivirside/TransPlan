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


# Content-Security-Policy (#250).
#
# script-src carries NO 'unsafe-inline'. That is only possible because the
# site has zero inline JavaScript: 25 inline event handlers (#407) and 26
# inline <script> blocks (#408) were removed first. Re-introducing a single
# one silently breaks this page under the policy — the tests that forbid them
# are what keep this directive honest.
#
# style-src DOES keep 'unsafe-inline': 126 style="" attributes and 15 <style>
# blocks remain, and inline styles carry far less risk than inline script.
# Removing them is a separate, larger piece of work.
#
# img-src names the map tile hosts explicitly. Without them `default-src
# 'self'` blocks every Leaflet tile, which is invisible to the test suite and
# very visible to a user.
#
# unpkg.com is here for a subtler reason: leaflet.css references its marker
# icons (marker-icon.png, marker-icon-2x.png, marker-shadow.png) from inside
# the STYLESHEET, so no HTML file mentions them and a scan of the markup
# cannot find them. Only loading a page with a map surfaces it — the markers
# silently vanish otherwise.
CSP_POLICY = (
    "default-src 'self'; script-src 'self' https://unpkg.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://unpkg.com; img-src 'self' data: https://unpkg.com https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)

# The app requests geolocation (shared/geo-utils.js); everything else is
# denied so embedded content cannot inherit a capability the site never uses.
PERMISSIONS_POLICY = "geolocation=(self), camera=(), microphone=(), payment=(), usb=()"

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": CSP_POLICY,
    "Permissions-Policy": PERMISSIONS_POLICY,
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers to every response (#250)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for key, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response
