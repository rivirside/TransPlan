"""
Score explainability service.

Mirrors the scoring logic in services/scoring.py but returns rich provenance
metadata for each category and sub-component. Used by POST /score?explain=true.

Design: keeps the production scoring path in scoring.py untouched (so existing
tests stay valid) and provides a parallel "explain" path here that re-runs the
same calculations while recording inputs, intermediate values, and data sources.
"""
from __future__ import annotations

from typing import Any

from services.data_loader import get_data
from services.scoring import (
    BASE_WAIT_TIMES,
    DEFAULT_WEIGHTS,
    VOLUME_THRESHOLDS,
    _cod_multiplier,
    _interpolate,
    _wait_time_multiplier,
)


def _component(
    name: str,
    value: float,
    weight: float,
    source: str,
    raw_input: Any = None,
    details: dict | None = None,
) -> dict:
    """Build a single component provenance dict."""
    return {
        "name": name,
        "value": round(value, 2),
        "weight_within_category": weight,
        "contribution": round(value * weight, 2),
        "source": source,
        "raw_input": raw_input,
        "details": details,
    }


def _lookup_table(rows: list[tuple], matched_label: str | None = None) -> list[dict]:
    """Build a lookup_table list from (label, value[, note]) tuples.
    Marks the row matching `matched_label` as highlighted.
    """
    out = []
    for row in rows:
        label = row[0]
        val = row[1]
        note = row[2] if len(row) > 2 else None
        out.append({
            "label": label,
            "value": val,
            "highlighted": (label == matched_label),
            "note": note,
        })
    return out


# ── Category 1: Medical Compatibility ───────────────────────────────────

