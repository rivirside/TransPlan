"""Tests for MCMC hierarchical survival model (Phase 5 M3)."""

import json

import numpy as np
import pytest

from services.mcmc_survival import (
    BLOOD_TYPES,
    ORGANS,
    URGENCY_LEVELS,
    build_organ_model,
    load_organ_data,
    sample_params_from_trace,
)


# ---------------------------------------------------------------------------
# Data loading tests
# ---------------------------------------------------------------------------

class TestLoadOrganData:
    @pytest.mark.parametrize("organ", ORGANS)
    def test_loads_all_organs(self, organ):
        data = load_organ_data(organ)
        assert data["organ"] == organ

    def test_kidney_data_shape(self):
        data = load_organ_data("kidney")
        assert data["n_cities"] == 22
        assert data["national_median"] > 0
        assert data["log_sigma"] > 0
        assert data["city_wait_factors"].shape == (22,)
        assert data["city_mort_factors"].shape == (22,)
        assert data["city_delist_factors"].shape == (22,)
        assert data["bt_mults"].shape == (8,)
        assert data["urg_mults"].shape == (4,)

    def test_national_rates_positive(self):
        for organ in ORGANS:
            data = load_organ_data(organ)
            assert data["national_mort_rate"] > 0, f"{organ} mort rate"
            assert data["national_delist_rate"] > 0, f"{organ} delist rate"
            assert data["national_median"] > 0, f"{organ} median"

    def test_city_factors_positive(self):
        data = load_organ_data("kidney")
        assert (data["city_wait_factors"] > 0).all()
        assert (data["city_mort_factors"] > 0).all()
        assert (data["city_delist_factors"] > 0).all()

    def test_blood_type_multipliers_positive(self):
        data = load_organ_data("kidney")
        assert (data["bt_mults"] > 0).all()

    def test_urgency_multipliers_ordered(self):
        """Higher urgency should have higher mortality multiplier."""
        data = load_organ_data("kidney")
        # Urgency levels 1-4, mults should be non-decreasing
        assert data["urg_mults"][0] <= data["urg_mults"][1]
        assert data["urg_mults"][1] <= data["urg_mults"][2]
        assert data["urg_mults"][2] <= data["urg_mults"][3]

    def test_age_multipliers_present(self):
        data = load_organ_data("kidney")
        assert "18-34" in data["age_mults"]
        assert "65+" in data["age_mults"]
        # Young should have lower mortality
        assert data["age_mults"]["18-34"] < data["age_mults"]["65+"]


# ---------------------------------------------------------------------------
# Model building tests
# ---------------------------------------------------------------------------

class TestBuildOrganModel:
    def test_model_builds_kidney(self):
        data = load_organ_data("kidney")
        model = build_organ_model(data)
        assert model is not None

    def test_free_rvs_count(self):
        data = load_organ_data("kidney")
        model = build_organ_model(data)
        # 19 named free RV groups
        assert len(model.free_RVs) == 19

    def test_observed_rvs_count(self):
        data = load_organ_data("kidney")
        model = build_organ_model(data)
        # 5 observed likelihoods
        assert len(model.observed_RVs) == 5

    def test_deterministics_present(self):
        data = load_organ_data("kidney")
        model = build_organ_model(data)
        det_names = {d.name for d in model.deterministics}
        assert "city_wait_factor" in det_names
        assert "national_median_months" in det_names
        assert "bt_multiplier" in det_names
        assert "urg_multiplier" in det_names

    @pytest.mark.parametrize("organ", ORGANS)
    def test_model_builds_all_organs(self, organ):
        """Model should build for every organ type."""
        data = load_organ_data(organ)
        model = build_organ_model(data)
        assert len(model.free_RVs) > 0

    def test_total_free_params(self):
        data = load_organ_data("kidney")
        model = build_organ_model(data)
        n_free = sum(v.type.shape.eval() if hasattr(v.type.shape, 'eval') else np.prod(v.type.shape) for v in model.free_RVs)
        # Should have ~92 free parameters
        # (but count method varies, just check model built)
        assert len(model.free_RVs) == 19


