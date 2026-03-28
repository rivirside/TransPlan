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
import logging

import numpy as np

from services.data_loader import get_data

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# CPT probability vectors for discretized nodes.
#
# Rationale: These encode "strong signal" tercile assignments.  When a
# continuous variable falls in its lowest tercile the corresponding
# discrete node receives 70 % of its probability mass on the matching
# "Low" state, 25 % on "Medium" (adjacent leakage), and 5 % on "High"
# (misclassification floor).  The 70/25/5 split is a standard weakly-
# informative parameterisation for expert-elicited ordinal CPTs
# (see Druzdzel & van der Gaag, "Building Probabilistic Networks:
# Where Do the Numbers Come From?", IEEE TKDE 12(4), 2000, pp. 481-486).
# ------------------------------------------------------------------
_CPT_STRONG = [0.70, 0.25, 0.05]   # Variable in its own tercile
_CPT_MEDIUM = [0.15, 0.70, 0.15]   # Variable in middle tercile
_CPT_WEAK   = [0.05, 0.25, 0.70]   # Variable in opposite tercile

# Monthly event rates for the competing-outcomes CPT.
# Derived from SRTR 2023 annual report median waiting times and
# waitlist removal rates (Table 1.4, 1.7, 5.2).
_TRANSPLANT_MONTHLY_RATES = [1/3, 1/9, 1/18, 1/30]   # Very short -> very long wait
_MORTALITY_MONTHLY_RATES  = [0.01/12, 0.03/12, 0.08/12]  # Low -> high risk
_DELISTING_MONTHLY_RATES  = [0.03/12, 0.08/12, 0.15/12]  # Low -> high risk

# Graft survival thresholds (1-year) for discretizing outcomes.
# Based on SRTR center-specific report performance categories:
# "as expected" = national average ~93 % (kidney 1yr), flagged < 88 %.
_GRAFT_SURV_HIGH_THRESHOLD = 93
_GRAFT_SURV_LOW_THRESHOLD  = 88

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

# Keep a copy for classic-mode backward compatibility
_CLASSIC_REGIONS = list(REGIONS)


def get_regions(granularity: str = "state") -> list[str]:
    """Return the region list for the given BBN granularity level.

    Modes:
      - "classic": 22 cities (original behavior)
      - "state":   ~50 US state abbreviations (centers grouped by state)
      - "full":    ~248 individual SRTR center codes
    """
    if granularity == "classic":
        return list(_CLASSIC_REGIONS)
    from services.data_loader import get_data
    data = get_data()
    all_centers = data.all_centers.get("centers", {})
    if granularity == "full":
        return sorted(all_centers.keys())
    # "state" mode
    states = sorted({c.get("state_abbr", "XX") for c in all_centers.values()})
    return states


def get_center_to_region_map(granularity: str = "state") -> dict[str, str]:
    """Map each center code to its BBN region for the given granularity."""
    if granularity == "full":
        return {code: code for code in get_regions("full")}
    from services.data_loader import get_data
    data = get_data()
    all_centers = data.all_centers.get("centers", {})
    if granularity == "state":
        return {code: c.get("state_abbr", "XX") for code, c in all_centers.items()}
    # "classic" mode — delegate to bayesian_network's mapping
    from services.bayesian_network import _get_center_region_map
    return _get_center_region_map()


def _region_factor(region: str, organ: str, granularity: str,
                   center_map: dict, field: str) -> float | None:
    """Return the average center-level factor for all centers in a BBN region.

    Returns None for 'classic' mode so the caller can fall back to
    legacy city-level data lookups.
    """
    if granularity == "classic":
        return None
    from services.data_loader import get_data
    data = get_data()
    codes = [c for c, r in center_map.items() if r == region]
    if not codes:
        return 1.0
    if field == "wait_time_factor":
        src = data.center_wait_times.get("center_wait_time_factors", {})
        vals = [src.get(c, {}).get(organ, 1.0) for c in codes]
    elif field == "mortality_factor":
        src = data.center_competing_risks.get("center_adjustments", {})
        vals = [src.get(c, {}).get(organ, {}).get("mortality_factor", 1.0) for c in codes]
    elif field == "delisting_factor":
        src = data.center_competing_risks.get("center_adjustments", {})
        vals = [src.get(c, {}).get(organ, {}).get("delisting_factor", 1.0) for c in codes]
    elif field == "graft_survival_1yr":
        src = data.center_outcomes.get("center_outcomes", {})
        vals = [src.get(c, {}).get(organ, {}).get("graft_survival_1yr", 90.0) for c in codes]
    else:
        return 1.0
    return sum(vals) / len(vals) if vals else 1.0


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
# Data access — delegates to the central data_loader singleton (#65)
# ──────────────────────────────────────────────────────────────────────


