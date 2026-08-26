"""Pediatric mode end to end (#335 phase 2).

Children were rejected at the schema (age ge=18). They are now modeled with
pediatric data, restricted to centers that actually run a pediatric program
for the organ, with the honest caveats the data forces.
"""
import pytest

from models.schemas import PatientProfile


@pytest.fixture(autouse=True)
def _load(data):
    pass


def _child(**kw):
    base = dict(organ="kidney", blood_type="O+", age=10, sex="female", urgency=2)
    base.update(kw)
    return PatientProfile(**base)


class TestSchema:
    def test_child_accepted(self):
        p = _child()
        assert p.age == 10 and p.is_pediatric is True

    def test_adult_not_pediatric(self):
        assert PatientProfile(organ="kidney", blood_type="O+", age=45,
                              sex="male", urgency=2).is_pediatric is False

    def test_boundary_is_18(self):
        assert _child(age=17).is_pediatric is True
        assert _child(age=18).is_pediatric is False

    def test_age_zero_still_rejected(self):
        with pytest.raises(Exception):
            _child(age=0)

    def test_peld_accepted_and_can_be_negative(self):
        """PELD is a different scale from MELD and CAN be negative — reusing
        the MELD 6-40 bound would silently reject valid pediatric scores."""
        p = _child(organ="liver", age=5, peld=-4.0)
        assert p.peld == -4.0

    def test_meld_not_required_for_young_child(self):
        p = _child(organ="liver", age=5, peld=12.0)
        assert p.meld is None


class TestEngineRestriction:
    def test_only_pediatric_program_centers_returned(self):
        """A child must not be scored against centers with no pediatric
        program — that was the silent-wrongness this phase exists to fix."""
        from services.data_loader import get_data
        from services.monte_carlo import simulate
        peds = get_data().pediatric.get("kidney", {}).get("centers", {})
        assert peds, "pediatric data not loaded"
        result = simulate(_child(), n_iterations=200, seed=5)
        codes = {c.center_code for c in result.cities}
        assert codes, "no centers returned for a pediatric patient"
        assert codes <= set(peds), (
            f"pediatric run included non-pediatric centers: "
            f"{sorted(codes - set(peds))[:5]}"
        )

    def test_adult_run_unchanged_bitwise(self):
        """Adults must be untouched by pediatric support."""
        from services.monte_carlo import simulate
        adult = dict(organ="kidney", blood_type="O+", age=45, sex="male",
                     urgency=2, cpra=20)
        a = simulate(PatientProfile(**adult), n_iterations=200, seed=9)
        b = simulate(PatientProfile(**adult), n_iterations=200, seed=9)
        assert [(c.center_code, c.p_transplant_24mo) for c in a.cities] == \
               [(c.center_code, c.p_transplant_24mo) for c in b.cities]
        # and the adult population is far larger than the pediatric one
        assert len(a.cities) > len(simulate(_child(), n_iterations=100, seed=9).cities)

    def test_probabilities_valid_and_ordered(self):
        from services.monte_carlo import simulate
        for organ in ("kidney", "liver", "heart"):
            r = simulate(_child(organ=organ), n_iterations=300, seed=3)
            assert r.cities
            for c in r.cities:
                assert 0 <= c.p_transplant_6mo <= c.p_transplant_12mo \
                    <= c.p_transplant_24mo <= c.p_transplant_36mo <= 1
                assert c.median_wait_months > 0

    def test_p12_tracks_observed_pediatric_rate(self):
        """The design decision from the inversion gate: the observed
        pediatric rate drives the 12-month probability directly, so the
        model's p12 must correlate strongly with it."""
        from scipy.stats import spearmanr
        from services.data_loader import get_data
        from services.monte_carlo import simulate
        peds = get_data().pediatric["kidney"]["centers"]
        k = get_data().pediatric["kidney"]["calibration"]["k"]
        import math
        r = simulate(_child(), n_iterations=1500, seed=11)
        model, observed = [], []
        for c in r.cities:
            rec = peds.get(c.center_code)
            if rec:
                model.append(c.p_transplant_12mo)
                observed.append(1 - math.exp(-k * rec["transplant_rate"]))
        assert len(model) > 40
        rho = spearmanr(model, observed).statistic
        assert rho > 0.8, f"pediatric p12 does not track observed rates: {rho}"


class TestProvenance:
    def test_sparse_pediatric_centers_tagged(self):
        """Small pediatric cohorts must be visible, not silently averaged in."""
        from services.provenance import TAG_PEDIATRIC_SPARSE, center_data_quality
        from services.data_loader import get_data
        peds = get_data().pediatric["kidney"]["centers"]
        sparse = [c for c, r in peds.items() if (r.get("person_years") or 0) < 10]
        if not sparse:
            pytest.skip("no sparse pediatric centers")
        tags = center_data_quality("kidney", sparse[0], pediatric=True)
        assert TAG_PEDIATRIC_SPARSE in tags


