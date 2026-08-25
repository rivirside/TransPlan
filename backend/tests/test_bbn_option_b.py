"""BBN option B: patient-specific competing-risk modulation (#238 / L-072).

The hybrid combination previously applied the center's population-average
death/delisting split to every patient. Option B modulates the observed
competing-risk vector on the cause-specific hazard scale by the patient's
age / urgency / MELD mortality multipliers, with:
  - a reference anchor: a reference patient (age 50-64, urgency 2, MELD
    15-25) reduces EXACTLY to the center's observed vector, and
  - a double-counting guard: the transplant hazard is never modulated
    (WaitCategory already carries the patient's wait signal).

Also covers the revival of the age_mortality_multipliers data block, which
the #104 rewrite silently deleted (BBN age edge + MCMC inference age
modulation were dead until 2026-08-25).
"""
import pytest

from models.schemas import PatientProfile
from services.competing_risks import get_patient_mortality_multiplier


@pytest.fixture(autouse=True)
def _load(data):
    pass


class TestAgeMultiplierRevival:
    def test_age_blocks_present_in_data(self):
        from services.data_loader import DATA_DIR
        import json
        d = json.load(open(DATA_DIR / "competing-risks.json"))
        assert "age_mortality_multipliers" in d
        assert "age_organ_overrides" in d

    def test_elderly_multiplier_above_one(self):
        assert get_patient_mortality_multiplier("kidney", age=70, urgency=2) > 1.0

    def test_young_multiplier_below_one(self):
        assert get_patient_mortality_multiplier("kidney", age=25, urgency=2) < 1.0

    def test_reference_patient_is_exactly_one(self):
        assert get_patient_mortality_multiplier("kidney", age=55, urgency=2) == 1.0
        assert get_patient_mortality_multiplier("liver", age=55, urgency=2,
                                                meld=20) == 1.0

    def test_heart_age_sensitivity_stronger(self):
        """The organ overrides encode heart's steeper age gradient."""
        heart = get_patient_mortality_multiplier("heart", age=70, urgency=2)
        kidney = get_patient_mortality_multiplier("kidney", age=70, urgency=2)
        assert heart > kidney

    def test_mcmc_inference_age_no_longer_dead(self):
        """mcmc_inference read a key the data file lost — it must resolve a
        real multiplier again."""
        import json
        from services.mcmc_inference import _get_age_bracket
        from services.data_loader import DATA_DIR
        cr = json.load(open(DATA_DIR / "competing-risks.json"))
        mult = cr["age_mortality_multipliers"].get(_get_age_bracket(70))
        assert isinstance(mult, (int, float)) and mult > 1.0


class TestOptionBModulation:
    def _oc(self, **patient_kwargs):
        from services.bayesian_network import _combine_outcomes, _query_city, build_model
        from services.bbn_parameterizer import get_regions
        from services.bayesian_network import _build_state_names
        # Query one real region once; modulate with different multipliers
        model = build_model("state")
        regions = get_regions("state")
        names = _build_state_names(regions)
        qr = _query_city(model, "kidney", "O+", "50-64", "2", regions[0],
                         regions=regions, node_state_names=names)
        m = get_patient_mortality_multiplier("kidney", **patient_kwargs)
        return _combine_outcomes(qr, mortality_modulation=m)

    def test_reference_anchor_exact(self):
        """m == 1.0 must reproduce the unmodulated result bit-for-bit."""
        base = self._oc(age=55, urgency=2)
        anchored = self._oc(age=55, urgency=2)
        assert base == anchored
        from services.bayesian_network import _combine_outcomes, build_model, _query_city, _build_state_names
        from services.bbn_parameterizer import get_regions
        model = build_model("state")
        regions = get_regions("state")
        names = _build_state_names(regions)
        qr = _query_city(model, "kidney", "O+", "50-64", "2", regions[0],
                         regions=regions, node_state_names=names)
        assert _combine_outcomes(qr) == _combine_outcomes(qr, mortality_modulation=1.0)

    def test_older_patient_more_mortality_less_transplant(self):
        ref = self._oc(age=55, urgency=2)
        old = self._oc(age=75, urgency=2)
        assert old["p_mortality_24"] > ref["p_mortality_24"]
        assert old["p_24"] <= ref["p_24"]

    def test_urgency_monotone(self):
        low = self._oc(age=55, urgency=1)
        high = self._oc(age=55, urgency=4)
        assert high["p_mortality_24"] > low["p_mortality_24"]

    def test_probabilities_still_sum_to_one(self):
        for kwargs in ({"age": 25, "urgency": 1}, {"age": 75, "urgency": 4}):
            oc = self._oc(**kwargs)
            total = oc["p_24"] + oc["p_mortality_24"] + oc["p_delisting_24"] + oc["p_waiting_24"]
            assert total == pytest.approx(1.0, abs=1e-9)


class TestOptionBEndToEnd:
    def test_bbn_age_direction_matches_mc(self):
        """With option B, the BBN's age response must at least share MC's
        direction: older -> lower p24 at matched centers."""
        from services.bayesian_network import simulate_bbn
        young = PatientProfile(organ="kidney", blood_type="O+", age=30,
                               sex="male", urgency=2, bbn_granularity="state")
        old = PatientProfile(organ="kidney", blood_type="O+", age=75,
                             sex="male", urgency=2, bbn_granularity="state")
        ry = simulate_bbn(young)
        ro = simulate_bbn(old)
        y = {c.center_code: c.p_transplant_24mo for c in ry.cities}
        o = {c.center_code: c.p_transplant_24mo for c in ro.cities}
        common = set(y) & set(o)
        worse = sum(1 for c in common if o[c] <= y[c])
        assert worse > 0.9 * len(common), (
            f"older patient not worse at {len(common)-worse}/{len(common)} centers"
        )

    def test_mortality_share_rises_with_age(self):
        from services.bayesian_network import simulate_bbn
        young = PatientProfile(organ="kidney", blood_type="O+", age=30,
                               sex="male", urgency=2, bbn_granularity="state")
        old = PatientProfile(organ="kidney", blood_type="O+", age=75,
                             sex="male", urgency=2, bbn_granularity="state")
        cy = {c.center_code: c.competing_risks for c in simulate_bbn(young).cities}
        co = {c.center_code: c.competing_risks for c in simulate_bbn(old).cities}
        common = [c for c in cy if c in co and cy[c] and co[c]]
        assert common
        higher = sum(1 for c in common
                     if co[c]["p_mortality_24mo"] >= cy[c]["p_mortality_24mo"])
        assert higher > 0.9 * len(common)
