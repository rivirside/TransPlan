"""The CSP must be strict, and identical in both places it is configured (#250).

It lives in two files because two things serve the site: `vercel.json` headers
cover the static HTML the CDN serves directly, and `security.py` covers API
responses and local development. Duplicated configuration is exactly the drift
this project keeps getting bitten by, so a test pins them together.

The policy is only possible because the site has zero inline JavaScript — 25
inline handlers and 26 inline <script> blocks were removed first. A single new
one would break the page under this policy without breaking any other test,
which is why the Jest guards forbidding them matter as much as this file.
"""
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
VERCEL = REPO / "vercel.json"

from security import CSP_POLICY, PERMISSIONS_POLICY, _SECURITY_HEADERS


def _vercel_headers() -> dict:
    doc = json.loads(VERCEL.read_text())
    for block in doc.get("headers", []):
        if block.get("source") == "/(.*)":
            return {h["key"]: h["value"] for h in block["headers"]}
    return {}


def _directives(policy: str) -> dict:
    out = {}
    for part in policy.split(";"):
        part = part.strip()
        if not part:
            continue
        name, _, rest = part.partition(" ")
        out[name] = rest.split()
    return out


def test_the_two_configurations_agree():
    v = _vercel_headers()
    assert v.get("Content-Security-Policy") == CSP_POLICY, (
        "vercel.json and backend/security.py disagree on the CSP. Production "
        "static HTML uses the first, the API and local dev use the second, so "
        "a difference means the policy you test is not the policy users get.")
    assert v.get("Permissions-Policy") == PERMISSIONS_POLICY


def test_script_src_forbids_inline():
    d = _directives(CSP_POLICY)
    assert "script-src" in d
    assert "'unsafe-inline'" not in d["script-src"], (
        "script-src allows inline again — that removes most of what this "
        "policy is for. If a new inline block was added, externalize it "
        "instead of widening the policy.")
    assert "'unsafe-eval'" not in d["script-src"]


def test_the_dangerous_directives_are_locked_down():
    d = _directives(CSP_POLICY)
    assert d.get("object-src") == ["'none'"]
    assert d.get("base-uri") == ["'self'"]
    assert d.get("form-action") == ["'self'"]
    assert d.get("frame-ancestors") == ["'none'"]
    assert d.get("default-src") == ["'self'"]


def test_map_tiles_are_allowed():
    """Without these, default-src 'self' blocks every Leaflet tile.

    Invisible to the rest of the suite and very visible to a user, so it is
    pinned rather than left to a browser check that might not be repeated.
    """
    img = _directives(CSP_POLICY).get("img-src", [])
    assert any("tile.openstreetmap.org" in s for s in img), img
    assert any("basemaps.cartocdn.com" in s for s in img), img


def test_leaflet_marker_icons_are_allowed():
    """Found only by loading a page with a map, never by scanning the markup.

    leaflet.css references marker-icon.png / marker-icon-2x.png /
    marker-shadow.png from inside the STYLESHEET, so no HTML file mentions
    them and a host scan of the HTML reports the policy as complete. Under the
    first version of this CSP every map marker was blocked and simply vanished
    — visible to a user, invisible to every test.
    """
    img = _directives(CSP_POLICY).get("img-src", [])
    assert any("unpkg.com" in s for s in img), (
        "img-src no longer allows unpkg.com, so Leaflet's marker icons will be "
        "blocked and markers will silently disappear from every map")


def test_the_cdn_hosts_the_pages_actually_use_are_allowed():
    d = _directives(CSP_POLICY)
    assert any("unpkg.com" in s for s in d["script-src"])
    assert any("cdn.jsdelivr.net" in s for s in d["script-src"])
    assert any("unpkg.com" in s for s in d["style-src"]), "leaflet.css is served from unpkg"


def test_style_src_inline_is_deliberate_not_accidental():
    """126 style="" attributes remain; the allowance is documented, not stray."""
    d = _directives(CSP_POLICY)
    assert "'unsafe-inline'" in d["style-src"]
    src = (REPO / "backend" / "security.py").read_text()
    assert "style-src DOES keep" in src, (
        "the style-src exception must stay explained, or it reads as an "
        "oversight and someone will 'fix' script-src the same way")


def test_middleware_ships_both_headers():
    assert "Content-Security-Policy" in _SECURITY_HEADERS
    assert "Permissions-Policy" in _SECURITY_HEADERS


def test_permissions_policy_allows_only_geolocation():
    assert "geolocation=(self)" in PERMISSIONS_POLICY
    for denied in ("camera=()", "microphone=()"):
        assert denied in PERMISSIONS_POLICY