def explain_medical_compatibility(patient: dict) -> tuple[float, list[dict]]:
    components = []

    bt_scores = {
        "O-": 70, "O+": 85, "A-": 88, "A+": 95,
        "B-": 82, "B+": 90, "AB-": 92, "AB+": 100,
    }
    bt = patient["blood_type"]
    bt_val = bt_scores.get(bt, 85)
    components.append(_component(
        f"Blood type ({bt})",
        bt_val, 0.40,
        "Built-in compatibility table",
        raw_input=bt,
        details={
            "summary": (
                "Each ABO/Rh type is assigned a score that proxies donor compatibility breadth. "
                "Universal recipients (AB+) score highest because they accept any blood type; "
                "universal donors (O-) score lowest because they receive the most competition."
            ),
            "lookup_table": _lookup_table([
                ("O-",  70, "Universal donor; highest waitlist competition"),
                ("O+",  85, None),
                ("A-",  88, None),
                ("B-",  82, None),
                ("B+",  90, None),
                ("A+",  95, None),
                ("AB-", 92, None),
                ("AB+", 100, "Universal recipient; accepts any donor"),
            ], matched_label=bt),
            "notes": (
                "Note: this scoring uses blood type as a compatibility proxy. Actual transplant "
                "matching also involves HLA crossmatching and antibody screening (cPRA), which "
                "are handled separately in the wait-time category for kidney patients."
            ),
        },
    ))

    age = patient["age"]
    age_brackets = [
        ("<18",   115, "Pediatric premium"),
        ("18-34", 105, None),
        ("35-49", 100, None),
        ("50-64", 95,  None),
        ("65-74", 85,  None),
        ("75+",   75,  None),
    ]
    if age < 18: age_val, age_bracket = 115, "<18"
    elif age < 35: age_val, age_bracket = 105, "18-34"
    elif age < 50: age_val, age_bracket = 100, "35-49"
    elif age < 65: age_val, age_bracket = 95, "50-64"
    elif age < 75: age_val, age_bracket = 85, "65-74"
    else: age_val, age_bracket = 75, "75+"
    components.append(_component(
        f"Age ({age}, bracket {age_bracket})",
        age_val, 0.25,
        "Built-in age scoring rules",
        raw_input=age,
        details={
            "summary": (
                "Younger patients generally tolerate transplantation better and have stronger "
                "post-transplant outcomes, so they receive higher compatibility scores."
            ),
            "lookup_table": _lookup_table(age_brackets, matched_label=age_bracket),
            "notes": (
                "Pediatric scores exceed 100 internally; final category scores are clamped to "
                "[0, 100]. Brackets are heuristic and not derived from a specific published "
                "study — they reflect general clinical patterns."
            ),
        },
    ))

    organ = patient["organ"]
    sex = patient["sex"]
    sex_val = 100
    sex_note = "No size-match penalty for this organ/sex"
    if organ in ("heart", "lung") and sex == "female":
        sex_val = 95
        sex_note = "Female + thoracic organ: 5% size-match penalty"
    components.append(_component(
        f"Sex/organ size match ({sex}, {organ})",
        sex_val, 0.15,
        sex_note,
        raw_input={"sex": sex, "organ": organ},
        details={
            "summary": (
                "Heart and lung transplants are size-matched (donor-recipient body size matters). "
                "Female patients have a smaller donor pool on average for thoracic organs, "
                "leading to a 5% penalty. Non-thoracic organs are not size-sensitive."
            ),
            "lookup_table": _lookup_table([
                ("Female + heart/lung", 95, "Smaller donor pool penalty"),
                ("All other cases",     100, "No size penalty"),
            ], matched_label=(
                "Female + heart/lung" if (organ in ("heart", "lung") and sex == "female")
                else "All other cases"
            )),
        },
    ))

    bmi_val = 100
    bmi_source = "BMI not used for non-thoracic organs"
    bmi_raw = None
    bmi_details = {
        "summary": (
            "BMI is used only for heart and lung transplants, where body size matters for "
            "donor-recipient matching. Non-thoracic organs default to a neutral 100."
        ),
        "lookup_table": _lookup_table([
            ("BMI < 18.5 (underweight)",  85, None),
            ("BMI 18.5-35 (normal range)", 100, None),
            ("BMI > 35 (obese)",          80, None),
            ("Non-thoracic organ",        100, "Not applicable"),
        ], matched_label=None),
    }
    if organ in ("heart", "lung") and patient.get("weight_lbs") and patient.get("height_inches"):
        bmi = (patient["weight_lbs"] / (patient["height_inches"] ** 2)) * 703
        bmi_raw = round(bmi, 1)
        if bmi < 18.5:
            bmi_val = 85
            bmi_source = f"BMI {bmi:.1f} (underweight): penalty applied"
            matched = "BMI < 18.5 (underweight)"
        elif bmi > 35:
            bmi_val = 80
            bmi_source = f"BMI {bmi:.1f} (obese): penalty applied"
            matched = "BMI > 35 (obese)"
        else:
            bmi_val = 100
            bmi_source = f"BMI {bmi:.1f} (normal range)"
            matched = "BMI 18.5-35 (normal range)"
        bmi_details["lookup_table"] = _lookup_table([
            ("BMI < 18.5 (underweight)",  85, None),
            ("BMI 18.5-35 (normal range)", 100, None),
            ("BMI > 35 (obese)",          80, None),
        ], matched_label=matched)
    else:
        bmi_details["lookup_table"][3]["highlighted"] = True
    components.append(_component(
        "BMI / size match",
        bmi_val, 0.20,
        bmi_source,
        raw_input=bmi_raw,
        details=bmi_details,
    ))

    score = sum(c["contribution"] for c in components)
    return min(100.0, score), components


# ── Category 2: Wait Time ───────────────────────────────────────────────

