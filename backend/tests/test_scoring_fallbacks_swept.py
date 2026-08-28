"""Every absent-data fallback in the scoring path, swept and pinned.

`_hospital_quality` turned out to have two defects reachable only when data
was absent (#446, #448), and `_donor_availability` a third (#452). That made
"what does this do when the data is missing?" worth asking of the whole
scoring path rather than one function at a time.

The results, so nobody has to redo the sweep to learn it was done:

    _hospital_quality  rating key      BUG   -> #446 (dead key, 22 centers)
    _hospital_quality  n_1yr = 0       BUG   -> #448 (undisclosed, 91 pairs)
    _donor_availability living donor   BUG   -> #452 (75 = 91st percentile)
    score_center       lat/lon = (0,0) LATENT-> #450 (guarded, 0 live cases)
    _interpolate       8 layers        CLEAN -> pinned below
    _policy            state tier      CLEAN -> pinned below
    _socioeconomic     state table     CLEAN -> pinned below
    _cod_multiplier    returns None    CLEAN -> caller handles it

The last three needed a correction before they were clean. Reading them with
`state_abbr` — which is NOT what `score_center` passes — made both state
scorers look like constants returning one value for all 48 states. They pass
`center["state"]`, the full name, and then return 26 and 24 distinct values.
That is the fifth time in this sweep an expectation of mine, not the code,
was the broken part; hence these tests read the field from `score_center`'s
own source rather than assuming.
"""
import collections
import inspect
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import scoring  # noqa: E402
from services.data_loader import load_all, get_data  # noqa: E402


@pytest.fixture(scope="module")
def data():
    load_all()
    return get_data()


def _spatial_layers():
    """Layer names and fallbacks, read from the source that uses them."""
    src = inspect.getsource(scoring)
    return [(m.group(1), float(m.group(2))) for m in
            re.finditer(r'_interpolate\("(\w+)",[^)]*fallback=([\d.]+)', src)]


def test_the_layer_scan_finds_layers(data):
    assert len(_spatial_layers()) >= 6, "the sweep below would be vacuous"


@pytest.mark.parametrize("layer,fallback", _spatial_layers())
def test_no_center_falls_back_on_a_spatial_layer(data, layer, fallback):
    """A missing surface would hand every center the same constant, and a
    query failure would hand it to individual centers silently."""
    surface = scoring._get_spatial_surface(layer)
    assert surface is not None, (
        f"spatial layer '{layer}' is unavailable — every center scores the "
        f"flat fallback {fallback} for it"
    )
    bad = []
    for code, c in data.all_centers.get("centers", {}).items():
        try:
            if surface.query(c["lat"], c["lon"]) is None:
                bad.append(code)
        except Exception:
            bad.append(code)
    assert bad == [], f"{layer}: {len(bad)} centers fall back at query time: {bad[:5]}"

    # Exercise _interpolate itself, not just the surface it should consult.
    # Asserting on _get_spatial_surface alone leaves the actual call path
    # untested — a negative test that stubbed the surface inside _interpolate
    # passed cleanly until this was added.
    values = {scoring._interpolate(layer, c["lat"], c["lon"], fallback=fallback)
              for c in data.all_centers.get("centers", {}).values()}
    assert len(values) > 1, (
        f"_interpolate('{layer}', ...) returns one value for all 248 centers "
        f"— it is not consulting the surface"
    )
    assert values != {fallback}, (
        f"_interpolate('{layer}', ...) returns the fallback {fallback} everywhere"
    )


def test_score_center_passes_the_full_state_name():
    """The premise of the two tests below, and the thing I got wrong first.

    `_socioeconomic`'s table is keyed by full state names. If `score_center`
    ever passes `state_abbr` instead, every lookup misses and the whole table
    goes dead silently — the same shape as the #446 rating key.
    """
    src = inspect.getsource(scoring.score_center)
    assert 'state = center.get("state"' in src, (
        "score_center no longer reads center['state'] — check that the state "
        "tables are still keyed to match what it passes"
    )
    assert "_socioeconomic(state)" in inspect.getsource(scoring)


def test_every_centers_state_resolves_in_the_policy_tiers(data):
    tiers = data.policy_tiers
    states = {c["state"] for c in data.all_centers.get("centers", {}).values()}
    missing = sorted(s for s in states if s not in tiers)
    assert missing == [], (
        f"{len(missing)} states have no policy tier and take the default: {missing}"
    )


def test_every_centers_state_resolves_in_the_socioeconomic_table(data):
    src = inspect.getsource(scoring._socioeconomic)
    table = set(re.findall(r'"([A-Z][a-zA-Z ]+)":\s*\d+', src))
    states = {c["state"] for c in data.all_centers.get("centers", {}).values()}
    missing = sorted(s for s in states if s not in table)
    assert missing == [], (
        f"{len(missing)} states are absent from the socioeconomic table and "
        f"take the default: {missing}"
    )


