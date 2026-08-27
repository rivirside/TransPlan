"""Every API route needs a vercel.json rewrite, or it 404s in production.

This class of bug shipped twice and went unnoticed for a long time: `/tier`
had NEVER had a rewrite, so the tier system silently ran on the frontend's
hardcoded defaults in production, and `/bias-audit` was added without one so
the equity panel could never have worked for a real user. Both were found by
hand, months and hours apart respectively.

Local development hides it completely — the dev server mounts the API
directly, so every route works. Only production routes through vercel.json.
"""
import json
from pathlib import Path

import pytest

from main import app

REPO = Path(__file__).resolve().parents[2]
VERCEL = REPO / "vercel.json"

# Routes served by the static CDN or by FastAPI's own tooling, which do not
# need an API rewrite.
# FastAPI's own docs surface, served by the framework rather than by a route
# this app defines. "/shutdown" is deliberately unrouted in production.
EXEMPT = {"/", "/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect", "/shutdown"}


def _rewrite_sources() -> set[str]:
    doc = json.loads(VERCEL.read_text())
    return {r["source"] for r in doc.get("rewrites", [])}


def _api_paths() -> set[str]:
    """Every path the app actually serves.

    Read from the OpenAPI schema rather than by walking ``app.routes``:
    this FastAPI version wraps included routers in ``_IncludedRouter``
    objects that expose no ``.path``, so a route walk silently sees only
    the four built-in docs routes and every assertion below passes
    vacuously. The schema is the public, version-stable API and is also
    exactly the surface production serves.
    """
    return {p for p in app.openapi()["paths"] if p not in EXEMPT}


def _covered(path: str, sources: set[str]) -> bool:
    if path in sources:
        return True
    for src in sources:
        # Vercel prefix wildcard: "/validation/:path*" matches the prefix
        # itself and everything beneath it, so it covers "/validation/temporal"
        # and "/trends/{organ}" alike.
        if ":" in src:
            prefix = src.split("/:", 1)[0]
            if prefix and (path == prefix or path.startswith(prefix + "/")):
                return True
    return False


def test_the_route_enumeration_is_not_vacuous():
    """Guard the guard.

    The first version of this file walked ``app.routes`` and found 4 paths
    instead of 59, so it passed even with a rewrite deleted. Any future
    change that breaks enumeration the same way fails here loudly rather
    than turning the checks below into no-ops.
    """
    paths = _api_paths()
    assert len(paths) > 40, f"expected the full API surface, enumerated only {sorted(paths)}"
    assert "/tier" in paths and "/simulate" in paths


def test_every_api_route_has_a_production_rewrite():
    sources = _rewrite_sources()
    missing = sorted(p for p in _api_paths() if not _covered(p, sources))
    assert not missing, (
        "these routes work locally but 404 in production — vercel.json needs "
        f"a rewrite for each: {missing}\n"
        "This exact bug shipped for /tier and /bias-audit."
    )


def test_rewrites_all_point_at_the_api_function():
    doc = json.loads(VERCEL.read_text())
    for r in doc.get("rewrites", []):
        assert r.get("destination"), f"rewrite {r} has no destination"


def test_no_duplicate_rewrite_sources():
    """A duplicate is dead config and a sign of a merge going wrong."""
    doc = json.loads(VERCEL.read_text())
    sources = [r["source"] for r in doc.get("rewrites", [])]
    dupes = {s for s in sources if sources.count(s) > 1}
    assert not dupes, f"duplicate rewrite sources: {sorted(dupes)}"
