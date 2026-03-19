"""
CPT parameterizer for the Bayesian Belief Network (Phase 5 M1).

Constructs all Conditional Probability Tables (CPTs) from existing TransPlan
data files — no data duplication. Each CPT builder reads from:
  - data/wait-time-distributions.json  (medians, blood type multipliers, city factors)
  - data/competing-risks.json          (mortality/delisting rates, urgency/age/city multipliers)
  - data/cause-of-death-by-region.json (organ recovery rates, state proportions)
  - data/post-transplant-outcomes.json (graft/patient survival, hazard ratios)

The BBN has 12 nodes arranged in a DAG:
  Evidence (5):  Organ, BloodType, AgeGroup, Urgency, Region
  Latent (3):    DonorSupply, WaitCategory, MortalityRisk
  Outcome (2):   DelistingRisk, CompetingOutcome
  Post-tx (2):   GraftSurvival1yr, CompoundSuccess

All CPTs are TabularCPD objects for pgmpy's BayesianNetwork.
"""
import json
import logging
from pathlib import Path

import numpy as np

from config import DATA_DIR

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Domain enumerations — shared across CPT builders and inference engine
# ──────────────────────────────────────────────────────────────────────

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
BLOOD_TYPES = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
AGE_GROUPS = ["18-34", "35-49", "50-64", "65+"]
URGENCY_LEVELS = [1, 2, 3, 4]
# Regions = 22 cities, indexed by position in this list
REGIONS = [
    "Pittsburgh", "Baltimore", "Philadelphia", "New York",
    "Minneapolis", "Madison", "Chicago", "Cleveland",
    "St. Louis", "Indianapolis", "Omaha", "Rochester",
    "Nashville", "Durham", "Miami", "Dallas",
    "Houston", "Portland", "Seattle", "San Francisco",
    "Los Angeles", "Palo Alto",
]

# City → state abbreviation (for COD lookup)
_CITY_STATE = {
    "Pittsburgh": "PA", "Baltimore": "MD", "Philadelphia": "PA",
    "New York": "NY", "Minneapolis": "MN", "Madison": "WI",
    "Chicago": "IL", "Cleveland": "OH", "St. Louis": "MO",
    "Indianapolis": "IN", "Omaha": "NE", "Rochester": "MN",
    "Nashville": "TN", "Durham": "NC", "Miami": "FL",
    "Dallas": "TX", "Houston": "TX", "Portland": "OR",
    "Seattle": "WA", "San Francisco": "CA", "Los Angeles": "CA",
    "Palo Alto": "CA",
}

_STATE_FULL_NAMES = {
    "PA": "Pennsylvania", "MD": "Maryland", "NY": "New York",
    "MN": "Minnesota", "WI": "Wisconsin", "IL": "Illinois",
    "OH": "Ohio", "MO": "Missouri", "IN": "Indiana",
    "NE": "Nebraska", "TN": "Tennessee", "NC": "North Carolina",
    "FL": "Florida", "TX": "Texas", "OR": "Oregon",
    "WA": "Washington", "CA": "California",
}

# Discrete states for latent/outcome nodes
DONOR_SUPPLY_STATES = ["low", "medium", "high"]
WAIT_CATEGORY_STATES = ["short", "moderate", "long", "very_long"]
MORTALITY_RISK_STATES = ["low", "moderate", "high"]
DELISTING_RISK_STATES = ["low", "moderate", "high"]
COMPETING_OUTCOME_STATES = ["transplant", "mortality", "delisting", "still_waiting"]
GRAFT_SURVIVAL_STATES = ["good", "moderate", "poor"]
COMPOUND_SUCCESS_STATES = ["success", "partial", "failure"]


# ──────────────────────────────────────────────────────────────────────
# Data loading (cached module-level)
# ──────────────────────────────────────────────────────────────────────

_cache: dict = {}