@pytest.mark.parametrize("fn_name,default", [("_policy", 70), ("_socioeconomic", 75)])
def test_the_state_scorers_actually_discriminate(data, fn_name, default):
    """Pin sensitivity beside the coverage checks. A table that resolves for
    every state but returns one value everywhere cannot reorder anything —
    the L-084 shape — and the coverage tests above would still pass."""
    fn = getattr(scoring, fn_name)
    states = {c["state"] for c in data.all_centers.get("centers", {}).values()}
    values = collections.Counter(fn(s) for s in states)
    assert len(values) >= 10, (
        f"{fn_name} returns only {len(values)} distinct values across "
        f"{len(states)} states — it can barely reorder centers"
    )
    most_common, count = values.most_common(1)[0]
    assert count < len(states) * 0.5, (
        f"{fn_name} returns {most_common} for {count} of {len(states)} states"
    )


# ── The simulation path ─────────────────────────────────────────────────
#
# The sweep above covers scoring. The engines are a separate path with their
# own lookups, and the same question applies: what happens when a key misses?
#
# All three sites below are clean, and are pinned rather than merely checked,
# because #446 showed what a lookup key that never matches costs.
#
# NOTE for anyone extending this: `_DISTRIBUTIONS` and `_RISKS` are lazily
# initialised module globals. Reading them straight after `load_all()` returns
# None, which makes every organ look absent. Both must be forced through a
# public call first. Getting this wrong twice is what prompted the note.

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
BLOOD_TYPES = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]


def test_every_organ_and_blood_type_resolves_a_multiplier(data):
    """A miss here would silently hand the patient the neutral 1.0 — the #446
    shape, on the input that most personalises a wait estimate."""
    import services.distributions as dist
    from services.blood_type import model_key

    dist.get_wait_time_params("kidney", "O+")      # force lazy init
    unresolved = []
    for organ in ORGANS:
        mult = (dist._DISTRIBUTIONS.get(organ) or {}).get("blood_type_multipliers", {})
        unresolved += [(organ, bt) for bt in BLOOD_TYPES if model_key(bt) not in mult]
    assert unresolved == [], f"{len(unresolved)} organ/blood-type combos take the default 1.0"


@pytest.mark.parametrize("organ", ORGANS)
def test_the_blood_type_multiplier_moves_the_median(organ, data):
    """Coverage without sensitivity is the L-084 shape. Expect FOUR distinct
    medians across eight blood types, not eight: model_key collapses Rh by
    design (#413/L-088), so O+ and O- are meant to agree."""
    import services.distributions as dist
    medians = {bt: dist.get_wait_time_params(organ, bt)[1] for bt in BLOOD_TYPES}
    assert len(set(medians.values())) == 4, (
        f"{organ}: {len(set(medians.values()))} distinct medians across 8 blood "
        f"types — expected 4 ABO groups after the Rh collapse"
    )
    for bt in ("O", "A", "B", "AB"):
        assert medians[f"{bt}+"] == medians[f"{bt}-"], f"{organ}: {bt} Rh split"


def test_every_organ_resolves_in_the_competing_risks_table(data):
    import services.competing_risks as cr
    cr.get_organ_risks("kidney")                   # force lazy init
    missing = [o for o in ORGANS if not cr._RISKS.get(o)]
    assert missing == [], f"{missing} fall back to an empty risk dict"

    rates = {o: cr.get_annual_mortality_rate(o) for o in ORGANS}
    assert len(set(rates.values())) == len(ORGANS), (
        f"only {len(set(rates.values()))} distinct mortality rates across "
        f"{len(ORGANS)} organs — the table may not be discriminating"
    )


def test_the_bbn_center_fallbacks_are_the_disclosed_ones(data):
    """Cross-check between engines. bbn_parameterizer defaults a missing center
    factor to 1.0; those centers must be exactly the ones the provenance tags
    already mark, or the BBN path is substituting without disclosure."""
    from services import provenance as pv

    wt = data.center_wait_times.get("center_wait_time_factors", {})
    ca = data.center_competing_risks.get("center_adjustments", {})
    centers = data.all_centers.get("centers", {})

    for organ in ORGANS:
        listed = [c for c, v in centers.items() if organ in (v.get("organs") or [])]
        wait_default = {c for c in listed if organ not in wt.get(c, {})}
        risk_default = {c for c in listed
                        if "mortality_factor" not in ca.get(c, {}).get(organ, {})}
        # The tag detectors are the disclosure; they must agree with the
        # defaults the engine actually takes.
        tagged_wait = {c for c in listed if pv._check_wait(data, organ, c)}
        tagged_risk = {c for c in listed if pv._check_risk(data, organ, c)}
        assert wait_default <= tagged_wait, (
            f"{organ}: {len(wait_default - tagged_wait)} centers take the BBN "
            f"wait-factor default undisclosed"
        )
        assert risk_default <= tagged_risk, (
            f"{organ}: {len(risk_default - tagged_risk)} centers take the BBN "
            f"mortality-factor default undisclosed"
        )
