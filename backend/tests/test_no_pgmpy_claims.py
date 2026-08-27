"""User-facing errors must not blame pgmpy — the project does not use it (#258).

`bbn_lite.py` exists specifically to avoid pgmpy, which pulls torch at ~2GB.
The module docstrings say so correctly. But two API responses still told
callers the opposite:

    503  "Bayesian inference unavailable (missing pgmpy dependency)"
         note="pgmpy not installed"

Both sit on `except ImportError` around `from services.bayesian_network import
simulate_bbn`, which imports numpy — so the one dependency the message names
is the one that could never be the cause. An operator debugging a 503 would be
sent to install a 2GB package that cannot fix it, and that the project
deliberately removed.

A wrong diagnostic is worse than none: it is confidently misleading.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"

# Places where naming pgmpy is CORRECT: explaining what the project replaced.
EXPLANATORY = re.compile(
    r"(not pgmpy|does not use pgmpy|replaces pgmpy|instead of pgmpy|"
    r"pgmpy-style|comparable to pgmpy|matches pgmpy|pgmpy requires)", re.I)


def _pgmpy_lines():
    hits = []
    for path in BACKEND.rglob("*.py"):
        if "tests" in path.parts:
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if "pgmpy" in line.lower():
                hits.append((path.relative_to(REPO), i, line.strip()))
    return hits


def test_no_user_facing_string_blames_pgmpy():
    """Any pgmpy mention inside a quoted message must be explanatory."""
    offenders = []
    for path, lineno, line in _pgmpy_lines():
        if EXPLANATORY.search(line):
            continue
        # A mention inside a string literal reaches a caller; a comment does not.
        in_string = re.search(r'''["'][^"']*pgmpy[^"']*["']''', line, re.I)
        if in_string:
            offenders.append(f"{path}:{lineno}: {line[:100]}")
    assert not offenders, (
        "these strings reach API callers and name a dependency the project "
        "does not use, so they would send an operator to install ~2GB of "
        f"torch that cannot fix the problem:\n  " + "\n  ".join(offenders))


def test_the_explanatory_mentions_are_still_there():
    """Guard the guard.

    If every pgmpy reference were deleted, the test above would pass while the
    codebase lost the explanation for WHY bbn_lite exists — which is the part
    worth keeping.
    """
    explanatory = [h for h in _pgmpy_lines() if EXPLANATORY.search(h[2])]
    assert len(explanatory) >= 3, (
        f"only {len(explanatory)} explanatory pgmpy references remain; the "
        "rationale for bbn_lite.py should stay documented")


def test_bayesian_import_failure_is_described_accurately():
    """The 503 should name what could actually fail."""
    src = (BACKEND / "routers" / "simulate.py").read_text()
    m = re.search(r'detail=f?"Bayesian inference unavailable[^"]*"', src)
    assert m, "the bayesian 503 detail string moved — update this test"
    assert "pgmpy" not in m.group(0).lower(), m.group(0)
