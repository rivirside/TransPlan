"""
MCMC Hierarchical Survival Model — Phase 5 M3.

Bayesian hierarchical model for transplant wait times, mortality, and
delisting rates.  Uses PyMC NUTS sampler to produce posterior distributions
over all parameters, enabling honest uncertainty quantification.

Architecture
------------
- One model per organ (6 total, separate traces)
- Three-level hierarchy: national → city → patient effects
- Fit on aggregate SRTR data (center-level summary statistics)
- Posterior traces cached as ArviZ NetCDF files (~10-50 MB each)

Observation model
-----------------
Observed city-level factors are noisy estimates of true underlying rates.
The hierarchical structure provides adaptive shrinkage (partial pooling):
- Small-volume centers shrink toward the national mean
- Large-volume centers retain their empirical estimates

Offline fitting takes 2-30 minutes per organ.  At query time, we sample
from the cached trace in ~50-200 ms (no re-fitting).
"""

import json
import logging
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np
import pymc as pm

from config import DATA_DIR

logger = logging.getLogger(__name__)

TRACE_DIR = DATA_DIR / "mcmc-traces"
ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
BLOOD_TYPES = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
URGENCY_LEVELS = [1, 2, 3, 4]


def trace_path(organ: str, granularity: str = "state") -> Path:
    """Return the path for a trace file at the given granularity.

    (#293: the legacy 22-city 'classic' granularity and its bare {organ}.nc
    trace naming are retired.)
    """
    if granularity == "classic":
        raise ValueError(
            "The 22-city 'classic' granularity was retired (#293); use 'state' or 'full'."
        )
    return TRACE_DIR / f"{organ}-{granularity}.nc"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_organ_data(organ: str, granularity: str = "state") -> dict[str, Any]:
    """Load and prepare all observed data for a single organ model.

    Parameters
    ----------
    organ : str
        One of ORGANS.
    granularity : str
        Region granularity for the model:
        - "state": ~50 US states (centers grouped by state)
        - "full":  ~248 individual SRTR center codes
        ("classic" — the legacy 22-city mode — was retired, #293.)
    """
    # National-level organ data (needed for all granularities)
    with open(DATA_DIR / "wait-time-distributions.json") as f:
        wt_data = json.load(f)
    with open(DATA_DIR / "competing-risks.json") as f:
        cr_data = json.load(f)

    organ_wt = wt_data[organ]
    organ_cr = cr_data[organ]

    # Blood type multipliers (organ-level, not region-level)
    bt_mults_raw = organ_wt.get("blood_type_multipliers", {})
    bt_mults = np.array([bt_mults_raw.get(bt, 1.0) for bt in BLOOD_TYPES], dtype=np.float64)

    # Urgency mortality multipliers
    urg_raw = organ_cr.get("urgency_mortality_multipliers", {})
    urg_mults = np.array([urg_raw.get(str(u), 1.0) for u in URGENCY_LEVELS], dtype=np.float64)

    # Age mortality multipliers
    age_raw = cr_data.get("age_mortality_multipliers", {})
    age_mults = {
        "18-34": age_raw.get("18-34", 0.4),
        "35-49": age_raw.get("35-49", 0.7),
        "50-64": age_raw.get("50-64", 1.0),
        "65+": age_raw.get("65+", 1.9),
    }

    if granularity == "classic":
        raise ValueError(
            "The 22-city 'classic' granularity was retired (#293); use 'state' or 'full'."
        )
    else:
        # state / full: Use center-level data with dynamic region grouping
        from services.bbn_parameterizer import get_center_to_region_map, get_regions
        from services.data_loader import get_data

        regions = get_regions(granularity)
        center_map = get_center_to_region_map(granularity)
        center_data = get_data()

        center_wt = center_data.center_wait_times.get("center_wait_time_factors", {})
        center_cr = center_data.center_competing_risks.get("center_adjustments", {})

        wait_factors = []
        mort_factors = []
        delist_factors = []
        for region in regions:
            codes = [c for c, r in center_map.items() if r == region]
            wf = [center_wt.get(c, {}).get(organ, 1.0) for c in codes]
            mf = [center_cr.get(c, {}).get(organ, {}).get("mortality_factor", 1.0) for c in codes]
            df = [center_cr.get(c, {}).get(organ, {}).get("delisting_factor", 1.0) for c in codes]
            wait_factors.append(sum(wf) / max(len(wf), 1))
            mort_factors.append(sum(mf) / max(len(mf), 1))
            delist_factors.append(sum(df) / max(len(df), 1))

        cities = regions
        city_wait_factors = np.array(wait_factors, dtype=np.float64)
        city_mort_factors = np.array(mort_factors, dtype=np.float64)
        city_delist_factors = np.array(delist_factors, dtype=np.float64)

    return {
        "organ": organ,
        "cities": cities,
        "n_cities": len(cities),
        "national_median": organ_wt["national_median_months"],
        "log_sigma": organ_wt["log_sigma"],
        "city_wait_factors": city_wait_factors,
        "city_mort_factors": city_mort_factors,
        "city_delist_factors": city_delist_factors,
        "national_mort_rate": organ_cr["annual_mortality_rate"],
        "national_delist_rate": organ_cr["annual_delisting_rate"],
        "bt_mults": bt_mults,
        "urg_mults": urg_mults,
        "age_mults": age_mults,
    }