def _get_bbn_data() -> dict:
    """Return dict with keys used by CPT builders, sourced from data_loader."""
    d = get_data()
    return {
        "wait_time": d.wait_time_distributions,
        "competing_risks": d.competing_risks,
        "cod": d.cause_of_death,
        "outcomes": d.post_transplant_outcomes,
    }


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
    data = _get_bbn_data()
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


def build_donor_supply_cpt(regions=None, n_regions=None, center_map=None,
                           granularity="classic") -> np.ndarray:
    """
    Build CPT for DonorSupply node.

    Shape: (3, n_organs, n_blood_types, n_regions)
    Axes:  [DonorSupply states, Organ, BloodType, Region]

    A composite score combines:
      - bt_factor: 1/bt_mult (higher bt_mult = longer wait = less supply)
      - cod_factor: COD multiplier (more donors for this organ in this region)
    The composite is discretized into low/medium/high terciles.
    """
    if regions is None:
        regions = REGIONS
    if n_regions is None:
        n_regions = len(regions)

    data = _get_bbn_data()
    wt = data.get("wait_time", {})

    n_o = len(ORGANS)
    n_b = len(BLOOD_TYPES)
    n_r = n_regions

    # Compute raw composite scores for all combinations
    scores = np.ones((n_o, n_b, n_r))

    for i, organ in enumerate(ORGANS):
        organ_data = wt.get(organ, {})
        bt_mults = organ_data.get("blood_type_multipliers", {})

        for j, bt in enumerate(BLOOD_TYPES):
            bt_mult = bt_mults.get(bt, 1.0)
            # Invert: higher bt_mult = longer wait = lower supply
            bt_factor = 1.0 / bt_mult if bt_mult > 0 else 1.0

            for k, region in enumerate(regions):
                if granularity == "classic":
                    state = _CITY_STATE.get(region, "")
                elif granularity == "state":
                    # Region IS the state abbreviation
                    state = region
                else:
                    # "full" — look up center's state from all_centers
                    from services.data_loader import get_data as _gd
                    all_c = _gd().all_centers.get("centers", {})
                    state = all_c.get(region, {}).get("state_abbr", "")
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
                    cpt[:, i, j, k] = _CPT_STRONG
                elif s <= t66:
                    # Medium supply
                    cpt[:, i, j, k] = _CPT_MEDIUM
                else:
                    # High supply
                    cpt[:, i, j, k] = _CPT_WEAK

    return cpt


# ──────────────────────────────────────────────────────────────────────
# CPT 2: WaitCategory — P(WaitCategory | Organ, BloodType, Region, DonorSupply)
#
# Discretizes the log-normal wait time CDF at 6/12/24 month boundaries.
# DonorSupply modulates the effective median (high supply → shorter wait).
# ──────────────────────────────────────────────────────────────────────

def build_wait_category_cpt(regions=None, n_regions=None, center_map=None,
                            granularity="classic") -> np.ndarray:
    """
    Build CPT for WaitCategory node.

    Shape: (4, n_organs, n_blood_types, n_regions, 3)
    Axes:  [WaitCategory states, Organ, BloodType, Region, DonorSupply]

    Uses log-normal CDF with adjusted median to compute:
      P(wait <= 6mo), P(6 < wait <= 12), P(12 < wait <= 24), P(wait > 24)
    """
    from scipy.stats import lognorm

    if regions is None:
        regions = REGIONS
    if n_regions is None:
        n_regions = len(regions)

    data = _get_bbn_data()
    wt = data.get("wait_time", {})
    city_factors = wt.get("city_wait_time_factors", {})
    # Remove _notes key
    city_factors = {k: v for k, v in city_factors.items() if k != "_notes"}

    n_o = len(ORGANS)
    n_b = len(BLOOD_TYPES)
    n_r = n_regions
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

            for k, region in enumerate(regions):
                # Get region wait-time multiplier
                rf = _region_factor(region, organ, granularity, center_map,
                                    "wait_time_factor")
                if rf is None:
                    # Classic mode — use city-level lookup
                    region_mult = city_factors.get(region, 1.0)
                else:
                    region_mult = rf

                for ds_idx in range(n_ds):
                    ds_mult = ds_multipliers[ds_idx]
                    adjusted_median = national_median * bt_mult * region_mult * ds_mult

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

