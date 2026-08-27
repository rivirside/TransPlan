"""#413 / L-088: Rh factor must not change any model output.

US solid-organ allocation is ABO-matched. Before this, an Rh-negative kidney
candidate was shown a median wait 2.74 months longer and a p24 0.018 lower
than an otherwise identical Rh-positive one, from a hand-set constant with no
source (docs/rh-factor-report.md).

The fix canonicalizes blood type to its ABO group at every model lookup rather
than editing the tables, so these tests assert *behavior*: same answer for
`X+` and `X-`, and — critically — a still-different answer between ABO groups.
Making Rh inert by accidentally making blood type inert would satisfy half of
this file and destroy the model, so both halves are checked everywhere.
"""
import pytest

from models.schemas import PatientProfile
from services import distributions, scoring
from services.blood_type import abo_group, model_key

GROUPS = ("O", "A", "B", "AB")
ORGANS = ("kidney", "liver", "heart", "lung", "pancreas", "intestine")


def _patient(organ, bt):
    return {"organ": organ, "blood_type": bt, "age": 50, "sex": "male",
            "urgency": 2}


# ── the mapping itself ──────────────────────────────────────────────────────

@pytest.mark.parametrize("group", GROUPS)
def test_both_rh_variants_map_to_one_key(group):
    assert model_key(f"{group}+") == model_key(f"{group}-") == f"{group}+"
    assert abo_group(f"{group}-") == group


def test_unrecognized_input_passes_through_for_the_caller_to_handle():
    """Not mapped to a plausible-looking default. Each caller has its own
    documented fallback (85 for scoring, 1.0 for multipliers); inventing one
    here would hide bad input behind a real-looking number."""
    assert model_key("banana") == "banana"
    assert abo_group("banana") is None
    # And the sliced-string implementation this replaced would have produced
    # "banan" + "+", which looks like a key.
    assert not model_key("banana").endswith("+")


# ── wait-time distribution ──────────────────────────────────────────────────

@pytest.mark.parametrize("organ", ORGANS)
@pytest.mark.parametrize("group", GROUPS)
def test_wait_params_ignore_rh(organ, group):
    plus = distributions.get_wait_time_params(organ, f"{group}+")
    minus = distributions.get_wait_time_params(organ, f"{group}-")
    assert plus == minus, f"{organ} {group}: Rh still moves the wait distribution"


@pytest.mark.parametrize("organ", ORGANS)
def test_abo_still_separates_the_groups(organ):
    """The other half. O must still wait longer than AB."""
    medians = {g: distributions.get_wait_time_params(organ, f"{g}+")[1]
               for g in GROUPS}
    assert len(set(round(m, 4) for m in medians.values())) == 4, (
        f"{organ}: ABO groups collapsed ({medians}) — the fix went too far"
    )
    assert medians["O"] > medians["AB"], (
        f"{organ}: O no longer waits longer than AB ({medians})"
    )


# ── scoring ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("group", GROUPS)
def test_medical_compatibility_ignores_rh(group):
    a = scoring._medical_compatibility(_patient("kidney", f"{group}+"))
    b = scoring._medical_compatibility(_patient("kidney", f"{group}-"))
    assert a == b, f"{group}: Rh still moves the compatibility score"


def test_scoring_still_separates_abo_groups():
    vals = {g: scoring._medical_compatibility(_patient("kidney", f"{g}+"))
            for g in GROUPS}
    assert len(set(vals.values())) == 4, f"ABO collapsed in scoring: {vals}"
    assert vals["AB"] > vals["O"]


def test_full_score_is_identical_for_both_rh_variants(data):
    """End to end through the real scorer, not just the sub-component."""
    plus = scoring.score_all_centers(_patient("kidney", "O+"))
    minus = scoring.score_all_centers(_patient("kidney", "O-"))
    assert [(c.code, round(c.total, 6)) for c in plus] == \
           [(c.code, round(c.total, 6)) for c in minus]


def test_the_explain_view_agrees_with_the_score_it_explains(data):
    """A provenance trail that disagrees with its own number is worse than
    none — and this table was edited separately, so it can drift."""
    from services.scoring_explain import explain_medical_compatibility
    for group in GROUPS:
        for rh in ("+", "-"):
            bt = f"{group}{rh}"
            explained, _ = explain_medical_compatibility(_patient("kidney", bt))
            direct = scoring._medical_compatibility(_patient("kidney", bt))
            assert round(explained, 6) == round(direct, 6), bt


def test_the_explain_lookup_table_no_longer_offers_rh_rows(data):
    from services.scoring_explain import explain_medical_compatibility
    _, components = explain_medical_compatibility(_patient("kidney", "O-"))
    bt_component = next(c for c in components if c["name"].startswith("Blood type"))
    labels = [row["label"] for row in bt_component["details"]["lookup_table"]]
    assert labels == ["O", "A", "B", "AB"], labels
    assert [r for r in bt_component["details"]["lookup_table"] if r["highlighted"]], \
        "the patient's own ABO group is not highlighted"


# ── the simulation engines ──────────────────────────────────────────────────

def test_monte_carlo_p24_is_identical_across_rh(data):
    from services import monte_carlo
    out = {}
    for bt in ("O+", "O-"):
        res = monte_carlo.simulate(
            PatientProfile(organ="kidney", blood_type=bt, age=50, sex="male",
                           urgency=2),
            n_iterations=2000, seed=11)
        out[bt] = [(c.center_code, round(c.p_transplant_24mo, 10))
                   for c in res.cities]
    assert out["O+"] == out["O-"]


def test_monte_carlo_still_responds_to_abo(data):
    """Guard the guard: if blood type stopped reaching the simulation at all,
    the test above would pass while the model was broken."""
    from services import monte_carlo
    out = {}
    for bt in ("O+", "AB+"):
        res = monte_carlo.simulate(
            PatientProfile(organ="kidney", blood_type=bt, age=50, sex="male",
                           urgency=2),
            n_iterations=2000, seed=11)
        out[bt] = res.cities[0].p_transplant_24mo
    assert abs(out["AB+"] - out["O+"]) > 0.01, (
        f"ABO no longer moves p24 ({out}) — Rh-blindness must not become "
        "blood-type-blindness"
    )


def test_bbn_supply_cpt_collapses_rh_but_not_abo(data):
    """The CPT axis deliberately keeps 8 levels — its shape is part of the
    fitted network — so the collapse has to show up in the VALUES."""
    import numpy as np
    from services.bbn_parameterizer import BLOOD_TYPES, build_donor_supply_cpt
    cpt = build_donor_supply_cpt()
    idx = {bt: i for i, bt in enumerate(BLOOD_TYPES)}
    # Shape is (node_card, organ, blood_type, region) — find the blood-type
    # axis by length rather than hardcoding 2, so a future reshape fails loudly
    # here instead of silently comparing organs to each other (which is what
    # the first version of this test did).
    axes = [i for i, n in enumerate(cpt.shape) if n == len(BLOOD_TYPES)]
    assert len(axes) == 1, f"cannot identify the blood-type axis in {cpt.shape}"
    bt_axis = axes[0]

    for g in GROUPS:
        assert np.allclose(np.take(cpt, idx[f"{g}+"], axis=bt_axis),
                           np.take(cpt, idx[f"{g}-"], axis=bt_axis)), \
            f"{g}: BBN still distinguishes Rh"
    assert not np.allclose(np.take(cpt, idx["O+"], axis=bt_axis),
                           np.take(cpt, idx["AB+"], axis=bt_axis)), \
        "BBN no longer distinguishes ABO groups"