def _load_data() -> dict:
    """Load all data files needed for CPT construction. Cached."""
    if _cache:
        return _cache

    def _read(filename: str) -> dict:
        path = DATA_DIR / filename
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {k: v for k, v in raw.items() if k != "_meta"}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning("BBN parameterizer: could not load %s: %s", filename, e)
            return {}

    _cache["wait_time"] = _read("wait-time-distributions.json")
    _cache["competing_risks"] = _read("competing-risks.json")
    _cache["cod"] = _read("cause-of-death-by-region.json")
    _cache["outcomes"] = _read("post-transplant-outcomes.json")

    return _cache


def clear_cache() -> None:
    """Clear cached data (for testing)."""
    _cache.clear()


# ──────────────────────────────────────────────────────────────────────
# Helper: normalize a probability vector to sum to 1
# ──────────────────────────────────────────────────────────────────────

def _normalize(arr: np.ndarray) -> np.ndarray:
    """Normalize array to sum to 1. If all zeros, return uniform."""
    s = arr.sum()
    if s <= 0:
        return np.ones_like(arr) / len(arr)
    return arr / s


# ──────────────────────────────────────────────────────────────────────
# CPT 1: DonorSupply — P(DonorSupply | Organ, BloodType, Region)
#
# Combines:
#   - Blood type multiplier (higher = longer wait = lower supply for that type)
#   - COD multiplier per region/organ (higher = more donors = higher supply)
# Discretized into low/medium/high
# ──────────────────────────────────────────────────────────────────────

def _compute_cod_multiplier(organ: str, state_abbrev: str) -> float:
    """Deterministic COD multiplier for one organ × state. Returns ~1.0."""
    data = _load_data()
    cod = data.get("cod", {})
    recovery_rates = cod.get("organRecoveryRates", {}).get(organ)
    state_name = _STATE_FULL_NAMES.get(state_abbrev)
    if not recovery_rates or not state_name:
        return 1.0

    proportions = cod.get("stateCauseOfDeathProportions", {}).get(state_name)
    if not proportions:
        return 1.0

    categories = ["trauma", "cardiovascular", "drug_intox", "stroke", "anoxia"]
    all_states = cod.get("stateCauseOfDeathProportions", {})
    if not all_states:
        return 1.0

    nat_total = sum(
        sum(sp.get(c, 0) * recovery_rates.get(c, 0) for c in categories)
        for sp in all_states.values()
    )
    nat_avg = nat_total / len(all_states)
    if nat_avg == 0:
        return 1.0

    state_score = sum(proportions.get(c, 0) * recovery_rates.get(c, 0) for c in categories)
    return state_score / nat_avg


def build_donor_supply_cpt() -> np.ndarray:
    """
    Build CPT for DonorSupply node.

    Shape: (3, n_organs, n_blood_types, n_regions)
    Axes:  [DonorSupply states, Organ, BloodType, Region]

    A composite score combines:
      - bt_factor: 1/bt_mult (higher bt_mult = longer wait = less supply)
      - cod_factor: COD multiplier (more donors for this organ in this region)
    The composite is discretized into low/medium/high terciles.
    """
    data = _load_data()
    wt = data.get("wait_time", {})

    n_o = len(ORGANS)
    n_b = len(BLOOD_TYPES)
    n_r = len(REGIONS)

    # Compute raw composite scores for all combinations
    scores = np.ones((n_o, n_b, n_r))

    for i, organ in enumerate(ORGANS):
        organ_data = wt.get(organ, {})
        bt_mults = organ_data.get("blood_type_multipliers", {})

        for j, bt in enumerate(BLOOD_TYPES):
            bt_mult = bt_mults.get(bt, 1.0)
            # Invert: higher bt_mult = longer wait = lower supply
            bt_factor = 1.0 / bt_mult if bt_mult > 0 else 1.0

            for k, city in enumerate(REGIONS):
                state = _CITY_STATE.get(city, "")
                cod_factor = _compute_cod_multiplier(organ, state)
                scores[i, j, k] = bt_factor * cod_factor

    # Build CPT: P(DonorSupply | Organ, BloodType, Region)
    # Compute tercile thresholds PER ORGAN to avoid cross-organ contamination (#59).
    # Different organs have fundamentally different supply/demand dynamics —
    # global terciles would misclassify organs with systematically different baselines.
    cpt = np.zeros((3, n_o, n_b, n_r))

    for i in range(n_o):
        organ_flat = scores[i, :, :].flatten()
        t33 = np.percentile(organ_flat, 33.3)
        t66 = np.percentile(organ_flat, 66.7)

        for j in range(n_b):
            for k in range(n_r):
                s = scores[i, j, k]
                if s <= t33:
                    # Low supply — high confidence
                    cpt[:, i, j, k] = [0.7, 0.25, 0.05]
                elif s <= t66:
                    # Medium supply
                    cpt[:, i, j, k] = [0.15, 0.7, 0.15]
                else:
                    # High supply
                    cpt[:, i, j, k] = [0.05, 0.25, 0.7]

    return cpt


