"""Tests for Travel Financial Assistance policy scenarios (#141).

Ported from the retired 22-city machinery to the per-center BEA RPP path
(#285 / 2026-08 review): every effect assertion now runs over all ~248
centers via get_center_multipliers and _center_rpp.
"""
import pytest

from services.policy_scenarios import (
    SCENARIOS,
    TRAVEL_SUBSIDY_TIERS,
    _center_rpp,
    get_center_multipliers,
    get_scenario,
    list_scenarios,
)


@pytest.fixture(autouse=True)
def _load(data):
    pass


# --- Scenario Registration ---

class TestTravelSubsidyRegistration:
    """Travel subsidy scenarios are registered correctly."""

    def test_four_travel_scenarios_registered(self):
        travel_ids = [sid for sid in SCENARIOS if sid.startswith("travel_assistance_")]
        assert len(travel_ids) == 4

    def test_scenario_ids_match_expected(self):
        expected = {
            "travel_assistance_5k",
            "travel_assistance_10k",
            "travel_assistance_20k",
            "travel_assistance_50k",
        }
        actual = {sid for sid in SCENARIOS if sid.startswith("travel_assistance_")}
        assert actual == expected

    def test_total_scenario_count(self):
        """4 original + 4 travel = 8 total scenarios."""
        assert len(SCENARIOS) == 8

    def test_all_have_required_fields(self):
        for sid, s in SCENARIOS.items():
            if not sid.startswith("travel_assistance_"):
                continue
            assert s.name
            assert s.short_description
            assert s.description
            assert len(s.references) > 0
            assert len(s.caveats) > 0

    def test_all_apply_to_all_organs(self):
        """Travel subsidy is organ-agnostic."""
        for sid, s in SCENARIOS.items():
            if sid.startswith("travel_assistance_"):
                assert s.organs == [], f"{sid} should apply to all organs"

    def test_subsidy_amount_carried_explicitly(self):
        """The tier amount lives on the scenario, not only in its id
        (2026-08 review: id string-parsing was the only source before)."""
        for amount in TRAVEL_SUBSIDY_TIERS:
            s = get_scenario(f"travel_assistance_{amount // 1000}k")
            assert s.subsidy_amount == amount


# --- Listing & Filtering ---

class TestTravelSubsidyListing:
    def test_list_all_includes_travel(self):
        all_scenarios = list_scenarios()
        travel = [s for s in all_scenarios if s.id.startswith("travel_assistance_")]
        assert len(travel) == 4

    def test_filter_by_any_organ_includes_travel(self):
        """Since organs=[], travel scenarios should appear for any organ."""
        for organ in ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]:
            results = list_scenarios(organ=organ)
            travel = [s for s in results if s.id.startswith("travel_assistance_")]
            assert len(travel) == 4, f"Travel scenarios missing for organ={organ}"

    def test_get_scenario_by_id(self):
        s = get_scenario("travel_assistance_20k")
        assert s is not None
        assert "$20,000" in s.name

    def test_get_nonexistent_travel_scenario(self):
        assert get_scenario("travel_assistance_100k") is None


# --- Per-Center Multiplier Logic ---

