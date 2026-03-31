"""
Center-level comprehensive scoring service.

Ports the 8-category scoring algorithm from algorithm.js to Python,
using center-level data (248 SRTR centers) instead of 22-city aggregates.
Geographic data (cost of living, air quality, health demographics) is
interpolated to center coordinates via the spatial RBF engine.
"""
import logging
import math
from dataclasses import dataclass
from functools import lru_cache

from services.data_loader import get_data

logger = logging.getLogger(__name__)

# ── Default weights (mirrors algorithm.js DEFAULT_WEIGHTS) ──────────────

DEFAULT_WEIGHTS = {
    "medicalCompatibility": 0.25,
    "waitTime": 0.20,
    "donorAvailability": 0.18,
    "hospitalQuality": 0.15,
    "geographic": 0.10,
    "healthDemographics": 0.07,
    "policy": 0.03,
    "socioeconomic": 0.02,
}

# ── Base wait time ranges by organ (years) ──────────────────────────────

BASE_WAIT_TIMES = {
    "kidney": {"min": 1.8, "max": 4.2},
    "liver": {"min": 0.8, "max": 2.5},
    "heart": {"min": 0.25, "max": 0.8},
    "lung": {"min": 0.3, "max": 0.9},
    "pancreas": {"min": 1.2, "max": 3.5},
    "intestine": {"min": 0.6, "max": 1.5},
}

# ── Volume thresholds for "high-volume" classification ──────────────────

VOLUME_THRESHOLDS = {
    "kidney": 300, "liver": 250, "heart": 120,
    "lung": 100, "pancreas": 80, "intestine": 20,
}


# ── Spatial interpolation cache ─────────────────────────────────────────

_spatial_cache: dict[str, object] = {}


def _get_spatial_surface(layer_name: str):
    """Get or create a cached SpatialSurface for a given layer."""
    if layer_name not in _spatial_cache:
        try:
            from services.spatial_interpolation import SpatialSurface
            _spatial_cache[layer_name] = SpatialSurface(layer_name)
        except Exception:
            logger.warning("Spatial layer '%s' unavailable", layer_name)
            _spatial_cache[layer_name] = None
    return _spatial_cache[layer_name]


def _interpolate(layer_name: str, lat: float, lon: float, fallback: float = 50.0) -> float:
    """Interpolate a spatial layer value at center coordinates."""
    surface = _get_spatial_surface(layer_name)
    if surface is None:
        return fallback
    try:
        return surface.query(lat, lon)
    except Exception:
        return fallback


# ── Category 1: Medical Compatibility (25%) ─────────────────────────────

def _medical_compatibility(patient: dict) -> float:
    """Pure patient-profile scoring — no geographic data needed."""
    score = 0.0

    # Blood type (40%)
    bt_scores = {
        "O-": 70, "O+": 85, "A-": 88, "A+": 95,
        "B-": 82, "B+": 90, "AB-": 92, "AB+": 100,
    }
    score += bt_scores.get(patient["blood_type"], 85) * 0.40

    # Age (25%)
    age = patient["age"]
    if age < 18:
        age_score = 115
    elif age < 35:
        age_score = 105
    elif age < 50:
        age_score = 100
    elif age < 65:
        age_score = 95
    elif age < 75:
        age_score = 85
    else:
        age_score = 75
    score += age_score * 0.25

    # Sex / organ size (15%)
    organ = patient["organ"]
    sex_score = 100
    if organ in ("heart", "lung") and patient["sex"] == "female":
        sex_score = 95
    score += sex_score * 0.15

    # BMI for thoracic (20%)
    if organ in ("heart", "lung") and patient.get("weight_lbs") and patient.get("height_inches"):
        bmi = (patient["weight_lbs"] / (patient["height_inches"] ** 2)) * 703
        if bmi < 18.5:
            size_score = 85
        elif bmi > 35:
            size_score = 80
        else:
            size_score = 100
        score += size_score * 0.20
    else:
        score += 100 * 0.20

    return min(100.0, score)


# ── Category 2: Wait Time & Competition (20%) ──────────────────────────