# ──────────────────────────────────────────────────────────────────────
# CPT 2: WaitCategory — P(WaitCategory | Organ, BloodType, Region, DonorSupply)
#
# Discretizes the log-normal wait time CDF at 6/12/24 month boundaries.
# DonorSupply modulates the effective median (high supply → shorter wait).
# ──────────────────────────────────────────────────────────────────────

def build_wait_category_cpt() -> np.ndarray:
    """
    Build CPT for WaitCategory node.

    Shape: (4, n_organs, n_blood_types, n_regions, 3)
    Axes:  [WaitCategory states, Organ, BloodType, Region, DonorSupply]

    Uses log-normal CDF with adjusted median to compute:
      P(wait <= 6mo), P(6 < wait <= 12), P(12 < wait <= 24), P(wait > 24)
    """
    from scipy.stats import lognorm

    data = _load_data()
    wt = data.get("wait_time", {})
    city_factors = wt.get("city_wait_time_factors", {})
    # Remove _notes key
    city_factors = {k: v for k, v in city_factors.items() if k != "_notes"}

    n_o = len(ORGANS)
    n_b = len(BLOOD_TYPES)
    n_r = len(REGIONS)
    n_ds = 3  # DonorSupply states

    # DonorSupply effect on median: low → 1.2x longer, medium → 1.0, high → 0.8x
    ds_multipliers = [1.2, 1.0, 0.8]

    cpt = np.zeros((4, n_o, n_b, n_r, n_ds))

    for i, organ in enumerate(ORGANS):
        organ_data = wt.get(organ, {})
        national_median = organ_data.get("national_median_months", 12.0)
        sigma = organ_data.get("log_sigma", 1.0)
        bt_mults = organ_data.get("blood_type_multipliers", {})

        for j, bt in enumerate(BLOOD_TYPES):
            bt_mult = bt_mults.get(bt, 1.0)

            for k, city in enumerate(REGIONS):
                city_mult = city_factors.get(city, 1.0)

                for ds_idx in range(n_ds):
                    ds_mult = ds_multipliers[ds_idx]
                    adjusted_median = national_median * bt_mult * city_mult * ds_mult

                    # Log-normal CDF: P(T <= t) where scale=median
                    dist = lognorm(s=sigma, scale=adjusted_median)
                    p6 = float(dist.cdf(6))
                    p12 = float(dist.cdf(12))
                    p24 = float(dist.cdf(24))

                    probs = np.array([
                        p6,                # short: <= 6 months
                        p12 - p6,           # moderate: 6-12 months
                        p24 - p12,          # long: 12-24 months
                        1.0 - p24,          # very_long: > 24 months
                    ])
                    # Ensure non-negative and normalized
                    probs = np.maximum(probs, 0.001)
                    cpt[:, i, j, k, ds_idx] = _normalize(probs)

    return cpt