# ---------------------------------------------------------------------------
# Model specification
# ---------------------------------------------------------------------------

# Empirical signal-fraction priors (#317, replaces the flat Beta(2,2) guess).
# From scripts/run-panel-variance.py: unbalanced one-way random-effects ANOVA
# on the center x release panel (~13 SRTR releases) — PER METRIC, because the
# splits differ enormously: wait factors are dominated by persistent center
# signal (raw 0.63-0.86) while mortality/delisting rates are mostly
# release-to-release noise (0.04-0.33; small cohorts make annual death rates
# very noisy). The flat Beta(2,2) was therefore simultaneously UNDER-trusting
# center wait differences and OVER-trusting center-specific death rates.
# Raw (conservative lower-bound) estimates as prior means, clamped to
# [0.1, 0.9] for Beta shape sanity, concentration 10 (mildly informative).
# Missing panels (intestine wait: 16 centers) keep Beta(2,2).
# Source: docs/panel-variance-report.md. Register: MCMC-34 (updated).
EMPIRICAL_FRAC_SIGNAL = {
    "kidney":   {"wait": 0.86, "mort": 0.17, "delist": 0.32},
    "liver":    {"wait": 0.77, "mort": 0.24, "delist": 0.29},
    "heart":    {"wait": 0.68, "mort": 0.13, "delist": 0.22},
    "lung":     {"wait": 0.77, "mort": 0.33, "delist": 0.11},
    "pancreas": {"wait": 0.63, "mort": 0.10, "delist": 0.12},
    "intestine": {"mort": 0.10, "delist": 0.10},
}
_FRAC_PRIOR_CONCENTRATION = 10.0


def _frac_signal_prior_params(organ: str, metric: str) -> tuple[float, float]:
    """(alpha, beta) for the signal-fraction Beta prior of (organ, metric)."""
    mean = EMPIRICAL_FRAC_SIGNAL.get(organ, {}).get(metric)
    if mean is None:
        return 2.0, 2.0
    mean = min(0.9, max(0.1, mean))
    return mean * _FRAC_PRIOR_CONCENTRATION, (1.0 - mean) * _FRAC_PRIOR_CONCENTRATION