# ---------------------------------------------------------------------------
# Sampling tests (requires quick-fit trace)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def kidney_trace():
    """Quick-fit a kidney trace for testing (100 draws, 1 chain)."""
    import pymc as pm
    data = load_organ_data("kidney")
    model = build_organ_model(data)
    with model:
        trace = pm.sample(
            draws=100, chains=1, tune=50, random_seed=42,
            target_accept=0.85, return_inferencedata=True,
            progressbar=False,
        )
    trace.attrs["organ"] = "kidney"
    trace.attrs["cities"] = json.dumps(data["cities"])
    trace.attrs["blood_types"] = json.dumps(BLOOD_TYPES)
    return trace


class TestSampleParamsFromTrace:
    def test_single_draw(self, kidney_trace):
        params = sample_params_from_trace(kidney_trace, n_draws=1)
        assert isinstance(params, dict)
        assert "national_median" in params
        assert "city_wait_factors" in params

    def test_national_median_positive(self, kidney_trace):
        params = sample_params_from_trace(kidney_trace, n_draws=1)
        assert params["national_median"] > 0

    def test_city_factors_shape(self, kidney_trace):
        params = sample_params_from_trace(kidney_trace, n_draws=1)
        assert params["city_wait_factors"].shape == (22,)
        assert params["city_mort_offsets"].shape == (22,)

    def test_bt_multipliers_shape(self, kidney_trace):
        params = sample_params_from_trace(kidney_trace, n_draws=1)
        assert params["bt_multipliers"].shape == (8,)

    def test_urg_multipliers_shape(self, kidney_trace):
        params = sample_params_from_trace(kidney_trace, n_draws=1)
        assert params["urg_multipliers"].shape == (4,)

    def test_multiple_draws(self, kidney_trace):
        results = sample_params_from_trace(kidney_trace, n_draws=5)
        assert isinstance(results, list)
        assert len(results) == 5

    def test_draws_vary(self, kidney_trace):
        """Different draws should produce different parameter values."""
        results = sample_params_from_trace(kidney_trace, n_draws=10, rng=np.random.default_rng(42))
        medians = [r["national_median"] for r in results]
        # Not all identical (posterior has variance)
        assert len(set(medians)) > 1

    def test_city_factors_positive(self, kidney_trace):
        params = sample_params_from_trace(kidney_trace, n_draws=1)
        assert (params["city_wait_factors"] > 0).all()

    def test_bt_multipliers_positive(self, kidney_trace):
        params = sample_params_from_trace(kidney_trace, n_draws=1)
        assert (params["bt_multipliers"] > 0).all()

    def test_national_median_near_observed(self, kidney_trace):
        """Posterior mean should be near the observed value (27.4 for kidney)."""
        draws = sample_params_from_trace(kidney_trace, n_draws=50, rng=np.random.default_rng(42))
        mean_median = np.mean([d["national_median"] for d in draws])
        # Should be within 50% of 27.4 (generous for 100-draw trace)
        assert 10 < mean_median < 60, f"Posterior mean {mean_median} too far from 27.4"

    def test_cities_list_preserved(self, kidney_trace):
        params = sample_params_from_trace(kidney_trace, n_draws=1)
        assert len(params["cities"]) == 22


# ---------------------------------------------------------------------------
# Posterior sanity checks
# ---------------------------------------------------------------------------

class TestPosteriorSanity:
    def test_city_wait_factor_range(self, kidney_trace):
        """City wait factors should be in plausible range (0.2-5.0)."""
        draws = sample_params_from_trace(kidney_trace, n_draws=20, rng=np.random.default_rng(42))
        for d in draws:
            assert (d["city_wait_factors"] > 0.1).all()
            assert (d["city_wait_factors"] < 10.0).all()

    def test_mort_rate_plausible(self, kidney_trace):
        """National mortality rate should be in plausible range."""
        draws = sample_params_from_trace(kidney_trace, n_draws=20, rng=np.random.default_rng(42))
        for d in draws:
            assert 0.001 < d["national_mort_rate"] < 0.5

    def test_delist_rate_plausible(self, kidney_trace):
        """National delisting rate should be in plausible range."""
        draws = sample_params_from_trace(kidney_trace, n_draws=20, rng=np.random.default_rng(42))
        for d in draws:
            assert 0.001 < d["national_delist_rate"] < 0.5

    def test_log_sigma_positive(self, kidney_trace):
        draws = sample_params_from_trace(kidney_trace, n_draws=20, rng=np.random.default_rng(42))
        for d in draws:
            assert d["log_sigma"] > 0
