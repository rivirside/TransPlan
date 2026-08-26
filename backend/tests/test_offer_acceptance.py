"""Offer Acceptance Rate Ratio + SRTR tiers integration (#320)."""
import pytest


@pytest.fixture(autouse=True)
def _load(data):
    pass


class TestOarrData:
    def test_loaded_with_coverage(self, data):
        k = data.offer_acceptance.get("kidney", {}).get("centers", {})
        assert len(k) > 180
        rec = next(iter(k.values()))
        assert 0 < rec["oar"] < 6

    def test_tiers_loaded_with_pediatric(self, data):
        k = data.srtr_tiers.get("kidney", {})
        assert len(k) > 190
        peds = [r for r in k.values() if "pediatric_graft_survival" in r]
        assert len(peds) > 80
        assert all(1 <= v <= 5 for r in k.values() for v in r.values())

    def test_f1_prefers_observed_oarr(self, data):
        """The acceptance factor must come from the OBSERVED OARR when
        present (#320), not the volume-proxy composite."""
        from services.monte_carlo import _get_acceptance_rate
        centers = data.offer_acceptance["kidney"]["centers"]
        code = next(c for c, r in centers.items() if abs(r["oar"] - 1.0) > 0.3)
        national = data.acceptance_rates["national_acceptance_rates"]["kidney"]
        from services.monte_carlo import _OARR_SIGNAL_FRACTION
        shrunk = 1.0 + _OARR_SIGNAL_FRACTION["kidney"] * (centers[code]["oar"] - 1.0)
        expected = min(national * max(0.3, min(shrunk, 3.0)), 1.0)
        assert _get_acceptance_rate("kidney", code) == pytest.approx(expected)
        # shrinkage pulls toward neutral: factor strictly between raw OARR and 1
        assert min(centers[code]["oar"], 1.0) <= shrunk <= max(centers[code]["oar"], 1.0)

    def test_center_detail_carries_oar_and_tiers(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        r = client.get("/centers/PAPT")
        assert r.status_code == 200
        body = r.json()
        assert "oar" in body["offer_acceptance"]["kidney"]
        assert "adult_graft_survival" in body["srtr_tiers"]["kidney"]

    def test_acceptance_provenance_recognizes_oarr(self, data):
        from services.provenance import center_data_quality, TAG_ACCEPTANCE
        code = next(iter(data.offer_acceptance["kidney"]["centers"]))
        assert TAG_ACCEPTANCE not in center_data_quality("kidney", code)
