"""
Posterior predictive checks — Phase 5 M5.

Compares MCMC posterior predictions against observed SRTR statistics to
validate that the Bayesian model adequately captures the data-generating
process.  Produces quantitative discrepancy metrics and pass/fail flags
for paper-quality model validation.

Checks performed:
  - National median wait: posterior predictive median vs observed
  - City wait factors: Spearman correlation of posterior vs observed ordering
  - Blood type multipliers: posterior vs observed rank agreement
  - Competing risk rates: posterior mortality/delisting vs observed
  - Calibration: fraction of observed values inside 90% posterior intervals
"""
import logging
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import spearmanr

from config import DATA_DIR
from services.mcmc_survival import (
    BLOOD_TYPES,
    URGENCY_LEVELS,
    load_organ_data,
    load_trace,
    sample_params_from_trace,
    trace_exists,
)

logger = logging.getLogger(__name__)

# Number of posterior draws for predictive checks
N_DRAWS = 200


@dataclass
class CheckResult:
    """Single posterior predictive check result."""
    name: str
    description: str
    observed: float
    posterior_mean: float
    posterior_ci_90: tuple[float, float]
    inside_ci: bool
    discrepancy: float  # |observed - posterior_mean| / observed
    passed: bool

    def __post_init__(self):
        # Comparisons like `rho > 0.7` yield numpy.bool_, which is not a Python
        # bool and breaks JSON serialization and isinstance checks. Coerce here
        # so every construction site is safe (the alternative is wrapping every
        # `inside_ci=`/`passed=` expression in bool()).
        self.inside_ci = bool(self.inside_ci)
        self.passed = bool(self.passed)


@dataclass
class PosteriorCheckReport:
    """Full posterior predictive check report for one organ."""
    organ: str
    n_draws: int
    checks: list[CheckResult]
    calibration_fraction: float  # fraction of checks where observed ∈ 90% CI
    overall_passed: bool
    notes: list[str] = field(default_factory=list)


def _ci_90(values: np.ndarray) -> tuple[float, float]:
    """Compute 90% credible interval from posterior samples."""
    return (float(np.percentile(values, 5)), float(np.percentile(values, 95)))


