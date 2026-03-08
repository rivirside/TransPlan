"""
Brier score calibration validation for M7.

Compares Monte Carlo predicted probabilities against analytical expectations
computed from the same SRTR-derived parameters. This is a self-consistency
check (calibration verification), not an external validation.

A true external Brier score would require held-out SRTR cohort outcomes.
That is a Phase 4 deliverable (prospective IRB study).

Brier score formula: BS = mean((P_predicted - P_observed)^2)
  - BS = 0.0 → perfect calibration
  - BS < 0.05 → excellent
  - BS < 0.20 → acceptable for FDA SaMD (per roadmap target)
  - BS = 0.25 → no better than predicting 50% for everything
"""
import logging
import time
from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import quad

from models.schemas import PatientProfile
from services.competing_risks import get_annual_delisting_rate, get_annual_mortality_rate
from services.distributions import get_wait_time_distribution
from services.monte_carlo import simulate, CITIES

logger = logging.getLogger(__name__)


@dataclass
class CityValidation:
    city: str
    p_predicted: float  # Monte Carlo estimate
    p_analytical: float  # numerical integration estimate
    squared_error: float


@dataclass
class BrierResult:
    organ: str
    blood_type: str
    brier_score: float
    n_cities: int
    iterations: int
    elapsed_seconds: float
    cities: list[CityValidation] = field(default_factory=list)


def _analytical_p_transplant_12mo(
    organ: str,
    blood_type: str,
    city: str,
    urgency: int = 2,
    cpra: int | None = None,
    meld: int | None = None,
    las: float | None = None,
) -> float:
    """
    Compute P(transplant first AND within 12 months) analytically.

    Uses numerical integration over the joint survival model:
      P = integral_0^12 f_T(t) * S_M(t) * S_D(t) dt

    where f_T is the transplant wait time pdf (log-normal),
    S_M is the mortality survival function (exponential),
    and S_D is the delisting survival function (exponential).
    """
    dist = get_wait_time_distribution(organ, blood_type, city, cpra, meld, las)

    annual_mort = get_annual_mortality_rate(organ, city, urgency, meld)
    annual_delist = get_annual_delisting_rate(organ, city)

    # Monthly hazard rates
    monthly_mort = annual_mort / 12.0
    monthly_delist = annual_delist / 12.0

    def integrand(t: float) -> float:
        # f_T(t): transplant wait time pdf at time t
        f_t = float(dist.pdf(t))
        # S_M(t): probability of surviving (not dying) to time t
        s_m = np.exp(-monthly_mort * t)
        # S_D(t): probability of not being delisted by time t
        s_d = np.exp(-monthly_delist * t)
        return f_t * s_m * s_d

    p_analytical, _ = quad(integrand, 0, 12, limit=100)
    return float(np.clip(p_analytical, 0.0, 1.0))


def compute_brier_score(
    organ: str,
    blood_type: str,
    urgency: int = 2,
    n_iterations: int = 1000,
    cpra: int | None = None,
    meld: int | None = None,
    las: float | None = None,
) -> BrierResult:
    """
    Compute calibration Brier score for one (organ, blood_type) across all 22 cities.

    Compares the Monte Carlo engine's P(transplant within 12 months) against
    analytical expectations from the same SRTR-derived parameters.
    """
    start = time.perf_counter()

    patient = PatientProfile(
        organ=organ, blood_type=blood_type, age=45, sex="male",
        urgency=urgency, cpra=cpra, meld=meld, las=las,
    )
    sim_result = simulate(patient, n_iterations=n_iterations)

    city_validations: list[CityValidation] = []
    squared_errors: list[float] = []

    for city_prob in sim_result.cities:
        p_mc = city_prob.p_transplant_12mo
        p_an = _analytical_p_transplant_12mo(
            organ, blood_type, city_prob.city, urgency, cpra, meld, las,
        )
        se = (p_mc - p_an) ** 2
        squared_errors.append(se)
        city_validations.append(CityValidation(
            city=city_prob.city,
            p_predicted=round(p_mc, 4),
            p_analytical=round(p_an, 4),
            squared_error=round(se, 6),
        ))

    brier = float(np.mean(squared_errors))
    elapsed = time.perf_counter() - start

    logger.info(
        "Brier validation: %s %s, BS=%.6f, %.2fs",
        organ, blood_type, brier, elapsed,
    )

    return BrierResult(
        organ=organ,
        blood_type=blood_type,
        brier_score=round(brier, 6),
        n_cities=len(squared_errors),
        iterations=n_iterations,
        elapsed_seconds=round(elapsed, 3),
        cities=sorted(city_validations, key=lambda c: c.squared_error, reverse=True),
    )


def validate_all_organs(n_iterations: int = 1000) -> dict[str, BrierResult]:
    """
    Run Brier score validation for all 6 organs with representative parameters.

    Returns dict keyed by organ name.
    """
    configs = [
        {"organ": "kidney", "blood_type": "O+", "urgency": 2, "cpra": 30},
        {"organ": "liver", "blood_type": "A+", "urgency": 2, "meld": 20},
        {"organ": "heart", "blood_type": "O+", "urgency": 2},
        {"organ": "lung", "blood_type": "B+", "urgency": 2, "las": 50.0},
        {"organ": "pancreas", "blood_type": "A+", "urgency": 2},
        {"organ": "intestine", "blood_type": "A+", "urgency": 2},
    ]

    results = {}
    for cfg in configs:
        organ = cfg.pop("organ")
        bt = cfg.pop("blood_type")
        urg = cfg.pop("urgency")
        result = compute_brier_score(organ, bt, urg, n_iterations, **cfg)
        results[organ] = result

    return results
