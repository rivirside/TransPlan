#!/usr/bin/env python3
"""Keep docs/backlog-2026-08.md honest about what is actually done.

The backlog doc is the tracker used to decide what to work on next. Nothing
recomputed it against GitHub, so it drifted twice:

  * 2026-08-26 — the whole `backlog-2026-08` branch had been merged and closed
    while the doc still described the work as in flight.
  * 2026-08-27 — twelve rows sat without a completion mark although their
    issues were closed, several of them by the Aug 26 measurement wave
    (#213, #238, #274, #294, #297, #298 ...).

A stale tracker is the documentation form of the guard lesson in CLAUDE.md: it
*reads* as coverage. Someone scanning for "what is left" sees closed work and
either redoes it or, worse, treats the remaining list as complete.

Design mirrors scripts/check-register.py, with one addition: the GitHub state
is snapshotted to a JSON file so `--check` (and the pytest that wraps it) runs
offline and deterministically. Refreshing the snapshot is a deliberate act;
drift between the doc and the snapshot is caught automatically.

    python scripts/check-backlog.py --refresh   # query gh, rewrite snapshot
    python scripts/check-backlog.py --check     # verify doc vs snapshot (CI)
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKLOG = REPO / "docs" / "backlog-2026-08.md"
SNAPSHOT = REPO / "docs" / "backlog-issue-state.json"

DONE_MARK = "✅"
# Rows whose "issue" cell names no issue number — inline work, parked items,
# or pointers to another row. Nothing to cross-check for these.
NO_ISSUE = re.compile(r"^\s*(\(inline\)|parked|see\s|—|-)?\s*$", re.I)


# Phase K is a different table — a 3-column record of code-review findings
# (`| # | Finding | Fix commit |`) with no issue links and no status column,
# so it has nothing to cross-check. It is exempted BY NAME rather than left to
# fall through the row regex, because a silent skip is exactly the failure this
# module exists to prevent: the first version of the guard below quietly
# ignored all 10 of these rows and reported success.
EXEMPT_PREFIXES = ("K", "DG")


def unparsed_rows(text: str) -> list[str]:
    """Lines that look like backlog rows but the parser did not understand.

    Counting successful parses is not enough: a format change affecting only a
    few rows leaves the total high while silently dropping exactly the rows it
    broke — and those could be the stale ones. So every line that looks like a
    data row must actually parse.
    """
    bad = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|") or s.count("|") < 4:
            continue
        if re.match(r"^\|\s*(#|-+|:?-+:?)\s*\|", s) or "|---" in s:
            continue          # header separator
        if re.match(r"^\|\s*(Item|Phase|Status|Finding)\b", s, re.I):
            continue          # header row
        if re.match(rf"^\|\s*(?:{'|'.join(EXEMPT_PREFIXES)})\d+\s*\|", s):
            continue          # deliberately not an issue-tracked table
        if not re.match(r"^\|\s*[A-J]\d+\s*\|", s):
            bad.append(s[:90])
    return bad


def parse_rows(text: str) -> list[dict]:
    """Table rows keyed by their A1/B2/... identifier."""
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*([A-J]\d+)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", line)
        if not m:
            continue
        rid, item, issue_cell, status = m.groups()
        rows.append({
            "id": rid,
            "item": item,
            "issue_cell": issue_cell,
            "issues": [int(n) for n in re.findall(r"#(\d+)", issue_cell)],
            "status": status,
            "done": DONE_MARK in status,
        })
    return rows


def fetch_states(numbers: list[int]) -> dict[str, str]:
    states = {}
    for n in sorted(set(numbers)):
        r = subprocess.run(
            ["gh", "issue", "view", str(n), "--json", "state", "-q", ".state"],
            capture_output=True, text=True,
        )
        states[str(n)] = r.stdout.strip() if r.returncode == 0 else "UNKNOWN"
    return states


def load_snapshot() -> dict[str, str]:
    if not SNAPSHOT.exists():
        return {}
    return json.loads(SNAPSHOT.read_text()).get("issues", {})


# A backlog row can legitimately be finished while its issue stays open,
# because several rows carve one item out of a broader issue. That is fine —
# what is not fine is leaving a reader to guess. So a done row pointing at an
# open issue must SAY that the issue covers more.
#
# (The first version of this check flagged all six such rows as errors. Acting
# on that would have removed accurate completion marks to satisfy a wrong
# rule, which is worse than the drift it was written to catch.)
_REMAINDER_WORDS = re.compile(
    r"residue|remainder|remaining|still open|stays open|partial|legacy|"
    r"tracked (on|in)|rest of|follow-?up", re.I)


def _acknowledges_remainder(status: str) -> bool:
    return bool(_REMAINDER_WORDS.search(status))


def check(rows: list[dict], states: dict[str, str]) -> list[str]:
    problems = []
    for row in rows:
        if not row["issues"]:
            continue
        known = [states.get(str(n)) for n in row["issues"]]
        if any(s is None or s == "UNKNOWN" for s in known):
            continue  # not in the snapshot; --refresh will pick it up
        all_closed = all(s == "CLOSED" for s in known)
        any_open = any(s == "OPEN" for s in known)

        if all_closed and not row["done"]:
            problems.append(
                f"{row['id']}: every issue is CLOSED ({row['issue_cell']}) but the "
                f"row is not marked {DONE_MARK} — status is {row['status']!r}. "
                "Someone reading this will redo finished work.")
        if any_open and row["done"] and not _acknowledges_remainder(row["status"]):
            open_ns = [n for n, s in zip(row["issues"], known) if s == "OPEN"]
            problems.append(
                f"{row['id']}: marked {DONE_MARK} but "
                f"{', '.join('#'+str(n) for n in open_ns)} is still OPEN, and the "
                f"status does not say why — status is {row['status']!r}. Either "
                "the row overstates what landed, or the issue covers a broader "
                f"remainder; say which (e.g. \"{DONE_MARK} ... (#N stays open for "
                "<remainder>)\").")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the doc against the snapshot; no network")
    ap.add_argument("--refresh", action="store_true",
                    help="query GitHub and rewrite the snapshot")
    args = ap.parse_args()

    if not BACKLOG.exists():
        print(f"missing {BACKLOG.relative_to(REPO)}", file=sys.stderr)
        return 1

    text = BACKLOG.read_text()
    rows = parse_rows(text)
    if not rows:
        print("parsed 0 backlog rows — the table format changed and this "
              "check would silently pass forever", file=sys.stderr)
        return 1

    # The non-empty check above only catches a TOTAL format break. A change
    # affecting some rows leaves the count high while dropping exactly the
    # rows it broke, which could be the stale ones. unparsed_rows() was
    # written for that and then never called.
    unparsed = unparsed_rows(text)
    if unparsed:
        print(f"{len(unparsed)} backlog rows did not parse — they are invisible "
              f"to the staleness check below:", file=sys.stderr)
        for line in unparsed[:10]:
            print(f"  - {line}", file=sys.stderr)
        if len(unparsed) > 10:
            print(f"  ... and {len(unparsed) - 10} more", file=sys.stderr)
        print("  Rows must be '| <Letter><digits> | item | issue | status |'. "
              "A table that is deliberately not issue-tracked needs its prefix "
              "in EXEMPT_PREFIXES.", file=sys.stderr)
        return 1

    if args.refresh:
        numbers = [n for r in rows for n in r["issues"]]
        states = fetch_states(numbers)
        SNAPSHOT.write_text(json.dumps(
            {"issues": states,
             "_meta": {"script": "scripts/check-backlog.py",
                       "note": "refresh with --refresh; --check reads this offline"}},
            indent=2, sort_keys=True) + "\n")
        print(f"snapshot refreshed: {len(states)} issues -> "
              f"{SNAPSHOT.relative_to(REPO)}")

    states = load_snapshot()
    problems = check(rows, states)

    if args.check:
        if problems:
            print(f"backlog doc is stale ({len(problems)} rows):", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 1
        tracked = sum(1 for r in rows if r["issues"])
        done = sum(1 for r in rows if r["done"])
        print(f"backlog current: {len(rows)} rows, {tracked} issue-linked, "
              f"{done} marked done, {len(rows) - done} outstanding")
        return 0

    for p in problems:
        print(f"  - {p}")
    if not args.refresh and not problems:
        print("backlog agrees with the snapshot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
