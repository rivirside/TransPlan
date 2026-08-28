"""#233: the BBN's graft-family constants cannot affect any output.

Register rows BBN-02 (`_GRAFT_POOR_MARGIN` 3.0pp), BBN-12 (GraftSurvival
_GOOD/_MODERATE triples), BBN-14 (graft default 90.0) and BBN-15
(CompoundSuccess CPT) are all carried as uncited and awaiting justification.
Measured 2026-08-28: **forcing each to an extreme leaves the /simulate
response byte-identical.**

The mechanism is structural, not a weak effect. `_query_city` returns four
marginals; `simulate_bbn` reads exactly two of them — `competing_outcome`
and `wait_category`. `graft_survival` and `compound_success` are computed on
every inference and discarded. The user-facing compound-success figure comes
from `services/outcomes.py`, which reads the post-transplant outcomes file
directly and never consults the network.

So citing these four would be ceremony: a source for a number that cannot
reach a reader. Removing them is not justified either — they cost 1.4-2.5%
of CPT build time — and doing so would foreclose surfacing BBN-native graft
reasoning later.

What this test does is put an alarm on that state. If the nodes are ever
wired to an output, these constants become live, and at that moment they
need the justification the register is holding for them.
"""
import json

import numpy as np
import pytest

from models.schemas import PatientProfile

REACHABLE_MARGINALS = {"competing_outcome", "wait_category"}
DEAD_MARGINALS = {"graft_survival", "compound_success"}


@pytest.fixture
def response(data):
    """A full /simulate-equivalent BBN response, as comparable JSON."""
    from services.bayesian_network import reset_model, simulate_bbn

    def run():
        reset_model()
        patient = PatientProfile(organ="kidney", blood_type="O+", age=50,
                                 sex="male", urgency=2, bbn_granularity="state")
        return json.dumps([c.model_dump() for c in simulate_bbn(patient).cities],
                          sort_keys=True, default=str)

    yield run
    reset_model()


def test_the_poor_margin_cannot_change_the_response(response, monkeypatch):
    """BBN-02. 3.0pp -> 50.0pp flags every center 'poor'."""
    import services.bbn_parameterizer as bp
    base = response()
    monkeypatch.setattr(bp, "_GRAFT_POOR_MARGIN", 50.0)
    assert response() == base, (
        "_GRAFT_POOR_MARGIN now reaches the response — BBN-02 has become "
        "load-bearing and needs the justification the register is holding"
    )


def test_the_graft_survival_cpt_cannot_change_the_response(response, monkeypatch):
    """BBN-12 / BBN-14. Force every center to the 'poor' state."""
    import services.bbn_parameterizer as bp
    base = response()
    real = bp.build_graft_survival_cpt

    def all_poor(*args, **kwargs):
        cpt = np.zeros_like(real(*args, **kwargs))
        cpt[2] = 1.0
        return cpt

    monkeypatch.setattr(bp, "build_graft_survival_cpt", all_poor)
    assert response() == base, (
        "GraftSurvival now reaches the response — BBN-12 and BBN-14 have "
        "become load-bearing"
    )


def test_the_compound_success_cpt_cannot_change_the_response(response, monkeypatch):
    """BBN-15. Collapse it to always-success."""
    import services.bbn_parameterizer as bp
    base = response()
    degenerate = np.zeros((3, 4, 3))
    degenerate[0] = 1.0
    monkeypatch.setattr(bp, "build_compound_success_cpt", lambda: degenerate)
    assert response() == base, (
        "CompoundSuccess now reaches the response — BBN-15 has become "
        "load-bearing"
    )


def test_the_response_is_not_simply_frozen(response, monkeypatch):
    """Guard the guard.

    Every assertion above is 'perturbing X changes nothing', which would also
    hold if the response were constant, the fixture broken, or monkeypatch
    silently not applying. Perturb something known to be LIVE and require the
    response to move.
    """
    import services.bbn_parameterizer as bp
    base = response()
    real = bp.build_competing_outcome_cpt

    def shifted(*args, **kwargs):
        cpt = real(*args, **kwargs).copy()
        cpt[0] *= 0.5                       # halve the transplant mass
        return cpt / cpt.sum(axis=0, keepdims=True)

    monkeypatch.setattr(bp, "build_competing_outcome_cpt", shifted)
    assert response() != base, (
        "perturbing CompetingOutcome — a node known to drive p24 — left the "
        "response unchanged, so the unreachability tests above prove nothing"
    )


def test_simulate_reads_only_the_two_live_marginals():
    """The structural reason, checked against the source rather than inferred.

    If a future edit reads `graft_survival` in simulate_bbn, the byte-compare
    tests would catch it only if it changed an output. This catches the read
    itself, which is the earlier and clearer signal.
    """
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "services"
           / "bayesian_network.py").read_text(encoding="utf-8")

    # Whole module, not just simulate_bbn: the live marginals are consumed in
    # _combine_outcomes and _estimate_median_wait, which are defined earlier.
    # Scoping to simulate_bbn's own body was the first version of this and it
    # reported competing_outcome as unread.
    #
    # `query_result[...]` is the READ form; `results[...] =` inside
    # _query_city is the write that populates it. Only reads matter here.
    for key in DEAD_MARGINALS:
        assert f'query_result["{key}"]' not in src, (
            f"the production BBN path now reads {key}; the register rows "
            "behind it (BBN-02/-12/-14/-15) are no longer inert and need the "
            "justification the register is holding for them"
        )
    for key in REACHABLE_MARGINALS:
        assert f'query_result["{key}"]' in src, (
            f"{key} is no longer read — the model's shape changed and this "
            "test's premise needs rechecking"
        )
