"""Tests for Travel Financial Assistance policy scenarios (#141)."""
import pytest

from services.policy_scenarios import (
    SCENARIOS,
    TRAVEL_SUBSIDY_TIERS,
    _get_city_col,
    list_scenarios,
    get_scenario,
    get_city_multipliers,
)


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


# --- Per-City Multiplier Logic ---

class TestTravelSubsidyCityMultipliers:
    def test_all_22_cities_have_adjustments(self):
        """Every original city should have per-city overrides."""
        s = get_scenario("travel_assistance_20k")
        assert len(s.city_adjustments) == 22

    def test_high_col_city_gets_larger_wait_reduction(self):
        """The highest-RPP city should see more wait reduction than the lowest."""
        col = _get_city_col()
        hi, lo = max(col, key=col.get), min(col, key=col.get)
        s = get_scenario("travel_assistance_20k")
        _, wait_hi = get_city_multipliers(s, hi)
        _, wait_lo = get_city_multipliers(s, lo)
        assert wait_hi < wait_lo, (
            f"High-COL city should have lower wait multiplier: "
            f"{hi}={wait_hi}, {lo}={wait_lo}"
        )

    def test_high_col_city_gets_larger_donor_boost(self):
        """The highest-RPP city should see more donor boost than the lowest."""
        col = _get_city_col()
        hi, lo = max(col, key=col.get), min(col, key=col.get)
        s = get_scenario("travel_assistance_20k")
        donor_hi, _ = get_city_multipliers(s, hi)
        donor_lo, _ = get_city_multipliers(s, lo)
        assert donor_hi > donor_lo

    def test_lowest_col_city_minimal_effect(self):
        """The lowest-RPP city should have near-baseline multipliers."""
        col = _get_city_col()
        lo = min(col, key=col.get)
        s = get_scenario("travel_assistance_5k")
        donor, wait = get_city_multipliers(s, lo)
        # With 5k subsidy and lowest COL, effect should be very small
        assert 0.99 <= donor <= 1.01
        assert 0.99 <= wait <= 1.01

    def test_multipliers_in_valid_range(self):
        """All multipliers should be in a reasonable range."""
        for sid in SCENARIOS:
            if not sid.startswith("travel_assistance_"):
                continue
            s = SCENARIOS[sid]
            for city in _get_city_col():
                donor, wait = get_city_multipliers(s, city)
                assert 0.8 <= donor <= 1.3, f"{sid}/{city}: donor={donor}"
                assert 0.8 <= wait <= 1.05, f"{sid}/{city}: wait={wait}"


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

    def test_city_effect_increases_with_amount(self):
        """For any given city, a larger subsidy should produce a larger wait reduction."""
        amounts = sorted(TRAVEL_SUBSIDY_TIERS.keys())
        for city in ["New York", "Cleveland", "Palo Alto"]:
            waits = []
            for a in amounts:
                s = get_scenario(f"travel_assistance_{a // 1000}k")
                _, wait = get_city_multipliers(s, city)
                waits.append(wait)
            for i in range(1, len(waits)):
                assert waits[i] <= waits[i - 1], (
                    f"Wait reduction not monotonic for {city}: {waits}"
                )


# --- Diminishing Returns ---

class TestDiminishingReturns:
    """The marginal effect per dollar should decrease with subsidy amount."""

    def test_marginal_wait_reduction_diminishes(self):
        """The per-dollar wait reduction should be larger for $5K than $50K."""
        amounts = sorted(TRAVEL_SUBSIDY_TIERS.keys())
        tiers = [TRAVEL_SUBSIDY_TIERS[a] for a in amounts]
        # Per-dollar max_col_effect
        per_dollar = [t["max_col_effect"] / a for a, t in zip(amounts, tiers)]
        # First tier should have highest per-dollar effect
        assert per_dollar[0] > per_dollar[-1], (
            f"No diminishing returns: per_dollar={per_dollar}"
        )


# --- COL Data Consistency ---

class TestCOLData:
    def test_all_22_cities_in_col_data(self):
        assert len(_get_city_col()) == 22

    def test_col_values_reasonable(self):
        for city, col in _get_city_col().items():
            assert 60 <= col <= 160, f"{city} has unreasonable COL={col}"

    def test_highest_col_is_expensive_coastal_metro(self):
        col = _get_city_col()
        assert max(col, key=col.get) in {
            "San Francisco", "Palo Alto", "New York", "Los Angeles", "Miami", "Seattle",
        }

    def test_lowest_col_is_low_cost_metro(self):
        col = _get_city_col()
        assert min(col, key=col.get) in {
            "Rochester", "Omaha", "Indianapolis", "Cleveland", "St. Louis", "Pittsburgh",
        }

    def test_col_has_meaningful_spread(self):
        values = list(_get_city_col().values())
        assert max(values) - min(values) >= 10
