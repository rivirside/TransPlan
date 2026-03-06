"""
Competing risks model: P(transplant) vs P(mortality) vs P(delisting) (Milestone 4).
# FIXME (Milestone 4): Implement Kaplan-Meier / exponential competing events.
"""


def get_annual_mortality_rate(organ: str, city: str, urgency: int) -> float:
    """
    Return estimated annual mortality rate while on waitlist.
    # FIXME (Milestone 4): Load from data/competing-risks.json.
    """
    # Placeholder national averages from published literature
    defaults = {
        "kidney": 0.06,
        "liver": 0.12,
        "heart": 0.15,
        "lung": 0.18,
        "pancreas": 0.05,
        "intestine": 0.20,
    }
    base = defaults.get(organ, 0.08)
    urgency_multiplier = 1.0 + (urgency - 1) * 0.15  # higher urgency → higher mortality
    return base * urgency_multiplier


def get_annual_delisting_rate(organ: str, city: str) -> float:
    """
    Return estimated annual delisting rate (improved/too sick/non-compliant).
    # FIXME (Milestone 4): Load from data/competing-risks.json.
    """
    defaults = {
        "kidney": 0.04,
        "liver": 0.06,
        "heart": 0.05,
        "lung": 0.07,
        "pancreas": 0.03,
        "intestine": 0.08,
    }
    return defaults.get(organ, 0.05)
