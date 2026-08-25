"""Canonical reference-patient definitions for validation scripts (#339).

Single source of truth: run-center-calibration, run-assumption-sweep, and
run-decile-calibration previously carried three copies whose parity was
claimed in comments but enforced by nothing. Every published validation
report describes THESE patients; change them here and everywhere follows.
"""

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]


def reference_patient_kwargs(organ: str) -> dict:
    """Kwargs for the per-organ reference candidate (PatientProfile-ready)."""
    base = {"organ": organ, "blood_type": "O+", "urgency": 2, "age": 50,
            "sex": "male", "adjust_for_cause_of_death": False}
    if organ == "kidney":
        base["cpra"] = 20
    elif organ == "liver":
        base["meld"] = 22
    elif organ == "lung":
        base["las"] = 50.0
    return base
