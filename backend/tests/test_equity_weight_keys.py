"""No demographic cell may silently drop out of the equity analysis.

`_profile_weight` multiplies three independent lookups, each defaulting to
0.0:

    bt_w.get(blood_type, 0.0) * ages.get(age_bracket, 0.0) * sex_w.get(sex, 0.0)

Because it is a product, ANY one key miss zeroes the whole cell — and a
zero-weight cell contributes nothing to the weighted Gini while the Gini still
computes and reports a perfectly ordinary number. That is the #446 shape (a
lookup key nothing matches) with a multiplicative amplifier, on the metric the
equity page exists to report.

Swept 2026-08-28: clean. All 48 cells resolve for every organ in both adult
and pediatric mode, weights summing to 1.0, and every organ carries an
observed pediatric age mix rather than the hardcoded fallback. Pinned rather
than merely noted, because the failure is silent by construction.

The keys are cross-checked between the GRID and the WEIGHT TABLES, not
asserted against a hand-copied list — the grid drives the simulation and the
tables drive the weighting, and a rename on either side is exactly what would
break this.

Note for anyone extending: the pediatric path uses PEDIATRIC_AGE_BRACKETS,
not AGE_BRACKETS (equity.py:376). Sweeping pediatric with the adult brackets
reports all 48 cells at zero weight, which looks like a catastrophic bug and
is not one. That happened here first.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import equity as eq  # noqa: E402
from services.data_loader import load_all, get_data  # noqa: E402

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]


@pytest.fixture(scope="module", autouse=True)
def _loaded():
    load_all()


def _brackets(pediatric):
    # Mirrors equity.py:376 exactly.
    return eq.PEDIATRIC_AGE_BRACKETS if pediatric else eq.AGE_BRACKETS


@pytest.mark.parametrize("organ", ORGANS)
@pytest.mark.parametrize("pediatric", [False, True], ids=["adult", "pediatric"])
def test_no_demographic_cell_has_zero_weight(organ, pediatric):
    brackets = _brackets(pediatric)
    weights = eq.waitlist_weights(organ)
    age_weights = eq.pediatric_age_weights(organ) if pediatric else None

    zero = []
    for bt in eq.BLOOD_TYPES:
        for ab in brackets:
            for sex in eq.SEXES:
                if eq._profile_weight(bt, ab["label"], sex,
                                      age_weights, weights) == 0.0:
                    zero.append((bt, ab["label"], sex))
    assert zero == [], (
        f"{organ}/{'pediatric' if pediatric else 'adult'}: {len(zero)} of "
        f"{len(eq.BLOOD_TYPES) * len(brackets) * len(eq.SEXES)} cells carry "
        f"zero weight and drop out of the Gini silently: {zero[:4]}"
    )


@pytest.mark.parametrize("organ", ORGANS)
@pytest.mark.parametrize("pediatric", [False, True], ids=["adult", "pediatric"])
def test_the_cell_weights_form_a_distribution(organ, pediatric):
    """A cell can also be diluted rather than zeroed — if the three tables
    stop covering the grid jointly, the total drifts off 1.0 while every
    individual cell stays positive."""
    brackets = _brackets(pediatric)
    weights = eq.waitlist_weights(organ)
    age_weights = eq.pediatric_age_weights(organ) if pediatric else None
    total = sum(
        eq._profile_weight(bt, ab["label"], sex, age_weights, weights)
        for bt in eq.BLOOD_TYPES for ab in brackets for sex in eq.SEXES
    )
    assert 0.98 <= total <= 1.02, (
        f"{organ}/{'pediatric' if pediatric else 'adult'}: cell weights sum to "
        f"{total:.4f}, not 1 — the grid and the weight tables have diverged"
    )


@pytest.mark.parametrize("organ", ORGANS)
def test_the_abo_decomposition_resolves_every_blood_type(organ):
    """A separate lookup from the one above (equity.py:240) and a separate
    chance to miss. A blood type absent here contributes prevalence 0 to the
    between/within split, quietly removing it from the decomposition."""
    weights = eq.waitlist_weights(organ).get("blood_type") or eq.BLOOD_TYPE_PREVALENCE
    missing = [bt for bt in eq.BLOOD_TYPES if bt not in weights]
    assert missing == [], f"{organ}: {missing} absent from the ABO prevalence table"
    total = sum(weights[bt] for bt in eq.BLOOD_TYPES)
    assert 0.98 <= total <= 1.02, f"{organ}: ABO prevalence sums to {total:.4f}"


@pytest.mark.parametrize("organ", ORGANS)
def test_pediatric_age_mix_is_observed_not_the_fallback(organ):
    """`pediatric_age_weights` falls back to a hardcoded constant when the
    parsed mix is absent or does not sum to 1. The fallback is legitimate, but
    silently using it for every organ would mean the pediatric equity numbers
    are the same hand-set distribution everywhere while appearing observed."""
    mix = (get_data().pediatric.get(organ, {}) or {}).get("national_age_mix")
    assert mix, (
        f"{organ}: no observed pediatric age mix — equity is using the "
        f"hardcoded _PEDIATRIC_WEIGHTS_FALLBACK for it"
    )
    resolved = eq.pediatric_age_weights(organ)
    assert set(resolved) == {ab["label"] for ab in eq.PEDIATRIC_AGE_BRACKETS}


def test_the_grid_and_the_tables_use_the_same_vocabulary():
    """Cross-check rather than a hand-copied list: the grid drives which
    profiles get simulated and the tables drive how they are weighted, so a
    rename on either side is what would break this."""
    assert set(eq.BLOOD_TYPES) == set(eq.BLOOD_TYPE_PREVALENCE), (
        "the simulated blood types and the prevalence table have diverged"
    )
    assert set(eq.SEXES) == set(eq.SEX_WEIGHTS)
    assert {ab["label"] for ab in eq.AGE_BRACKETS} == set(eq.AGE_BRACKET_WEIGHTS)