def run_posterior_checks(organ: str) -> PosteriorCheckReport:
    """
    Run posterior predictive checks for a given organ.

    Draws parameter sets from the MCMC posterior trace and compares
    derived quantities against the observed SRTR values that were used
    to fit the model.  A well-calibrated model should have ~90% of
    observed values falling inside the 90% posterior intervals.

    Raises RuntimeError if no trace exists for the organ.
    """
    if not trace_exists(organ):
        raise RuntimeError(
            f"No MCMC trace for {organ}. Run scripts/fit-mcmc-model.py first."
        )

    trace = load_trace(organ)
    if trace is None:
        raise RuntimeError(f"Failed to load MCMC trace for {organ}.")

    observed = load_organ_data(organ)
    rng = np.random.default_rng(42)
    draws = sample_params_from_trace(trace, n_draws=N_DRAWS, rng=rng)

    checks: list[CheckResult] = []

    # ------------------------------------------------------------------
    # 1. National median wait time
    # ------------------------------------------------------------------
    obs_median = observed["national_median"]
    post_medians = np.array([d["national_median"] for d in draws])
    ci = _ci_90(post_medians)
    inside = ci[0] <= obs_median <= ci[1]
    disc = abs(obs_median - float(np.mean(post_medians))) / obs_median if obs_median > 0 else 0.0
    checks.append(CheckResult(
        name="national_median_wait",
        description="National median wait time (months)",
        observed=round(obs_median, 2),
        posterior_mean=round(float(np.mean(post_medians)), 2),
        posterior_ci_90=(round(ci[0], 2), round(ci[1], 2)),
        inside_ci=inside,
        discrepancy=round(disc, 4),
        passed=disc < 0.20,  # <20% relative error
    ))

    # ------------------------------------------------------------------
    # 2. Log-sigma (wait time dispersion)
    # ------------------------------------------------------------------
    obs_sigma = observed["log_sigma"]
    post_sigmas = np.array([d["log_sigma"] for d in draws])
    ci = _ci_90(post_sigmas)
    inside = ci[0] <= obs_sigma <= ci[1]
    disc = abs(obs_sigma - float(np.mean(post_sigmas))) / obs_sigma if obs_sigma > 0 else 0.0
    checks.append(CheckResult(
        name="log_sigma",
        description="Wait time log-normal shape parameter",
        observed=round(obs_sigma, 3),
        posterior_mean=round(float(np.mean(post_sigmas)), 3),
        posterior_ci_90=(round(ci[0], 3), round(ci[1], 3)),
        inside_ci=inside,
        discrepancy=round(disc, 4),
        passed=disc < 0.15,
    ))

    # ------------------------------------------------------------------
    # 3. City wait factors — rank correlation
    # ------------------------------------------------------------------
    obs_city_factors = observed["city_wait_factors"]
    n_cities = observed["n_cities"]

    # Collect posterior city factor arrays
    post_city_factors = np.array([
        d["city_wait_factors"][:n_cities] if len(d["city_wait_factors"]) >= n_cities
        else np.pad(d["city_wait_factors"], (0, n_cities - len(d["city_wait_factors"])), constant_values=1.0)
        for d in draws
    ])
    post_mean_factors = np.mean(post_city_factors, axis=0)

    if n_cities >= 3:
        rho, _ = spearmanr(obs_city_factors, post_mean_factors)
        checks.append(CheckResult(
            name="city_wait_factor_rank",
            description="Spearman rank correlation of city wait factors (observed vs posterior mean)",
            observed=1.0,  # perfect self-correlation is the ideal
            posterior_mean=round(float(rho), 4),
            posterior_ci_90=(round(float(rho), 4), 1.0),  # point metric, not interval
            inside_ci=rho > 0.7,
            discrepancy=round(1.0 - float(rho), 4),
            passed=rho > 0.7,
        ))

    # ------------------------------------------------------------------
    # 4. City wait factors — calibration (fraction inside 90% CI)
    # ------------------------------------------------------------------
    city_inside_count = 0
    for i in range(n_cities):
        ci = _ci_90(post_city_factors[:, i])
        if ci[0] <= obs_city_factors[i] <= ci[1]:
            city_inside_count += 1
    city_cal = city_inside_count / n_cities if n_cities > 0 else 0.0
    checks.append(CheckResult(
        name="city_factor_calibration",
        description=f"Fraction of {n_cities} city factors inside 90% posterior CI",
        observed=0.90,  # expected for well-calibrated model
        posterior_mean=round(city_cal, 3),
        posterior_ci_90=(0.0, 1.0),
        inside_ci=city_cal >= 0.60,
        discrepancy=round(abs(0.90 - city_cal), 3),
        passed=city_cal >= 0.60,  # relaxed: >=60% inside is acceptable
    ))

    # ------------------------------------------------------------------
    # 5. Blood type multipliers — rank preservation
    # ------------------------------------------------------------------
    obs_bt = observed["bt_mults"]
    post_bt = np.array([d["bt_multipliers"][:len(BLOOD_TYPES)] for d in draws])
    post_bt_mean = np.mean(post_bt, axis=0)

    if len(obs_bt) >= 3:
        bt_rho, _ = spearmanr(obs_bt, post_bt_mean)
        checks.append(CheckResult(
            name="blood_type_rank",
            description="Spearman rank correlation of blood type multipliers",
            observed=1.0,
            posterior_mean=round(float(bt_rho), 4),
            posterior_ci_90=(round(float(bt_rho), 4), 1.0),
            inside_ci=bt_rho > 0.7,
            discrepancy=round(1.0 - float(bt_rho), 4),
            passed=bt_rho > 0.7,
        ))

    # ------------------------------------------------------------------
    # 6. National mortality rate
    # ------------------------------------------------------------------
    obs_mort = observed["national_mort_rate"]
    post_morts = np.array([d["national_mort_rate"] for d in draws])
    ci = _ci_90(post_morts)
    inside = ci[0] <= obs_mort <= ci[1]
    disc = abs(obs_mort - float(np.mean(post_morts))) / obs_mort if obs_mort > 0 else 0.0
    checks.append(CheckResult(
        name="national_mortality_rate",
        description="National annual waitlist mortality rate",
        observed=round(obs_mort, 4),
        posterior_mean=round(float(np.mean(post_morts)), 4),
        posterior_ci_90=(round(ci[0], 4), round(ci[1], 4)),
        inside_ci=inside,
        discrepancy=round(disc, 4),
        passed=disc < 0.25,
    ))

    # ------------------------------------------------------------------
    # 7. National delisting rate
    # ------------------------------------------------------------------
    obs_delist = observed["national_delist_rate"]
    post_delists = np.array([d["national_delist_rate"] for d in draws])
    ci = _ci_90(post_delists)
    inside = ci[0] <= obs_delist <= ci[1]
    disc = abs(obs_delist - float(np.mean(post_delists))) / obs_delist if obs_delist > 0 else 0.0
    checks.append(CheckResult(
        name="national_delisting_rate",
        description="National annual waitlist delisting rate",
        observed=round(obs_delist, 4),
        posterior_mean=round(float(np.mean(post_delists)), 4),
        posterior_ci_90=(round(ci[0], 4), round(ci[1], 4)),
        inside_ci=inside,
        discrepancy=round(disc, 4),
        passed=disc < 0.25,
    ))

    # ------------------------------------------------------------------
    # 8. Urgency multipliers — monotonicity check
    # ------------------------------------------------------------------
    post_urg = np.array([d["urg_multipliers"][:len(URGENCY_LEVELS)] for d in draws])
    post_urg_mean = np.mean(post_urg, axis=0)
    # Urgency multipliers should be monotonically increasing (higher urgency → higher mortality)
    is_monotone = all(post_urg_mean[i] <= post_urg_mean[i + 1] for i in range(len(post_urg_mean) - 1))
    checks.append(CheckResult(
        name="urgency_monotonicity",
        description="Posterior urgency multipliers are monotonically increasing",
        observed=1.0,  # expected: monotone
        posterior_mean=1.0 if is_monotone else 0.0,
        posterior_ci_90=(0.0, 1.0),
        inside_ci=is_monotone,
        discrepancy=0.0 if is_monotone else 1.0,
        passed=is_monotone,
    ))

    # ------------------------------------------------------------------
    # Aggregate calibration
    # ------------------------------------------------------------------
    interval_checks = [c for c in checks if c.name not in {
        "city_wait_factor_rank", "blood_type_rank",
        "city_factor_calibration", "urgency_monotonicity",
    }]
    n_inside = sum(1 for c in interval_checks if c.inside_ci)
    calibration = n_inside / len(interval_checks) if interval_checks else 0.0

    n_passed = sum(1 for c in checks if c.passed)
    overall = n_passed >= len(checks) * 0.7  # 70% of checks must pass

    notes = []
    if calibration < 0.5:
        notes.append(
            f"Poor calibration: only {n_inside}/{len(interval_checks)} "
            "interval checks have observed values inside 90% posterior CI"
        )
    failed_names = [c.name for c in checks if not c.passed]
    if failed_names:
        notes.append(f"Failed checks: {', '.join(failed_names)}")

    logger.info(
        "Posterior checks %s: %d/%d passed, calibration=%.2f",
        organ, n_passed, len(checks), calibration,
    )

    return PosteriorCheckReport(
        organ=organ,
        n_draws=N_DRAWS,
        checks=checks,
        calibration_fraction=round(calibration, 3),
        overall_passed=overall,
        notes=notes,
    )
