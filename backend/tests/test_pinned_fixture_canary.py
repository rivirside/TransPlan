"""Pinned-fixture canary (#341).

Many suites pin live-data center codes (PAPT, OHCC, ALCH, ...) as convenient
concrete examples. The weekly data refresh can invalidate any of them — a
program retires, a factor is re-derived, a trends series shrinks — and the
result used to be dozens of confusing failures scattered across suites.

This canary asserts every pinned assumption in ONE place with an explanatory
message. If a test here fails after a data refresh: the DATA changed, not the
code — either the refresh is wrong (check the never-shrink guards first) or
the pinned code must be replaced in the suites listed in each assertion.
Prefer the conftest `pick_center` fixture for new tests.
"""
import pytest


@pytest.fixture(autouse=True)
def _load(data):
    pass


def _center(data, code):
    rec = data.all_centers.get("centers", {}).get(code)
    assert rec is not None, (
        f"pinned center {code} vanished from all-centers data — a weekly "
        f"refresh likely retired it; update the suites that pin it"
    )
    return rec


class TestPinnedCenters:
    def test_papt_all_organs(self, data):
        """PAPT (UPMC): pinned as an all-six-organ center by test_sensitivity,
        test_distributions, scripts/run-clinical-backtest."""
        rec = _center(data, "PAPT")
        assert len(rec.get("organs", [])) == 6, (
            f"PAPT no longer performs all six organs ({rec.get('organs')}) — "
            f"replace it in test_sensitivity.TestAllOrgans and friends"
        )
        wt = data.center_wait_times["center_wait_time_factors"]
        assert isinstance(wt.get("PAPT", {}).get("kidney"), (int, float)), (
            "PAPT lost its kidney wait factor (test_distributions pins it)"
        )

    def test_ohcc_kidney_factor_and_heart(self, data):
        """OHCC (Cleveland Clinic): test_distributions pins its kidney factor;
        scripts pin it as a heart center."""
        rec = _center(data, "OHCC")
        assert "kidney" in rec["organs"] and "heart" in rec["organs"]
        wt = data.center_wait_times["center_wait_time_factors"]
        assert isinstance(wt.get("OHCC", {}).get("kidney"), (int, float))

    def test_alch_kidney_trends(self, data):
        """ALCH: test_center_trends and the age/what-if suites pin it as a
        kidney center with a long archived trends series."""
        rec = _center(data, "ALCH")
        assert "kidney" in rec["organs"]
        series = data.center_trends.get("centers", {}).get("ALCH", {}).get("kidney", {})
        assert len(series.get("years", [])) >= 10, (
            "ALCH's kidney trends series shrank below 10 releases "
            "(test_center_trends pins it) — check srtr-trends-centers.json"
        )

    def test_alua_center_level_outcomes(self, data):
        """ALUA: test_data_quality pins it as a center with CENTER-LEVEL
        observed survival (survival_source == 'center')."""
        rec = _center(data, "ALUA")
        assert data.observed_outcome("kidney", "ALUA") is not None, (
            "ALUA lost its kidney observed outcomes (test_data_quality pins it)"
        )

    def test_tnvu_kidney_liver(self, data):
        """TNVU (Vanderbilt): endpoint suites pin it for kidney/liver runs."""
        rec = _center(data, "TNVU")
        assert "kidney" in rec["organs"] and "liver" in rec["organs"]

    def test_casu_all_organs(self, data):
        """CASU (Stanford): scripts and sensitivity sweeps pin it as an
        all-organ center."""
        rec = _center(data, "CASU")
        assert len(rec.get("organs", [])) == 6

    def test_cala_kidney_only(self, data):
        """CALA (Harbor UCLA): test_data_loader's wrong-organ rejection case
        RELIES on CALA not performing heart."""
        rec = _center(data, "CALA")
        assert "kidney" in rec["organs"]
        assert "heart" not in rec["organs"], (
            "CALA now performs heart — test_data_loader's resolve_center "
            "wrong-organ case needs a different kidney-only center"
        )