def explain_wait_time(center_code: str, organ: str, patient: dict) -> tuple[float, list[dict], str | None]:
    data = get_data()
    cwt = data.center_wait_times.get("center_wait_time_factors", {})
    factor = cwt.get(center_code, {}).get(organ, 1.0)

    avg_wait = (BASE_WAIT_TIMES[organ]["min"] + BASE_WAIT_TIMES[organ]["max"]) / 2
    city_wait_years = avg_wait * factor
    multiplier = _wait_time_multiplier(organ, patient)
    adjusted_years = city_wait_years * multiplier
    max_wait = BASE_WAIT_TIMES[organ]["max"] * 1.5
    score = max(0.0, 100.0 - (adjusted_years / max_wait) * 100.0)

    # Describe the multiplier source and build its details
    if organ == "kidney":
        cpra = patient.get("cpra") or 0
        mult_src = f"cPRA={cpra} (kidney sensitization curve)"
        clinical_details = {
            "summary": (
                "Calculated PRA (cPRA) measures the proportion of donors a sensitized "
                "patient would react against. Higher cPRA means longer waits because fewer "
                "donors are immunologically compatible."
            ),
            "lookup_table": _lookup_table([
                ("cPRA 0-20%",   "1.0×",  "No sensitization effect"),
                ("cPRA 20-50%",  "1.0-1.5×", "Mild sensitization"),
                ("cPRA 50-80%",  "1.5-2.5×", "Moderate"),
                ("cPRA 80-97%",  "2.5-3.0×", "High"),
                ("cPRA 97-100%", "3.0-5.0×", "Highly sensitized (priority points partially offset this)"),
            ], matched_label=(
                "cPRA 0-20%" if cpra <= 20 else
                "cPRA 20-50%" if cpra <= 50 else
                "cPRA 50-80%" if cpra <= 80 else
                "cPRA 80-97%" if cpra <= 97 else
                "cPRA 97-100%"
            )),
            "formula": (
                "if cpra <= 20: 1.0\n"
                "elif cpra <= 50: 1.0 + (cpra-20)/30 × 0.5\n"
                "elif cpra <= 80: 1.5 + (cpra-50)/30 × 1.0\n"
                "elif cpra <= 97: 2.5 + (cpra-80)/17 × 0.5\n"
                "else: 3.0 + (cpra-97)/3 × 2.0"
            ),
            "notes": "cPRA also unlocks waitlist priority points in real allocation; this scoring captures wait-time impact only.",
        }
    elif organ == "liver":
        meld = patient.get("meld")
        mult_src = f"MELD={meld} (MELD acuity curve)"
        clinical_details = {
            "summary": (
                "MELD (Model for End-Stage Liver Disease) drives liver allocation in the US. "
                "Higher MELD = sicker patient = faster transplant. The multiplier is inverse: "
                "high MELD reduces expected wait time."
            ),
            "lookup_table": _lookup_table([
                ("MELD ≥ 35", "0.15×", "Critical; transplant typically within weeks"),
                ("MELD 25-34", "0.4×",  "Severe; weeks to months"),
                ("MELD 15-24", "1.0×",  "Moderate; baseline wait"),
                ("MELD < 15",  "2.0×",  "Lower priority; longer wait"),
            ], matched_label=(
                "MELD ≥ 35" if (meld and meld >= 35) else
                "MELD 25-34" if (meld and meld >= 25) else
                "MELD 15-24" if (meld and meld >= 15) else
                "MELD < 15" if meld else None
            )) if meld else None,
            "notes": "MELD is recalculated as the patient's condition changes; this is a snapshot estimate.",
        }
    elif organ == "lung":
        las = patient.get("las")
        mult_src = f"LAS={las} (LAS acuity curve)"
        clinical_details = {
            "summary": (
                "Lung Allocation Score (LAS) balances medical urgency against expected transplant "
                "benefit. Higher LAS = faster transplant."
            ),
            "lookup_table": _lookup_table([
                ("LAS ≥ 50", "0.3×", "High acuity"),
                ("LAS 35-49", "0.7×", "Moderate acuity"),
                ("LAS < 35",  "1.2×", "Lower acuity"),
            ], matched_label=(
                "LAS ≥ 50" if (las and las >= 50) else
                "LAS 35-49" if (las and las >= 35) else
                "LAS < 35" if las else None
            )) if las else None,
        }
    else:
        urgency = patient["urgency"]
        mult_src = f"Urgency level {urgency} (default urgency table)"
        clinical_details = {
            "summary": "For organs without standardized acuity scores, urgency level (1-4) controls the multiplier.",
            "lookup_table": _lookup_table([
                ("Urgency 1 (lowest)",  "0.3×", "Very stable"),
                ("Urgency 2",           "0.6×", "Stable"),
                ("Urgency 3",           "1.0×", "Active waitlist"),
                ("Urgency 4 (highest)", "1.4×", "Decompensating"),
            ], matched_label=f"Urgency {urgency}" + (" (lowest)" if urgency == 1 else " (highest)" if urgency == 4 else "")),
        }

    components = [
        _component(
            f"Center wait factor ({center_code})",
            factor, 1.0,
            "data/wait-time-distributions-centers.json (center-specific multiplier)",
            raw_input=factor,
            details={
                "summary": (
                    "Each center has an SRTR-derived wait time multiplier relative to a national "
                    "baseline. Values < 1.0 mean shorter-than-average waits; > 1.0 means longer."
                ),
                "notes": (
                    "Source: SRTR Program-Specific Reports (PSRs), aggregated across the most "
                    "recent biannual releases."
                ),
            },
        ),
        _component(
            f"Organ baseline avg wait ({organ})",
            avg_wait, 1.0,
            f"BASE_WAIT_TIMES[{organ}]: min={BASE_WAIT_TIMES[organ]['min']}, max={BASE_WAIT_TIMES[organ]['max']}",
            raw_input={"min": BASE_WAIT_TIMES[organ]["min"], "max": BASE_WAIT_TIMES[organ]["max"]},
            details={
                "summary": "Baseline expected wait times per organ, used as the reference for center-specific scaling.",
                "lookup_table": _lookup_table([
                    ("kidney",    "1.8-4.2 yrs", None),
                    ("liver",     "0.8-2.5 yrs", None),
                    ("heart",     "0.25-0.8 yrs", "High acuity, short waits"),
                    ("lung",      "0.3-0.9 yrs", None),
                    ("pancreas",  "1.2-3.5 yrs", None),
                    ("intestine", "0.6-1.5 yrs", None),
                ], matched_label=organ),
            },
        ),
        _component(
            f"Clinical multiplier ({mult_src})",
            multiplier, 1.0,
            "Organ-specific acuity curve (cPRA, MELD, LAS, or urgency)",
            raw_input=multiplier,
            details=clinical_details,
        ),
        _component(
            "Center-adjusted wait (years)",
            city_wait_years, 1.0,
            "avg_wait × center_factor",
            raw_input=round(city_wait_years, 2),
        ),
        _component(
            "Final patient-adjusted wait (years)",
            adjusted_years, 1.0,
            "city_wait_years × clinical_multiplier",
            raw_input=round(adjusted_years, 2),
        ),
    ]

    notes = (
        f"Score = 100 - (adjusted_wait / max_wait) × 100 = "
        f"100 - ({adjusted_years:.2f} / {max_wait:.2f}) × 100 = {score:.1f}"
    )
    return score, components, notes


