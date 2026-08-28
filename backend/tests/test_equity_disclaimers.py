"""#235: the equity disclaimers assert facts about the model — check them.

The issue proposed moving these strings out of `equity.py` into a config file
"for easier updates". Declined, with reasons in the issue thread: these are not
copy, they are precise claims about what the model does, each tied to a
specific modeling decision. The real defect is not where they live — it is that
nothing verified them, so two had gone stale:

  * "Weighted metrics use the OBSERVED per-organ waitlist composition" was
    false of the between/within decomposition, which was still on
    general-population prevalence (#337 moved the headline metric and missed
    this one).
  * The rare-group claim described a distortion that #413 changed, by making
    Rh inert so that AB- is no longer a distinct cell.

Externalizing them would have moved them FURTHER from the code they describe.
Pinning them to it is the fix.
"""
import re

import pytest

from models.schemas import PatientProfile
from services import equity
from services.equity import (
    AGE_BRACKETS,
    BLOOD_TYPES,
    EQUITY_DISCLAIMERS,
    SEXES,
)

TEXT = " ".join(EQUITY_DISCLAIMERS)


@pytest.fixture(scope="module")
def kidney_result(data):
    return equity.compute_equity_analysis(
        PatientProfile(organ="kidney", blood_type="O+", age=50, sex="male",
                       urgency=2),
        n_iterations=100, seed=5)


def test_the_cell_count_claim_matches_the_actual_matrix():
    """'48 demographic cells' is arithmetic on three lists that can change."""
    claimed = {int(m) for m in re.findall(r"\b(\d+) (?:demographic )?cells", TEXT)}
    actual = len(BLOOD_TYPES) * len(AGE_BRACKETS) * len(SEXES)
    assert claimed, "no cell-count claim found to check"
    assert claimed == {actual}, (
        f"disclaimers claim {claimed} cells, matrix is "
        f"{len(BLOOD_TYPES)}x{len(AGE_BRACKETS)}x{len(SEXES)} = {actual}"
    )


def test_the_distinct_cell_claim_is_true(kidney_result):
    """'only 24 are distinct' — because Rh is inert since #413. If Rh ever
    becomes live again this is wrong, and so is the reason given for it."""
    claimed = re.search(r"only (\d+) are distinct", TEXT)
    assert claimed, "no distinct-cell claim found"
    bt_rows = kidney_result.cities[0].dimension_disparities["blood_type"]
    by_label = {r["value"]: round(r["p24"], 12) for r in bt_rows}
    distinct_bt = len(set(by_label.values()))
    expected = distinct_bt * len(AGE_BRACKETS) * len(SEXES)
    assert int(claimed.group(1)) == expected, (
        f"disclaimer says {claimed.group(1)} distinct cells; the blood-type "
        f"dimension has {distinct_bt} distinct values -> {expected}"
    )


def test_each_rh_pair_really_is_identical(kidney_result):
    """The claim that +/- pairs are identical 'by construction'."""
    rows = {r["value"]: r["p24"]
            for r in kidney_result.cities[0].dimension_disparities["blood_type"]}
    for group in ("O", "A", "B", "AB"):
        assert rows[f"{group}+"] == rows[f"{group}-"], (
            f"{group}: the Rh pair differs, so the disclaimer's 'identical by "
            "construction' is false — did #413 get reverted?"
        )
    # And not vacuously: the ABO groups must still differ from each other.
    assert len({rows[f"{g}+"] for g in ("O", "A", "B", "AB")}) == 4


def test_the_weighted_metrics_claim_covers_the_decomposition(data):
    """The disclaimer says weighted metrics 'including the between/within
    blood-type decomposition' use the observed composition. Verify by forcing
    the observed weights to differ and checking the decomposition moves."""
    results = [{"blood_type": bt, "p24": 0.5 + 0.01 * i, "weight": 1.0}
               for i, bt in enumerate(BLOOD_TYPES)]
    with_organ = equity._abo_decomposition(results, "kidney")
    general = equity._abo_decomposition(results, None)
    assert with_organ != general, (
        "passing an organ no longer changes the decomposition — it is not "
        "using the observed waitlist composition, and the disclaimer says it is"
    )


def test_the_type_b_claim_is_supported_by_the_shipped_weights(data):
    """'type B is 1.5x over-represented on the kidney waitlist'."""
    obs = equity.waitlist_weights("kidney").get("blood_type") or {}
    gen = equity.BLOOD_TYPE_PREVALENCE
    ratio = (obs["B+"] + obs["B-"]) / (gen["B+"] + gen["B-"])
    assert 1.3 <= ratio <= 1.7, (
        f"kidney type B over-representation is now {ratio:.2f}x; the "
        "disclaimer says 1.5x"
    )


def test_the_closed_form_claim_matches_the_reported_iterations(kidney_result):
    """'computed in closed form ... no Monte Carlo uncertainty' (#216).
    If sampling came back, iterations_per_profile would stop being 0."""
    assert "closed form" in TEXT
    assert kidney_result.iterations_per_profile == 0, (
        "iterations_per_profile is non-zero, so the equity path is sampling "
        "again and the closed-form disclaimer is false"
    )


def test_every_disclaimer_is_delivered(kidney_result):
    """They are described as mandatory on every response."""
    assert kidney_result.disclaimers == EQUITY_DISCLAIMERS
    assert len(kidney_result.disclaimers) >= 7


def test_disclaimers_do_not_claim_unmodeled_dimensions_are_modeled():
    """They enumerate what is NOT modeled; that list must stay true."""
    for absent in ("race", "insurance", "socioeconomic"):
        assert absent in TEXT.lower(), f"{absent} is no longer disclosed as unmodeled"
    swept = {"blood type", "age", "sex"}
    for dim in swept:
        assert dim in TEXT.lower()
