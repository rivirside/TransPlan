"""Tests for services/cross_validation.py — cross-engine validation."""
import pytest
from unittest.mock import patch, MagicMock

from models.schemas import CityProbability, PatientProfile, SimulationResult
from services.cross_validation import (
    CrossValidationResult,
    EnginePairComparison,
    CityEngineRow,
    cross_validate,
    _build_city_map,
    _build_ci_map,
    _compare_pair,
)


# -- Fixtures --

@pytest.fixture
def kidney_patient() -> PatientProfile:
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male", urgency=2, cpra=50)


def _make_sim_result(patient, city_data: list[dict], mode="monte_carlo") -> SimulationResult:
    """Helper to build a SimulationResult from simplified city data."""
    cities = []
    for cd in city_data:
        cities.append(CityProbability(
            city=cd["city"],
            state=cd.get("state", "XX"),
            p_transplant_6mo=cd.get("p6", 0.1),
            p_transplant_12mo=cd.get("p12", 0.2),
            p_transplant_24mo=cd["p24"],
            p_transplant_36mo=cd.get("p36", 0.5),
            confidence_interval_95=cd.get("ci", (cd["p24"] - 0.05, cd["p24"] + 0.05)),
            median_wait_months=cd.get("median", 12.0),
        ))
    return SimulationResult(
        patient=patient,
        cities=cities,
        iterations=1000,
        elapsed_seconds=1.0,
        inference_mode=mode,
    )


# -- _build_city_map / _build_ci_map --

class TestBuildMaps:
    def test_city_map_extracts_p24(self, kidney_patient):
        result = _make_sim_result(kidney_patient, [
            {"city": "Nashville", "p24": 0.45},
            {"city": "Pittsburgh", "p24": 0.52},
        ])
        m = _build_city_map(result)
        assert m["Nashville"] == 0.45
        assert m["Pittsburgh"] == 0.52

    def test_ci_map_extracts_intervals(self, kidney_patient):
        result = _make_sim_result(kidney_patient, [
            {"city": "Nashville", "p24": 0.45, "ci": (0.40, 0.50)},
        ])
        m = _build_ci_map(result)
        assert m["Nashville"] == (0.40, 0.50)


# -- _compare_pair --

class TestComparePair:
    def test_identical_maps_give_perfect_correlation(self):
        m = {"A": 0.5, "B": 0.3, "C": 0.7, "D": 0.1, "E": 0.9}
        comp = _compare_pair("engine1", m, "engine2", m)
        assert comp.spearman_rho == 1.0
        assert comp.mean_abs_diff_p24 == 0.0
        assert comp.max_abs_diff_p24 == 0.0
        assert comp.rank_agreement_top5 == 5

    def test_different_maps_have_nonzero_diff(self):
        m_a = {"A": 0.5, "B": 0.3, "C": 0.7}
        m_b = {"A": 0.6, "B": 0.2, "C": 0.8}
        comp = _compare_pair("mc", m_a, "bbn", m_b)
        assert comp.mean_abs_diff_p24 > 0
        assert comp.max_abs_diff_p24 >= comp.mean_abs_diff_p24

    def test_max_diff_city_identified(self):
        m_a = {"A": 0.5, "B": 0.3, "C": 0.7}
        m_b = {"A": 0.5, "B": 0.3, "C": 0.2}  # C has biggest diff
        comp = _compare_pair("mc", m_a, "bbn", m_b)
        assert comp.max_diff_city == "C"
        assert comp.max_abs_diff_p24 == 0.5

    def test_top5_overlap_with_partial_agreement(self):
        # 5 cities each, but different orderings
        m_a = {"A": 0.9, "B": 0.8, "C": 0.7, "D": 0.6, "E": 0.5, "F": 0.1}
        m_b = {"A": 0.9, "B": 0.8, "C": 0.7, "D": 0.1, "E": 0.1, "F": 0.6}
        comp = _compare_pair("mc", m_a, "bbn", m_b)
        # top5 of m_a: A,B,C,D,E; top5 of m_b: A,B,C,F,... — overlap is 3 (A,B,C)
        assert comp.rank_agreement_top5 >= 3


# -- cross_validate with mocked engines --

