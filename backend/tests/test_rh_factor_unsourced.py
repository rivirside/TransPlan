"""L-088 / #180: the Rh half of the blood-type tables is hand-set, not derived.

US solid-organ allocation is ABO-matched; RhD is not part of OPTN matching for
any of the six organs. The model nevertheless penalizes Rh-negative candidates
in two places, through two conventions that disagree with each other.

These tests pin the *evidence* for that claim rather than the claim itself, so
the conclusion can be reopened by data instead of inherited on authority. If
someone later derives Rh multipliers from a real source, the structural
signature will change and these fail — which is the point: they should be
re-examined then, not silently satisfied.

**#413 landed the fix at the lookup, not in the tables.** The eight-entry
tables are still on disk — they are the record of what was there, and the
revert is one line if Rh-stratified evidence appears — so the structural
tests below still describe the files. What changed is that nothing reads the
Rh half any more, which `test_rh_is_inert.py` covers.

Full measurement: docs/rh-factor-report.md
"""
import json
import re
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "data"
GROUPS = ("O", "A", "B", "AB")
ORGANS = ("kidney", "liver", "heart", "lung", "pancreas", "intestine")


@pytest.fixture(scope="module")
def multipliers():
    raw = json.loads((DATA / "wait-time-distributions.json").read_text())
    return {o: raw[o]["blood_type_multipliers"] for o in ORGANS}


def test_the_rh_adjustment_is_a_flat_per_organ_constant(multipliers):
    """22 of 24 cells are one of two round numbers.

    A quantity estimated from data does not do that. This is the core of the
    L-088 argument, so it is checked rather than asserted in prose.
    """
    round_cells = 0
    for organ, bt in multipliers.items():
        for g in GROUPS:
            offset = round(bt[f"{g}-"] - bt[f"{g}+"], 3)
            if offset in (0.05, 0.10):
                round_cells += 1
    assert round_cells >= 22, (
        f"only {round_cells}/24 Rh offsets are 0.05 or 0.10 — the tables no "
        "longer look hand-set, so L-088's argument needs re-examining"
    )


def test_the_rh_adjustment_always_penalizes(multipliers):
    """Directional, not noise. Every Rh-negative entry is a LONGER wait."""
    for organ, bt in multipliers.items():
        for g in GROUPS:
            assert bt[f"{g}-"] > bt[f"{g}+"], (
                f"{organ} {g}: Rh-negative is no longer penalized — if this is "
                "a deliberate fix, close L-088 and delete this test"
            )


def test_srtr_does_not_stratify_blood_type_by_rh():
    """The reason no calibration gate can adjudicate this.

    The observed waitlist composition is the project's only blood-type ground
    truth. It ships EIGHT keys, which looks like Rh data and is not: DATA-46
    splits each ABO group 84/16 by the US Rh share because the source has four
    columns. So the check has to read the SOURCE, not the derived file — the
    derived file is exactly what would fool a casual reviewer here.

    If SRTR ever publishes Rh-stratified counts, the Rh multipliers become
    testable and L-088 turns from a mechanism argument into a measurement.
    """
    src = (Path(__file__).resolve().parents[2]
           / "scripts" / "parse-waitlist-composition.py").read_text()
    start = src.index("ABO_COLS = {")
    cols = set(re.findall(r'"(TPC_B[A-Z]+_N[A-Z])"', src[start:src.index("}", start)]))
    assert len(cols) == 4, f"expected 4 ABO source columns, found {sorted(cols)}"
    assert not any(re.search(r"_B[A-Z]*(POS|NEG|RH)", c) for c in cols), (
        f"an Rh-stratified SRTR column appeared ({sorted(cols)}) — the L-088 "
        "multipliers may now be testable against data"
    )

    # And the derived file must keep saying so, or the 8 keys become a claim.
    meta = json.loads((DATA / "waitlist-composition.json").read_text())["_meta"]
    assert "without Rh" in meta.get("rh_assumption", ""), (
        "waitlist-composition.json stopped disclosing that its 8 blood-type "
        "keys are an assumed split of 4 observed ABO groups"
    )


def test_the_two_rh_conventions_disagree():
    """The wait table and the score table encode different Rh penalties.

    Two independent hand-set conventions for one claimed phenomenon is
    stronger evidence of hand-setting than either alone, so it is pinned.

    Reads the score table directly rather than calling the scorer: since #413
    the scorer no longer consults the Rh rows, so going through it would
    measure the fix instead of the evidence for it.
    """
    src = (Path(__file__).resolve().parents[1]
           / "services" / "scoring.py").read_text()
    start = src.index("bt_scores = {")
    body = src[start:src.index("}", start)]
    table = {m.group(1): int(m.group(2))
             for m in re.finditer(r'"(\w+[+-])":\s*(\d+)', body)}
    assert len(table) == 8, f"expected 8 score-table entries, got {table}"
    gaps = {g: table[f"{g}+"] - table[f"{g}-"] for g in GROUPS}
    # Assert the SPREAD, not merely "more than one distinct value". A first
    # version of this checked distinctness and passed against gaps of
    # 8/7/8/8 — technically non-uniform, but no longer evidence of anything.
    # The claim is that O is penalized twice as hard as A for no stated
    # reason: raw gaps 15 (O) vs 7 (A), scaled by the 40% sub-weight.
    spread = max(gaps.values()) - min(gaps.values())
    assert spread >= 6, (
        f"the scoring Rh gaps have converged (spread {spread}, {gaps}) — they "
        "ran 7 (A) to 15 (O). Two conventions that now agree is weaker "
        "evidence of hand-setting; re-check L-088"
    )
