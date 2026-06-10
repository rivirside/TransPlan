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

# (Removed #211: the hardcoded _TRANSPLANT/_MORTALITY/_DELISTING_MONTHLY_RATES
# that drove the old competing-exponential CompetingOutcome CPT. It is now
# grounded in observed per-center SRTR rates — see build_competing_outcome_cpt.)

# Graft survival thresholds (1-year) for discretizing outcomes.
# Based on SRTR center-specific report performance categories:
# Graft survival is now classified relative to each ORGAN'S national 1-yr rate
# (#214), not a single global threshold. _GRAFT_POOR_MARGIN is how far below the
# organ-national rate (percentage points) a center must fall to be flagged
# "poor" when only the survival percentage (not the HR CI) is available.
_GRAFT_POOR_MARGIN = 3.0

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
    # "classic" mode — delegate to bayesian_network's mapping.
    # NOTE: Deferred import to avoid circular dependency. bbn_parameterizer is
    # imported by bayesian_network at module level; importing bayesian_network
    # here at call time breaks the cycle. Do not move to top-level imports.
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
    ds_arr = np.array(ds_multipliers)  # (n_ds,)

    cpt = np.zeros((4, n_o, n_b, n_r, n_ds))

    # Vectorized over (BloodType, Region, DonorSupply) per organ. The previous
    # implementation constructed a fresh scipy lognorm object and called .cdf()
    # for every (organ, bt, region, ds) cell — ~107k frozen-dist constructions
    # at full granularity (~12s). lognorm.cdf accepts an array `scale`, so we
    # compute all medians at once and evaluate three CDF cut-points per organ.
    # Math is identical to the scalar version, so outputs are bit-for-bit equal
    # (gated by test_bbn_golden).
    for i, organ in enumerate(ORGANS):
        organ_data = wt.get(organ, {})
        national_median = organ_data.get("national_median_months", 12.0)
        sigma = organ_data.get("log_sigma", 1.0)
        bt_mults = organ_data.get("blood_type_multipliers", {})

        bt_arr = np.array([bt_mults.get(bt, 1.0) for bt in BLOOD_TYPES])  # (n_b,)
        region_arr = np.empty(n_r)
        for k, region in enumerate(regions):
            rf = _region_factor(region, organ, granularity, center_map, "wait_time_factor")
            region_arr[k] = city_factors.get(region, 1.0) if rf is None else rf

        # Adjusted median per (BloodType, Region, DonorSupply) via broadcasting.
        adjusted_median = (
            national_median
            * bt_arr[:, None, None]
            * region_arr[None, :, None]
            * ds_arr[None, None, :]
        )  # (n_b, n_r, n_ds)

        c6 = lognorm.cdf(6, s=sigma, scale=adjusted_median)
        c12 = lognorm.cdf(12, s=sigma, scale=adjusted_median)
        c24 = lognorm.cdf(24, s=sigma, scale=adjusted_median)

        probs = np.stack([
            c6,            # short: <= 6 months
            c12 - c6,      # moderate: 6-12 months
            c24 - c12,     # long: 12-24 months
            1.0 - c24,     # very_long: > 24 months
        ], axis=0)  # (4, n_b, n_r, n_ds)
        probs = np.maximum(probs, 0.001)
        probs = probs / probs.sum(axis=0, keepdims=True)  # == _normalize over states
        cpt[:, i, :, :, :] = probs

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

    # Tercile thresholds computed PER ORGAN (#209): mortality-rate distributions
    # differ sharply by organ (e.g. kidney vs heart), so a single global cut-point
    # mislabels risk. Each organ's cells are bucketed against its own terciles.
    cpt = np.zeros((3, n_o, n_a, n_u, n_r))

    for i in range(n_o):
        organ_rates = rates[i]  # (n_a, n_u, n_r)
        t33 = np.percentile(organ_rates, 33.3)
        t66 = np.percentile(organ_rates, 66.7)
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

    # Tercile thresholds computed PER ORGAN (#209) — see build_mortality_risk_cpt.
    cpt = np.zeros((3, n_o, n_r, n_w))

    for i in range(n_o):
        organ_rates = rates[i]  # (n_r, n_w)
        t33 = np.percentile(organ_rates, 33.3)
        t66 = np.percentile(organ_rates, 66.7)
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