def build_mortality_risk_cpt(regions=None, n_regions=None, center_map=None,
                             granularity="classic") -> np.ndarray:
    """
    Build CPT for MortalityRisk node.

    Shape: (3, n_organs, n_age_groups, n_urgency, n_regions)
    Axes:  [MortalityRisk states, Organ, AgeGroup, Urgency, Region]
    """
    if regions is None:
        regions = REGIONS
    if n_regions is None:
        n_regions = len(regions)

    data = _get_bbn_data()
    cr = data.get("competing_risks", {})
    city_adj = cr.get("city_adjustments", {})
    age_mults = cr.get("age_mortality_multipliers", {})
    age_overrides = cr.get("age_organ_overrides", {})

    n_o = len(ORGANS)
    n_a = len(AGE_GROUPS)
    n_u = len(URGENCY_LEVELS)
    n_r = n_regions

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

                for r, region in enumerate(regions):
                    # Get region mortality factor
                    rf = _region_factor(region, organ, granularity, center_map,
                                        "mortality_factor")
                    if rf is None:
                        # Classic mode — use city-level lookup
                        city_data = city_adj.get(region, {})
                        region_mort = city_data.get("mortality_factor", 1.0)
                        if isinstance(region_mort, str):
                            region_mort = 1.0
                    else:
                        region_mort = rf

                    rates[i, a, u, r] = base_rate * urg_mult * age_mult * region_mort

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
                        cpt[:, i, a, u, r] = _CPT_STRONG
                    elif rate <= t66:
                        cpt[:, i, a, u, r] = _CPT_MEDIUM
                    else:
                        cpt[:, i, a, u, r] = _CPT_WEAK

    return cpt


# ──────────────────────────────────────────────────────────────────────
# CPT 4: DelistingRisk — P(DelistingRisk | Organ, Region, WaitCategory)
#
# Base delisting rate × city factor, modulated by wait category
# (longer wait → higher delisting risk).
# ──────────────────────────────────────────────────────────────────────

def build_delisting_risk_cpt(regions=None, n_regions=None, center_map=None,
                             granularity="classic") -> np.ndarray:
    """
    Build CPT for DelistingRisk node.

    Shape: (3, n_organs, n_regions, 4)
    Axes:  [DelistingRisk states, Organ, Region, WaitCategory]
    """
    if regions is None:
        regions = REGIONS
    if n_regions is None:
        n_regions = len(regions)

    data = _get_bbn_data()
    cr = data.get("competing_risks", {})
    city_adj = cr.get("city_adjustments", {})

    n_o = len(ORGANS)
    n_r = n_regions
    n_w = 4  # WaitCategory states

    # Wait category multipliers on delisting (longer wait → more likely to delist)
    wait_delist_mults = [0.5, 0.8, 1.2, 1.8]

    rates = np.zeros((n_o, n_r, n_w))

    for i, organ in enumerate(ORGANS):
        organ_data = cr.get(organ, {})
        base_rate = organ_data.get("annual_delisting_rate", 0.05)

        for r, region in enumerate(regions):
            # Get region delisting factor
            rf = _region_factor(region, organ, granularity, center_map,
                                "delisting_factor")
            if rf is None:
                # Classic mode — use city-level lookup
                city_data = city_adj.get(region, {})
                region_delist = city_data.get("delisting_factor", 1.0)
                if isinstance(region_delist, str):
                    region_delist = 1.0
            else:
                region_delist = rf

            for w in range(n_w):
                rates[i, r, w] = base_rate * region_delist * wait_delist_mults[w]

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
                    cpt[:, i, r, w] = _CPT_STRONG
                elif rate <= t66:
                    cpt[:, i, r, w] = _CPT_MEDIUM
                else:
                    cpt[:, i, r, w] = _CPT_WEAK

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

    # Map discrete states to monthly rates (see module-level constants for sources)
    transplant_rates = _TRANSPLANT_MONTHLY_RATES
    mortality_rates = _MORTALITY_MONTHLY_RATES
    delisting_rates = _DELISTING_MONTHLY_RATES

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