# ──────────────────────────────────────────────────────────────────────
# CPT 3: MortalityRisk — P(MortalityRisk | Organ, AgeGroup, Urgency, Region)
#
# Uses competing-risks.json annual mortality rates with:
#   - Urgency multipliers (per organ)
#   - Age multipliers (global + organ overrides)
#   - City mortality factors
# Discretized into low/moderate/high.
# ──────────────────────────────────────────────────────────────────────

def build_mortality_risk_cpt() -> np.ndarray:
    """
    Build CPT for MortalityRisk node.

    Shape: (3, n_organs, n_age_groups, n_urgency, n_regions)
    Axes:  [MortalityRisk states, Organ, AgeGroup, Urgency, Region]
    """
    data = _load_data()
    cr = data.get("competing_risks", {})
    city_adj = cr.get("city_adjustments", {})
    age_mults = cr.get("age_mortality_multipliers", {})
    age_overrides = cr.get("age_organ_overrides", {})

    n_o = len(ORGANS)
    n_a = len(AGE_GROUPS)
    n_u = len(URGENCY_LEVELS)
    n_r = len(REGIONS)

    # Compute raw annual mortality rates for all combinations
    rates = np.zeros((n_o, n_a, n_u, n_r))

    for i, organ in enumerate(ORGANS):
        organ_data = cr.get(organ, {})
        base_rate = organ_data.get("annual_mortality_rate", 0.03)
        urg_mults = organ_data.get("urgency_mortality_multipliers", {})
        organ_age_overrides = age_overrides.get(organ, {})

        for a, age_group in enumerate(AGE_GROUPS):
            # Age multiplier: organ-specific override or global
            age_mult = organ_age_overrides.get(age_group,
                        age_mults.get(age_group, 1.0))
            # Skip _notes keys
            if isinstance(age_mult, str):
                age_mult = 1.0

            for u, urgency in enumerate(URGENCY_LEVELS):
                urg_mult = urg_mults.get(str(urgency), 1.0)

                for r, city in enumerate(REGIONS):
                    city_data = city_adj.get(city, {})
                    city_mort = city_data.get("mortality_factor", 1.0)
                    if isinstance(city_mort, str):
                        city_mort = 1.0

                    rates[i, a, u, r] = base_rate * urg_mult * age_mult * city_mort

    # Determine tercile thresholds
    flat = rates.flatten()
    t33 = np.percentile(flat, 33.3)
    t66 = np.percentile(flat, 66.7)

    cpt = np.zeros((3, n_o, n_a, n_u, n_r))

    for i in range(n_o):
        for a in range(n_a):
            for u in range(n_u):
                for r in range(n_r):
                    rate = rates[i, a, u, r]
                    if rate <= t33:
                        cpt[:, i, a, u, r] = [0.7, 0.25, 0.05]
                    elif rate <= t66:
                        cpt[:, i, a, u, r] = [0.15, 0.7, 0.15]
                    else:
                        cpt[:, i, a, u, r] = [0.05, 0.25, 0.7]

    return cpt


# ──────────────────────────────────────────────────────────────────────
# CPT 4: DelistingRisk — P(DelistingRisk | Organ, Region, WaitCategory)
#
# Base delisting rate × city factor, modulated by wait category
# (longer wait → higher delisting risk).
# ──────────────────────────────────────────────────────────────────────

