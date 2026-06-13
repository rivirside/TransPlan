"""Security hardening tests (Phase 2 of #270): rate limiting, forwarded-IP
trust, CORS origin policy, docs exposure, and response headers."""
import pytest
from fastapi.testclient import TestClient

from main import app
from services.data_loader import load_all

load_all()
client = TestClient(app, raise_server_exceptions=False)

KIDNEY = {"organ": "kidney", "blood_type": "O+", "age": 45, "sex": "male", "urgency": 2, "cpra": 0}


# -- #246: forwarded-IP trust --

class TestForwardedIp:
    def test_uses_last_entry_not_attacker_supplied_first(self):
        """The trustworthy hop is the one our proxy appends (rightmost), not
        the client-supplied leftmost — otherwise the limiter is bypassable."""
        from middleware.rate_limit import _pick_forwarded_ip
        assert _pick_forwarded_ip("1.1.1.1, 203.0.113.9") == "203.0.113.9"

    def test_single_value(self):
        from middleware.rate_limit import _pick_forwarded_ip
        assert _pick_forwarded_ip("203.0.113.9") == "203.0.113.9"

    def test_strips_whitespace(self):
        from middleware.rate_limit import _pick_forwarded_ip
        assert _pick_forwarded_ip("1.1.1.1 ,  203.0.113.9  ") == "203.0.113.9"


# -- #248: CORS origin policy --

class TestCorsOriginRegex:
    def test_allows_production_and_localhost(self):
        import re
        from security import CORS_ORIGIN_REGEX
        rx = re.compile(CORS_ORIGIN_REGEX)
        for ok in (
            "http://localhost:8002", "http://127.0.0.1:5500",
            "https://transplant.today", "https://www.transplant.today",
            "https://transplan.vercel.app",
            "https://transplan-git-main-team.vercel.app",
        ):
            assert rx.match(ok), f"should allow {ok}"

    def test_rejects_arbitrary_vercel_and_lookalikes(self):
        import re
        from security import CORS_ORIGIN_REGEX
        rx = re.compile(CORS_ORIGIN_REGEX)
        for bad in (
            "https://evil.vercel.app",
            "https://transplanevil.vercel.app",
            "https://transplant.today.evil.com",
        ):
            assert not rx.match(bad), f"should reject {bad}"


# -- #247: docs exposure --

class TestDocsUrls:
    def test_disabled_in_production(self):
        from security import docs_urls
        # docs, redoc, AND the raw openapi schema all off in prod.
        assert docs_urls(is_prod=True) == (None, None, None)

    def test_enabled_in_dev(self):
        from security import docs_urls
        assert docs_urls(is_prod=False) == ("/docs", "/redoc", "/openapi.json")


# -- #250: security headers --

class TestSecurityHeaders:
    def test_present_on_response(self):
        r = client.get("/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert "Referrer-Policy" in r.headers


# -- #245: rate limiting on the unprefixed (production) routes --

class TestRateLimitOnUnprefixedRoutes:
    def _exhaust(self, tier):
        import time
        from middleware.rate_limit import _limiter, RATE_LIMITS
        now = time.monotonic()
        limit = RATE_LIMITS[tier]["default"]
        for ip in ("testclient", "127.0.0.1", "unknown"):
            with _limiter._lock:
                _limiter._windows[f"{ip}:{tier}"] = [now] * (limit + 1)

    def test_simulate_is_rate_limited(self):
        self._exhaust("simulation")
        r = client.post("/simulate", json=KIDNEY)
        assert r.status_code == 429

    def test_score_is_rate_limited(self):
        self._exhaust("simulation")
        r = client.post("/score", json=KIDNEY)
        assert r.status_code == 429

    def test_health_is_not_rate_limited(self):
        """Ops endpoints (keepalive polling) must stay unthrottled."""
        self._exhaust("data")
        self._exhaust("simulation")
        r = client.get("/health")
        assert r.status_code == 200


# -- #249: server-side tier caps on validation params --

class TestValidationTierCaps:
    def test_model_sensitivity_caps_sweep_steps(self):
        """Web tier caps sweep steps at max_validation_sweep_steps (6); a
        request for 10 must be clamped server-side, not honored."""
        body = {
            "patient": KIDNEY, "param": "elasticity",
            "n_steps": 10, "base_iterations": 100, "seed": 1,
        }
        r = client.post("/validation/model-sensitivity", json=body)
        assert r.status_code == 200
        from tier_config import get_tier
        assert len(r.json()["values"]) <= get_tier().max_validation_sweep_steps