def build_organ_model(data: dict[str, Any]) -> pm.Model:
    """
    Build a PyMC hierarchical model for a single organ.

    The model has three levels:
      Level 0 (national): hyperpriors on median wait, mortality, delisting
      Level 1 (city):     random effects on wait/mortality/delisting factors
      Level 2 (patient):  blood type and urgency effects

    Observed data = our aggregate SRTR-derived point estimates.
    Observation noise is modeled as a learned parameter (sigma_obs_*).

    Returns a PyMC Model (not yet sampled).
    """
    n_cities = data["n_cities"]
    n_bt = len(BLOOD_TYPES)
    n_urg = len(URGENCY_LEVELS)

    # Observed values (log-transformed where multiplicative)
    obs_log_city_wait = np.log(data["city_wait_factors"])
    obs_log_city_mort = np.log(data["city_mort_factors"])
    obs_log_city_delist = np.log(data["city_delist_factors"])
    obs_log_bt = np.log(data["bt_mults"])
    obs_log_urg = np.log(data["urg_mults"])

    with pm.Model() as model:
        # ===== Level 0: National hyperpriors =====
        # HONESTY NOTE (#257): the national-level prior means below are anchored
        # to the same SRTR-derived point estimates the Monte Carlo engine uses,
        # with tight sigmas, and the likelihood observes aggregate factors (one
        # observation per latent, no event/censoring data). The posterior is
        # therefore pinned near the MC values — this engine quantifies parameter
        # uncertainty / propagates it; it does NOT independently validate the MC
        # point estimates. Do not frame cross-engine agreement as validation.

        # Log-normal wait time: national median and shape
        log_median_national = pm.Normal(
            "log_median_national",
            mu=np.log(data["national_median"]),
            sigma=0.3,
        )
        log_sigma = pm.TruncatedNormal(
            "log_sigma",
            mu=data["log_sigma"],
            sigma=0.15,
            lower=0.3,
            upper=2.5,
        )

        # National mortality and delisting rates (log-scale)
        log_mort_national = pm.Normal(
            "log_mort_national",
            mu=np.log(data["national_mort_rate"]),
            sigma=0.3,
        )
        log_delist_national = pm.Normal(
            "log_delist_national",
            mu=np.log(data["national_delist_rate"]),
            sigma=0.3,
        )

        # ===== Level 1: City random effects (shared frailty) =====
        #
        # Mortality and delisting offsets are drawn from a bivariate normal
        # with an LKJ-Cholesky correlation prior.  This learns the
        # mort ↔ delist correlation from data rather than imposing a fixed
        # copula θ at query time.  Wait-time offsets remain independent
        # (supply-side; different causal pathway from mortality/delisting).

        # Wait-time city offsets (independent — supply-driven).
        #
        # IDENTIFIABILITY (#207, MCMC-09): with ONE observation per center,
        # obs_i ~ N(offset_i, σ_obs) with offset_i ~ N(0, σ_city) identifies
        # only σ_city² + σ_obs²; the split is prior-driven. Sampling σ_city
        # and σ_obs separately puts NUTS on that ridge (kidney full-mode fit:
        # R-hat 1.07–1.08, ESS ~40 in both centered and non-centered forms).
        # Reparameterize honestly: sample the IDENTIFIED total spread and an
        # explicitly prior-driven signal fraction. Offsets stay CENTERED —
        # with strongly informative per-group likelihoods, centered is the
        # well-conditioned form (non-centering helps only weak-data groups).
        _organ = data.get("organ", "")
        wait_a, wait_b = _frac_signal_prior_params(_organ, "wait")
        mort_a, mort_b = _frac_signal_prior_params(_organ, "mort")
        delist_a, delist_b = _frac_signal_prior_params(_organ, "delist")
        sigma_total_wait = pm.HalfNormal("sigma_total_wait", sigma=0.5)
        frac_signal_wait = pm.Beta("frac_signal_wait", alpha=wait_a, beta=wait_b)
        sigma_city_wait = pm.Deterministic(
            "sigma_city_wait", sigma_total_wait * pm.math.sqrt(frac_signal_wait),
        )
        city_wait_offset = pm.Normal(
            "city_wait_offset",
            mu=0,
            sigma=sigma_city_wait,
            shape=n_cities,
        )

        # Mortality × Delisting: shared frailty with an LKJ correlation prior
        # (η=2 weakly favors small correlations). Same identifiability ridge
        # as the wait side (one observation per center), so the same
        # total-spread × signal-fraction reparameterization is applied to
        # each dimension; the 2x2 Cholesky is built explicitly from the
        # derived city sigmas and the LKJ correlation. (The old code also had
        # a bug: separate sigma_city_mort/delist HalfNormals were never
        # connected to the offsets — the dead `city_sd` stack — so their
        # posteriors were pure prior.)
        sigma_total_mort = pm.HalfNormal("sigma_total_mort", sigma=0.5)
        frac_signal_mort = pm.Beta("frac_signal_mort", alpha=mort_a, beta=mort_b)
        sigma_city_mort = pm.Deterministic(
            "sigma_city_mort", sigma_total_mort * pm.math.sqrt(frac_signal_mort),
        )
        sigma_total_delist = pm.HalfNormal("sigma_total_delist", sigma=0.5)
        frac_signal_delist = pm.Beta("frac_signal_delist", alpha=delist_a, beta=delist_b)
        sigma_city_delist = pm.Deterministic(
            "sigma_city_delist", sigma_total_delist * pm.math.sqrt(frac_signal_delist),
        )

        # LKJ(η) on a 2x2 correlation is exactly ρ = 2·Beta(η, η) − 1
        # (version-proof; this pymc's LKJCorr API lacks return_matrix).
        rho_beta = pm.Beta("mort_delist_rho_beta", alpha=2.0, beta=2.0)
        rho = 2.0 * rho_beta - 1.0

        # Explicit 2x2 Cholesky: [[σm, 0], [σd·ρ, σd·√(1-ρ²)]]
        chol = pm.math.stack([
            pm.math.stack([sigma_city_mort, 0.0]),
            pm.math.stack([sigma_city_delist * rho,
                           sigma_city_delist * pm.math.sqrt(1.0 - rho ** 2)]),
        ])

        # (n_cities, 2) joint offsets — columns: [mort, delist]. Centered
        # (see identifiability note above).
        city_joint_offset = pm.MvNormal(
            "city_joint_offset",
            mu=0,
            chol=chol,
            shape=(n_cities, 2),
        )

        # Unpack for readability and backward compat with observation model
        city_mort_offset = pm.Deterministic(
            "city_mort_offset", city_joint_offset[:, 0]
        )
        city_delist_offset = pm.Deterministic(
            "city_delist_offset", city_joint_offset[:, 1]
        )

        # Expose the learned correlation as a named deterministic
        pm.Deterministic("mort_delist_corr", rho)

        # ===== Level 2: Patient-level effects =====

        # Blood type effects (log-scale)
        sigma_bt = pm.HalfNormal("sigma_bt", sigma=0.3)
        bt_effect = pm.Normal(
            "bt_effect",
            mu=0,
            sigma=sigma_bt,
            shape=n_bt,
        )

        # Urgency mortality effects (log-scale)
        sigma_urg = pm.HalfNormal("sigma_urg", sigma=0.4)
        urg_effect = pm.Normal(
            "urg_effect",
            mu=0,
            sigma=sigma_urg,
            shape=n_urg,
        )

        # ===== Observation model =====
        # Our SRTR-derived point estimates are noisy observations of the
        # true underlying parameters.  Observation noise is learned.

        # sigma_obs_wait is the complement of the wait signal fraction (see
        # identifiability note above): total² = city² + obs².
        sigma_obs_wait = pm.Deterministic(
            "sigma_obs_wait", sigma_total_wait * pm.math.sqrt(1.0 - frac_signal_wait),
        )
        sigma_obs_mort = pm.Deterministic(
            "sigma_obs_mort", sigma_total_mort * pm.math.sqrt(1.0 - frac_signal_mort),
        )
        sigma_obs_delist = pm.Deterministic(
            "sigma_obs_delist", sigma_total_delist * pm.math.sqrt(1.0 - frac_signal_delist),
        )
        sigma_obs_bt = pm.HalfNormal("sigma_obs_bt", sigma=0.10)
        sigma_obs_urg = pm.HalfNormal("sigma_obs_urg", sigma=0.10)

        # Likelihood: observed factors ~ Normal(latent offset, sigma_obs)
        pm.Normal(
            "obs_city_wait",
            mu=city_wait_offset,
            sigma=sigma_obs_wait,
            observed=obs_log_city_wait,
        )
        pm.Normal(
            "obs_city_mort",
            mu=city_mort_offset,
            sigma=sigma_obs_mort,
            observed=obs_log_city_mort,
        )
        pm.Normal(
            "obs_city_delist",
            mu=city_delist_offset,
            sigma=sigma_obs_delist,
            observed=obs_log_city_delist,
        )
        pm.Normal(
            "obs_bt",
            mu=bt_effect,
            sigma=sigma_obs_bt,
            observed=obs_log_bt,
        )
        pm.Normal(
            "obs_urg",
            mu=urg_effect,
            sigma=sigma_obs_urg,
            observed=obs_log_urg,
        )

        # ===== Derived quantities =====
        # Exponentiate for convenience (saved in trace as deterministics)
        pm.Deterministic("city_wait_factor", pm.math.exp(city_wait_offset))
        pm.Deterministic("national_median_months", pm.math.exp(log_median_national))
        pm.Deterministic("national_mort_rate", pm.math.exp(log_mort_national))
        pm.Deterministic("national_delist_rate", pm.math.exp(log_delist_national))
        pm.Deterministic("bt_multiplier", pm.math.exp(bt_effect))
        pm.Deterministic("urg_multiplier", pm.math.exp(urg_effect))

    return model


