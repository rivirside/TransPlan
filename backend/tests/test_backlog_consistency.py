"""The backlog doc must agree with the issues it references.

docs/backlog-2026-08.md is the tracker used to decide what to work on next,
and nothing recomputed it, so it drifted twice: once when its whole branch was
merged while the doc still described the work as in flight, and again when
twelve rows sat unmarked although their issues were closed — several closed by
the Aug 26 measurement wave.

That is the guard lesson from CLAUDE.md in documentation form: a stale tracker
READS as coverage. Someone scanning for what is left sees finished work and
either redoes it or trusts a remaining list that is wrong.

The check runs against a committed snapshot of issue states rather than the
network, so it is deterministic and offline; refreshing the snapshot
(`scripts/check-backlog.py --refresh`) is a deliberate act.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "check-backlog.py"
SNAPSHOT = REPO / "docs" / "backlog-issue-state.json"
BACKLOG = REPO / "docs" / "backlog-2026-08.md"


def test_backlog_agrees_with_issue_snapshot():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"backlog doc is stale:\n{result.stderr or result.stdout}")


def test_parser_still_sees_the_table():
    """Guard the guard.

    If the table format changes and the row regex stops matching, every
    assertion above passes vacuously — the same failure mode that made the
    first version of the vercel-rewrite test useless.

    Negative-tested. What this catches: a malformed or renamed row id, a new
    row whose id does not parse, and wholesale format change (via the count
    floors). Writing it also surfaced a real gap — Phase K's 10 rows were
    silently invisible to the checker until they were exempted by name.

    What it does NOT catch, stated rather than implied: a row rewritten into
    something that no longer looks like a table row at all, which is
    indistinguishable from deliberate deletion. The count floors bound how
    much of that can happen unnoticed.
    """
    sys.path.insert(0, str(REPO / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_backlog", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    text = BACKLOG.read_text()
    rows = mod.parse_rows(text)
    assert len(rows) > 50, f"parsed only {len(rows)} backlog rows"
    assert sum(1 for r in rows if r["issues"]) > 40, "no issue links parsed"
    assert sum(1 for r in rows if r["done"]) > 20, "no completion marks parsed"

    # Counting parses is not enough: a format change hitting only a few rows
    # keeps the total high while dropping exactly the rows it broke.
    unparsed = mod.unparsed_rows(text)
    assert not unparsed, (
        f"{len(unparsed)} lines look like backlog rows but did not parse, so "
        f"they are silently exempt from every check above: {unparsed[:3]}")


def test_snapshot_covers_every_referenced_issue():
    """An issue missing from the snapshot is skipped, so silence != agreement."""
    sys.path.insert(0, str(REPO / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_backlog", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rows = mod.parse_rows(BACKLOG.read_text())
    referenced = {str(n) for r in rows for n in r["issues"]}
    known = set(json.loads(SNAPSHOT.read_text())["issues"])
    missing = sorted(referenced - known, key=int)
    assert not missing, (
        f"issues referenced by the backlog but absent from the snapshot: "
        f"{missing} — run scripts/check-backlog.py --refresh")


def test_snapshot_has_no_unknown_states():
    states = json.loads(SNAPSHOT.read_text())["issues"]
    unknown = sorted(n for n, s in states.items() if s not in {"OPEN", "CLOSED"})
    assert not unknown, f"issues with unresolved state: {unknown}"