def build_delisting_risk_cpt() -> np.ndarray:
    """
    Build CPT for DelistingRisk node.

    Shape: (3, n_organs, n_regions, 4)
    Axes:  [DelistingRisk states, Organ, Region, WaitCategory]
    """
    data = _load_data()
    cr = data.get("competing_risks", {})
    city_adj = cr.get("city_adjustments", {})

    n_o = len(ORGANS)
    n_r = len(REGIONS)
    n_w = 4  # WaitCategory states

    # Wait category multipliers on delisting (longer wait → more likely to delist)
    wait_delist_mults = [0.5, 0.8, 1.2, 1.8]

    rates = np.zeros((n_o, n_r, n_w))

    for i, organ in enumerate(ORGANS):
        organ_data = cr.get(organ, {})
        base_rate = organ_data.get("annual_delisting_rate", 0.05)

        for r, city in enumerate(REGIONS):
            city_data = city_adj.get(city, {})
            city_delist = city_data.get("delisting_factor", 1.0)
            if isinstance(city_delist, str):
                city_delist = 1.0

            for w in range(n_w):
                rates[i, r, w] = base_rate * city_delist * wait_delist_mults[w]

    # Tercile thresholds
    flat = rates.flatten()
    t33 = np.percentile(flat, 33.3)
    t66 = np.percentile(flat, 66.7)

    cpt = np.zeros((3, n_o, n_r, n_w))

    for i in range(n_o):
        for r in range(n_r):
            for w in range(n_w):
                rate = rates[i, r, w]
                if rate <= t33:
                    cpt[:, i, r, w] = [0.7, 0.25, 0.05]
                elif rate <= t66:
                    cpt[:, i, r, w] = [0.15, 0.7, 0.15]
                else:
                    cpt[:, i, r, w] = [0.05, 0.25, 0.7]

    return cpt


# ──────────────────────────────────────────────────────────────────────
# CPT 5: CompetingOutcome — P(Outcome | WaitCategory, MortalityRisk, DelistingRisk)
#
# Analytical competing exponentials: given discrete wait/mortality/delisting
# risk levels, compute probability of each outcome at 24 months.
# ──────────────────────────────────────────────────────────────────────

def build_competing_outcome_cpt() -> np.ndarray:
    """
    Build CPT for CompetingOutcome node.

    Shape: (4, 4, 3, 3)
    Axes:  [CompetingOutcome states, WaitCategory, MortalityRisk, DelistingRisk]

    Uses analytical competing exponentials at 24-month horizon.
    """
    n_w = 4  # WaitCategory
    n_m = 3  # MortalityRisk
    n_d = 3  # DelistingRisk

    # Map discrete states to monthly rates
    # WaitCategory → transplant rate (events/month): based on median in category
    # short=3mo median → rate=1/3, moderate=9mo → 1/9, long=18mo → 1/18, very_long=30mo → 1/30
    transplant_rates = [1/3, 1/9, 1/18, 1/30]

    # MortalityRisk → monthly mortality rate
    # low: ~1%/yr = 0.01/12, moderate: ~3%/yr = 0.03/12, high: ~8%/yr = 0.08/12
    mortality_rates = [0.01/12, 0.03/12, 0.08/12]

    # DelistingRisk → monthly delisting rate
    # low: ~3%/yr, moderate: ~8%/yr, high: ~15%/yr
    delisting_rates = [0.03/12, 0.08/12, 0.15/12]

    horizon = 24.0  # months

    cpt = np.zeros((4, n_w, n_m, n_d))

    for w in range(n_w):
        for m in range(n_m):
            for d in range(n_d):
                lam_t = transplant_rates[w]
                lam_m = mortality_rates[m]
                lam_d = delisting_rates[d]
                lam_total = lam_t + lam_m + lam_d

                if lam_total <= 0:
                    cpt[:, w, m, d] = [0.25, 0.25, 0.25, 0.25]
                    continue

                # P(event i wins AND happens before horizon) =
                # (lam_i / lam_total) * (1 - exp(-lam_total * horizon))
                p_any_event = 1.0 - np.exp(-lam_total * horizon)

                p_transplant = (lam_t / lam_total) * p_any_event
                p_mortality = (lam_m / lam_total) * p_any_event
                p_delisting = (lam_d / lam_total) * p_any_event
                p_waiting = 1.0 - p_any_event

                probs = np.array([p_transplant, p_mortality, p_delisting, p_waiting])
                probs = np.maximum(probs, 0.001)
                cpt[:, w, m, d] = _normalize(probs)

    return cpt