def _observed_vector_12mo(organ: str, region: str, center_map: dict) -> tuple[np.ndarray, float]:
    """Region-level observed 12-month outcome proportions + total cohort n.

    Aggregates the SRTR Table B7 observed rates of every center mapped to
    *region* (volume-weighted by cohort n), returning a 4-way proportion vector
    [transplant, death, removed-other, still-waiting] that sums to 1, plus the
    summed n. Centers with no observed record contribute nothing; if the region
    has no data at all, returns (national_vector, 0.0).

    Q6 note: "removed-other" = SRTR REMDET (worsened) + REMREC (improved) +
    REFTX (refused). All three are genuine non-transplant exits, so they belong
    in the competing-risks denominator; the UI labels this state "removed
    without transplant (other causes)" rather than implying it is all negative.
    """
    from services.data_loader import get_data
    data = get_data()

    codes = [c for c, r in center_map.items() if r == region] if center_map else []
    tx = death = removed = n_total = 0.0
    for code in codes:
        rec = data.observed_outcome(organ, code)
        if not rec or rec.get("transplant_rate") is None:
            continue
        w = float(rec.get("n") or 0) or 1.0  # weight by cohort; missing n → 1
        tx += w * rec["transplant_rate"]
        death += w * (rec.get("waitlist_death_rate") or 0.0)
        removed += w * (rec.get("delisting_rate") or 0.0)
        n_total += w if rec.get("n") else 0.0

    if tx + death + removed == 0:  # no usable center data → national prior
        return _national_vector_12mo(organ), 0.0

    wsum = sum((float(data.observed_outcome(organ, c).get("n") or 0) or 1.0)
               for c in codes if data.observed_outcome(organ, c)
               and data.observed_outcome(organ, c).get("transplant_rate") is not None)
    tx, death, removed = tx / wsum / 100.0, death / wsum / 100.0, removed / wsum / 100.0
    waiting = max(0.0, 1.0 - tx - death - removed)
    vec = np.array([tx, death, removed, waiting])
    s = vec.sum()
    return (vec / s if s > 0 else _national_vector_12mo(organ)), n_total


def _national_vector_12mo(organ: str) -> np.ndarray:
    """National 12-month outcome proportion vector (shrinkage prior)."""
    from services.data_loader import get_data
    natl = get_data().observed_national(organ)
    tx = (natl.get("transplant_rate") or 50.0) / 100.0
    death = (natl.get("waitlist_death_rate") or 5.0) / 100.0
    removed = (natl.get("delisting_rate") or 5.0) / 100.0
    waiting = max(0.0, 1.0 - tx - death - removed)
    vec = np.array([tx, death, removed, waiting])
    return vec / vec.sum()


def _estimate_concentration(organ: str, regions: list, center_map: dict,
                            p_nat: np.ndarray) -> float:
    """Empirical-Bayes (Beta moment) estimate of the Dirichlet prior strength k
    for an organ, from the dispersion of center transplant rates around the
    national mean (#211, replaces the previous fixed magic constant).

    Larger k ⇒ centers shrink harder toward national (used when between-center
    dispersion is small relative to sampling noise). Clipped to [2, 400].
    """
    p_mean = float(p_nat[0])  # national transplant proportion
    if not (0.0 < p_mean < 1.0):
        return 25.0
    props, ns = [], []
    for region in regions:
        vec, n = _observed_vector_12mo(organ, region, center_map)
        if n >= 1:
            props.append(vec[0])
            ns.append(n)
    if len(props) < 5:
        return 25.0  # too few sampled regions to estimate dispersion
    props = np.array(props)
    ns = np.array(ns, dtype=float)
    w = ns / ns.sum()
    between_var = float(np.sum(w * (props - p_mean) ** 2))     # observed dispersion
    sampling_var = float(np.sum(w * p_mean * (1 - p_mean) / ns))  # expected binomial noise
    tau2 = between_var - sampling_var                          # true between-center variance
    if tau2 <= 1e-6:
        return 400.0  # dispersion is all noise → shrink hard
    k = p_mean * (1 - p_mean) / tau2 - 1.0
    return float(np.clip(k, 2.0, 400.0))


def _extend_12_to_24(p12: np.ndarray) -> np.ndarray:
    """Extend a 12-month competing-risks CIF vector to 24 months under a
    constant-cause-specific-hazard assumption (#211 shape assumption).

    With constant hazards, S(24)=S(12)^2 and each cause-specific CIF scales by
    (1 - S(24))/(1 - S(12)) = 1 + S(12). So:
        p24_event   = p12_event * (1 + wait12)
        p24_waiting = wait12 ** 2
    This preserves the simplex exactly: (1-w)(1+w) + w^2 = 1. Documented as an
    assumption (constant second-year hazards), not an observation.
    """
    tx, death, removed, wait = p12
    factor = 1.0 + wait
    return np.array([tx * factor, death * factor, removed * factor, wait * wait])


