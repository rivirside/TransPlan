"""
Tests for the BBN CPT parameterizer (Phase 5 M1, Issue #37).

Validates:
  - All CPTs build without error
  - Shapes match DAG cardinalities
  - All columns sum to 1.0 (proper probability distributions)
  - Tercile logic produces expected discrete mappings
  - Data-derived values respond to known data patterns
  - Edge cases: missing data, boundary conditions
"""
import numpy as np
import pytest

from services.bbn_parameterizer import (
    AGE_GROUPS,
    BLOOD_TYPES,
    COMPETING_OUTCOME_STATES,
    COMPOUND_SUCCESS_STATES,
    DELISTING_RISK_STATES,
    DONOR_SUPPLY_STATES,
    GRAFT_SURVIVAL_STATES,
    MORTALITY_RISK_STATES,
    ORGANS,
    REGIONS,
    URGENCY_LEVELS,
    WAIT_CATEGORY_STATES,
    age_to_group,
    build_all_cpts,
    build_competing_outcome_cpt,
    build_compound_success_cpt,
    build_delisting_risk_cpt,
    build_donor_supply_cpt,
    build_graft_survival_cpt,
    build_mortality_risk_cpt,
    build_wait_category_cpt,
    get_center_to_region_map,
    get_regions,
    _normalize,
)
from services.data_loader import get_data, load_all

# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True, scope="module")
def _ensure_data_loaded():
    """Load data once for the entire test module."""
    try:
        get_data()
    except RuntimeError:
        load_all()


# ──────────────────────────────────────────────────────────────────────
# Enumeration sanity
# ──────────────────────────────────────────────────────────────────────


def test_enumerations_correct_sizes():
    assert len(ORGANS) == 6
    assert len(BLOOD_TYPES) == 8
    assert len(AGE_GROUPS) == 4
    assert len(URGENCY_LEVELS) == 4
    assert len(REGIONS) >= 22  # Classic set has 22; may grow


def test_discrete_states_nonempty():
    for states in [
        DONOR_SUPPLY_STATES, WAIT_CATEGORY_STATES,
        MORTALITY_RISK_STATES, DELISTING_RISK_STATES,
        COMPETING_OUTCOME_STATES, GRAFT_SURVIVAL_STATES,
        COMPOUND_SUCCESS_STATES,
    ]:
        assert len(states) >= 2


# ──────────────────────────────────────────────────────────────────────
# CPT shapes
# ──────────────────────────────────────────────────────────────────────


def test_donor_supply_cpt_shape():
    n = len(REGIONS)
    cpt = build_donor_supply_cpt()
    assert cpt.shape == (3, 6, 8, n)


def test_wait_category_cpt_shape():
    n = len(REGIONS)
    cpt = build_wait_category_cpt()
    assert cpt.shape == (4, 6, 8, n, 3)


def test_mortality_risk_cpt_shape():
    n = len(REGIONS)
    cpt = build_mortality_risk_cpt()
    assert cpt.shape == (3, 6, 4, 4, n)


def test_delisting_risk_cpt_shape():
    n = len(REGIONS)
    cpt = build_delisting_risk_cpt()
    assert cpt.shape == (3, 6, n, 4)


def test_competing_outcome_cpt_shape():
    # #211: CompetingOutcome is now (4, n_organs, n_regions) — grounded in
    # observed per-(organ, center) rates, not the old (4,4,3,3) latent CPT.
    n = len(REGIONS)
    cpt = build_competing_outcome_cpt()
    assert cpt.shape == (4, 6, n)


def test_graft_survival_cpt_shape():
    cpt = build_graft_survival_cpt()
    assert cpt.shape == (3, 6, 22)