class TestTravelSubsidyCenterMultipliers:
    def test_rpp_covers_full_center_population(self):
        rpp, _, _ = _center_rpp()
        assert len(rpp) > 200, f"RPP coverage only {len(rpp)} centers"

    def test_high_col_center_gets_larger_wait_reduction(self):
        """The highest-RPP center should see more wait reduction than the lowest."""
        rpp, _, _ = _center_rpp()
        hi, lo = max(rpp, key=rpp.get), min(rpp, key=rpp.get)
        s = get_scenario("travel_assistance_20k")
        _, wait_hi = get_center_multipliers(s, hi)
        _, wait_lo = get_center_multipliers(s, lo)
        assert wait_hi < wait_lo, (
            f"High-COL center should have lower wait multiplier: "
            f"{hi}={wait_hi}, {lo}={wait_lo}"
        )

    def test_high_col_center_gets_larger_donor_boost(self):
        rpp, _, _ = _center_rpp()
        hi, lo = max(rpp, key=rpp.get), min(rpp, key=rpp.get)
        s = get_scenario("travel_assistance_20k")
        donor_hi, _ = get_center_multipliers(s, hi)
        donor_lo, _ = get_center_multipliers(s, lo)
        assert donor_hi > donor_lo

    def test_lowest_col_center_minimal_effect(self):
        """The lowest-RPP center should have near-baseline multipliers."""
        rpp, _, _ = _center_rpp()
        lo = min(rpp, key=rpp.get)
        s = get_scenario("travel_assistance_5k")
        donor, wait = get_center_multipliers(s, lo)
        assert 0.99 <= donor <= 1.01
        assert 0.99 <= wait <= 1.01

    def test_multipliers_in_valid_range(self):
        """All multipliers should be in a reasonable range, for every center."""
        rpp, _, _ = _center_rpp()
        for sid in SCENARIOS:
            if not sid.startswith("travel_assistance_"):
                continue
            s = SCENARIOS[sid]
            for code in rpp:
                donor, wait = get_center_multipliers(s, code)
                assert 0.8 <= donor <= 1.3, f"{sid}/{code}: donor={donor}"
                assert 0.8 <= wait <= 1.05, f"{sid}/{code}: wait={wait}"

    def test_unknown_center_falls_back_to_global(self):
        s = get_scenario("travel_assistance_20k")
        d, w = get_center_multipliers(s, "ZZZZ")
        assert (d, w) == (s.donor_rate_multiplier, s.wait_time_multiplier)


# --- Price Point Monotonicity ---

class TestSubsidyMonotonicity:
    """Larger subsidies should have larger effects."""

    def test_global_donor_multiplier_increases_with_amount(self):
        amounts = sorted(TRAVEL_SUBSIDY_TIERS.keys())
        donors = [get_scenario(f"travel_assistance_{a // 1000}k").donor_rate_multiplier for a in amounts]
        for i in range(1, len(donors)):
            assert donors[i] >= donors[i - 1], f"Donor multiplier not monotonic: {donors}"

    def test_global_wait_multiplier_decreases_with_amount(self):
        amounts = sorted(TRAVEL_SUBSIDY_TIERS.keys())
        waits = [get_scenario(f"travel_assistance_{a // 1000}k").wait_time_multiplier for a in amounts]
        for i in range(1, len(waits)):
            assert waits[i] <= waits[i - 1], f"Wait multiplier not monotonic: {waits}"

    def test_center_effect_increases_with_amount(self):
        """For any given center, a larger subsidy means a larger wait cut."""
        amounts = sorted(TRAVEL_SUBSIDY_TIERS.keys())
        rpp, _, _ = _center_rpp()
        codes = sorted(rpp, key=rpp.get)
        for code in {codes[0], codes[len(codes) // 2], codes[-1]}:
            waits = []
            for a in amounts:
                s = get_scenario(f"travel_assistance_{a // 1000}k")
                _, wait = get_center_multipliers(s, code)
                waits.append(wait)
            for i in range(1, len(waits)):
                assert waits[i] <= waits[i - 1], (
                    f"Wait reduction not monotonic for {code}: {waits}"
                )


# --- Diminishing Returns ---

class TestDiminishingReturns:
    """The marginal effect per dollar should decrease with subsidy amount."""

    def test_marginal_wait_reduction_diminishes(self):
        """The per-dollar wait reduction should be larger for $5K than $50K."""
        amounts = sorted(TRAVEL_SUBSIDY_TIERS.keys())
        tiers = [TRAVEL_SUBSIDY_TIERS[a] for a in amounts]
        per_dollar = [t["max_col_effect"] / a for a, t in zip(amounts, tiers)]
        assert per_dollar[0] > per_dollar[-1], (
            f"No diminishing returns: per_dollar={per_dollar}"
        )


# --- COL (BEA RPP) Data Consistency ---

class TestCOLData:
    def test_col_values_reasonable(self):
        rpp, _, _ = _center_rpp()
        for code, col in rpp.items():
            assert 60 <= col <= 160, f"{code} has unreasonable COL={col}"

    def test_cached_range_matches_dict(self):
        rpp, col_min, col_max = _center_rpp()
        assert col_min == min(rpp.values())
        assert col_max == max(rpp.values())

    def test_col_has_meaningful_spread(self):
        _, col_min, col_max = _center_rpp()
        assert col_max - col_min >= 10
