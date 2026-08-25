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

from models.schemas import (
    PatientProfile,
    WhatIfRequest,
    PolicyScenarioRequest,
    TravelSubsidyRequest,
    TravelSubsidyCityResult,
    TravelSubsidyTierResult,
    TravelSubsidyAnalysisResult,
)
from services.what_if import compute_what_if, WhatIfResult
from services.policy_scenarios import (
    PolicyScenario, list_scenarios, get_scenario, get_city_multipliers,
    TRAVEL_SUBSIDY_TIERS,
)

router = APIRouter()


# --- Raw multiplier endpoint (unchanged) ---

@router.post("/what-if", response_model=WhatIfResult)
def run_what_if(request: WhatIfRequest) -> WhatIfResult:
    try:
        from tier_config import get_tier
        tier = get_tier()
        iterations = min(request.iterations, tier.max_whatif_iterations)
        return compute_what_if(
            patient=request.patient,
            city=request.city,
            center_code=request.center_code,
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

class PolicyScenarioResult(BaseModel):
    """Result of a policy scenario analysis."""
    scenario: PolicyScenario
    city: str
    state: str
    center_code: str = Field("", description="SRTR center code when the run was center-based")
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

    # Effective multipliers: per-center (BEA RPP-derived for travel scenarios,
    # #285) when a center code is given; legacy per-city table otherwise.
    if request.center_code:
        from services.policy_scenarios import get_center_multipliers
        donor_mult, wait_mult = get_center_multipliers(scenario, request.center_code)
    else:
        donor_mult, wait_mult = get_city_multipliers(scenario, request.city)

    # Clamp iterations to tier cap
    from tier_config import get_tier
    tier = get_tier()
    iterations = min(request.iterations, tier.max_whatif_iterations)

    # Run the what-if engine with scenario-derived multipliers
    try:
        result = compute_what_if(
            patient=request.patient,
            city=request.city,
            center_code=request.center_code,
            donor_rate_multiplier=donor_mult,
            wait_time_multiplier=wait_mult,
            n_iterations=iterations,
            seed=request.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return PolicyScenarioResult(
        scenario=scenario,
        city=result.city,
        state=result.state,
        center_code=result.center_code,
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

    from services.data_loader import get_data
    from services.policy_scenarios import get_center_multipliers
    from services.what_if import compute_what_if_closed_form

    # Determine which centers to analyze (#285: all 248, not the 22 cities).
    # The per-center comparison is closed-form (deterministic competing-risks
    # integral), so the full center population is cheap and noise-free.
    all_centers = get_data().centers_for_organ(request.patient.organ)
    if request.center_codes:
        wanted = set(request.center_codes)
        center_list = [c for c in all_centers if c.get("code") in wanted]
    elif request.cities:
        # Legacy filter: match against center display names
        wanted = set(request.cities)
        center_list = [c for c in all_centers if c.get("name") in wanted]
    else:
        center_list = all_centers
    if not center_list:
        raise HTTPException(
            status_code=400,
            detail="No valid centers found. Check center_codes.",
        )

    tiers = []
    for amount in sorted(TRAVEL_SUBSIDY_TIERS.keys()):
        scenario_id = f"travel_assistance_{amount // 1000}k"
        scenario = get_scenario(scenario_id)
        if not scenario:
            continue

        city_results = []
        for center in center_list:
            code = center.get("code", "")
            donor_mult, wait_mult = get_center_multipliers(scenario, code)
            try:
                result = compute_what_if_closed_form(
                    patient=request.patient,
                    center_code=code,
                    donor_rate_multiplier=donor_mult,
                    wait_time_multiplier=wait_mult,
                )
                city_results.append(TravelSubsidyCityResult(**result))
            except Exception:
                logger.warning("Travel subsidy analysis failed for %s at %s", code, scenario_id)
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
        "Travel subsidy analysis complete: %s, %d tiers × %d centers, %.2fs",
        request.patient.organ, len(tiers), len(center_list), elapsed,
    )

    return TravelSubsidyAnalysisResult(
        organ=request.patient.organ,
        tiers=tiers,
        total_cities=len(center_list),
        iterations_per_city=0,  # closed-form — no Monte Carlo sampling (#285)
        elapsed_seconds=round(elapsed, 3),
        disclaimers=[
            "This is a demand-side accessibility model. It estimates how "
            "financial assistance for travel/relocation affects transplant "
            "probability by enabling access to better-matched centers.",
            "Per-center effects are proportional to each center's BEA cost of "
            "living (RPP). Higher-COL areas show larger improvements because "
            "the subsidy makes them newly accessible to lower-income patients.",
            "Probabilities are computed in closed form (competing-risks "
            "integral), so results carry no Monte Carlo noise; the copula and "
            "stochastic cause-of-death adjustments are omitted.",
            "System-wide averages assume equal patient distribution across "
            "centers. Real-world impact depends on where patients actually live.",
            "Equilibrium effects (increased demand at popular centers) are "
            "approximated. See Tier 2 analysis for full equilibrium modeling.",
            "These are model estimates, not empirical observations. Actual "
            "program outcomes would depend on implementation details.",
        ],
    )
