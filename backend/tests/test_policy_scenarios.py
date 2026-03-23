"""Tests for Phase 4 M4: Policy Scenario Engine."""
import pytest

from services.policy_scenarios import (
    SCENARIOS,
    PolicyScenario,
    CityAdjustment,
    list_scenarios,
    get_scenario,
    get_city_multipliers,
)


# --- Scenario Registry ---

class TestScenarioRegistry:
    def test_eight_scenarios_defined(self):
        assert len(SCENARIOS) == 8

    def test_scenario_ids(self):
        expected = {
            "kidney_250nm", "continuous_distribution", "increased_dcd", "hcv_positive_donors",
            "travel_assistance_5k", "travel_assistance_10k", "travel_assistance_20k", "travel_assistance_50k",
        }
        assert set(SCENARIOS.keys()) == expected

    def test_all_scenarios_have_required_fields(self):
        for s in SCENARIOS.values():
            assert s.id
            assert s.name
            assert s.short_description
            assert s.description
            assert len(s.references) > 0
            assert len(s.caveats) > 0

    def test_scenario_ids_match_keys(self):
        for key, s in SCENARIOS.items():
            assert key == s.id


# --- list_scenarios ---

class TestListScenarios:
    def test_list_all(self):
        result = list_scenarios()
        assert len(result) == 8

    def test_filter_by_kidney(self):
        result = list_scenarios(organ="kidney")
        ids = {s.id for s in result}
        # kidney_250nm (kidney only), continuous (all), increased_dcd (kidney+),
        # hcv_positive (kidney+liver)
        assert "kidney_250nm" in ids
        assert "continuous_distribution" in ids
        assert "increased_dcd" in ids
        assert "hcv_positive_donors" in ids

    def test_filter_by_heart(self):
        result = list_scenarios(organ="heart")
        ids = {s.id for s in result}
        # kidney_250nm is kidney-only, hcv is kidney/liver only
        assert "kidney_250nm" not in ids
        assert "hcv_positive_donors" not in ids
        assert "continuous_distribution" in ids
        assert "increased_dcd" in ids

    def test_filter_by_pancreas(self):
        result = list_scenarios(organ="pancreas")
        ids = {s.id for s in result}
        # continuous_distribution and all travel_assistance apply to all organs
        assert "continuous_distribution" in ids
        assert "travel_assistance_20k" in ids
        # DCD excludes pancreas
        assert "increased_dcd" not in ids


# --- get_scenario ---

class TestGetScenario:
    def test_get_existing(self):
        s = get_scenario("kidney_250nm")
        assert s is not None
        assert s.name == "2021 Kidney 250nm Circles"

    def test_get_nonexistent(self):
        assert get_scenario("nonexistent") is None


# --- get_city_multipliers ---

class TestGetCityMultipliers:
    def test_kidney_250nm_large_center(self):
        """Large centers should see donor reduction and wait increase."""
        s = get_scenario("kidney_250nm")
        donor, wait = get_city_multipliers(s, "New York")
        assert donor < 1.0  # less donor access
        assert wait > 1.0   # longer waits

    def test_kidney_250nm_small_center(self):
        """Small centers should see donor improvement and wait decrease."""
        s = get_scenario("kidney_250nm")
        donor, wait = get_city_multipliers(s, "Madison")
        assert donor > 1.0  # more donor access
        assert wait < 1.0   # shorter waits

    def test_kidney_250nm_medium_center(self):
        """Medium centers should see moderate improvement."""
        s = get_scenario("kidney_250nm")
        donor, wait = get_city_multipliers(s, "Nashville")
        assert donor > 1.0
        assert wait < 1.0
        # Moderate — less improvement than small centers
        donor_small, _ = get_city_multipliers(s, "Madison")
        assert donor < donor_small

    def test_continuous_distribution_stronger_than_250nm(self):
        """Continuous distribution should have larger effect than 250nm circles."""
        s_250 = get_scenario("kidney_250nm")
        s_cd = get_scenario("continuous_distribution")

        # For small centers, continuous distribution gives more improvement
        d_250, _ = get_city_multipliers(s_250, "Omaha")
        d_cd, _ = get_city_multipliers(s_cd, "Omaha")
        assert d_cd > d_250  # more donor improvement

        # For large centers, continuous distribution penalizes more
        d_250_ny, _ = get_city_multipliers(s_250, "New York")
        d_cd_ny, _ = get_city_multipliers(s_cd, "New York")
        assert d_cd_ny < d_250_ny  # more donor reduction

    def test_dcd_global_multiplier_no_city_overrides(self):
        """DCD uses global multipliers (no per-city overrides)."""
        s = get_scenario("increased_dcd")
        donor, wait = get_city_multipliers(s, "Nashville")
        assert donor == s.donor_rate_multiplier
        assert wait == s.wait_time_multiplier
        # Same for any city
        donor2, wait2 = get_city_multipliers(s, "New York")
        assert donor == donor2
        assert wait == wait2

    def test_hcv_global_multiplier(self):
        """HCV+ uses global multipliers."""
        s = get_scenario("hcv_positive_donors")
        donor, wait = get_city_multipliers(s, "Pittsburgh")
        assert donor == s.donor_rate_multiplier
        assert wait == s.wait_time_multiplier

    def test_all_22_cities_have_multipliers(self):
        """Every TransPlan city should return valid multipliers."""
        cities = [
            "Pittsburgh", "Baltimore", "Philadelphia", "New York", "Minneapolis",
            "Madison", "Chicago", "Cleveland", "St. Louis", "Indianapolis",
            "Omaha", "Rochester", "Nashville", "Durham", "Miami",
            "Dallas", "Houston", "Portland", "Seattle", "San Francisco",
            "Los Angeles", "Palo Alto",
        ]
        for s in SCENARIOS.values():
            for city in cities:
                donor, wait = get_city_multipliers(s, city)
                assert 0.5 <= donor <= 2.0, f"{s.id}/{city}: donor={donor}"
                assert 0.5 <= wait <= 2.0, f"{s.id}/{city}: wait={wait}"


# --- Scenario content quality ---

class TestScenarioContent:
    def test_kidney_250nm_is_kidney_only(self):
        s = get_scenario("kidney_250nm")
        assert s.organs == ["kidney"]

    def test_continuous_distribution_all_organs(self):
        s = get_scenario("continuous_distribution")
        assert s.organs == []  # empty = all organs

    def test_dcd_excludes_pancreas_intestine(self):
        s = get_scenario("increased_dcd")
        assert "pancreas" not in s.organs
        assert "intestine" not in s.organs

    def test_hcv_kidney_liver_only(self):
        s = get_scenario("hcv_positive_donors")
        assert set(s.organs) == {"kidney", "liver"}

    def test_kidney_250nm_has_22_city_overrides(self):
        s = get_scenario("kidney_250nm")
        assert len(s.city_adjustments) == 22

    def test_all_scenarios_have_references(self):
        for s in SCENARIOS.values():
            assert len(s.references) >= 2, f"{s.id} has <2 references"

    def test_multipliers_in_reasonable_range(self):
        """Global multipliers should be modest (0.85-1.35)."""
        for s in SCENARIOS.values():
            assert 0.85 <= s.donor_rate_multiplier <= 1.35, f"{s.id} donor={s.donor_rate_multiplier}"
            assert 0.85 <= s.wait_time_multiplier <= 1.15, f"{s.id} wait={s.wait_time_multiplier}"
