"""Every national substitute a patient sees is marked, and nothing else is.

L-087: centers without published SRTR data are still ranked, using national
averages. #411/B8 added a per-row dagger so a reader can see which rows those
are. This checks the dagger against the DATA rather than against the engine's
own tags — otherwise the assertion is circular, since `row_level_degraded` is
computed from those same tags.

Two directions, both of which matter to a patient:

  - a center using a national substitute WITHOUT a marker reads as
    center-specific when it is not;
  - a marker on a center that does have its data undermines the marker
    everywhere, because a reader who checks one and finds it wrong stops
    trusting the rest.

Verified 2026-08-28 across all six organs and three row-level tags: 0 and 0.

Getting there took three wrong expectations, which is the reason this file
states its sources explicitly. `TAG_OUTCOMES` is driven by
`srtr-observed-rates.json`, NOT the similarly-named
`post-transplant-outcomes-centers.json`; and the acceptance tag is absent
because acceptance modelling is off in the default path, not because it is
missing. An "expected" set built from the wrong file makes the machinery look
broken when it is not.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import provenance as pv  # noqa: E402
from services.data_loader import load_all  # noqa: E402
from services.monte_carlo import simulate  # noqa: E402
from models.schemas import PatientProfile  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]


def _load(name, container):
    return json.loads((REPO / "data" / name).read_text(encoding="utf-8"))[container]


@pytest.fixture(scope="module")
def sources():
    load_all()
    wait = _load("wait-time-distributions-centers.json", "center_wait_time_factors")
    comp = _load("competing-risks-centers.json", "center_adjustments")
    obs = json.loads(
        (REPO / "data" / "srtr-observed-rates.json").read_text(encoding="utf-8"))
    # #447/L-099: the fourth source. Absent from this map until 2026-08-28,
    # which is why the file below could report "0 undisclosed" while 91
    # center-organ pairs were scored on a zero with no marker. A disclosure
    # test is only as complete as its list of sources, so each entry names
    # the file it reads.
    pt = _load("post-transplant-outcomes-centers.json", "center_outcomes")
    return {
        # wait-time-distributions-centers.json
        pv.TAG_WAIT: lambda o, c: o in wait.get(c, {}),
        # competing-risks-centers.json
        pv.TAG_RISK: lambda o, c: o in comp.get(c, {}),
        # srtr-observed-rates.json  (NOT post-transplant-outcomes-centers.json)
        pv.TAG_OUTCOMES: lambda o, c: c in obs.get(o, {}).get("centers", {}),
        # post-transplant-outcomes-centers.json — drives 40% of hospital
        # quality via n_1yr, defaulting to 0 when the record is absent.
        pv.TAG_PT_OUTCOMES: lambda o, c: bool(pt.get(c, {}).get(o)),
    }


@pytest.fixture(scope="module")
def runs():
    load_all()
    out = {}
    for organ in ORGANS:
        patient = PatientProfile(organ=organ, blood_type="O+", age=45,
                                 sex="male", urgency=2)
        out[organ] = simulate(patient, n_iterations=200, seed=42)
    return out


@pytest.mark.parametrize("organ", ORGANS)
def test_no_undisclosed_national_substitute(organ, runs, sources):
    """The direction that misleads: a substitute presented as center data."""
    result = runs[organ]
    for tag, present in sources.items():
        missing = {c.center_code for c in result.cities
                   if not present(organ, c.center_code)}
        tagged = {c.center_code for c in result.cities
                  if tag in (c.data_quality or [])}
        undisclosed = sorted(missing - tagged)
        assert not undisclosed, (
            f"{organ}: {len(undisclosed)} centers use the national {tag} "
            f"substitute with no marker: {undisclosed[:6]}"
        )


@pytest.mark.parametrize("organ", ORGANS)
def test_no_spurious_markers(organ, runs, sources):
    """The direction that erodes trust in the markers that are right."""
    result = runs[organ]
    for tag, present in sources.items():
        missing = {c.center_code for c in result.cities
                   if not present(organ, c.center_code)}
        tagged = {c.center_code for c in result.cities
                  if tag in (c.data_quality or [])}
        spurious = sorted(tagged - missing)
        assert not spurious, (
            f"{organ}: {len(spurious)} centers marked as using a national "
            f"{tag} substitute but have their own data: {spurious[:6]}"
        )


def test_the_check_can_actually_fail(runs, sources):
    """A 0-and-0 result across 18 combinations is only reassuring if a real
    gap would show. Inject one."""
    result = runs["kidney"]
    codes = {c.center_code for c in result.cities}
    tagged = {c.center_code for c in result.cities
              if pv.TAG_RISK in (c.data_quality or [])}
    untagged = sorted(codes - tagged)
    assert untagged, "every kidney center is tagged; the probe below is void"

    # Pretend a center with full data is missing its competing-risks block.
    victim = untagged[0]
    present = lambda o, c: False if c == victim else sources[pv.TAG_RISK](o, c)
    missing = {c.center_code for c in result.cities
               if not present("kidney", c.center_code)}
    assert victim in (missing - tagged), (
        "the comparison cannot detect an undisclosed substitute"
    )


def test_markers_are_actually_present_somewhere(runs):
    """Pin sensitivity next to the invariance. If the engine stopped emitting
    row-level tags entirely, both assertions above would pass vacuously --
    missing minus empty is empty only when nothing is missing, but a reader
    scanning green tests would not know which."""
    total = 0
    for organ in ORGANS:
        for c in runs[organ].cities:
            total += sum(1 for t in (c.data_quality or [])
                         if t in pv.ROW_LEVEL_TAGS)
    assert total >= 50, (
        f"only {total} row-level tags emitted across all six organs — the "
        "engine may have stopped tagging, which would make the disclosure "
        "checks pass while disclosing nothing"
    )
