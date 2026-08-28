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