def _wait_time_multiplier(organ: str, patient: dict) -> float:
    """Organ-specific wait time multiplier from clinical scores."""
    cpra = patient.get("cpra") or 0
    if organ == "kidney" and cpra > 0:
        if cpra <= 20:
            return 1.0
        if cpra <= 50:
            return 1.0 + (cpra - 20) / 30 * 0.5
        if cpra <= 80:
            return 1.5 + (cpra - 50) / 30 * 1.0
        if cpra <= 97:
            return 2.5 + (cpra - 80) / 17 * 0.5
        return 3.0 + (cpra - 97) / 3 * 2.0

    meld = patient.get("meld")
    if organ == "liver" and meld:
        if meld >= 35:
            return 0.15
        if meld >= 25:
            return 0.4
        if meld >= 15:
            return 1.0
        return 2.0

    las = patient.get("las")
    if organ == "lung" and las:
        if las >= 50:
            return 0.3
        if las >= 35:
            return 0.7
        return 1.2

    urgency_factors = {1: 0.3, 2: 0.6, 3: 1.0, 4: 1.4}
    return urgency_factors.get(patient["urgency"], 1.0)


def _wait_time_score(center_code: str, organ: str, patient: dict) -> float:
    """Score based on center-level wait time factors."""
    data = get_data()
    cwt = data.center_wait_times.get("center_wait_time_factors", {})
    factor = cwt.get(center_code, {}).get(organ, 1.0)

    avg_wait = (BASE_WAIT_TIMES[organ]["min"] + BASE_WAIT_TIMES[organ]["max"]) / 2
    city_wait = avg_wait * factor
    multiplier = _wait_time_multiplier(organ, patient)
    adjusted = city_wait * multiplier

    max_wait = BASE_WAIT_TIMES[organ]["max"] * 1.5
    return max(0.0, 100.0 - (adjusted / max_wait) * 100.0)


# ── Category 3: Donor Availability (18%) ────────────────────────────────

def _cod_multiplier(state: str, organ: str) -> float | None:
    """Compute organ-specific cause-of-death multiplier for a state."""
    data = get_data()
    cod = data.cause_of_death
    rates = (cod.get("organRecoveryRates") or {}).get(organ)
    props = (cod.get("stateCauseOfDeathProportions") or {}).get(state)
    if not rates or not props:
        return None

    cats = ["trauma", "cardiovascular", "drug_intox", "stroke", "anoxia"]
    state_score = sum(props.get(c, 0) * rates.get(c, 0) for c in cats)

    all_props = cod.get("stateCauseOfDeathProportions", {}).values()
    if not all_props:
        return None
    nat_avg = sum(
        sum(sp.get(c, 0) * rates.get(c, 0) for c in cats)
        for sp in all_props
    ) / len(list(cod["stateCauseOfDeathProportions"]))

    return state_score / nat_avg if nat_avg > 0 else None


def _donor_availability(state: str, organ: str, patient: dict, lat: float = 0.0, lon: float = 0.0) -> float:
    """State-level donor availability scoring."""
    data = get_data()
    score = 0.0

    # State registration rate (39%)
    reg_rates = (data.donor_registration.get("stateRegistrationRates") or {})
    reg = reg_rates.get(state, 35)
    score += (reg / 69) * 100 * 0.39

    # Population factor — use state average since we don't have per-center data (25%)
    # Large-state centers get a boost; small-state centers get national average
    state_pop_scores = {
        "New York": 100, "California": 95, "Texas": 88, "Florida": 80,
        "Illinois": 90, "Pennsylvania": 85, "Ohio": 70, "Georgia": 75,
        "North Carolina": 72, "Michigan": 72, "New Jersey": 78,
        "Virginia": 72, "Washington": 74, "Arizona": 70,
        "Massachusetts": 78, "Tennessee": 71, "Indiana": 69,
        "Maryland": 75, "Minnesota": 72, "Wisconsin": 62,
        "Missouri": 67, "Colorado": 70, "Alabama": 60,
        "South Carolina": 60, "Louisiana": 62, "Kentucky": 58,
        "Oregon": 70, "Oklahoma": 58, "Connecticut": 65,
        "Iowa": 55, "Utah": 60, "Arkansas": 52,
        "Mississippi": 50, "Kansas": 55, "Nevada": 62,
        "Nebraska": 58, "New Mexico": 52,
    }
    pop = state_pop_scores.get(state, 60)
    score += (pop / 100) * 100 * 0.25

    # Living donor program (28%) — state average fallback
    ldp = (data.donor_registration.get("livingDonorProgramStrength") or {})
    # Try center's city first, then generic state score
    living_score = 75  # national average fallback
    for city_name, val in ldp.items():
        if city_name in state:
            living_score = val
            break
    score += living_score * 0.28

    # Traffic/trauma (8%) — interpolated from hotspot data, fallback 65
    trauma = _interpolate("trauma", lat, lon, fallback=65.0)
    score += max(0, min(100, trauma)) * 0.08

    # COD multiplier if enabled
    if patient.get("adjust_for_cause_of_death"):
        mult = _cod_multiplier(state, organ)
        if mult is not None:
            score *= mult

    return max(0.0, min(100.0, score))