# ── Category 3: Donor Availability ──────────────────────────────────────

def explain_donor_availability(
    state: str, organ: str, patient: dict, lat: float, lon: float,
) -> tuple[float, list[dict], str | None]:
    data = get_data()
    components = []
    notes_parts = []

    reg_rates = (data.donor_registration.get("stateRegistrationRates") or {})
    reg = reg_rates.get(state, 35)
    reg_score = (reg / 69) * 100
    components.append(_component(
        f"State donor registration rate ({state})",
        reg_score, 0.39,
        f"data/donor-registration.json: {reg}% (normalized vs national max 69%)",
        raw_input=reg,
    ))

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
    components.append(_component(
        f"State population factor ({state})",
        pop, 0.25,
        f"Built-in state population proxy" + (" (fallback to national avg 60)" if state not in state_pop_scores else ""),
        raw_input=pop,
    ))

    ldp = (data.donor_registration.get("livingDonorProgramStrength") or {})
    living_score = 75
    living_source = "data/donor-registration.json: fallback to national avg (75)"
    for city_name, val in ldp.items():
        if city_name in state:
            living_score = val
            living_source = f"data/donor-registration.json: {city_name} living donor program ({val})"
            break
    components.append(_component(
        "Living donor program strength",
        living_score, 0.28,
        living_source,
        raw_input=living_score,
    ))

    trauma = _interpolate("trauma", lat, lon, fallback=65.0)
    components.append(_component(
        "Trauma/donor pool proxy",
        max(0, min(100, trauma)), 0.08,
        f"Spatial interpolation at ({lat:.3f}, {lon:.3f}) from traffic fatality hotspots (fallback=65 if unavailable)",
        raw_input=round(trauma, 2),
    ))

    score = sum(c["contribution"] for c in components)

    if patient.get("adjust_for_cause_of_death"):
        mult = _cod_multiplier(state, organ)
        if mult is not None:
            old_score = score
            score *= mult
            notes_parts.append(
                f"Cause-of-death adjustment applied: ×{mult:.3f} → {score:.1f} (was {old_score:.1f})"
            )

    notes = " | ".join(notes_parts) if notes_parts else None
    return max(0.0, min(100.0, score)), components, notes