class TestCrossValidate:
    def _mock_mc_result(self, patient):
        return _make_sim_result(patient, [
            {"city": "Nashville", "state": "TN", "p24": 0.45},
            {"city": "Pittsburgh", "state": "PA", "p24": 0.52},
            {"city": "Houston", "state": "TX", "p24": 0.38},
        ], mode="monte_carlo")

    def _mock_bbn_result(self, patient):
        return _make_sim_result(patient, [
            {"city": "Nashville", "state": "TN", "p24": 0.43},
            {"city": "Pittsburgh", "state": "PA", "p24": 0.50},
            {"city": "Houston", "state": "TX", "p24": 0.40},
        ], mode="bayesian")

    @patch("services.cross_validation._run_mcmc", return_value=None)
    @patch("services.cross_validation._run_bbn")
    @patch("services.cross_validation._run_mc")
    def test_returns_result_with_two_engines(self, mock_mc, mock_bbn, mock_mcmc, kidney_patient):
        mock_mc.return_value = self._mock_mc_result(kidney_patient)
        mock_bbn.return_value = self._mock_bbn_result(kidney_patient)

        result = cross_validate(kidney_patient, n_iterations=100)
        assert isinstance(result, CrossValidationResult)
        assert len(result.engines_run) == 2
        assert "monte_carlo" in result.engines_run
        assert "bayesian" in result.engines_run

    @patch("services.cross_validation._run_mcmc", return_value=None)
    @patch("services.cross_validation._run_bbn")
    @patch("services.cross_validation._run_mc")
    def test_pairwise_comparison_produced(self, mock_mc, mock_bbn, mock_mcmc, kidney_patient):
        mock_mc.return_value = self._mock_mc_result(kidney_patient)
        mock_bbn.return_value = self._mock_bbn_result(kidney_patient)

        result = cross_validate(kidney_patient, n_iterations=100)
        assert len(result.pairwise) == 1  # one pair: MC vs BBN
        comp = result.pairwise[0]
        assert isinstance(comp, EnginePairComparison)
        assert comp.spearman_rho > 0  # similar orderings should correlate

    @patch("services.cross_validation._run_mcmc", return_value=None)
    @patch("services.cross_validation._run_bbn")
    @patch("services.cross_validation._run_mc")
    def test_city_table_produced(self, mock_mc, mock_bbn, mock_mcmc, kidney_patient):
        mock_mc.return_value = self._mock_mc_result(kidney_patient)
        mock_bbn.return_value = self._mock_bbn_result(kidney_patient)

        result = cross_validate(kidney_patient, n_iterations=100)
        assert len(result.city_table) == 3
        cities = {row.city for row in result.city_table}
        assert cities == {"Nashville", "Pittsburgh", "Houston"}

    @patch("services.cross_validation._run_mcmc", return_value=None)
    @patch("services.cross_validation._run_bbn")
    @patch("services.cross_validation._run_mc")
    def test_city_row_has_both_engine_values(self, mock_mc, mock_bbn, mock_mcmc, kidney_patient):
        mock_mc.return_value = self._mock_mc_result(kidney_patient)
        mock_bbn.return_value = self._mock_bbn_result(kidney_patient)

        result = cross_validate(kidney_patient, n_iterations=100)
        nash = next(r for r in result.city_table if r.city == "Nashville")
        assert nash.mc_p24 == 0.45
        assert nash.bbn_p24 == 0.43

    @patch("services.cross_validation._run_mcmc", return_value=None)
    @patch("services.cross_validation._run_bbn", return_value=None)
    @patch("services.cross_validation._run_mc")
    def test_single_engine_adds_note(self, mock_mc, mock_bbn, mock_mcmc, kidney_patient):
        mock_mc.return_value = self._mock_mc_result(kidney_patient)

        result = cross_validate(kidney_patient, n_iterations=100)
        assert len(result.engines_run) == 1
        assert any("need >= 2" in n for n in result.notes)

    @patch("services.cross_validation._run_mcmc", return_value=None)
    @patch("services.cross_validation._run_bbn", return_value=None)
    @patch("services.cross_validation._run_mc", return_value=None)
    def test_no_engines_adds_note(self, mock_mc, mock_bbn, mock_mcmc, kidney_patient):
        result = cross_validate(kidney_patient, n_iterations=100)
        assert len(result.engines_run) == 0
        assert any("0 engine" in n for n in result.notes)

    @patch("services.cross_validation._run_mcmc", return_value=None)
    @patch("services.cross_validation._run_bbn")
    @patch("services.cross_validation._run_mc")
    def test_elapsed_recorded(self, mock_mc, mock_bbn, mock_mcmc, kidney_patient):
        mock_mc.return_value = self._mock_mc_result(kidney_patient)
        mock_bbn.return_value = self._mock_bbn_result(kidney_patient)

        result = cross_validate(kidney_patient, n_iterations=100)
        assert result.elapsed_seconds >= 0

    @patch("services.cross_validation._run_mcmc", return_value=None)
    @patch("services.cross_validation._run_bbn")
    @patch("services.cross_validation._run_mc")
    def test_low_correlation_flagged(self, mock_mc, mock_bbn, mock_mcmc, kidney_patient):
        """When engines produce very different rankings, a warning note is added."""
        mock_mc.return_value = _make_sim_result(kidney_patient, [
            {"city": "Nashville", "state": "TN", "p24": 0.9},
            {"city": "Pittsburgh", "state": "PA", "p24": 0.1},
            {"city": "Houston", "state": "TX", "p24": 0.5},
        ])
        mock_bbn.return_value = _make_sim_result(kidney_patient, [
            {"city": "Nashville", "state": "TN", "p24": 0.1},
            {"city": "Pittsburgh", "state": "PA", "p24": 0.9},
            {"city": "Houston", "state": "TX", "p24": 0.5},
        ])

        result = cross_validate(kidney_patient, n_iterations=100)
        assert any("Low rank correlation" in n for n in result.notes)