# ---------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------

def fit_organ_model(
    organ: str,
    n_samples: int = 2000,
    n_chains: int = 2,
    n_tune: int = 1000,
    random_seed: int = 42,
    target_accept: float = 0.90,
    granularity: str = "state",
    cores: int | None = None,
) -> az.InferenceData:
    """
    Build and fit the hierarchical model for one organ.

    Returns an ArviZ InferenceData object containing the posterior trace.
    Typical runtime: 1-10 minutes depending on hardware.
    """
    data = load_organ_data(organ, granularity=granularity)
    model = build_organ_model(data)

    logger.info(
        "Fitting MCMC model for %s: %d samples × %d chains, %d tune",
        organ, n_samples, n_chains, n_tune,
    )

    with model:
        trace = pm.sample(
            draws=n_samples,
            chains=n_chains,
            tune=n_tune,
            random_seed=random_seed,
            target_accept=target_accept,
            return_inferencedata=True,
            progressbar=True,
            # cores=1 runs chains sequentially — needed in environments where
            # pymc's fork/spawn workers die (headless shells on macOS)
            **({"cores": cores} if cores else {}),
        )

    # Add metadata
    trace.attrs["organ"] = organ
    trace.attrs["n_cities"] = data["n_cities"]
    trace.attrs["cities"] = json.dumps(data["cities"])
    trace.attrs["blood_types"] = json.dumps(BLOOD_TYPES)

    # Log diagnostics
    summary = az.summary(trace, var_names=["sigma_city_wait", "sigma_city_mort", "log_sigma"])
    logger.info("Fit complete for %s. Key diagnostics:\n%s", organ, summary.to_string())

    return trace