def build_competing_outcome_cpt(regions=None, n_regions=None, center_map=None,
                                granularity="classic") -> np.ndarray:
    """
    Build CPT for CompetingOutcome node — empirically grounded (#206/#211, opt A).

    Shape: (4, n_organs, n_regions)
    Axes:  [CompetingOutcome states (transplant, death, removed-other, waiting),
            Organ, Region]

    Each (organ, region) cell is the center's OBSERVED 12-month competing-risk
    outcome vector (SRTR Table B7), Dirichlet-shrunk toward the organ-national
    vector for small cohorts, then extended to the model's 24-month horizon.
    No latent-state (WaitCategory/Mortality/Delisting) modulation — the cell is
    the center's own observed population outcomes (option A).
    """
    if regions is None:
        regions = REGIONS
    if n_regions is None:
        n_regions = len(regions)

    n_o = len(ORGANS)
    cpt = np.zeros((4, n_o, n_regions))

    for i, organ in enumerate(ORGANS):
        p_nat = _national_vector_12mo(organ)
        k = _estimate_concentration(organ, regions, center_map, p_nat)
        for r, region in enumerate(regions):
            p_obs, n = _observed_vector_12mo(organ, region, center_map)
            # Dirichlet–multinomial shrinkage on the joint simplex (preserves sum=1).
            p12 = (n * p_obs + k * p_nat) / (n + k)
            p24 = _extend_12_to_24(p12)
            p24 = np.maximum(p24, 0.001)
            cpt[:, i, r] = _normalize(p24)

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

    # Graft-survival classes: [good, moderate, poor].
    _GOOD, _MODERATE, _POOR = [0.75, 0.20, 0.05], [0.20, 0.65, 0.15], list(_CPT_WEAK)

    cpt = np.zeros((3, n_o, n_r))

    for i, organ in enumerate(ORGANS):
        national = outcomes.get(organ, {})
        nat_graft = national.get("national_graft_survival_1yr")

        for r, region in enumerate(regions):
            # (1) Significance-based classification from the center's graft-failure
            # hazard-ratio 95% CI (#214) — only meaningful at full granularity,
            # where the region is a single center. Replaces the arbitrary HR
            # 0.8/1.2 cutoffs with a proper significance test vs. national (HR=1).
            ci = _center_graft_hr_ci(organ, region, granularity)
            if ci is not None:
                lo, hi = ci
                if hi < 1.0:        # failure hazard significantly below national
                    cpt[:, i, r] = _GOOD
                elif lo > 1.0:      # significantly above national
                    cpt[:, i, r] = _POOR
                else:               # CI straddles 1 → as expected
                    cpt[:, i, r] = _MODERATE
                continue

            # (2) Classify the center's 1-yr graft survival relative to its
            # ORGAN'S national rate (#214) — not a single global 88/93 threshold,
            # which mislabels organs with different baselines (kidney ~95 vs
            # lung ~90). state/full use aggregated center data; classic the
            # legacy city lookup.
            graft_1yr = _region_factor(region, organ, granularity, center_map,
                                       "graft_survival_1yr")
            if graft_1yr is None:
                graft_1yr = city_outcomes.get(region, {}).get(organ, {}).get("graft_survival_1yr")

            if graft_1yr is not None and nat_graft is not None:
                if graft_1yr >= nat_graft:
                    cpt[:, i, r] = _GOOD
                elif graft_1yr < nat_graft - _GRAFT_POOR_MARGIN:
                    cpt[:, i, r] = _POOR
                else:
                    cpt[:, i, r] = _MODERATE
            elif graft_1yr is not None:
                cpt[:, i, r] = _MODERATE  # have a value but no national ref
            else:
                cpt[:, i, r] = _MODERATE  # no data → organ-national prior (moderate)

    return cpt


def _center_graft_hr_ci(organ: str, region: str, granularity: str):
    """Per-center graft-failure HR 95% CI [lo, hi] from SRTR C-series, or None.

    Only returned at "full" granularity, where a BBN region is a single center
    code; at coarser granularities a region spans multiple centers and no single
    CI applies.
    """
    if granularity != "full":
        return None
    from services.data_loader import get_data
    rec = get_data().center_outcomes.get("center_outcomes", {}).get(region, {}).get(organ, {})
    ci = rec.get("graft_hr_1yr_ci")
    if ci and len(ci) == 2 and rec.get("graft_hr_1yr") is not None:
        return float(ci[0]), float(ci[1])
    return None


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
        "CompetingOutcome": build_competing_outcome_cpt(**geo_kwargs),
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
