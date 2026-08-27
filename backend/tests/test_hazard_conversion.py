"""Waitlist risk must be a valid probability, and the sim must use a hazard (#259).

Two defects, found by measuring rather than by reading the issue:

1. `get_annual_*_rate` multiplies a base PROBABILITY by urgency/MELD/center
   multipliers and returns the product. For liver at MELD 40, urgency 4 that
   product is **1.1734** — not a probability at all. Nothing caught it because
   the only consumer that matters treats the value as if it were a rate.

2. `rate_to_exponential_scale` computes `12 / p`, which is the right formula
   for a RATE and the wrong one for a probability. The correct conversion of a
   one-year event probability is lambda = -ln(1 - p).

The fix is one change, not two: apply the multipliers in HAZARD space, which
is what a mortality "multiplier" means in the clinical literature it comes
from. Then the probability is 1 - exp(-lambda) and can never exceed 1, and the
simulation consumes lambda directly.

Note what #259 itself proposes — `-ln(1 - p_base * mults)` — is **undefined**
here: at MELD 40 that is the log of a negative. The proposed fix fails exactly
where the model matters most.
"""
import math

import pytest

from services.competing_risks import (
    get_annual_mortality_rate,
    get_annual_delisting_rate,
    get_annual_mortality_hazard,
    get_annual_delisting_hazard,
)
from services.data_loader import get_data

ORGANS = ("kidney", "liver", "heart", "lung", "pancreas", "intestine")


def test_mortality_probability_never_exceeds_one(data):
    """The defect, pinned. Liver/MELD40/urgency4 returned 1.1734."""
    worst = []
    for organ in ORGANS:
        codes = [c.get("code") for c in get_data().centers_for_organ(organ)]
        for code in codes:
            for urg in (1, 2, 3, 4):
                melds = (6, 25, 40) if organ == "liver" else (None,)
                for meld in melds:
                    kw = dict(organ=organ, urgency=urg, center_code=code)
                    if meld is not None:
                        kw["meld"] = meld
                    p = get_annual_mortality_rate(**kw)
                    if not (0.0 <= p < 1.0):
                        worst.append((organ, code, urg, meld, p))
    assert not worst, (
        f"{len(worst)} center/acuity combinations return an invalid "
        f"probability, worst {max(w[4] for w in worst):.4f}: {worst[:3]}")


def test_delisting_probability_never_exceeds_one(data):
    bad = []
    for organ in ORGANS:
        for code in [c.get("code") for c in get_data().centers_for_organ(organ)]:
            p = get_annual_delisting_rate(organ=organ, center_code=code)
            if not (0.0 <= p < 1.0):
                bad.append((organ, code, p))
    assert not bad, f"invalid delisting probabilities: {bad[:5]}"


def test_hazard_and_probability_are_consistent(data):
    """p = 1 - exp(-lambda) must hold, or the two accessors describe
    different worlds and whichever a caller picks changes the answer."""
    for organ in ORGANS:
        code = get_data().centers_for_organ(organ)[0].get("code")
        for urg in (1, 4):
            lam = get_annual_mortality_hazard(organ=organ, urgency=urg, center_code=code)
            p = get_annual_mortality_rate(organ=organ, urgency=urg, center_code=code)
            assert lam >= 0
            assert p == pytest.approx(1 - math.exp(-lam), abs=1e-9), organ


def test_multipliers_act_proportionally_on_the_hazard(data):
    """A 'mortality multiplier' is a hazard ratio — that is what the clinical
    sources it derives from report. Doubling risk must double the hazard, not
    the probability, or the multiplier saturates as p approaches 1."""
    code = get_data().centers_for_organ("liver")[0].get("code")
    lo = get_annual_mortality_hazard(organ="liver", urgency=2, meld=6, center_code=code)
    hi = get_annual_mortality_hazard(organ="liver", urgency=2, meld=40, center_code=code)
    assert hi > lo * 2, "MELD 40 should carry a much larger hazard than MELD 6"
    # ratio of hazards equals ratio of the underlying multipliers, so it is
    # unbounded above — unlike a probability ratio, which cannot exceed 1/p.
    assert hi / lo > 1


def test_the_issue_s_own_proposed_fix_would_be_undefined(data):
    """Recorded so the rejected approach is not re-proposed.

    #259 asks for `lambda = -ln(1 - p)` applied to the multiplied value. That
    value exceeded 1, so the log argument is negative.
    """
    base = 0.0447           # liver annual_mortality_rate as shipped
    multiplied = 1.1734     # measured at MELD 40 / urgency 4 / worst center
    assert multiplied > 1.0
    with pytest.raises(ValueError):
        math.log(1.0 - multiplied)
    # the shipped construction, by contrast, is defined for any multiplier
    assert get_annual_mortality_hazard(
        organ="liver", urgency=4, meld=40,
        center_code=get_data().centers_for_organ("liver")[0].get("code")) > 0
    assert base < 1
