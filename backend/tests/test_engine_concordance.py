"""Cross-engine concordance regression gates (#314).

The three inference engines share inputs and should rank centers nearly
identically. A change that silently decouples one engine from the shared
center-level data (e.g. the MCMC region-mapping bug and the BBN provenance
drop caught in the 2026-08 review) shows up as a concordance collapse long
before anyone eyeballs a ranking.

Floors are set ~0.05-0.08 below the values measured on 2026-08-25
(kidney 0.995, liver 0.964, heart 0.936, lung 0.868 at 1500 iterations,
seed 42) — generous enough for MC noise and data refreshes, tight enough
that an engine riding the wrong data fails loudly.
"""
import pytest
from scipy.stats import spearmanr

from models.schemas import PatientProfile
from services.bayesian_network import simulate_bbn
from services.monte_carlo import simulate

# (organ, floor) — lung has the fewest centers, hence the loosest floor.
FLOORS = [
    ("kidney", 0.93),
    ("liver", 0.90),
    ("heart", 0.86),
    ("lung", 0.78),
]


@pytest.fixture(autouse=True)
def _load(data):
    pass


def _p24_maps(organ: str):
    p = PatientProfile(organ=organ, blood_type="O+", age=45, sex="male",
                       urgency=2, bbn_granularity="full")
    mc = simulate(p, n_iterations=1500, seed=42)
    bbn = simulate_bbn(p)
    mc_map = {c.center_code: c.p_transplant_24mo for c in mc.cities}
    bbn_map = {c.center_code: c.p_transplant_24mo for c in bbn.cities}
    return mc_map, bbn_map


class TestMcBbnConcordance:
    @pytest.mark.parametrize("organ,floor", FLOORS)
    def test_rank_concordance_floor(self, organ, floor):
        mc_map, bbn_map = _p24_maps(organ)
        common = sorted(set(mc_map) & set(bbn_map))
        assert len(common) > 50, (
            f"{organ}: engines share only {len(common)} centers — one engine "
            f"is dropping most of the population"
        )
        rho = spearmanr([mc_map[c] for c in common],
                        [bbn_map[c] for c in common]).statistic
        assert rho >= floor, (
            f"{organ}: MC-vs-BBN Spearman {rho:.3f} fell below the {floor} "
            f"floor (measured 2026-08-25 baseline was higher) — an engine has "
            f"likely decoupled from the shared center-level inputs"
        )

    def test_center_populations_agree(self):
        """Both engines must serve (nearly) the same center set."""
        mc_map, bbn_map = _p24_maps("kidney")
        only_mc = set(mc_map) - set(bbn_map)
        only_bbn = set(bbn_map) - set(mc_map)
        assert len(only_mc) < 10 and len(only_bbn) < 10, (
            f"center populations diverge: {len(only_mc)} MC-only, "
            f"{len(only_bbn)} BBN-only"
        )