def test_graft_survival_hr_ci_significance():
    """#214: graft class comes from the HR 95% CI vs national (HR=1), not the
    old arbitrary 0.8/1.2 cutoffs — CI entirely below 1 → good, above 1 → poor."""
    import numpy as np
    from services.bbn_parameterizer import (
        build_graft_survival_cpt, get_regions, get_center_to_region_map,
        _center_graft_hr_ci, ORGANS,
    )
    g = "full"
    regions = get_regions(g)
    cmap = get_center_to_region_map(g)
    cpt = build_graft_survival_cpt(regions=regions, n_regions=len(regions),
                                   center_map=cmap, granularity=g)
    assert np.allclose(cpt.sum(axis=0), 1.0)
    ki = ORGANS.index("kidney")
    checked_good = checked_poor = False
    for idx, rg in enumerate(regions):
        ci = _center_graft_hr_ci("kidney", rg, g)
        if not ci:
            continue
        cls = int(np.argmax(cpt[:, ki, idx]))  # 0=good,1=moderate,2=poor
        if ci[1] < 1.0:
            assert cls == 0, f"{rg}: HR-CI {ci} below 1 should be good, got {cls}"
            checked_good = True
        elif ci[0] > 1.0:
            assert cls == 2, f"{rg}: HR-CI {ci} above 1 should be poor, got {cls}"
            checked_poor = True
    assert checked_good, "expected at least one significantly-better center to verify"


def test_compound_success_cpt_shape():
    cpt = build_compound_success_cpt()
    assert cpt.shape == (3, 4, 3)


# ──────────────────────────────────────────────────────────────────────
# Normalization: all columns must sum to 1.0
# ──────────────────────────────────────────────────────────────────────


def _check_normalization(cpt: np.ndarray, name: str):
    """Assert every column (first axis) sums to ~1.0."""
    sums = cpt.sum(axis=0)
    np.testing.assert_allclose(
        sums, 1.0, atol=1e-6,
        err_msg=f"{name} CPT has columns that don't sum to 1.0"
    )


def test_donor_supply_normalized():
    _check_normalization(build_donor_supply_cpt(), "DonorSupply")


def test_wait_category_normalized():
    _check_normalization(build_wait_category_cpt(), "WaitCategory")


def test_mortality_risk_normalized():
    _check_normalization(build_mortality_risk_cpt(), "MortalityRisk")


def test_delisting_risk_normalized():
    _check_normalization(build_delisting_risk_cpt(), "DelistingRisk")


def test_competing_outcome_normalized():
    _check_normalization(build_competing_outcome_cpt(), "CompetingOutcome")


def test_graft_survival_normalized():
    _check_normalization(build_graft_survival_cpt(), "GraftSurvival1yr")


def test_compound_success_normalized():
    _check_normalization(build_compound_success_cpt(), "CompoundSuccess")


# ──────────────────────────────────────────────────────────────────────
# Non-negativity
# ──────────────────────────────────────────────────────────────────────


def test_all_cpts_nonnegative():
    cpts = build_all_cpts()
    for name, cpt in cpts.items():
        assert np.all(cpt >= 0), f"{name} CPT has negative values"


# ──────────────────────────────────────────────────────────────────────
# Semantic checks: known data patterns
# ──────────────────────────────────────────────────────────────────────


def test_donor_supply_ab_favorable():
    """AB blood type has lowest wait multiplier → should tend toward higher supply."""
    cpt = build_donor_supply_cpt()
    # AB+ is index 6 in BLOOD_TYPES
    ab_plus_idx = BLOOD_TYPES.index("AB+")
    o_plus_idx = BLOOD_TYPES.index("O+")

    # Average "high supply" probability across all organs/regions
    ab_high = cpt[2, :, ab_plus_idx, :].mean()
    o_high = cpt[2, :, o_plus_idx, :].mean()

    assert ab_high > o_high, (
        f"AB+ should have higher P(high supply) than O+ but got "
        f"AB+={ab_high:.3f} vs O+={o_high:.3f}"
    )


def test_wait_category_short_organs():
    """Heart/lung have short national medians → more P(short wait)."""
    cpt = build_wait_category_cpt()
    heart_idx = ORGANS.index("heart")
    kidney_idx = ORGANS.index("kidney")

    # Average P(short) across blood types, regions, donor supply states
    heart_short = cpt[0, heart_idx, :, :, :].mean()
    kidney_short = cpt[0, kidney_idx, :, :, :].mean()

    assert heart_short > kidney_short, (
        f"Heart should have higher P(short wait) than kidney: "
        f"heart={heart_short:.3f} vs kidney={kidney_short:.3f}"
    )


