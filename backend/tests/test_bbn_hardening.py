"""BBN robustness items from #298.

Three of the issue's four items; the fourth (BBN-22's pediatric age clamp)
was retired in #370 and is covered by tests/test_pediatric_mode.py.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]


class TestSyntheticFallbackFailsLoudly:
    """BBN-17: the national 50/5/5 synthetic fallback used to engage with only
    a log warning. CompetingOutcome is the BBN's ONLY fully data-grounded node
    (#206 rebuilt it specifically to remove magic numbers), so falling back
    ungrounds the thing that makes the network defensible — and returns
    plausible-looking probabilities while doing it. That is the 2026-08-05
    failure mode: a missing data file producing a working-looking model.
    """

    def test_all_organs_have_a_real_baseline(self, data):
        """If this fails, the raise below is about to fire in production."""
        from services.data_loader import get_data
        d = get_data()
        for organ in ("kidney", "liver", "heart", "lung", "pancreas", "intestine"):
            natl = d.observed_national(organ)
            assert natl, f"{organ} has no national outcome baseline"
            for field in ("transplant_rate", "waitlist_death_rate", "delisting_rate"):
                assert natl.get(field) is not None, f"{organ} missing {field}"

    def test_missing_baseline_raises_rather_than_substituting(self, data):
        from services.bbn_parameterizer import _national_vector_12mo
        from services.data_loader import get_data
        d = get_data()
        saved = d.srtr_observed_rates
        try:
            d.srtr_observed_rates = {}
            with pytest.raises(ValueError, match="data-grounded"):
                _national_vector_12mo("kidney")
        finally:
            d.srtr_observed_rates = saved

    def test_partial_baseline_also_raises(self, data):
        """A block present but missing one rate is the subtler case — it would
        previously have taken the `or 50.0` default for just that field."""
        from services.bbn_parameterizer import _national_vector_12mo
        from services.data_loader import get_data
        d = get_data()
        saved = d.srtr_observed_rates
        try:
            d.srtr_observed_rates = {
                "kidney": {"national": {"transplant_rate": 36.7,
                                        "waitlist_death_rate": None,
                                        "delisting_rate": 2.0}}}
            with pytest.raises(ValueError, match="waitlist_death_rate"):
                _national_vector_12mo("kidney")
        finally:
            d.srtr_observed_rates = saved

    def test_healthy_path_returns_a_normalized_vector(self, data):
        from services.bbn_parameterizer import _national_vector_12mo
        vec = _national_vector_12mo("kidney")
        assert len(vec) == 4
        assert abs(vec.sum() - 1.0) < 1e-9
        assert (vec >= 0).all()


class TestCptNormalizationIsStrictlyChecked:
    """#298 item 3: check_model's tolerance was atol=0.05, loose enough for a
    5%-un-normalized auto-generated CPT to pass. It is now 1e-6; this is the
    regression test the issue asked for."""

    def _net(self, child_values):
        from services.bbn_lite import BayesianNet, Factor
        net = BayesianNet([("A", "B")])
        net.add_cpd("A", Factor(["A"], [2], np.array([0.5, 0.5])))
        net.add_cpd("B", Factor(["B", "A"], [2, 2], child_values))
        return net

    def test_a_normalized_cpt_passes(self):
        assert self._net(np.array([[0.5, 0.5], [0.5, 0.5]])).check_model()

    def test_a_slightly_unnormalized_cpt_is_rejected(self):
        # 2% off — comfortably inside the old atol=0.05, so this is exactly
        # the table the loose tolerance used to wave through.
        bad = np.array([[0.51, 0.5], [0.51, 0.5]])
        assert not self._net(bad).check_model(), (
            "a 2% un-normalized CPT passed — the tolerance has been loosened")

    def test_the_check_is_tight_not_merely_present(self):
        """Guards against someone 'fixing' a build bug by relaxing atol: even
        a 0.1% error must fail."""
        subtle = np.array([[0.501, 0.5], [0.5, 0.5]])
        assert not self._net(subtle).check_model()

    def test_every_built_cpt_is_normalized(self, data):
        """The real protection: the CPTs actually shipped must be exact."""
        from services.bayesian_network import build_model
        model = build_model("state")
        assert model.check_model()
        for factor in model.cpd_factors:
            v = factor.values
            sums = v.sum() if v.ndim == 1 else v.sum(axis=0)
            assert np.allclose(sums, 1.0, atol=1e-6), (
                f"{factor.variables[0]} CPT columns sum to {np.unique(sums)[:4]}")


class TestNoCircularImport:
    """L-070: bbn_parameterizer and bayesian_network had a deferred import
    guarding a cycle. The function it guarded (_get_center_region_map) was
    removed with the classic granularity in #293, so the cycle is gone — but a
    real cycle only fails in ONE import order, so both are checked."""

    @pytest.mark.parametrize("first,second", [
        ("services.bbn_parameterizer", "services.bayesian_network"),
        ("services.bayesian_network", "services.bbn_parameterizer"),
    ])
    def test_either_import_order_works(self, first, second):
        result = subprocess.run(
            [sys.executable, "-c", f"import {first}; import {second}"],
            capture_output=True, text=True, cwd=str(REPO / "backend"))
        assert result.returncode == 0, (
            f"importing {first} before {second} failed — a circular import has "
            f"been reintroduced:\n{result.stderr[-400:]}")

    def test_no_module_level_import_of_bayesian_network(self):
        """The cycle would return if someone added this import at module level."""
        src = (REPO / "backend" / "services" / "bbn_parameterizer.py").read_text()
        for line in src.splitlines():
            stripped = line.strip()
            if line.startswith(("import ", "from ")) and "bayesian_network" in stripped:
                pytest.fail(f"module-level import re-creates the cycle: {stripped}")