# ── Category 4: Hospital Quality (15%) ──────────────────────────────────

def _hospital_quality(center_code: str, organ: str, patient: dict) -> float:
    """Center-level quality scoring using actual SRTR outcomes data."""
    data = get_data()
    score = 0.0

    # Volume from outcomes data (40%)
    outcomes = data.center_outcomes.get("center_outcomes", {}).get(center_code, {}).get(organ, {})
    n_txp = outcomes.get("n_1yr", 0)
    threshold = VOLUME_THRESHOLDS.get(organ, 100)
    volume_score = min(100.0, (n_txp / threshold) * 100)
    score += volume_score * 0.40

    # Performance rating from SRTR (25%)
    rating = outcomes.get("performance_rating", "as_expected")
    rating_scores = {
        "better_than_expected": 100,
        "as_expected": 80,
        "lower_than_expected": 55,
        "insufficient_data": 70,
    }
    score += rating_scores.get(rating, 70) * 0.25

    # Graft survival as quality proxy (20%)
    graft_1yr = outcomes.get("graft_survival_1yr")
    if graft_1yr is not None:
        # National avg ~95% for kidney, ~90% for liver, etc.
        # Normalize: 80% → 0, 100% → 100
        graft_score = max(0, min(100, (graft_1yr - 80) / 20 * 100))
        score += graft_score * 0.20
    else:
        score += 70 * 0.20  # fallback

    # Insurance acceptance (15%)
    if patient.get("insurance") == "medicaid":
        score += 85 * 0.85 * 0.15
    elif patient.get("insurance") == "uninsured":
        score += 85 * 0.70 * 0.15
    else:
        score += 85 * 0.15

    return min(100.0, score)


# ── Category 5: Geographic & Logistical (10%) ───────────────────────────

def _geographic(lat: float, lon: float) -> float:
    """Interpolate cost of living and air quality at center coordinates."""
    score = 0.0

    # Cost of living (40%) — lower is better
    col = _interpolate("cost_of_living", lat, lon, fallback=100.0)
    # Normalize: assume range 80-200
    col_score = max(0, min(100, 100 - ((col - 80) / 120) * 100))
    score += col_score * 0.40

    # Climate (35%) — interpolated from 22-city climate scores, fallback 70
    climate = _interpolate("climate", lat, lon, fallback=70.0)
    score += max(0, min(100, climate)) * 0.35

    # Air quality (25%)
    aq = _interpolate("air_quality", lat, lon, fallback=70.0)
    # AQI-like: lower is better; spatial engine returns quality score (higher = better)
    score += max(0, min(100, aq)) * 0.25

    return score


# ── Category 6: Health Demographics (7%) ────────────────────────────────

def _health_demographics(lat: float, lon: float) -> float:
    """Interpolate county-level health data at center coordinates."""
    score = 100.0

    diabetes = _interpolate("health_diabetesRate", lat, lon, fallback=10.5)
    obesity = _interpolate("health_obesityRate", lat, lon, fallback=31.9)
    score -= (diabetes - 7) * 2
    score -= (obesity - 25) * 1.5

    # CKD, hypertension, smoking — try interpolation, fallback to national avg
    ckd = _interpolate("health_ckdRate", lat, lon, fallback=14.0)
    hypertension = _interpolate("health_hypertensionRate", lat, lon, fallback=32.0)
    smoking = _interpolate("health_smokingRate", lat, lon, fallback=14.0)
    score -= (ckd - 11) * 2.5
    score -= (hypertension - 27) * 1.0
    score -= (smoking - 13) * 1.5

    return max(30.0, min(100.0, score))


# ── Category 7: Policy & Legal (3%) ─────────────────────────────────────

