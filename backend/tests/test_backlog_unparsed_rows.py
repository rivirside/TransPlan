"""The backlog drift checker's own format guard was never called.

`scripts/check-backlog.py` defines `unparsed_rows()` with a docstring that
states the hazard precisely:

    Counting successful parses is not enough: a format change affecting only a
    few rows leaves the total high while silently dropping exactly the rows it
    broke — and those could be the stale ones.

It is then never invoked. `main()` calls `parse_rows()` and checks only that
the result is non-empty, which is the very "silently pass forever" failure the
helper exists to prevent — for a subset of rows rather than all of them.

Found 2026-08-28 by negative-testing something else: adding a new table with a
`DG` prefix should have made the checker complain until the prefix was
exempted, and it did not. The exemption turned out to be genuinely needed —
without it the helper reports all 9 new rows — so the guard was correct, just
unreachable.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "check-backlog.py"


@pytest.fixture(scope="module")
def cb():
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location("check_backlog", SCRIPT)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        sys.path.remove(str(REPO / "scripts"))


def test_unparsed_rows_is_actually_called(cb):
    """A helper defined and never invoked provides nothing while reading, in a
    review, as though the hazard is handled."""
    src = SCRIPT.read_text(encoding="utf-8")
    body = src[src.index("def main("):]
    # Strip comments first. The comment explaining why the call is there
    # contains the function's name, so a plain substring search passes on the
    # explanation alone — which it did, until a negative test caught it.
    code = "\n".join(
        line.split("#", 1)[0] for line in body.splitlines()
    )
    assert "unparsed_rows(" in code, (
        "check-backlog.py defines unparsed_rows() but main() never calls it — "
        "a format change that breaks only some rows still passes"
    )


def test_the_doc_currently_parses_cleanly(cb):
    bad = cb.unparsed_rows(cb.BACKLOG.read_text(encoding="utf-8"))
    assert bad == [], f"{len(bad)} backlog rows do not parse: {bad[:3]}"


def test_the_detector_can_actually_fail(cb):
    """Pin sensitivity alongside the clean result above. A checker reporting
    zero is only reassuring if zero is a finding rather than a constant."""
    broken = (
        "| A1 | real row | #1 | done |\n"
        "| ZZ9 | a row whose prefix the parser does not know | #2 | |\n"
    )
    bad = cb.unparsed_rows(broken)
    assert len(bad) == 1
    assert "ZZ9" in bad[0]


def test_exempt_prefixes_are_narrow(cb):
    """The exemption list is how this check would get neutralised: exempt
    enough prefixes and every row is 'deliberately not issue-tracked'."""
    assert len(cb.EXEMPT_PREFIXES) <= 3, (
        f"EXEMPT_PREFIXES has grown to {cb.EXEMPT_PREFIXES} — each entry is a "
        "table the drift check no longer sees"
    )


def test_a_broken_row_fails_the_check_end_to_end(cb, tmp_path, monkeypatch):
    """The whole point: --check must exit non-zero, not merely print."""
    doc = cb.BACKLOG.read_text(encoding="utf-8")
    broken = doc + "\n| QQ1 | a row in no recognised format | #999 | |\n"
    target = tmp_path / "backlog.md"
    target.write_text(broken, encoding="utf-8")
    monkeypatch.setattr(cb, "BACKLOG", target)
    monkeypatch.setattr(sys, "argv", ["check-backlog.py", "--check"])

    assert cb.main() == 1, "a malformed row must make --check fail"
