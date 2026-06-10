"""Tests for public REST API v1 — rate limiting, versioned routes, API key auth."""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Test client with data loaded."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from main import app
    from services.data_loader import load_all
    load_all()
    return TestClient(app)


class TestApiV1Meta:
    """Test /api/v1/ meta endpoint."""

    def test_api_info(self, client):
        r = client.get("/api/v1/")
        assert r.status_code == 200
        data = r.json()
        assert data["api_version"] == "1.0"
        assert "endpoints" in data
        assert "rate_limits" in data
        assert "simulation" in data["endpoints"]
        assert "data" in data["endpoints"]

    def test_api_health(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "degraded")
        assert "version" in data


class TestApiV1Endpoints:
    """Test that v1 endpoints mirror the existing ones."""

    def test_centers(self, client):
        r = client.get("/api/v1/centers")
        assert r.status_code == 200
        data = r.json()
        assert "centers" in data or "cities" in data
        assert "total" in data

    def test_centers_focus_only(self, client):
        r = client.get("/api/v1/centers?focus_only=true")
        assert r.status_code == 200
        data = r.json()
        assert "cities" in data
        assert data["total"] <= 22

    def test_spatial_layers(self, client):
        r = client.get("/api/v1/spatial-layers")
        assert r.status_code == 200
        data = r.json()
        assert "layers" in data
        assert len(data["layers"]) > 0

    def test_policy_scenarios(self, client):
        r = client.get("/api/v1/policy-scenarios")
        assert r.status_code == 200
        scenarios = r.json()
        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

    def test_simulate(self, client):
        r = client.post("/api/v1/simulate?iterations=100", json={
            "organ": "kidney",
            "blood_type": "O+",
            "age": 45,
            "sex": "male",
            "urgency": 2,
        })
        assert r.status_code == 200
        data = r.json()
        assert "cities" in data
        assert len(data["cities"]) > 0

    def test_trends(self, client):
        r = client.get("/api/v1/trends/kidney")
        assert r.status_code == 200


class TestRateLimiting:
    """Test rate limiting behavior."""

    def test_rate_limit_not_triggered_under_limit(self, client):
        """Normal requests should not be rate-limited."""
        for _ in range(5):
            r = client.get("/api/v1/centers")
            assert r.status_code == 200

    def test_rate_limit_429_response_format(self, client):
        """When rate limit is exceeded, response should be well-structured."""
        from middleware.rate_limit import _limiter, RATE_LIMITS

        # TestClient uses "testclient" as the host, which gets used as the IP key
        # Exhaust rate limit for all possible client IPs
        import time
        now = time.monotonic()
        limit = RATE_LIMITS["data"]["default"]
        for ip in ("testclient", "127.0.0.1", "unknown"):
            key = f"{ip}:data"
            with _limiter._lock:
                _limiter._windows[key] = [now] * (limit + 1)

        r = client.get("/api/v1/centers")
        assert r.status_code == 429
        data = r.json()
        assert "rate_limit_exceeded" in str(data)

        # Clean up
        with _limiter._lock:
            for ip in ("testclient", "127.0.0.1", "unknown"):
                _limiter._windows.pop(f"{ip}:data", None)


class TestClientIpExtraction:
    """X-Forwarded-For is spoofable — only trusted behind a known proxy (#218)."""

    @staticmethod
    def _make_request(headers=None, client_host="10.0.0.1"):
        from starlette.requests import Request
        raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": raw_headers,
            "client": (client_host, 12345),
        }
        return Request(scope)

    def test_xff_ignored_without_trusted_proxy(self, monkeypatch):
        from middleware.rate_limit import _get_client_ip
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("TRANSPLAN_TRUST_PROXY", raising=False)
        req = self._make_request({"X-Forwarded-For": "1.2.3.4"})
        assert _get_client_ip(req) == "10.0.0.1"

    def test_xff_honored_on_vercel(self, monkeypatch):
        from middleware.rate_limit import _get_client_ip
        monkeypatch.setenv("VERCEL", "1")
        req = self._make_request({"X-Forwarded-For": "1.2.3.4"})
        assert _get_client_ip(req) == "1.2.3.4"

    def test_xff_uses_rightmost_entry_behind_proxy(self, monkeypatch):
        """Leftmost entries are client-forgeable; the proxy appends the real IP."""
        from middleware.rate_limit import _get_client_ip
        monkeypatch.setenv("TRANSPLAN_TRUST_PROXY", "1")
        req = self._make_request({"X-Forwarded-For": "6.6.6.6, 1.2.3.4"})
        assert _get_client_ip(req) == "1.2.3.4"

    def test_falls_back_to_client_host(self, monkeypatch):
        from middleware.rate_limit import _get_client_ip
        monkeypatch.setenv("TRANSPLAN_TRUST_PROXY", "1")
        req = self._make_request()
        assert _get_client_ip(req) == "10.0.0.1"


class TestCorsOriginRegex:
    """CORS must not allow arbitrary Vercel subdomains (#215)."""

    @staticmethod
    def _allowed(origin):
        import re
        from main import app
        for middleware in app.user_middleware:
            regex = middleware.kwargs.get("allow_origin_regex")
            if regex:
                return re.match(regex, origin) is not None
        raise AssertionError("CORS middleware with allow_origin_regex not found")

    def test_production_domains_allowed(self):
        assert self._allowed("https://transplant.today")
        assert self._allowed("https://www.transplant.today")
        assert self._allowed("http://localhost:3000")
        assert self._allowed("http://127.0.0.1:8002")

    def test_transplan_vercel_previews_allowed(self):
        assert self._allowed("https://transplan.vercel.app")
        assert self._allowed("https://transplan-git-main-team.vercel.app")
        assert self._allowed("https://transplan-abc123xyz-team.vercel.app")

    def test_arbitrary_vercel_subdomains_rejected(self):
        assert not self._allowed("https://evil.vercel.app")
        assert not self._allowed("https://attacker-site.vercel.app")
        assert not self._allowed("https://transplanfake.vercel.app")

    def test_unrelated_origins_rejected(self):
        assert not self._allowed("https://evil.com")
        assert not self._allowed("https://transplant.today.evil.com")
        assert not self._allowed("http://transplant.today")  # http on prod domain


class TestApiKeyAuth:
    """Test API key authentication for higher rate limits."""

    def test_unauthenticated_has_default_limits(self, client):
        """Without API key, default rate limits apply."""
        r = client.get("/api/v1/")
        assert r.status_code == 200

    def test_invalid_api_key_still_works(self, client):
        """Invalid API key = unauthenticated (not rejected)."""
        r = client.get("/api/v1/", headers={"X-Api-Key": "invalid-key"})
        assert r.status_code == 200

    def test_valid_api_key_accepted(self, client):
        """Valid API key should work."""
        os.environ["TRANSPLAN_API_KEYS"] = "test-key-123"
        try:
            r = client.get("/api/v1/", headers={"X-Api-Key": "test-key-123"})
            assert r.status_code == 200
        finally:
            os.environ.pop("TRANSPLAN_API_KEYS", None)


class TestBackwardCompatibility:
    """Ensure unprefixed routes still work."""

    def test_health_unprefixed(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_centers_unprefixed(self, client):
        r = client.get("/centers")
        assert r.status_code == 200

    def test_simulate_unprefixed(self, client):
        r = client.post("/simulate?iterations=100", json={
            "organ": "kidney",
            "blood_type": "O+",
            "age": 45,
            "sex": "male",
            "urgency": 2,
        })
        assert r.status_code == 200