def _policy(state: str) -> float:
    """State-level policy scoring."""
    data = get_data()
    tiers = data.policy_tiers
    return tiers.get(state, 70)


# ── Category 8: Socioeconomic (2%) ──────────────────────────────────────

def _socioeconomic(state: str) -> float:
    """State-level transplant support services score.

    Based on: patient housing (30%), financial assistance (25%),
    transplant support groups (20%), caregiver resources (15%),
    health literacy (10%).
    """
    state_socio = {
        "Alabama": 72, "Alaska": 68, "Arizona": 76, "Arkansas": 70,
        "California": 84, "Colorado": 83, "Connecticut": 84, "Delaware": 76,
        "District of Columbia": 82, "Florida": 78, "Georgia": 76, "Hawaii": 74,
        "Idaho": 70, "Illinois": 82, "Indiana": 80, "Iowa": 82,
        "Kansas": 74, "Kentucky": 73, "Louisiana": 72, "Maine": 75,
        "Maryland": 83, "Massachusetts": 86, "Michigan": 80, "Minnesota": 88,
        "Mississippi": 68, "Missouri": 84, "Montana": 69, "Nebraska": 85,
        "Nevada": 73, "New Hampshire": 78, "New Jersey": 81, "New Mexico": 72,
        "New York": 85, "North Carolina": 86, "North Dakota": 72, "Ohio": 92,
        "Oklahoma": 71, "Oregon": 82, "Pennsylvania": 90, "Puerto Rico": 65,
        "Rhode Island": 79, "South Carolina": 73, "South Dakota": 71, "Tennessee": 84,
        "Texas": 88, "Utah": 77, "Vermont": 76, "Virginia": 80,
        "Washington": 89, "West Virginia": 70, "Wisconsin": 87, "Wyoming": 68,
    }
    return state_socio.get(state, 75)


# ── Master scoring function ─────────────────────────────────────────────

@dataclass
class CenterScoreResult:
    code: str
    name: str
    state: str
    state_abbr: str
    lat: float
    lon: float
    organs: list[str]
    total: float
    breakdown: dict[str, float]
    rank: int = 0


def score_center(center: dict, patient: dict, weights: dict) -> CenterScoreResult | None:
    """Score a single center for a patient profile."""
    code = center["code"]
    organ = patient["organ"]

    # Skip centers that don't perform this organ
    if organ not in center.get("organs", []):
        return None

    lat = center.get("lat", 0)
    lon = center.get("lon", 0)
    state = center.get("state", "")

    breakdown = {
        "medicalCompatibility": _medical_compatibility(patient),
        "waitTime": _wait_time_score(code, organ, patient),
        "donorAvailability": _donor_availability(state, organ, patient, lat, lon),
        "hospitalQuality": _hospital_quality(code, organ, patient),
        "geographic": _geographic(lat, lon),
        "healthDemographics": _health_demographics(lat, lon),
        "policy": _policy(state),
        "socioeconomic": _socioeconomic(state),
    }

    total = sum(breakdown[k] * weights[k] for k in weights)
    total = max(0.0, min(100.0, total))

    return CenterScoreResult(
        code=code,
        name=center.get("name", code),
        state=state,
        state_abbr=center.get("state_abbr", ""),
        lat=lat,
        lon=lon,
        organs=center.get("organs", []),
        total=round(total, 1),
        breakdown={k: round(v, 1) for k, v in breakdown.items()},
    )


def score_all_centers(patient: dict, custom_weights: dict | None = None) -> list[CenterScoreResult]:
    """Score all 248 centers for a patient profile, return sorted by total desc."""
    data = get_data()
    centers = data.all_centers.get("centers", {})

    # Resolve weights
    weights = dict(DEFAULT_WEIGHTS)
    if custom_weights:
        expected = set(DEFAULT_WEIGHTS.keys())
        if set(custom_weights.keys()) == expected:
            total_w = sum(custom_weights.values())
            if total_w > 0:
                weights = {k: v / total_w for k, v in custom_weights.items()}

    results = []
    for code, center_data in centers.items():
        result = score_center(center_data, patient, weights)
        if result is not None:
            results.append(result)

    # Sort by total descending
    results.sort(key=lambda r: r.total, reverse=True)

    # Assign ranks
    for i, r in enumerate(results):
        r.rank = i + 1

    logger.info("Scored %d centers for %s/%s", len(results), patient["organ"], patient["blood_type"])
    return results