# ── Category 4: Hospital Quality ────────────────────────────────────────

def explain_hospital_quality(center_code: str, organ: str, patient: dict) -> tuple[float, list[dict]]:
    data = get_data()
    components = []

    outcomes = data.center_outcomes.get("center_outcomes", {}).get(center_code, {}).get(organ, {})

    n_txp = outcomes.get("n_1yr", 0)
    threshold = VOLUME_THRESHOLDS.get(organ, 100)
    volume_score = min(100.0, (n_txp / threshold) * 100)
    components.append(_component(
        f"Annual transplant volume ({n_txp} {organ}s/yr)",
        volume_score, 0.40,
        f"data/post-transplant-outcomes-centers.json: n_1yr={n_txp}; threshold={threshold}",
        raw_input=n_txp,
        details={
            "summary": (
                "Higher annual transplant volume correlates with better outcomes "
                "(volume-outcome relationship is well-established in transplant literature). "
                "Score is the percentage of an organ-specific 'high-volume' threshold, capped at 100."
            ),
            "lookup_table": _lookup_table([
                ("kidney",    300, "High-volume threshold"),
                ("liver",     250, None),
                ("heart",     120, None),
                ("lung",      100, None),
                ("pancreas",  80,  None),
                ("intestine", 20,  None),
            ], matched_label=organ),
            "formula": f"score = min(100, volume / threshold × 100) = min(100, {n_txp} / {threshold} × 100)",
        },
    ))

    rating = outcomes.get("performance_rating", "as_expected")
    rating_scores = {
        "better_than_expected": 100,
        "as_expected": 80,
        "lower_than_expected": 55,
        "insufficient_data": 70,
    }
    rating_val = rating_scores.get(rating, 70)
    components.append(_component(
        f"SRTR performance rating ({rating})",
        rating_val, 0.25,
        f"data/post-transplant-outcomes-centers.json: performance_rating={rating}",
        raw_input=rating,
        details={
            "summary": (
                "SRTR rates each transplant program's outcomes relative to expected "
                "(adjusted for patient mix). The rating is derived from 1-year graft and "
                "patient survival compared to a national risk-adjusted benchmark."
            ),
            "lookup_table": _lookup_table([
                ("better_than_expected", 100, "Outperforms national benchmark"),
                ("as_expected",          80,  "Within expected range (most centers)"),
                ("insufficient_data",    70,  "Newer or smaller program"),
                ("lower_than_expected",  55,  "Underperforms benchmark"),
            ], matched_label=rating),
            "notes": "Ratings come directly from SRTR's biannual program-specific reports.",
        },
    ))

    graft_1yr = outcomes.get("graft_survival_1yr")
    if graft_1yr is not None:
        graft_score = max(0, min(100, (graft_1yr - 80) / 20 * 100))
        components.append(_component(
            f"1-year graft survival ({graft_1yr:.1f}%)",
            graft_score, 0.20,
            f"data/post-transplant-outcomes-centers.json: graft_survival_1yr={graft_1yr}; normalized 80%→0, 100%→100",
            raw_input=graft_1yr,
        ))
    else:
        components.append(_component(
            "1-year graft survival (unavailable)",
            70, 0.20,
            "Fallback when graft_survival_1yr is null",
            raw_input=None,
        ))

    insurance = patient.get("insurance") or "private"
    if insurance == "medicaid":
        ins_score = 85 * 0.85
        ins_note = "Medicaid: 15% center-acceptance penalty"
    elif insurance == "uninsured":
        ins_score = 85 * 0.70
        ins_note = "Uninsured: 30% center-acceptance penalty"
    else:
        ins_score = 85
        ins_note = "Private/Medicare: no penalty"
    components.append(_component(
        f"Insurance acceptance ({insurance})",
        ins_score, 0.15,
        ins_note,
        raw_input=insurance,
    ))

    score = sum(c["contribution"] for c in components)
    return min(100.0, score), components