def save_trace(organ: str, trace: az.InferenceData, granularity: str = "state") -> Path:
    """Save an ArviZ trace to NetCDF file."""
    path = trace_path(organ, granularity)
    path.parent.mkdir(parents=True, exist_ok=True)
    trace.to_netcdf(str(path))
    logger.info("Saved trace for %s to %s (%.1f MB)", organ, path, path.stat().st_size / 1e6)
    return path


def load_trace(organ: str, granularity: str = "state") -> az.InferenceData | None:
    """Load a cached ArviZ trace.  Returns None if not found."""
    path = trace_path(organ, granularity)
    if not path.exists():
        return None
    trace = az.from_netcdf(str(path))
    logger.info("Loaded cached trace for %s from %s", organ, path)
    return trace


def trace_exists(organ: str, granularity: str = "state") -> bool:
    """Check whether a cached trace file exists for the given organ."""
    return trace_path(organ, granularity).exists()


def find_fitted_granularity(organ: str) -> str | None:
    """First granularity with a fitted trace on disk (state preferred).

    Validation consumers (posterior_checks, convergence) must resolve the
    trace the same way inference does — fit-mcmc-model.py defaults to
    --granularity full, so a bare default of "state" would report "no trace"
    for organs /simulate happily serves (2026-08 review finding).
    """
    for g in ("state", "full"):
        if trace_exists(organ, g):
            return g
    return None


