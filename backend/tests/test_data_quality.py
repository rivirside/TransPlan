"""Tests for the data_quality provenance fields (#300).

Silent fallbacks (missing center data defaulting to national factors) must be
visible in API responses — this is what let bugs like #287 hide.
"""
import pytest

from models.schemas import PatientProfile
from services.monte_carlo import simulate


@pytest.fixture(autouse=True)
def _load(data):
    pass


@pytest.fixture
def kidney_patient():
    return PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                          urgency=2, cpra=20)


class TestDataQuality:
    def test_summary_present_and_consistent(self, kidney_patient):
        result = simulate(kidney_patient, n_iterations=200, seed=42)
        dq = result.data_quality
        assert dq is not None
        assert dq["centers_total"] == len(result.cities)
        wt = dq["wait_time_factors"]
        assert wt["center_level"] + wt["national_default"] == dq["centers_total"]
        assert dq["fully_center_level"] <= dq["centers_total"]

    def test_most_kidney_centers_are_center_level(self, kidney_patient):
        """The SRTR parse covers nearly all centers — a majority falling back
        would mean the data files regressed (2026-08-05 incident class)."""
        result = simulate(kidney_patient, n_iterations=200, seed=42)
        dq = result.data_quality
        assert dq["wait_time_factors"]["center_level"] > 0.8 * dq["centers_total"]

    def test_per_center_tags_match_summary(self, kidney_patient):
        result = simulate(kidney_patient, n_iterations=200, seed=42)
        n_missing_obs = sum(
            1 for c in result.cities
            if c.data_quality and "no_observed_outcomes" in c.data_quality
        )
        assert n_missing_obs == result.data_quality["observed_outcomes"]["missing"]

    def test_intestine_shows_degradation_honestly(self):
        """Sparse organs must not pretend to be fully center-level."""
        p = PatientProfile(organ="intestine", blood_type="A+", age=45, sex="male",
                           urgency=2)
        result = simulate(p, n_iterations=200, seed=42)
        dq = result.data_quality
        assert dq is not None
        # There should be at least SOME degradation signal for intestine,
        # or (if data is complete) everything consistent
        assert dq["fully_center_level"] + sum(
            1 for c in result.cities if c.data_quality) == dq["centers_total"]


class TestProvenanceHonesty:
    """#219: 'no center code' must never read as 'fully center-level'."""

    def test_empty_code_returns_all_tags(self):
        from services.provenance import center_data_quality, ALL_TAGS
        assert center_data_quality("kidney", "") == ALL_TAGS

    def test_bbn_results_carry_data_quality(self, kidney_patient):
        """#219 item 4: data_quality was null for BBN runs, reading as 'no
        degraded inputs' instead of 'not measured'."""
        from services.bayesian_network import simulate_bbn
        result = simulate_bbn(kidney_patient)
        assert result.data_quality is not None
        assert result.data_quality["centers_total"] == len(result.cities)

    def test_outcomes_declare_survival_source(self, kidney_patient):
        """#219 item 2: national averages were written into center-named
        survival fields with no discriminator."""
        from services.outcomes import build_outcomes_dict
        with_center = build_outcomes_dict("kidney", "x", 0.5, center_code="ALUA")
        assert with_center["survival_source"] == "center"
        no_center = build_outcomes_dict("kidney", "x", 0.5, center_code="XXXX")
        assert no_center["survival_source"] == "national"

    def test_bbn_per_center_tags_attached(self):
        """Regression (2026-08 review): BBN computed tags but dropped them,
        making summarize() claim every center was fully center-level."""
        from services.bayesian_network import simulate_bbn
        p = PatientProfile(organ="intestine", blood_type="A+", age=45,
                           sex="male", urgency=2, bbn_granularity="state")
        result = simulate_bbn(p)
        dq = result.data_quality
        # Intestine data is sparse — a fully-center-level claim would be false
        assert dq["fully_center_level"] < dq["centers_total"], (
            "BBN claims every intestine center is fully center-level — "
            "per-center tags are not being attached"
        )
        tagged = [c for c in result.cities if c.data_quality]
        assert tagged, "no CityProbability carries data_quality tags"

    def test_bbn_unknown_shortlist_raises(self):
        """BBN must reject an all-unknown center_codes shortlist like MC."""
        from services.bayesian_network import simulate_bbn
        p = PatientProfile(organ="kidney", blood_type="O+", age=45, sex="male",
                           urgency=2, bbn_granularity="state",
                           center_codes=["ZZZZ"])
        with pytest.raises(ValueError, match="center_codes"):
            simulate_bbn(p)


class TestExtensibleProvenance:
    """#340: the tag registry is data-driven — new families must not require
    touching every consumer, and /score must not mutate a shared dict."""

    def test_five_tag_families(self):
        from services import provenance
        assert len(provenance.ALL_TAGS) == 5
        assert provenance.TAG_ACCEPTANCE in provenance.ALL_TAGS
        assert provenance.TAG_TRENDS in provenance.ALL_TAGS

    def test_summary_covers_every_family(self, kidney_patient):
        from services import provenance
        result = simulate(kidney_patient, n_iterations=100, seed=1)
        dq = result.data_quality
        for tag in provenance.ALL_TAGS:
            family = provenance.FAMILIES[tag][0]
            assert family in dq, f"summary missing family {family}"
            fam = dq[family]
            assert sum(fam.values()) == dq["centers_total"]

    def test_acceptance_tag_fires_for_missing_center_factor(self):
        from services.provenance import center_data_quality, TAG_ACCEPTANCE
        from services.data_loader import get_data
        data = get_data()
        ar = data.acceptance_rates.get("center_acceptance_factors", {})
        oarr = data.offer_acceptance.get("kidney", {}).get("centers", {})
        # #320: the tag fires only when BOTH sources are absent — the
        # observed OARR is now the preferred center-level source
        centers = data.centers_for_organ("kidney")
        missing = next((c["code"] for c in centers
                        if "kidney" not in ar.get(c["code"], {})
                        and c["code"] not in oarr), None)
        if missing is None:
            pytest.skip("every kidney center has an acceptance source")
        assert TAG_ACCEPTANCE in center_data_quality("kidney", missing)

    def test_scoring_summary_shape(self):
        """The /score summary excludes non-scoring families WITHOUT mutating
        the shared summarize() result."""
        from services.provenance import scoring_summary
        dq = scoring_summary("kidney", ["PAPT", "OHCC", "ZZZZ"],
                             spatial_layers_unavailable=["air_quality"])
        assert "competing_risks" not in dq
        assert dq["centers_total"] == 3
        assert dq["spatial_layers_unavailable"] == ["air_quality"]
        assert "wait_time_factors" in dq