def build_graft_survival_cpt(regions=None, n_regions=None, center_map=None,
                             granularity="classic") -> np.ndarray:
    """
    Build CPT for GraftSurvival1yr node.

    Shape: (3, n_organs, n_regions)
    Axes:  [GraftSurvival states, Organ, Region]
    """
    if regions is None:
        regions = REGIONS
    if n_regions is None:
        n_regions = len(regions)

    data = _get_bbn_data()
    outcomes = data.get("outcomes", {})
    city_outcomes = outcomes.get("city_outcomes", {})

    n_o = len(ORGANS)
    n_r = n_regions

    cpt = np.zeros((3, n_o, n_r))

    for i, organ in enumerate(ORGANS):
        national = outcomes.get(organ, {})
        nat_graft = national.get("national_graft_survival_1yr")

        for r, region in enumerate(regions):
            # Try center-level aggregation for state/full modes
            rf = _region_factor(region, organ, granularity, center_map,
                                "graft_survival_1yr")
            if rf is not None:
                # state or full mode — use aggregated center-level data
                graft_1yr = rf
                if graft_1yr >= _GRAFT_SURV_HIGH_THRESHOLD:
                    cpt[:, i, r] = [0.75, 0.20, 0.05]
                elif graft_1yr >= _GRAFT_SURV_LOW_THRESHOLD:
                    cpt[:, i, r] = [0.20, 0.65, 0.15]
                else:
                    cpt[:, i, r] = _CPT_WEAK
                continue

            # Classic mode — use city-level lookup
            city_data = city_outcomes.get(region, {}).get(organ, {})
            graft_1yr = city_data.get("graft_survival_1yr")
            hr = city_data.get("graft_hr_1yr")

            if graft_1yr is not None:
                # Use actual center-level data
                if graft_1yr >= _GRAFT_SURV_HIGH_THRESHOLD:
                    cpt[:, i, r] = [0.75, 0.20, 0.05]
                elif graft_1yr >= _GRAFT_SURV_LOW_THRESHOLD:
                    cpt[:, i, r] = [0.20, 0.65, 0.15]
                else:
                    cpt[:, i, r] = _CPT_WEAK
            elif hr is not None and nat_graft is not None:
                # Use hazard ratio relative to national
                if hr < 0.8:
                    cpt[:, i, r] = [0.75, 0.20, 0.05]
                elif hr < 1.2:
                    cpt[:, i, r] = [0.20, 0.65, 0.15]
                else:
                    cpt[:, i, r] = _CPT_WEAK
            else:
                # No data — use national average or uniform
                if nat_graft is not None:
                    if nat_graft >= _GRAFT_SURV_HIGH_THRESHOLD:
                        cpt[:, i, r] = [0.60, 0.30, 0.10]
                    elif nat_graft >= _GRAFT_SURV_LOW_THRESHOLD:
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


def build_region_prior(n_regions: int | None = None) -> np.ndarray:
    """Uniform prior over regions (overridden by evidence)."""
    n = n_regions if n_regions is not None else len(REGIONS)
    return np.ones(n) / n


# ──────────────────────────────────────────────────────────────────────
# Master builder — constructs all CPTs at once
# ──────────────────────────────────────────────────────────────────────

def build_all_cpts(granularity: str = "classic") -> dict[str, np.ndarray]:
    """
    Build all CPTs for the BBN. Returns dict of node_name → CPT array.

    Args:
        granularity: Region resolution level.
            "classic" — 22 cities (original behavior, default)
            "state"   — ~50 US state abbreviations
            "full"    — ~248 individual SRTR center codes

    CPT shapes (Region dimension varies by granularity):
      Organ:            (6,)
      BloodType:        (8,)
      AgeGroup:         (4,)
      Urgency:          (4,)
      Region:           (n_regions,)
      DonorSupply:      (3, 6, 8, n_regions)
      WaitCategory:     (4, 6, 8, n_regions, 3)
      MortalityRisk:    (3, 6, 4, 4, n_regions)
      DelistingRisk:    (3, 6, n_regions, 4)
      CompetingOutcome: (4, 4, 3, 3)
      GraftSurvival1yr: (3, 6, n_regions)
      CompoundSuccess:  (3, 4, 3)
    """
    regions = get_regions(granularity)
    n_regions = len(regions)
    center_map = get_center_to_region_map(granularity)

    logger.info("Building all BBN CPTs (granularity=%s, %d regions)...",
                granularity, n_regions)

    # Common kwargs for geography-dependent CPT builders
    geo_kwargs = dict(regions=regions, n_regions=n_regions,
                      center_map=center_map, granularity=granularity)

    cpts = {
        "Organ": build_organ_prior(),
        "BloodType": build_blood_type_prior(),
        "AgeGroup": build_age_group_prior(),
        "Urgency": build_urgency_prior(),
        "Region": build_region_prior(n_regions),
        "DonorSupply": build_donor_supply_cpt(**geo_kwargs),
        "WaitCategory": build_wait_category_cpt(**geo_kwargs),
        "MortalityRisk": build_mortality_risk_cpt(**geo_kwargs),
        "DelistingRisk": build_delisting_risk_cpt(**geo_kwargs),
        "CompetingOutcome": build_competing_outcome_cpt(),
        "GraftSurvival1yr": build_graft_survival_cpt(**geo_kwargs),
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
