"""Absence of living-donor data must not be rewarded.

`_donor_availability` gives a center with no living-donor score a flat **75**,
worth 28% of that category. Measured against the real distribution, 75 sits at

    kidney  81st percentile of 196 scored centers (mean 55.3, median 57.1)
    liver   91st percentile of  56 scored centers (mean 42.5, median 45.1)

So 92 of 148 liver centers — 62% — were scored better than nine tenths of the
centers that were actually measured, purely for having no data. A center
measured and found to do little living donation ranked *below* one never
measured at all.

**Why the value is changed here and the analogous zero in `_hospital_quality`
was not** (#448/L-099): there the zero was directionally defensible, because
SRTR suppresses small programs and the affected centers had a median waitlist
cohort of 17 against 166. Here no reading supports it. The score is
`100·log1p(count)/log1p(max)` over SRTR Table D1 living-donor counts, and
absence from a living-donor table cannot imply top-decile living-donor
activity.

**What is NOT claimed.** Absence is not proven to mean zero. Checked against
the raw 2511 workbooks: all 39 kidney and all 92 liver missing centers are
absent from Table D1 *entirely* — none has an unparseable cell, so the parser
drops nobody. But SRTR does list some centers with a count of 0 (7 kidney, 5
liver), and if the table covered every program the absent ones would appear
that way too. That asymmetry is unexplained, so scoring absence as 0 would
assert something unverified — and it changes the top-ranked liver center.
The median is the "no information, assume typical" position: it removes an
unearned advantage without asserting a penalty. #451 tracks the data question.
"""
import json
import statistics
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import provenance as pv  # noqa: E402
from services import scoring  # noqa: E402
from services.data_loader import load_all, get_data  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LIVING_ORGANS = ("kidney", "liver")


@pytest.fixture(scope="module")
def data():
    load_all()
    return get_data()


def _real_scores(data, organ):
    return [v for v in data.living_donors.get("scores", {}).get(organ, {}).values()
            if isinstance(v, (int, float))]


@pytest.mark.parametrize("organ", LIVING_ORGANS)
def test_the_fallback_is_not_better_than_typical(data, organ):
    """The invariant. Whatever value is chosen, a center with no data must not
    outrank the median measured center on this component."""
    real = _real_scores(data, organ)
    assert len(real) >= 40, f"only {len(real)} {organ} scores; the check is weak"
    fallback = scoring.living_donor_fallback(organ)
    median = statistics.median(real)
    assert fallback <= median + 1e-9, (
        f"{organ}: centers with NO living-donor data score {fallback}, above the "
        f"median measured center ({median}) — absence is rewarded"
    )


@pytest.mark.parametrize("organ", LIVING_ORGANS)
def test_the_fallback_is_derived_from_the_data(data, organ):
    """Not a hand-set constant: it must track the file, so a data refresh
    cannot leave it stranded at a percentile nobody re-checked."""
    real = _real_scores(data, organ)
    assert scoring.living_donor_fallback(organ) == pytest.approx(
        statistics.median(real), abs=1e-6)


def test_a_non_living_donor_organ_still_gets_a_neutral_value():
    """Heart, lung, pancreas and intestine have no living donation at all, so
    the component is not informative for them and must not penalise."""
    for organ in ("heart", "lung", "pancreas", "intestine"):
        assert scoring.living_donor_fallback(organ) == 75.0


@pytest.mark.parametrize("organ", LIVING_ORGANS)
def test_missing_living_donor_data_is_disclosed(organ, data):
    """A substituted value the reader cannot see is the #448 defect again."""
    from services.monte_carlo import simulate
    from models.schemas import PatientProfile

    result = simulate(PatientProfile(organ=organ, blood_type="O+", age=45,
                                     sex="male", urgency=2),
                      n_iterations=200, seed=42)
    scores = data.living_donors.get("scores", {}).get(organ, {})
    missing = {c.center_code for c in result.cities
               if not isinstance(scores.get(c.center_code), (int, float))}
    tagged = {c.center_code for c in result.cities
              if pv.TAG_LIVING_DONOR in (c.data_quality or [])}
    assert missing - tagged == set(), (
        f"{organ}: {len(missing - tagged)} centers use the living-donor "
        f"substitute with no marker"
    )
    assert tagged - missing == set(), (
        f"{organ}: {len(tagged - missing)} centers marked but have their own score"
    )


def test_the_tag_does_not_fire_for_non_living_donor_organs():
    """Heart has no living donation; a marker there would be noise on every
    row and would say nothing about which center differs."""
    from services.monte_carlo import simulate
    from models.schemas import PatientProfile
    result = simulate(PatientProfile(organ="heart", blood_type="O+", age=45,
                                     sex="male", urgency=2),
                      n_iterations=200, seed=42)
    tagged = [c.center_code for c in result.cities
              if pv.TAG_LIVING_DONOR in (c.data_quality or [])]
    assert tagged == [], f"{len(tagged)} heart centers tagged for living-donor data"


def test_the_premise_still_holds(data):
    """Guard the finding. If coverage ever becomes complete, the fallback stops
    mattering and this suite is pinning nothing."""
    for organ in LIVING_ORGANS:
        scores = data.living_donors.get("scores", {}).get(organ, {})
        listed = [c for c, v in data.all_centers.get("centers", {}).items()
                  if organ in (v.get("organs") or [])]
        missing = [c for c in listed if not isinstance(scores.get(c), (int, float))]
        assert missing, (
            f"{organ}: every listed center now has a living-donor score — "
            "the fallback is unreachable and this suite can be retired"
        )