def test_mortality_risk_urgency_effect():
    """Higher urgency should increase mortality risk."""
    cpt = build_mortality_risk_cpt()
    # urgency=1 is index 0, urgency=4 is index 3
    # P(high mortality) at urgency 4 vs urgency 1, averaged across organs/ages/regions
    high_at_urg4 = cpt[2, :, :, 3, :].mean()
    high_at_urg1 = cpt[2, :, :, 0, :].mean()

    assert high_at_urg4 > high_at_urg1, (
        f"Urgency 4 should have higher mortality risk than urgency 1: "
        f"urg4={high_at_urg4:.3f} vs urg1={high_at_urg1:.3f}"
    )


def test_mortality_risk_age_effect():
    """Older age groups should have higher mortality risk."""
    cpt = build_mortality_risk_cpt()
    # 65+ is index 3, 18-34 is index 0
    high_old = cpt[2, :, 3, :, :].mean()
    high_young = cpt[2, :, 0, :, :].mean()

    assert high_old >= high_young, (
        f"65+ should have higher or equal mortality risk than 18-34: "
        f"old={high_old:.3f} vs young={high_young:.3f}"
    )


def test_competing_outcome_simplex():
    """Every (organ, region) cell is a valid distribution summing to 1 (#211)."""
    import numpy as np
    from services.bbn_parameterizer import get_regions, get_center_to_region_map
    g = "full"
    regions = get_regions(g)
    cmap = get_center_to_region_map(g)
    cpt = build_competing_outcome_cpt(regions=regions, n_regions=len(regions),
                                      center_map=cmap, granularity=g)
    sums = cpt.sum(axis=0)
    assert np.allclose(sums, 1.0), f"CompetingOutcome cells must sum to 1; got [{sums.min()},{sums.max()}]"


def test_competing_outcome_tracks_observed_rates():
    """The transplant component must rank-correlate with the centers' OBSERVED
    transplant rates — the whole point of grounding it empirically (#211)."""
    import numpy as np
    from scipy.stats import spearmanr
    from services.bbn_parameterizer import (
        get_regions, get_center_to_region_map, _observed_vector_12mo, ORGANS,
    )
    g = "full"
    regions = get_regions(g)
    cmap = get_center_to_region_map(g)
    cpt = build_competing_outcome_cpt(regions=regions, n_regions=len(regions),
                                      center_map=cmap, granularity=g)
    oi = ORGANS.index("kidney")
    co_tx = np.asarray(cpt[0, oi, :], float).ravel()
    obs_tx = np.array([_observed_vector_12mo("kidney", r, cmap)[0][0] for r in regions])
    rho = float(np.asarray(spearmanr(co_tx, obs_tx)[0]))
    assert rho > 0.9, f"CompetingOutcome transplant prob should track observed rates; rho={rho:.3f}"


def test_extend_12_to_24_preserves_simplex():
    """The 12→24-month extension keeps the vector on the simplex exactly (#211)."""
    import numpy as np
    from services.bbn_parameterizer import _extend_12_to_24
    for p12 in ([0.5, 0.1, 0.1, 0.3], [0.9, 0.02, 0.03, 0.05], [0.1, 0.2, 0.1, 0.6]):
        p24 = _extend_12_to_24(np.array(p12))
        assert abs(p24.sum() - 1.0) < 1e-9
        # 24-month event probabilities are >= their 12-month values (more time).
        assert all(p24[i] >= p12[i] - 1e-9 for i in range(3))
        assert p24[3] <= p12[3] + 1e-9  # less still-waiting at 24mo


def test_compound_success_mortality_is_failure():
    """If CompetingOutcome=mortality, CompoundSuccess should be ~failure."""
    cpt = build_compound_success_cpt()
    # CompetingOutcome=mortality(1), any GraftSurvival
    for gs in range(3):
        p_failure = cpt[2, 1, gs]  # failure state
        assert p_failure > 0.8, (
            f"Mortality outcome should map to ~failure but got P(failure)={p_failure:.3f}"
        )


def test_compound_success_transplant_good_graft():
    """Transplant + good graft → high P(success)."""
    cpt = build_compound_success_cpt()
    # CompetingOutcome=transplant(0), GraftSurvival=good(0)
    p_success = cpt[0, 0, 0]
    assert p_success > 0.7, f"Expected high success prob, got {p_success:.3f}"