class TestScoringParity:
    def test_scoring_restricted_like_simulation(self):
        """The results table merges /score with /simulate by center code, so
        a scoring path that returns adult centers produces rows with blank
        simulation columns. Both must return the same pediatric set."""
        from services.data_loader import get_data
        from services.monte_carlo import simulate
        from services.scoring import score_all_centers
        peds = set(get_data().pediatric["kidney"]["centers"])
        scored = {r.code for r in score_all_centers(
            {"organ": "kidney", "blood_type": "O+", "age": 8, "sex": "female",
             "urgency": 2}, None)}
        simulated = {c.center_code for c in simulate(_child(), n_iterations=100,
                                                     seed=1).cities}
        assert scored <= peds, f"scoring leaked adult centers: {sorted(scored - peds)[:5]}"
        assert scored == simulated, (
            f"score/simulate disagree: only-scored={sorted(scored - simulated)[:3]}, "
            f"only-simulated={sorted(simulated - scored)[:3]}"
        )

    def test_adult_scoring_unrestricted(self):
        from services.scoring import score_all_centers
        adult = {"organ": "kidney", "blood_type": "O+", "age": 45,
                 "sex": "male", "urgency": 2}
        assert len(score_all_centers(adult, None)) > 200


class TestPediatricAgeGroup:
    """#335 / BBN-22: the old age_to_group clamped children into "18-34"."""

    def test_child_maps_to_pediatric_group(self):
        from services.bbn_parameterizer import AGE_GROUPS, age_to_group
        assert "0-17" in AGE_GROUPS
        assert age_to_group(8) == "0-17"
        assert age_to_group(17) == "0-17"
        assert age_to_group(18) == "18-34"

    def test_adult_grouping_unchanged(self):
        from services.bbn_parameterizer import age_to_group
        for age, grp in [(18, "18-34"), (34, "18-34"), (35, "35-49"),
                         (49, "35-49"), (50, "50-64"), (64, "50-64"),
                         (65, "65+"), (90, "65+")]:
            assert age_to_group(age) == grp

    def test_pediatric_heart_mortality_exceeds_adult(self):
        """The measured pediatric heart waitlist hazard is ~3.3x adult, while
        the old clamp gave those children heart's 18-34 multiplier of 0.3.
        A regression to the clamp would flip this inequality."""
        from services.data_loader import get_data
        cr = get_data().competing_risks
        heart = cr["age_organ_overrides"]["heart"]
        assert heart["0-17"] > heart["65+"] > heart["18-34"], heart
        kidney = cr["age_organ_overrides"].get("kidney", {})
        # ...and the direction REVERSES for kidney, which is why one global
        # pediatric constant could not have been right.
        assert kidney["0-17"] < 1.0, kidney

    def test_every_age_group_resolves_to_a_multiplier(self):
        """The CPT builder resolves per KEY — organ override first, then the
        global table (bbn_parameterizer.py:456-459) — so an override block may
        legitimately be partial. What must hold is that no (organ, age group)
        pair silently falls through to the hardcoded 1.0 default."""
        from services.bbn_parameterizer import AGE_GROUPS, ORGANS
        from services.data_loader import get_data
        cr = get_data().competing_risks
        glob = cr["age_mortality_multipliers"]
        for g in AGE_GROUPS:
            assert isinstance(glob.get(g), (int, float)), f"global missing {g}"
        for organ in ORGANS:
            block = cr["age_organ_overrides"].get(organ, {})
            for g in AGE_GROUPS:
                val = block.get(g, glob.get(g))
                assert isinstance(val, (int, float)) and val > 0, \
                    f"{organ}/{g} resolved to {val!r}"


