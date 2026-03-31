"""What-if scenario analysis endpoints.

POST /what-if — Raw multiplier-based what-if analysis (Phase 3 M5).
POST /policy-scenario — Policy scenario analysis with literature-backed parameters (Phase 4 M4).
GET /policy-scenarios — List available predefined policy scenarios.
GET /policy-scenarios/{scenario_id} — Get a specific scenario's details.
POST /travel-subsidy-analysis — Compare all travel subsidy price points for a patient (#141).
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field

from models.schemas import PatientProfile
from services.what_if import compute_what_if, WhatIfResult
from services.policy_scenarios import (
    PolicyScenario, list_scenarios, get_scenario, get_city_multipliers,
    TRAVEL_SUBSIDY_TIERS,
)

router = APIRouter()


# --- Raw multiplier endpoint (unchanged) ---

class WhatIfRequest(BaseModel):
    patient: PatientProfile
    city: str = Field(
        default="Nashville",
        description="City name (legacy) or display label",
    )
    center_code: str = Field(
        default="",
        description="SRTR center code (preferred over city name)",
    )
    donor_rate_multiplier: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Multiplier for donor availability. >1 = more donors (shorter waits), <1 = fewer donors (longer waits)",
    )
    wait_time_multiplier: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Multiplier for base wait time distribution. >1 = longer waits, <1 = shorter waits",
    )
    iterations: int = Field(default=500, ge=100, le=2000)
    seed: Optional[int] = Field(None, ge=0, le=2147483647, description="RNG seed for reproducibility")


@router.post("/what-if", response_model=WhatIfResult)
def run_what_if(request: WhatIfRequest) -> WhatIfResult:
    try:
        from tier_config import get_tier
        tier = get_tier()
        iterations = min(request.iterations, tier.max_whatif_iterations)
        return compute_what_if(
            patient=request.patient,
            city=request.city,
            donor_rate_multiplier=request.donor_rate_multiplier,
            wait_time_multiplier=request.wait_time_multiplier,
            n_iterations=iterations,
            seed=request.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("What-if analysis failed for %s/%s", request.patient.organ, request.city)
        raise HTTPException(status_code=500, detail="What-if analysis failed — see server logs") from e


# --- Policy scenario endpoints (Phase 4 M4) ---

class PolicyScenarioRequest(BaseModel):
    patient: PatientProfile
    scenario_id: str = Field(description="ID of the predefined policy scenario")
    city: str = Field(
        default="Nashville",
        description="City to run scenario analysis for",
    )
    iterations: int = Field(default=500, ge=100, le=2000)
    seed: Optional[int] = Field(None, ge=0, le=2147483647, description="RNG seed for reproducibility")


class PolicyScenarioResult(BaseModel):
    """Result of a policy scenario analysis."""
    scenario: PolicyScenario
    city: str
    state: str
    donor_rate_multiplier: float = Field(description="Effective multiplier for this city")
    wait_time_multiplier: float = Field(description="Effective multiplier for this city")
    baseline_p24: float
    adjusted_p24: float
    delta_p24: float
    baseline_ci_95: tuple[float, float]
    adjusted_ci_95: tuple[float, float]
    baseline_median_wait: float
    adjusted_median_wait: float
    iterations: int
    elapsed_seconds: float
    seed_used: int = Field(0, description="RNG seed used for this run (for reproducibility)")


@router.get("/policy-scenarios", response_model=list[PolicyScenario])
def get_policy_scenarios(organ: Optional[str] = None) -> list[PolicyScenario]:
    """List available predefined policy scenarios, optionally filtered by organ."""
    return list_scenarios(organ=organ)


@router.get("/policy-scenarios/{scenario_id}", response_model=PolicyScenario)
def get_policy_scenario(scenario_id: str) -> PolicyScenario:
    """Get details of a specific policy scenario."""
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return scenario


@router.post("/policy-scenario", response_model=PolicyScenarioResult)
def run_policy_scenario(request: PolicyScenarioRequest) -> PolicyScenarioResult:
    """
    Run a predefined policy scenario for a specific city.

    Looks up the scenario's per-city multipliers (or global defaults),
    then runs the same paired-seed Monte Carlo as /what-if.
    """
    scenario = get_scenario(request.scenario_id)
    if not scenario:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{request.scenario_id}' not found",
        )

    # Check organ applicability
    if scenario.organs and request.patient.organ not in scenario.organs:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Scenario '{scenario.name}' applies to "
                f"{', '.join(scenario.organs)} only, not {request.patient.organ}"
            ),
        )

    # Get effective multipliers for this city
    donor_mult, wait_mult = get_city_multipliers(scenario, request.city)

    # Clamp iterations to tier cap
    from tier_config import get_tier
    tier = get_tier()
    iterations = min(request.iterations, tier.max_whatif_iterations)

    # Run the what-if engine with scenario-derived multipliers
    result = compute_what_if(
        patient=request.patient,
        city=request.city,
        donor_rate_multiplier=donor_mult,
        wait_time_multiplier=wait_mult,
        n_iterations=iterations,
        seed=request.seed,
    )

    return PolicyScenarioResult(
        scenario=scenario,
        city=result.city,
        state=result.state,
        donor_rate_multiplier=donor_mult,
        wait_time_multiplier=wait_mult,
        baseline_p24=result.baseline_p24,
        adjusted_p24=result.adjusted_p24,
        delta_p24=result.delta_p24,
        baseline_ci_95=result.baseline_ci_95,
        adjusted_ci_95=result.adjusted_ci_95,
        baseline_median_wait=result.baseline_median_wait,
        adjusted_median_wait=result.adjusted_median_wait,
        iterations=result.iterations,
        elapsed_seconds=result.elapsed_seconds,
    )


# --- Travel subsidy multi-price-point comparison (#141) ---

class TravelSubsidyRequest(BaseModel):
    patient: PatientProfile
    cities: list[str] = Field(
        default_factory=list,
        description="Cities to analyze. Empty = all available centers.",
    )
    iterations: int = Field(default=500, ge=100, le=2000)
    seed: Optional[int] = Field(None, ge=0, le=2147483647, description="RNG seed for reproducibility")


class TravelSubsidyCityResult(BaseModel):
    """Result for one city at one price point."""
    city: str
    state: str
    baseline_p24: float
    adjusted_p24: float
    delta_p24: float
    baseline_median_wait: float
    adjusted_median_wait: float


class TravelSubsidyTierResult(BaseModel):
    """Result for one price point across all cities."""
    subsidy_amount: int
    label: str
    scenario_id: str
    system_avg_baseline_p24: float = Field(description="Average P(transplant ≤ 24mo) across all cities, no subsidy")
    system_avg_adjusted_p24: float = Field(description="Average P(transplant ≤ 24mo) across all cities, with subsidy")
    system_delta_p24: float = Field(description="System-wide improvement in average P24")
    system_avg_baseline_wait: float
    system_avg_adjusted_wait: float
    cities: list[TravelSubsidyCityResult]


class TravelSubsidyAnalysisResult(BaseModel):
    """Full multi-price-point travel subsidy comparison."""
    organ: str
    tiers: list[TravelSubsidyTierResult]
    total_cities: int
    iterations_per_city: int
    elapsed_seconds: float
    seed_used: int = Field(0, description="RNG seed used for this run (for reproducibility)")
    disclaimers: list[str]


@router.post("/travel-subsidy-analysis", response_model=TravelSubsidyAnalysisResult)
def run_travel_subsidy_analysis(request: TravelSubsidyRequest) -> TravelSubsidyAnalysisResult:
    """
    Compare all travel subsidy price points ($5K/$10K/$20K/$50K) for a patient.

    For each price point, runs paired Monte Carlo for each city and computes
    the system-wide average improvement in P(transplant ≤ 24 months).
    Returns a diminishing-returns curve across price points.
    """
    import time
    start = time.perf_counter()

    from services.monte_carlo import _get_cities

    # Clamp iterations to tier cap
    from tier_config import get_tier
    tier = get_tier()
    clamped_iterations = min(request.iterations, tier.max_whatif_iterations)

    # Determine which cities to analyze
    all_cities = _get_cities()
    if request.cities:
        city_list = [c for c in all_cities if c["city"] in request.cities]
        if not city_list:
            raise HTTPException(
                status_code=400,
                detail=f"No valid cities found. Check city names.",
            )
    else:
        city_list = all_cities

    tiers = []
    for amount in sorted(TRAVEL_SUBSIDY_TIERS.keys()):
        scenario_id = f"travel_assistance_{amount // 1000}k"
        scenario = get_scenario(scenario_id)
        if not scenario:
            continue

        city_results = []
        for city_info in city_list:
            city = city_info["city"]
            donor_mult, wait_mult = get_city_multipliers(scenario, city)

            try:
                result = compute_what_if(
                    patient=request.patient,
                    city=city,
                    donor_rate_multiplier=donor_mult,
                    wait_time_multiplier=wait_mult,
                    n_iterations=clamped_iterations,
                    seed=request.seed,
                )
                city_results.append(TravelSubsidyCityResult(
                    city=result.city,
                    state=result.state,
                    baseline_p24=result.baseline_p24,
                    adjusted_p24=result.adjusted_p24,
                    delta_p24=result.delta_p24,
                    baseline_median_wait=result.baseline_median_wait,
                    adjusted_median_wait=result.adjusted_median_wait,
                ))
            except Exception:
                logger.warning("Travel subsidy analysis failed for %s at %s", city, scenario_id)
                continue

        if not city_results:
            continue

        # System-wide averages
        avg_baseline_p24 = sum(c.baseline_p24 for c in city_results) / len(city_results)
        avg_adjusted_p24 = sum(c.adjusted_p24 for c in city_results) / len(city_results)
        avg_baseline_wait = sum(c.baseline_median_wait for c in city_results) / len(city_results)
        avg_adjusted_wait = sum(c.adjusted_median_wait for c in city_results) / len(city_results)

        tier_info = TRAVEL_SUBSIDY_TIERS[amount]
        tiers.append(TravelSubsidyTierResult(
            subsidy_amount=amount,
            label=tier_info["label"],
            scenario_id=scenario_id,
            system_avg_baseline_p24=round(avg_baseline_p24, 4),
            system_avg_adjusted_p24=round(avg_adjusted_p24, 4),
            system_delta_p24=round(avg_adjusted_p24 - avg_baseline_p24, 4),
            system_avg_baseline_wait=round(avg_baseline_wait, 1),
            system_avg_adjusted_wait=round(avg_adjusted_wait, 1),
            cities=city_results,
        ))

    elapsed = time.perf_counter() - start
    logger.info(
        "Travel subsidy analysis complete: %s, %d tiers × %d cities, %.2fs",
        request.patient.organ, len(tiers), len(city_list), elapsed,
    )

    return TravelSubsidyAnalysisResult(
        organ=request.patient.organ,
        tiers=tiers,
        total_cities=len(city_list),
        iterations_per_city=clamped_iterations,
        elapsed_seconds=round(elapsed, 3),
        disclaimers=[
            "This is a demand-side accessibility model. It estimates how "
            "financial assistance for travel/relocation affects transplant "
            "probability by enabling access to better-matched centers.",
            "Per-city effects are proportional to cost of living. Higher-COL "
            "cities show larger improvements because the subsidy makes them "
            "newly accessible to lower-income patients.",
            "System-wide averages assume equal patient distribution across "
            "cities. Real-world impact depends on where patients actually live.",
            "Equilibrium effects (increased demand at popular centers) are "
            "approximated. See Tier 2 analysis for full equilibrium modeling.",
            "These are model estimates, not empirical observations. Actual "
            "program outcomes would depend on implementation details.",
        ],
    )