# ── Category 5: Geographic ──────────────────────────────────────────────

def explain_geographic(lat: float, lon: float) -> tuple[float, list[dict]]:
    components = []

    col = _interpolate("cost_of_living", lat, lon, fallback=100.0)
    col_score = max(0, min(100, 100 - ((col - 80) / 120) * 100))
    components.append(_component(
        f"Cost of living (index={col:.1f})",
        col_score, 0.40,
        f"Spatial interpolation from BLS data at ({lat:.3f}, {lon:.3f}); normalized 80→100, 200→0",
        raw_input=round(col, 1),
    ))

    climate = _interpolate("climate", lat, lon, fallback=70.0)
    components.append(_component(
        f"Climate score ({climate:.1f})",
        max(0, min(100, climate)), 0.35,
        f"Spatial interpolation from climate scores at ({lat:.3f}, {lon:.3f})",
        raw_input=round(climate, 1),
    ))

    aq = _interpolate("air_quality", lat, lon, fallback=70.0)
    components.append(_component(
        f"Air quality ({aq:.1f})",
        max(0, min(100, aq)), 0.25,
        f"Spatial interpolation from EPA AQS monitors at ({lat:.3f}, {lon:.3f})",
        raw_input=round(aq, 1),
    ))

    score = sum(c["contribution"] for c in components)
    return score, components


# ── Category 6: Health Demographics ─────────────────────────────────────