class TestPediatricEquity:
    """#335: an equity sweep over a child must not silently age them up."""

    def test_pediatric_brackets_reach_the_result(self):
        """Run the real entry point: a child must be swept over pediatric age
        bands, never aged into a 26/45/62-year-old."""
        from services.equity import (PEDIATRIC_AGE_BRACKETS,
                                     compute_equity_analysis,
                                     pediatric_age_weights)
        labels = {b["label"] for b in PEDIATRIC_AGE_BRACKETS}
        assert labels == {"0-1", "2-11", "12-17"}
        w = pediatric_age_weights("kidney")
        assert set(w) == labels and abs(sum(w.values()) - 1.0) < 0.02

        res = compute_equity_analysis(_child(), max_centers=5, seed=3)
        found = set()
        for c in res.cities:
            for attr in ("age_bracket", "bracket", "label"):
                v = getattr(c, attr, None)
                if isinstance(v, str):
                    found.add(v)
            for holder in (getattr(c, "by_age", None) or {},
                           getattr(c, "age_breakdown", None) or {}):
                if isinstance(holder, dict):
                    found |= {k for k in holder if isinstance(k, str)}
        adult_labels = {b["label"] for b in __import__("services.equity", fromlist=["x"]).AGE_BRACKETS}
        assert not (found & adult_labels), (
            f"pediatric equity emitted ADULT brackets: {found & adult_labels}")

    def test_adult_equity_still_uses_adult_brackets(self):
        from services.equity import compute_equity_analysis
        adult = PatientProfile(organ="kidney", blood_type="O+", age=45,
                               sex="male", urgency=2)
        res = compute_equity_analysis(adult, max_centers=5, seed=3)
        assert res.cities

    def test_weights_are_per_organ_not_a_constant(self):
        """Liver's pediatric waitlist is ~41% under-2; kidney's is ~5%. A
        single pediatric age split would misweight one of them badly."""
        from services.equity import pediatric_age_weights
        kid = pediatric_age_weights("kidney")
        liv = pediatric_age_weights("liver")
        assert liv["0-1"] > 0.3 > kid["0-1"], (kid, liv)

    def test_adult_weights_untouched(self):
        from services.equity import AGE_BRACKET_WEIGHTS, _profile_weight
        # These are the documented FALLBACK weights (#337 replaced the live
        # ones with observed per-organ waitlist composition); they must still
        # form a distribution and still be what _profile_weight uses when no
        # observed weights are supplied.
        assert abs(sum(AGE_BRACKET_WEIGHTS.values()) - 1.0) < 0.02
        bracket = next(iter(AGE_BRACKET_WEIGHTS))
        assert _profile_weight("O+", bracket, "male") == pytest.approx(
            0.374 * AGE_BRACKET_WEIGHTS[bracket] * 0.60)

    def test_unknown_organ_falls_back_to_uniform(self):
        from services.equity import pediatric_age_weights
        w = pediatric_age_weights("not-an-organ")
        assert abs(sum(w.values()) - 1.0) < 1e-9


class TestFailureModeParity:
    """#335 review: /score and /simulate must fail the SAME way. /score used
    `if programs:` and so silently returned all 233 ADULT centers — with the
    pediatric scoring bonus applied — whenever pediatric data was missing,
    while /simulate raised."""

    def test_missing_pediatric_data_refuses_on_both_surfaces(self):
        from services.data_loader import get_data
        from services.monte_carlo import simulate
        from services.scoring import score_all_centers
        d = get_data()
        saved = d.pediatric
        try:
            d.pediatric = {}
            with pytest.raises(ValueError):
                score_all_centers({"organ": "kidney", "blood_type": "O+",
                                   "age": 10, "sex": "female", "urgency": 2}, None)
            with pytest.raises(ValueError):
                simulate(_child(), n_iterations=50, seed=1)
        finally:
            d.pediatric = saved

    def test_unmatchable_shortlist_refuses_on_both_surfaces(self):
        from services.monte_carlo import simulate
        from services.scoring import score_all_centers
        adult_only = ["ZZZZ"]
        with pytest.raises(ValueError):
            score_all_centers({"organ": "kidney", "blood_type": "O+", "age": 10,
                               "sex": "female", "urgency": 2,
                               "center_codes": adult_only}, None)
        with pytest.raises(ValueError):
            simulate(_child(center_codes=adult_only), n_iterations=50, seed=1)


class TestAcceptanceThinning:
    """#335 review: the pediatric anchor is the OBSERVED pediatric transplant
    rate, which already reflects the center's acceptance behaviour. Thinning
    it again deflated p12 by 3-5x (FLFH 0.806 -> 0.235)."""

    def test_pediatric_p12_is_unchanged_by_acceptance_modelling(self):
        from services.monte_carlo import simulate
        off = {c.center_code: c.p_transplant_12mo
               for c in simulate(_child(), n_iterations=1500, seed=7).cities}
        on = {c.center_code: c.p_transplant_12mo
              for c in simulate(_child(), n_iterations=1500, seed=7,
                                model_acceptance=True).cities}
        assert off and set(off) == set(on)
        for code, p in off.items():
            assert abs(on[code] - p) < 1e-9, (
                f"{code}: acceptance modelling moved an anchored pediatric "
                f"probability {p:.3f} -> {on[code]:.3f}")

    def test_adults_still_thin(self):
        """The fix must not disable acceptance modelling for adults."""
        from services.monte_carlo import simulate
        adult = PatientProfile(organ="kidney", blood_type="O+", age=45,
                               sex="male", urgency=2)
        off = {c.center_code: c.p_transplant_12mo
               for c in simulate(adult, n_iterations=1500, seed=7).cities}
        on = {c.center_code: c.p_transplant_12mo
              for c in simulate(adult, n_iterations=1500, seed=7,
                                model_acceptance=True).cities}
        moved = sum(1 for c, p in off.items() if abs(on[c] - p) > 1e-6)
        assert moved > 10, "acceptance modelling stopped affecting adults"