# ──────────────────────────────────────────────────────────────────────
# build_all_cpts
# ──────────────────────────────────────────────────────────────────────


def test_build_all_returns_12_cpts():
    cpts = build_all_cpts()
    assert len(cpts) == 12


def test_build_all_keys():
    cpts = build_all_cpts()
    expected = {
        "Organ", "BloodType", "AgeGroup", "Urgency", "Region",
        "DonorSupply", "WaitCategory", "MortalityRisk", "DelistingRisk",
        "CompetingOutcome", "GraftSurvival1yr", "CompoundSuccess",
    }
    assert set(cpts.keys()) == expected


# ──────────────────────────────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────────────────────────────


def test_normalize_basic():
    arr = np.array([1.0, 2.0, 3.0])
    result = _normalize(arr)
    np.testing.assert_allclose(result, [1/6, 2/6, 3/6])


def test_normalize_zeros():
    """All-zero input should return uniform distribution."""
    arr = np.array([0.0, 0.0, 0.0])
    result = _normalize(arr)
    np.testing.assert_allclose(result, [1/3, 1/3, 1/3])


def test_age_to_group_boundaries():
    assert age_to_group(17) == "18-34"
    assert age_to_group(18) == "18-34"
    assert age_to_group(34) == "18-34"
    assert age_to_group(35) == "35-49"
    assert age_to_group(49) == "35-49"
    assert age_to_group(50) == "50-64"
    assert age_to_group(64) == "50-64"
    assert age_to_group(65) == "65+"
    assert age_to_group(99) == "65+"


# ──────────────────────────────────────────────────────────────────────
# Dynamic granularity: get_regions / get_center_to_region_map
# ──────────────────────────────────────────────────────────────────────


def test_get_regions_classic_returns_22():
    regions = get_regions("classic")
    assert len(regions) == 22
    assert "Pittsburgh" in regions


def test_get_regions_state_returns_states():
    regions = get_regions("state")
    assert len(regions) >= 40
    assert len(regions) <= 55


def test_get_regions_full_returns_all_centers():
    regions = get_regions("full")
    assert len(regions) >= 200


def test_get_center_to_region_map_state():
    mapping = get_center_to_region_map("state")
    regions = get_regions("state")
    assert all(v in regions for v in mapping.values())


def test_get_center_to_region_map_full():
    mapping = get_center_to_region_map("full")
    for code, region in mapping.items():
        assert code == region


# ──────────────────────────────────────────────────────────────────────
# Dynamic granularity: build_all_cpts with different modes
# ──────────────────────────────────────────────────────────────────────


def test_build_all_cpts_classic_region_shape():
    cpts = build_all_cpts(granularity="classic")
    # Region prior should have 22 values
    region_cpt = cpts["Region"]
    assert region_cpt.shape[0] == 22


def test_build_all_cpts_state_region_shape():
    cpts = build_all_cpts(granularity="state")
    regions = get_regions("state")
    region_cpt = cpts["Region"]
    assert region_cpt.shape[0] == len(regions)


def test_donor_supply_normalized_state():
    cpts = build_all_cpts(granularity="state")
    ds = cpts["DonorSupply"]
    # Check normalization on first few slices
    for i in range(min(3, ds.shape[1])):
        for j in range(min(3, ds.shape[2])):
            for k in range(min(3, ds.shape[3])):
                total = ds[:, i, j, k].sum()
                assert abs(total - 1.0) < 1e-5, f"Not normalized at [{i},{j},{k}]: {total}"


def test_build_all_cpts_state_all_normalized():
    """All CPTs in state mode must have columns summing to 1."""
    cpts = build_all_cpts(granularity="state")
    for name, cpt in cpts.items():
        sums = cpt.sum(axis=0)
        np.testing.assert_allclose(
            sums, 1.0, atol=1e-5,
            err_msg=f"{name} CPT (state mode) has columns not summing to 1.0"
        )


def test_build_all_cpts_state_nonnegative():
    """All CPTs in state mode must be non-negative."""
    cpts = build_all_cpts(granularity="state")
    for name, cpt in cpts.items():
        assert np.all(cpt >= 0), f"{name} CPT (state mode) has negative values"
