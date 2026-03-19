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


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_organ_data(organ: str) -> dict[str, Any]:
    """Load and prepare all observed data for a single organ model."""
    with open(DATA_DIR / "wait-time-distributions.json") as f:
        wt_data = json.load(f)
    with open(DATA_DIR / "competing-risks.json") as f:
        cr_data = json.load(f)

    organ_wt = wt_data[organ]
    organ_cr = cr_data[organ]

    # City-level wait time factors (shared across organs)
    city_factors_raw = wt_data.get("city_wait_time_factors", {})
    cities = sorted(k for k in city_factors_raw if not k.startswith("_"))
    city_wait_factors = np.array([city_factors_raw[c] for c in cities], dtype=np.float64)

    # City-level competing risk adjustments (shared across organs)
    city_adj_raw = cr_data.get("city_adjustments", {})
    city_mort_factors = np.array(
        [city_adj_raw.get(c, {}).get("mortality_factor", 1.0) for c in cities],
        dtype=np.float64,
    )
    city_delist_factors = np.array(
        [city_adj_raw.get(c, {}).get("delisting_factor", 1.0) for c in cities],
        dtype=np.float64,
    )

    # Blood type multipliers
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

        # ===== Level 1: City random effects =====

        # Hierarchical standard deviations
        sigma_city_wait = pm.HalfNormal("sigma_city_wait", sigma=0.4)
        sigma_city_mort = pm.HalfNormal("sigma_city_mort", sigma=0.4)
        sigma_city_delist = pm.HalfNormal("sigma_city_delist", sigma=0.4)

        # City-level offsets (log-scale, centered at 0 = national average)
        city_wait_offset = pm.Normal(
            "city_wait_offset",
            mu=0,
            sigma=sigma_city_wait,
            shape=n_cities,
        )
        city_mort_offset = pm.Normal(
            "city_mort_offset",
            mu=0,
            sigma=sigma_city_mort,
            shape=n_cities,
        )
        city_delist_offset = pm.Normal(
            "city_delist_offset",
            mu=0,
            sigma=sigma_city_delist,
            shape=n_cities,
        )

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

        sigma_obs_wait = pm.HalfNormal("sigma_obs_wait", sigma=0.15)
        sigma_obs_mort = pm.HalfNormal("sigma_obs_mort", sigma=0.15)
        sigma_obs_delist = pm.HalfNormal("sigma_obs_delist", sigma=0.15)
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
) -> az.InferenceData:
    """
    Build and fit the hierarchical model for one organ.

    Returns an ArviZ InferenceData object containing the posterior trace.
    Typical runtime: 1-10 minutes depending on hardware.
    """
    data = load_organ_data(organ)
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


def save_trace(organ: str, trace: az.InferenceData) -> Path:
    """Save an ArviZ trace to NetCDF file."""
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    path = TRACE_DIR / f"{organ}.nc"
    trace.to_netcdf(str(path))
    logger.info("Saved trace for %s to %s (%.1f MB)", organ, path, path.stat().st_size / 1e6)
    return path


def load_trace(organ: str) -> az.InferenceData | None:
    """Load a cached ArviZ trace.  Returns None if not found."""
    path = TRACE_DIR / f"{organ}.nc"
    if not path.exists():
        return None
    trace = az.from_netcdf(str(path))
    logger.info("Loaded cached trace for %s from %s", organ, path)
    return trace


def trace_exists(organ: str) -> bool:
    """Check whether a cached trace file exists for the given organ."""
    return (TRACE_DIR / f"{organ}.nc").exists()


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
            "cities": cities,
        })
    return results
