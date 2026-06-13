"""MCMC-19: convergence diagnostics must read traces from the SAME location
mcmc_survival writes them. The old convergence.py looked in
data/mcmc_traces/{organ}_trace.nc while traces are saved to
data/mcmc-traces/{organ}.nc — so diagnostics never ran on real fitted traces."""
import json

import pytest

from services.mcmc_survival import (
    BLOOD_TYPES,
    build_organ_model,
    load_organ_data,
    save_trace,
    trace_path,
)


@pytest.fixture(scope="module", autouse=True)
def _fit_kidney_trace():
    import pymc as pm
    from services.data_loader import load_all

    load_all()
    data = load_organ_data("kidney")
    model = build_organ_model(data)
    with model:
        trace = pm.sample(
            draws=100, chains=2, tune=50, random_seed=42,
            target_accept=0.85, return_inferencedata=True, progressbar=False,
        )
    trace.attrs["organ"] = "kidney"
    trace.attrs["cities"] = json.dumps(data["cities"])
    trace.attrs["blood_types"] = json.dumps(BLOOD_TYPES)
    save_trace("kidney", trace)
    yield
    p = trace_path("kidney")
    if p.exists():
        p.unlink()


class TestConvergenceFindsTrace:
    def test_finds_the_saved_trace(self):
        from services.convergence import get_convergence_diagnostics
        diag = get_convergence_diagnostics("kidney")
        assert diag.available is True, f"should find the saved trace; notes={diag.notes}"

    def test_reports_chains_and_draws(self):
        from services.convergence import get_convergence_diagnostics
        diag = get_convergence_diagnostics("kidney")
        assert diag.n_chains == 2
        assert diag.n_draws == 100
        assert len(diag.parameters) > 0

    def test_missing_organ_is_unavailable(self):
        from services.convergence import get_convergence_diagnostics
        diag = get_convergence_diagnostics("intestine")  # no trace fitted
        assert diag.available is False
