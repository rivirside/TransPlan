"""Dual CAS/LAS lung input support (#303, option 1).

OPTN replaced LAS with the Composite Allocation Score on 2023-03-09. The
multiplier tables are LAS-era, so a CAS input is mapped to an effective LAS
by quantile-matching the at-transplant score distributions published in the
OPTN/SRTR 2023 Annual Data Report (Table LU 7): CAS 29 ~ LAS 35 (~21st
percentile of transplanted candidates), CAS 31 ~ LAS 43 (~51st),
CAS 36 ~ LAS 60 (~77th).
"""
import pytest

from models.schemas import PatientProfile
from services.distributions import cas_to_effective_las


@pytest.fixture(autouse=True)
def _load(data):
    pass


class TestCasMapping:
    def test_anchor_points(self):
        """Quantile anchors from SRTR ADR 2023 Table LU 7."""
        assert cas_to_effective_las(29.0) == pytest.approx(35.0)
        assert cas_to_effective_las(31.0) == pytest.approx(43.0)
        assert cas_to_effective_las(36.0) == pytest.approx(60.0)

    def test_monotone_increasing(self):
        prev = -1.0
        for cas10 in range(0, 1001, 5):
            las = cas_to_effective_las(cas10 / 10.0)
            assert las >= prev, f"mapping not monotone at CAS {cas10/10.0}"
            prev = las

    def test_clamped_to_las_range(self):
        assert 0.0 <= cas_to_effective_las(0.0)
        assert cas_to_effective_las(100.0) <= 100.0

    def test_typical_waitlist_cas_maps_to_moderate_las(self):
        """Most waiting candidates sit in the high-20s CAS — that must not
        map into the urgent LAS bands (>=50)."""
        assert cas_to_effective_las(27.0) < 50.0


class TestPatientProfileCas:
    def test_cas_derives_effective_las(self):
        p = PatientProfile(organ="lung", blood_type="O+", age=55, sex="male",
                           urgency=2, cas=31.0)
        assert p.cas == 31.0
        assert p.las == pytest.approx(43.0)

    def test_explicit_las_wins_over_cas(self):
        """An explicit legacy LAS is used directly — the mapping only fills
        the gap when no LAS is given."""
        p = PatientProfile(organ="lung", blood_type="O+", age=55, sex="male",
                           urgency=2, cas=31.0, las=70.0)
        assert p.las == 70.0

    def test_no_scores_stays_none(self):
        p = PatientProfile(organ="lung", blood_type="O+", age=55, sex="male",
                           urgency=2)
        assert p.las is None and p.cas is None


class TestCasEndToEnd:
    def test_higher_cas_means_faster_transplant(self):
        """Higher CAS = more urgent = lower wait multiplier = higher p24,
        matching the LAS-band semantics."""
        from services.distributions import get_wait_time_params
        _, m_low = get_wait_time_params("lung", "O+", las=cas_to_effective_las(27.0))
        _, m_high = get_wait_time_params("lung", "O+", las=cas_to_effective_las(40.0))
        assert m_high < m_low

    def test_simulate_accepts_cas(self):
        from services.monte_carlo import simulate
        p = PatientProfile(organ="lung", blood_type="O+", age=55, sex="male",
                           urgency=2, cas=36.0)
        result = simulate(p, n_iterations=100, seed=5)
        assert result.cities
        assert result.patient.cas == 36.0


class TestPediatricGate:
    """#335 phase 1 REJECTED sub-18 inputs rather than mis-model them. Phase 2
    replaced that gate with real pediatric support, so the contract is now
    that children are accepted and routed to the pediatric path — see
    tests/test_pediatric_mode.py. What must still hold here is that the
    boundary is exact and that impossible ages are refused."""

    def test_pediatric_age_accepted(self):
        p = PatientProfile(organ="kidney", blood_type="O+", age=12, sex="male",
                           urgency=2)
        assert p.age == 12 and p.is_pediatric

    def test_age_below_one_rejected(self):
        with pytest.raises(Exception) as exc:
            PatientProfile(organ="kidney", blood_type="O+", age=0, sex="male",
                           urgency=2)
        assert "age" in str(exc.value)

    def test_adult_boundary_accepted(self):
        p = PatientProfile(organ="kidney", blood_type="O+", age=18, sex="male",
                           urgency=2)
        assert p.age == 18