def explain_health_demographics(lat: float, lon: float) -> tuple[float, list[dict], str]:
    components = []

    diabetes = _interpolate("health_diabetesRate", lat, lon, fallback=10.5)
    obesity = _interpolate("health_obesityRate", lat, lon, fallback=31.9)
    ckd = _interpolate("health_ckdRate", lat, lon, fallback=14.0)
    hypertension = _interpolate("health_hypertensionRate", lat, lon, fallback=32.0)
    smoking = _interpolate("health_smokingRate", lat, lon, fallback=14.0)

    score = 100.0
    diabetes_pen = (diabetes - 7) * 2
    obesity_pen = (obesity - 25) * 1.5
    ckd_pen = (ckd - 11) * 2.5
    hyper_pen = (hypertension - 27) * 1.0
    smoking_pen = (smoking - 13) * 1.5

    score -= diabetes_pen + obesity_pen + ckd_pen + hyper_pen + smoking_pen

    components.append(_component(
        f"Diabetes rate ({diabetes:.1f}%)",
        diabetes, 1.0,
        f"CDC PLACES: penalty = (rate - 7) × 2 = {diabetes_pen:.1f} pts off base 100",
        raw_input=round(diabetes, 1),
    ))
    components.append(_component(
        f"Obesity rate ({obesity:.1f}%)",
        obesity, 1.0,
        f"CDC PLACES: penalty = (rate - 25) × 1.5 = {obesity_pen:.1f} pts off base 100",
        raw_input=round(obesity, 1),
    ))
    components.append(_component(
        f"CKD rate ({ckd:.1f}%)",
        ckd, 1.0,
        f"CDC PLACES: penalty = (rate - 11) × 2.5 = {ckd_pen:.1f} pts off base 100",
        raw_input=round(ckd, 1),
    ))
    components.append(_component(
        f"Hypertension rate ({hypertension:.1f}%)",
        hypertension, 1.0,
        f"CDC PLACES: penalty = (rate - 27) × 1.0 = {hyper_pen:.1f} pts off base 100",
        raw_input=round(hypertension, 1),
    ))
    components.append(_component(
        f"Smoking rate ({smoking:.1f}%)",
        smoking, 1.0,
        f"CDC PLACES: penalty = (rate - 13) × 1.5 = {smoking_pen:.1f} pts off base 100",
        raw_input=round(smoking, 1),
    ))

    final = max(30.0, min(100.0, score))
    notes = (
        f"Score = 100 - sum of penalties = 100 - "
        f"({diabetes_pen:.1f} + {obesity_pen:.1f} + {ckd_pen:.1f} + {hyper_pen:.1f} + {smoking_pen:.1f}) "
        f"= {score:.1f}, clamped to [30, 100] = {final:.1f}"
    )
    return final, components, notes


# ── Category 7: Policy ──────────────────────────────────────────────────

def explain_policy(state: str) -> tuple[float, list[dict]]:
    data = get_data()
    tiers = data.policy_tiers
    val = tiers.get(state, 70)
    component = _component(
        f"State policy tier ({state})",
        val, 1.0,
        f"data/manual/policy-tiers.json: {state} = {val}" + (" (fallback 70 for unknown state)" if state not in tiers else ""),
        raw_input=val,
    )
    return val, [component]


# ── Category 8: Socioeconomic ───────────────────────────────────────────

# Same lookup table as scoring.py — duplicated here for clarity
_STATE_SOCIO = {
    "Alabama": 72, "Alaska": 68, "Arizona": 76, "Arkansas": 70,
    "California": 84, "Colorado": 83, "Connecticut": 84, "Delaware": 76,
    "District of Columbia": 82, "Florida": 78, "Georgia": 76, "Hawaii": 74,
    "Idaho": 70, "Illinois": 82, "Indiana": 80, "Iowa": 82,
    "Kansas": 74, "Kentucky": 73, "Louisiana": 72, "Maine": 75,
    "Maryland": 83, "Massachusetts": 86, "Michigan": 80, "Minnesota": 88,
    "Mississippi": 68, "Missouri": 84, "Montana": 69, "Nebraska": 85,
    "Nevada": 73, "New Hampshire": 78, "New Jersey": 81, "New Mexico": 72,
    "New York": 85, "North Carolina": 86, "North Dakota": 72, "Ohio": 92,
    "Oklahoma": 71, "Oregon": 82, "Pennsylvania": 90,
}