# ---------------------------------------------------------------------------
# Parameter extraction from trace
# ---------------------------------------------------------------------------

def sample_params_from_trace(
    trace: az.InferenceData,
    n_draws: int = 1,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """
    Draw a random parameter set from the posterior trace.

    Returns a dict with:
      - national_median: float
      - log_sigma: float
      - city_wait_factors: array of shape (n_cities,)
      - national_mort_rate: float
      - national_delist_rate: float
      - city_mort_offsets: array of shape (n_cities,)  [log-scale]
      - city_delist_offsets: array of shape (n_cities,) [log-scale]
      - bt_multipliers: array of shape (8,)
      - urg_multipliers: array of shape (4,)
      - mort_delist_corr: float (learned correlation, -1 to 1)
      - cities: list of city names
    """
    if rng is None:
        rng = np.random.default_rng()

    posterior = trace.posterior
    n_chain = posterior.dims["chain"]
    n_sample = posterior.dims["draw"]
    total_draws = n_chain * n_sample

    # Pick random draw indices
    flat_idx = rng.integers(0, total_draws, size=n_draws)
    chain_idx = flat_idx // n_sample
    draw_idx = flat_idx % n_sample

    # Extract learned mort↔delist correlation if available (shared frailty model)
    has_corr = "mort_delist_corr" in posterior

    # For single draw, return scalars/1D arrays
    if n_draws == 1:
        c, d = int(chain_idx[0]), int(draw_idx[0])
        cities = json.loads(str(trace.attrs.get("cities", "[]")))

        return {
            "national_median": float(posterior["national_median_months"].values[c, d]),
            "log_sigma": float(posterior["log_sigma"].values[c, d]),
            "city_wait_factors": posterior["city_wait_factor"].values[c, d, :].astype(np.float64),
            "national_mort_rate": float(posterior["national_mort_rate"].values[c, d]),
            "national_delist_rate": float(posterior["national_delist_rate"].values[c, d]),
            "city_mort_offsets": posterior["city_mort_offset"].values[c, d, :].astype(np.float64),
            "city_delist_offsets": posterior["city_delist_offset"].values[c, d, :].astype(np.float64),
            "bt_multipliers": posterior["bt_multiplier"].values[c, d, :].astype(np.float64),
            "urg_multipliers": posterior["urg_multiplier"].values[c, d, :].astype(np.float64),
            "mort_delist_corr": float(posterior["mort_delist_corr"].values[c, d]) if has_corr else 0.0,
            "cities": cities,
        }

    # For multiple draws, return arrays with leading n_draws dimension
    results = []
    cities = json.loads(str(trace.attrs.get("cities", "[]")))
    for i in range(n_draws):
        c, d = int(chain_idx[i]), int(draw_idx[i])
        results.append({
            "national_median": float(posterior["national_median_months"].values[c, d]),
            "log_sigma": float(posterior["log_sigma"].values[c, d]),
            "city_wait_factors": posterior["city_wait_factor"].values[c, d, :].astype(np.float64),
            "national_mort_rate": float(posterior["national_mort_rate"].values[c, d]),
            "national_delist_rate": float(posterior["national_delist_rate"].values[c, d]),
            "city_mort_offsets": posterior["city_mort_offset"].values[c, d, :].astype(np.float64),
            "city_delist_offsets": posterior["city_delist_offset"].values[c, d, :].astype(np.float64),
            "bt_multipliers": posterior["bt_multiplier"].values[c, d, :].astype(np.float64),
            "urg_multipliers": posterior["urg_multiplier"].values[c, d, :].astype(np.float64),
            "mort_delist_corr": float(posterior["mort_delist_corr"].values[c, d]) if has_corr else 0.0,
            "cities": cities,
        })
    return results