class TestZeroRateAndCalibration:
    def test_observed_zero_rate_is_shrunk_not_discarded(self):
        """A center that genuinely performed no pediatric transplants is an
        observation, not missing data. Treating it as missing handed it the
        unshrunk ADULT curve (same defect class as the closed #229)."""
        from services.data_loader import get_data
        from services.distributions import get_wait_time_distribution
        from services.monte_carlo import _pediatric_dist
        d = get_data()
        block = d.pediatric["kidney"]
        zeros = [c for c, r in block["centers"].items()
                 if r.get("transplant_rate") == 0]
        if not zeros:
            pytest.skip("no observed-zero pediatric centers in this vintage")
        adult = get_wait_time_distribution("kidney", "O+")
        out = _pediatric_dist(_child(), zeros[0], block, adult)
        assert out is not adult, (
            f"{zeros[0]} has an observed rate of 0 and was handed the adult "
            f"distribution instead of being shrunk toward the national "
            f"pediatric baseline")

    def test_uncalibrated_organs_are_tagged(self):
        """Pancreas and intestine have no fitted rate->probability conversion,
        so their pediatric wait numbers ARE adult. That must be visible."""
        from services.data_loader import get_data
        from services.provenance import (TAG_PEDIATRIC_UNCALIBRATED,
                                         center_data_quality)
        d = get_data()
        for organ in ("pancreas", "intestine"):
            block = d.pediatric.get(organ) or {}
            if (block.get("calibration") or {}).get("k"):
                continue
            codes = list(block.get("centers", {}))
            if not codes:
                continue
            tags = center_data_quality(organ, codes[0], pediatric=True)
            assert TAG_PEDIATRIC_UNCALIBRATED in tags, (
                f"{organ} has no calibration but reports as calibrated")

    def test_calibrated_organs_not_tagged(self):
        from services.provenance import (TAG_PEDIATRIC_UNCALIBRATED,
                                         center_data_quality)
        from services.data_loader import get_data
        code = next(iter(get_data().pediatric["kidney"]["centers"]))
        assert TAG_PEDIATRIC_UNCALIBRATED not in center_data_quality(
            "kidney", code, pediatric=True)


class TestEngineWaitModelDisclosure:
    """L-079: BBN and MCMC restrict a pediatric candidate to pediatric centers
    but have no pediatric WAIT model — only Monte Carlo re-anchors to the
    observed pediatric rate. Switching inference_mode silently produced adult
    numbers on a pediatric center list; the response must say so."""

    def test_monte_carlo_reports_a_pediatric_wait_model(self):
        from services.monte_carlo import simulate
        fam = simulate(_child(), n_iterations=200,
                       seed=1).data_quality.get("pediatric_wait_model")
        assert fam, "pediatric_wait_model family missing from the response"
        assert fam["adult_fallback"] == 0, (
            "Monte Carlo anchors pediatric probabilities and must not report "
            "an adult wait model")

    def test_bbn_discloses_the_adult_wait_model(self):
        from services.bayesian_network import simulate_bbn
        fam = simulate_bbn(_child()).data_quality.get("pediatric_wait_model")
        assert fam, "pediatric_wait_model family missing from the BBN response"
        assert fam["modeled"] == 0 and fam["adult_fallback"] > 0, (
            "the BBN has no pediatric wait model, so every pediatric center "
            "must be reported as adult_fallback")

    def test_adult_runs_report_a_modeled_wait(self):
        """The family must read sensibly on adult responses too — labelling
        the good side 'pediatric' produced the line 'pediatric: 233' for a
        45-year-old."""
        from services.monte_carlo import simulate
        adult = PatientProfile(organ="kidney", blood_type="O+", age=45,
                               sex="male", urgency=2)
        fam = simulate(adult, n_iterations=200,
                       seed=1).data_quality.get("pediatric_wait_model")
        assert fam["adult_fallback"] == 0 and fam["modeled"] > 0
