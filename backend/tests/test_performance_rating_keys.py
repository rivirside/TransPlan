"""The scorer has never penalised a center SRTR flagged as underperforming.

`_hospital_quality` scores SRTR's performance rating through a lookup table
whose poor-performance key is `lower_than_expected`. The parser
(`scripts/parse-srtr-reports.py:467`) emits `worse_than_expected`. Nothing
produces `lower_than_expected`, in `data/` or anywhere else.

So every center SRTR classified as statistically worse than expected
(ci_lo > 1.0) falls through `rating_scores.get(rating, 70)` to the default 70
— above the 55 the table plainly intends, equal to "insufficient data", and
only 10 below "as expected". 22 center-organ records are affected.

It is the dead-code-reads-as-coverage shape again, and a bad instance of it:
`scoring_explain.py` shows users a table row labelled "Underperforms
benchmark" for a key that can never match, so the UI documents a penalty the
model does not apply. One lung center classified worse-than-expected ranked
**#3** for its organ.

The durable half of this file is not the key spelling but
`test_every_emitted_rating_is_scored`: the parser and the scorer must agree
about the vocabulary, checked against the parser's source rather than a
hand-copied list.
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import scoring  # noqa: E402
from services import scoring_explain  # noqa: E402
from services.data_loader import load_all, get_data  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PARSER = REPO / "scripts" / "parse-srtr-reports.py"


def _ratings_the_parser_emits():
    """Read them out of the classifier rather than hand-copying a list, so a
    new SRTR category cannot be added on one side only."""
    src = PARSER.read_text(encoding="utf-8")
    start = src.index("def _performance_rating(")
    # Stop at the next top-level def, so the window is the whole classifier
    # and nothing after it. An earlier version of this helper started at one
    # of the return statements and silently missed the two above it, which
    # made the fixed code look broken.
    rest = src[start:]
    end = rest.index("\ndef ", 1)
    return set(re.findall(r'return "([a-z_]+)"', rest[:end]))


def _score_table():
    src = (REPO / "backend" / "services" / "scoring.py").read_text(encoding="utf-8")
    block = src[src.index("rating_scores = {"):]
    block = block[:block.index("}")]
    return dict(re.findall(r'"([a-z_]+)":\s*(\d+)', block))


def test_every_emitted_rating_is_scored():
    """The invariant. A rating the parser can emit but the scorer does not
    know silently becomes the default, which is indistinguishable from a
    deliberate score."""
    emitted = _ratings_the_parser_emits()
    scored = set(_score_table())
    assert emitted, "could not read the parser's rating vocabulary"
    missing = emitted - scored
    assert not missing, (
        f"parse-srtr-reports.py emits {sorted(missing)} but scoring.py has no "
        f"entry, so those centers silently take the default"
    )


def test_no_dead_keys_in_the_score_table():
    """The other direction. A key nothing emits looks like a policy the model
    applies and is never reached."""
    emitted = _ratings_the_parser_emits()
    dead = set(_score_table()) - emitted
    assert not dead, (
        f"scoring.py scores {sorted(dead)}, which the parser never emits — "
        "a penalty that reads as applied but cannot fire"
    )


def test_underperformance_actually_costs_a_center():
    """Behavioural, not spelling: whatever the key is called, a center SRTR
    flagged as worse than expected must score below one rated as expected."""
    table = {k: int(v) for k, v in _score_table().items()}
    assert table["worse_than_expected"] < table["as_expected"], (
        "SRTR-flagged underperformance does not lower the score"
    )
    assert table["worse_than_expected"] < table.get("insufficient_data", 70), (
        "a center measured and found wanting scores no worse than one that "
        "was never measured"
    )


def test_a_missing_record_is_not_claimed_as_as_expected():
    """A center with no published outcomes has not been rated 'as expected' —
    SRTR has not rated it at all, and uses `insufficient_data` for exactly
    this (154 records carry it)."""
    src = (REPO / "backend" / "services" / "scoring.py").read_text(encoding="utf-8")
    assert 'outcomes.get("performance_rating", "as_expected")' not in src, (
        "a center with no SRTR outcomes record is scored as though SRTR rated "
        "it 'as expected'"
    )


def test_the_explain_table_matches_the_scorer():
    """scoring_explain renders this table to users. If it drifts from the
    scorer, the explanation is of a model that is not running."""
    explain_src = (REPO / "backend" / "services" / "scoring_explain.py").read_text(
        encoding="utf-8")
    for rating in _ratings_the_parser_emits():
        assert rating in explain_src, (
            f"scoring_explain.py never mentions '{rating}', so its shown "
            "breakdown cannot describe those centers"
        )
    emitted = _ratings_the_parser_emits()
    dead = set(re.findall(r'"(better_than_expected|as_expected|lower_than_expected|'
                          r'worse_than_expected|insufficient_data)"', explain_src))
    assert not (dead - emitted), (
        f"scoring_explain.py references {sorted(dead - emitted)}, which nothing emits"
    )


def test_the_affected_centers_are_real():
    """Guard the premise. If no center is ever flagged, both the bug and the
    fix are theoretical and this suite is pinning nothing."""
    load_all()
    co = get_data().center_outcomes.get("center_outcomes", {})
    flagged = [(code, organ)
               for code, organs in co.items()
               for organ, rec in organs.items()
               if rec.get("performance_rating") == "worse_than_expected"]
    assert len(flagged) >= 10, (
        f"only {len(flagged)} centers flagged worse_than_expected; re-check "
        "whether the parser's classifier still produces this category"
    )