def explain_socioeconomic(state: str) -> tuple[float, list[dict]]:
    # The real function has a longer table; use the same value it would produce
    from services.scoring import _socioeconomic
    val = _socioeconomic(state)
    component = _component(
        f"State support services index ({state})",
        val, 1.0,
        "Built-in state socioeconomic index (housing 30%, financial assistance 25%, "
        "support groups 20%, caregiver resources 15%, health literacy 10%)",
        raw_input=val,
    )
    return val, [component]


# ── Master explain function ─────────────────────────────────────────────

# Maps category key → (function, args)
def explain_center_score(
    center: dict,
    patient: dict,
    weights: dict,
) -> dict | None:
    """Compute a center's score and return full provenance.

    Returns None if the center doesn't perform this organ.
    """
    code = center["code"]
    organ = patient["organ"]
    if organ not in center.get("organs", []):
        return None

    lat = center.get("lat", 0)
    lon = center.get("lon", 0)
    state = center.get("state", "")

    # Compute each category with provenance
    med_score, med_components = explain_medical_compatibility(patient)
    wait_score, wait_components, wait_notes = explain_wait_time(code, organ, patient)
    donor_score, donor_components, donor_notes = explain_donor_availability(state, organ, patient, lat, lon)
    quality_score, quality_components = explain_hospital_quality(code, organ, patient)
    geo_score, geo_components = explain_geographic(lat, lon)
    health_score, health_components, health_notes = explain_health_demographics(lat, lon)
    policy_score, policy_components = explain_policy(state)
    socio_score, socio_components = explain_socioeconomic(state)

    category_results = [
        ("medicalCompatibility", med_score, med_components, None),
        ("waitTime", wait_score, wait_components, wait_notes),
        ("donorAvailability", donor_score, donor_components, donor_notes),
        ("hospitalQuality", quality_score, quality_components, None),
        ("geographic", geo_score, geo_components, None),
        ("healthDemographics", health_score, health_components, health_notes),
        ("policy", policy_score, policy_components, None),
        ("socioeconomic", socio_score, socio_components, None),
    ]

    total = sum(score * weights[key] for key, score, _, _ in category_results)
    total = max(0.0, min(100.0, total))

    categories = []
    for key, score, components, notes in category_results:
        w = weights[key]
        categories.append({
            "category": key,
            "score": round(score, 2),
            "weight": round(w, 4),
            "contribution": round(score * w, 2),
            "components": components,
            "notes": notes,
        })

    data_sources = [
        "data/wait-time-distributions-centers.json",
        "data/competing-risks-centers.json",
        "data/post-transplant-outcomes-centers.json",
        "data/donor-registration.json",
        "data/cost-of-living.json",
        "data/air-quality.json",
        "data/health-demographics.json",
        "data/manual/policy-tiers.json",
        "data/manual/climate-scores.json",
        "Built-in scoring rules (see backend/services/scoring.py)",
    ]
    if patient.get("adjust_for_cause_of_death"):
        data_sources.append("data/cause-of-death.json (COD adjustment enabled)")

    return {
        "code": code,
        "name": center.get("name", code),
        "total": round(total, 2),
        "weights_used": {k: round(v, 4) for k, v in weights.items()},
        "categories": categories,
        "data_sources": data_sources,
    }


def explain_all_centers(
    patient: dict,
    custom_weights: dict | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Compute provenance for all centers. Set `limit` to cap (e.g. top 10)."""
    data = get_data()
    centers = data.all_centers.get("centers", {})

    weights = dict(DEFAULT_WEIGHTS)
    if custom_weights:
        expected = set(DEFAULT_WEIGHTS.keys())
        if set(custom_weights.keys()) == expected:
            total_w = sum(custom_weights.values())
            if total_w > 0:
                weights = {k: v / total_w for k, v in custom_weights.items()}

    results = []
    for code, center_data in centers.items():
        result = explain_center_score(center_data, patient, weights)
        if result is not None:
            results.append(result)

    results.sort(key=lambda r: r["total"], reverse=True)
    if limit is not None:
        results = results[:limit]
    return results