# ──────────────────────────────────────────────────────────────────────
# CPT 6: GraftSurvival1yr — P(GraftSurvival | Organ, Region)
#
# From post-transplant-outcomes.json: center-level graft survival rates
# and hazard ratios → discretized into good/moderate/poor.
# ──────────────────────────────────────────────────────────────────────

def build_graft_survival_cpt() -> np.ndarray:
    """
    Build CPT for GraftSurvival1yr node.

    Shape: (3, n_organs, n_regions)
    Axes:  [GraftSurvival states, Organ, Region]
    """
    data = _load_data()
    outcomes = data.get("outcomes", {})
    city_outcomes = outcomes.get("city_outcomes", {})

    n_o = len(ORGANS)
    n_r = len(REGIONS)

    cpt = np.zeros((3, n_o, n_r))

    for i, organ in enumerate(ORGANS):
        national = outcomes.get(organ, {})
        nat_graft = national.get("national_graft_survival_1yr")

        for r, city in enumerate(REGIONS):
            city_data = city_outcomes.get(city, {}).get(organ, {})
            graft_1yr = city_data.get("graft_survival_1yr")
            hr = city_data.get("graft_hr_1yr")

            if graft_1yr is not None:
                # Use actual center-level data
                if graft_1yr >= 93:
                    cpt[:, i, r] = [0.75, 0.20, 0.05]
                elif graft_1yr >= 88:
                    cpt[:, i, r] = [0.20, 0.65, 0.15]
                else:
                    cpt[:, i, r] = [0.05, 0.25, 0.70]
            elif hr is not None and nat_graft is not None:
                # Use hazard ratio relative to national
                if hr < 0.8:
                    cpt[:, i, r] = [0.75, 0.20, 0.05]
                elif hr < 1.2:
                    cpt[:, i, r] = [0.20, 0.65, 0.15]
                else:
                    cpt[:, i, r] = [0.05, 0.25, 0.70]
            else:
                # No data — use national average or uniform
                if nat_graft is not None:
                    if nat_graft >= 93:
                        cpt[:, i, r] = [0.60, 0.30, 0.10]
                    elif nat_graft >= 88:
                        cpt[:, i, r] = [0.25, 0.55, 0.20]
                    else:
                        cpt[:, i, r] = [0.10, 0.35, 0.55]
                else:
                    cpt[:, i, r] = [0.33, 0.34, 0.33]

    return cpt


# ──────────────────────────────────────────────────────────────────────
# CPT 7: CompoundSuccess — P(CompoundSuccess | CompetingOutcome, GraftSurvival1yr)
#
# Deterministic composition:
#   - If not transplanted → failure
#   - If transplanted + good graft → success
#   - If transplanted + moderate graft → partial
#   - If transplanted + poor graft → failure
# ──────────────────────────────────────────────────────────────────────

def build_compound_success_cpt() -> np.ndarray:
    """
    Build CPT for CompoundSuccess node.

    Shape: (3, 4, 3)
    Axes:  [CompoundSuccess states, CompetingOutcome, GraftSurvival1yr]

    Near-deterministic: outcome determines success path.
    """
    n_co = 4  # CompetingOutcome states
    n_gs = 3  # GraftSurvival states

    cpt = np.zeros((3, n_co, n_gs))

    for co in range(n_co):
        for gs in range(n_gs):
            if co == 0:  # transplant
                if gs == 0:  # good graft
                    cpt[:, co, gs] = [0.85, 0.12, 0.03]
                elif gs == 1:  # moderate graft
                    cpt[:, co, gs] = [0.30, 0.50, 0.20]
                else:  # poor graft
                    cpt[:, co, gs] = [0.05, 0.25, 0.70]
            elif co == 1:  # mortality
                cpt[:, co, gs] = [0.0, 0.0, 1.0]
            elif co == 2:  # delisting
                cpt[:, co, gs] = [0.0, 0.15, 0.85]
            else:  # still_waiting
                cpt[:, co, gs] = [0.0, 0.30, 0.70]

    # Ensure no exact zeros (pgmpy requires strictly positive for some operations)
    cpt = np.maximum(cpt, 0.001)
    # Re-normalize each column
    for co in range(n_co):
        for gs in range(n_gs):
            cpt[:, co, gs] = _normalize(cpt[:, co, gs])

    return cpt


