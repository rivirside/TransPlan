"""Dev static files must not be cached (#363).

The dev server sent no cache directives, so browsers kept serving the
previous JS after an edit. That silently invalidates browser verification:
a fix appears not to work, or a broken change appears to work. Production
sets the same header via vercel.json.
"""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@pytest.mark.parametrize("path", ["/api-client.js", "/styles.css", "/index.html"])
def test_assets_are_no_cache(path):
    r = client.get(path)
    if r.status_code == 404:
        pytest.skip(f"{path} not present in this checkout")
    cc = r.headers.get("cache-control", "")
    assert "no-cache" in cc, f"{path} served with Cache-Control={cc!r}"


def test_blocked_paths_still_blocked():
    """The header change must not have widened what the server will serve."""
    for path in ("/backend/main.py", "/.env", "/scripts/validate-data.js",
                 "/package.json"):
        assert client.get(path).status_code == 404, f"{path} became reachable"
