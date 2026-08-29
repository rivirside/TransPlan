"""Every register row must point at code that exists.

The register's Location column is what makes a row actionable: it is how
someone goes and justifies the assumption. A row pointing at a deleted file
cannot be acted on, and it is not inert — the counts and the priority
shortlist are computed from status and risk, so a stale row consumes attention
that belongs to a real assumption.

Found 2026-08-28: four rows (DATA-29..32) describe `hospital-quality.json`,
which does not exist. `fetch-hospital-quality.js` was deleted in the 22-city
retirement (CLAUDE.md, K6). DATA-29 was marked high-risk AND uncited, so it
sat on the priority shortlist — for a file nothing can read. Its own note says
"_meta claims CMS API but L-046 shows CMS endpoint 400s", which is the same
dead CMS source the site was still crediting in #459.

Also found: DATA-19 cited post-transplant-outcomes.json:52-64 in a 47-line
file — a range left behind when the 22-city blocks were retired.

Two rows use a `module.symbol` location instead of file:line
(SURV-42 `bayesian_network._CI_INFLATION_LAG1`, SURV-43
`monte_carlo._pediatric_dist`). That is a deliberate alternative for
assumptions that live in a constant rather than a line range, so the check
accepts it rather than forcing a false precision.

A regex note, because it cost a wrong reading first: `\\.(?:py|js|json)`
matches `.js` inside `.json` and truncates the filename, reporting 57
nonexistent files. Longest alternative first.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
REGISTER = REPO / "docs" / "clinical-assumptions-register.md"

# json BEFORE js: alternation is ordered, and `.js` matches inside `.json`.
LOCATION = re.compile(r"([\w./-]+\.(?:json|py|js|md|html|css))(?::(\d+))?")
SEARCH_DIRS = ("", "backend/", "scripts/", "data/", "backend/services/", "docs/")


def _rows():
    text = REGISTER.read_text(encoding="utf-8")
    return re.findall(r"^\|\s*([A-Z]+-\d+)\s*\|\s*([^|]+?)\s*\|", text, re.M)


def _resolve(filename):
    for prefix in SEARCH_DIRS:
        candidate = REPO / (prefix + filename)
        if candidate.exists():
            return candidate
    return None


def test_the_register_parses():
    rows = _rows()
    assert len(rows) >= 200, f"only {len(rows)} register rows parsed"


def test_every_location_points_at_a_file_that_exists():
    missing = []
    for row_id, location in _rows():
        m = LOCATION.match(location.strip().strip("`"))
        if not m:
            continue                      # module.symbol form, checked below
        if _resolve(m.group(1)) is None:
            missing.append((row_id, m.group(1)))
    assert missing == [], (
        f"{len(missing)} register rows point at files that do not exist — they "
        f"cannot be acted on, and any that are high-risk and unjustified sit on "
        f"the priority shortlist regardless: {missing}"
    )


def test_line_numbers_are_within_the_file():
    stale = []
    for row_id, location in _rows():
        m = LOCATION.match(location.strip().strip("`"))
        if not m or not m.group(2):
            continue
        path = _resolve(m.group(1))
        if path is None:
            continue
        n_lines = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        if int(m.group(2)) > n_lines:
            stale.append((row_id, f"{m.group(1)}:{m.group(2)} in a {n_lines}-line file"))
    assert stale == [], f"register rows cite lines past end of file: {stale}"


def test_non_file_locations_are_a_known_small_set():
    """`module.symbol` is a legitimate location for an assumption that lives in
    a constant, but it should stay rare — it is also what a malformed row looks
    like."""
    odd = []
    for row_id, location in _rows():
        loc = location.strip().strip("`")
        if LOCATION.match(loc):
            continue
        odd.append((row_id, loc[:50]))
    assert len(odd) <= 4, (
        f"{len(odd)} rows have no parseable file location: {odd}"
    )
    for row_id, loc in odd:
        assert re.match(r"^[\w]+\.[\w]+", loc), (
            f"{row_id} location is neither file:line nor module.symbol: {loc!r}"
        )


def test_the_shortlist_names_no_deleted_file():
    """The shortlist is where a stale row does real damage: it is the list
    someone works through."""
    text = REGISTER.read_text(encoding="utf-8")
    tail = text[text.index("Priority to justify"):] if "Priority to justify" in text else ""
    assert tail, "the register no longer has a priority shortlist"
    bad = []
    for m in re.finditer(r"\*\*([A-Z]+-\d+)\*\*\s+([\w./-]+\.(?:json|py|js|md))", tail):
        if _resolve(m.group(2)) is None:
            bad.append((m.group(1), m.group(2)))
    assert bad == [], f"priority shortlist points at deleted files: {bad}"