# ──────────────────────────────────────────────────────────────────────
# Evidence node priors (uniform — these get set as evidence during inference)
# ──────────────────────────────────────────────────────────────────────

def build_organ_prior() -> np.ndarray:
    """Uniform prior over organs (overridden by evidence)."""
    return np.ones(len(ORGANS)) / len(ORGANS)


def build_blood_type_prior() -> np.ndarray:
    """Uniform prior over blood types (overridden by evidence)."""
    return np.ones(len(BLOOD_TYPES)) / len(BLOOD_TYPES)


def build_age_group_prior() -> np.ndarray:
    """Uniform prior over age groups (overridden by evidence)."""
    return np.ones(len(AGE_GROUPS)) / len(AGE_GROUPS)


def build_urgency_prior() -> np.ndarray:
    """Uniform prior over urgency levels (overridden by evidence)."""
    return np.ones(len(URGENCY_LEVELS)) / len(URGENCY_LEVELS)


def build_region_prior() -> np.ndarray:
    """Uniform prior over regions (overridden by evidence)."""
    return np.ones(len(REGIONS)) / len(REGIONS)


# ──────────────────────────────────────────────────────────────────────
# Master builder — constructs all CPTs at once
# ──────────────────────────────────────────────────────────────────────

def build_all_cpts() -> dict[str, np.ndarray]:
    """
    Build all CPTs for the BBN. Returns dict of node_name → CPT array.

    CPT shapes:
      Organ:            (6,)
      BloodType:        (8,)
      AgeGroup:         (4,)
      Urgency:          (4,)
      Region:           (22,)
      DonorSupply:      (3, 6, 8, 22)
      WaitCategory:     (4, 6, 8, 22, 3)
      MortalityRisk:    (3, 6, 4, 4, 22)
      DelistingRisk:    (3, 6, 22, 4)
      CompetingOutcome: (4, 4, 3, 3)
      GraftSurvival1yr: (3, 6, 22)
      CompoundSuccess:  (3, 4, 3)
    """
    logger.info("Building all BBN CPTs from data files...")

    cpts = {
        "Organ": build_organ_prior(),
        "BloodType": build_blood_type_prior(),
        "AgeGroup": build_age_group_prior(),
        "Urgency": build_urgency_prior(),
        "Region": build_region_prior(),
        "DonorSupply": build_donor_supply_cpt(),
        "WaitCategory": build_wait_category_cpt(),
        "MortalityRisk": build_mortality_risk_cpt(),
        "DelistingRisk": build_delisting_risk_cpt(),
        "CompetingOutcome": build_competing_outcome_cpt(),
        "GraftSurvival1yr": build_graft_survival_cpt(),
        "CompoundSuccess": build_compound_success_cpt(),
    }

    logger.info("All BBN CPTs built: %s", {k: v.shape for k, v in cpts.items()})
    return cpts


# ──────────────────────────────────────────────────────────────────────
# Utility: map patient age to age group
# ──────────────────────────────────────────────────────────────────────

def age_to_group(age: int) -> str:
    """Map patient age (int) to BBN age group string."""
    if age < 18:
        return "18-34"  # Clamp pediatric to youngest adult group
    elif age < 35:
        return "18-34"
    elif age < 50:
        return "35-49"
    elif age < 65:
        return "50-64"
    else:
        return "65+"
