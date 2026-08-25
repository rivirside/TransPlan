"""Regression tests for #306 — age/sex wait multipliers must reach every engine.

The #294 assumption sweep found the age/sex knob had exactly zero effect:
monte_carlo.simulate, what_if._run_single, and the Brier analytical benchmark
never passed age/sex to get_wait_time_distribution, so the OPTN-derived
demographic multipliers (#48) were silently dead outside sensitivity/equity.
"""
import pytest

from models.schemas import PatientProfile
from services.monte_carlo import simulate
from services.what_if import compute_what_if
from services.brier_score import _analytical_p_transplant_12mo


@pytest.fixture(autouse=True)
def _load(data):
    pass


def _kidney(age):
    return PatientProfile(organ="kidney", blood_type="O+", age=age, sex="male",
                          urgency=2, cpra=20)


class TestMonteCarloAgeSex:
    def test_older_patient_waits_longer(self):
        """age >= 55 carries a 1.10 wait multiplier vs 0.95 for age < 35, so
        at the same seed the older patient's median wait must be longer at
        (essentially) every center."""
        young = simulate(_kidney(26), n_iterations=500, seed=42)
        old = simulate(_kidney(62), n_iterations=500, seed=42)
        young_by = {c.center_code: c for c in young.cities}
        longer = equal = 0
        for c in old.cities:
            y = young_by.get(c.center_code)
            if y is None:
                continue
            if c.median_wait_months > y.median_wait_months:
                longer += 1
            elif c.median_wait_months == y.median_wait_months:
                equal += 1
        assert equal == 0, f"{equal} centers identical — age is not reaching the engine"
        assert longer > 0.95 * len(old.cities)

    def test_male_kidney_waits_longer_than_female(self):
        male = simulate(_kidney(45), n_iterations=500, seed=42)
        female_patient = PatientProfile(organ="kidney", blood_type="O+", age=45,
                                        sex="female", urgency=2, cpra=20)
        female = simulate(female_patient, n_iterations=500, seed=42)
        m = {c.center_code: c.median_wait_months for c in male.cities}
        f = {c.center_code: c.median_wait_months for c in female.cities}
        common = set(m) & set(f)
        assert sum(m[c] > f[c] for c in common) > 0.95 * len(common)


class TestWhatIfAgeSex:
    def test_age_changes_result(self):
        young = compute_what_if(_kidney(26), center_code="ALCH", n_iterations=400, seed=7)
        old = compute_what_if(_kidney(62), center_code="ALCH", n_iterations=400, seed=7)
        assert old.baseline_median_wait > young.baseline_median_wait


class TestBrierAnalyticalAgeSex:
    def test_age_changes_analytical_p12(self):
        p_young = _analytical_p_transplant_12mo("kidney", "O+", "x", cpra=20,
                                                center_code="ALCH", age=26, sex="male")
        p_old = _analytical_p_transplant_12mo("kidney", "O+", "x", cpra=20,
                                              center_code="ALCH", age=62, sex="male")
        assert p_young > p_old
