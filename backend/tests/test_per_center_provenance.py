"""Per-center data-provenance on /score (#227/#228).

The response-level summary has said "6 of 233 centers use national defaults"
since #219. It never said WHICH — so a reader could not tell whether the
degraded center was the one ranked first or the one ranked 200th.

Measured 2026-08-27 on the shipped data: for pancreas that is 10 of the top
10 and for intestine 6 of the top 10, i.e. exactly the organs where the
reader has least other information to fall back on.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from services import provenance
from services.provenance import (
    ALL_TAGS,
    ORGAN_LEVEL_TAGS,
    ROW_LEVEL_TAGS,
    SCORING_EXCLUDE,
    center_data_quality,
    scoring_summary,
    scoring_tags,
)

REPO = Path(__file__).resolve().parents[2]
RESULTS_TABLE_JS = REPO / "simulator" / "results-table.js"


@pytest.fixture(scope="module")
def client(data):
    return TestClient(app)


# ── The row/organ split is a claim about the detectors, so check it ──────────

@pytest.mark.parametrize("tag", ORGAN_LEVEL_TAGS)
def test_organ_level_tags_really_are_center_invariant(data, tag):
    """A tag is only safe to omit from per-row marking if it cannot vary.

    If a detector later becomes center-specific, the tag starts carrying
    row-level information and dropping it from the badge would hide a real
    difference. This fails the moment that happens.
    """
    codes = [c["code"] for c in data.centers_for_organ("kidney")]
    assert len(codes) > 50, "need a real center population for this to mean anything"
    present = {tag in center_data_quality("kidney", code) for code in codes}
    assert len(present) == 1, (
        f"{tag} varies between centers, so it is no longer organ-level — move "
        f"it out of ORGAN_LEVEL_TAGS or the per-row badge will hide it"
    )


def test_row_and_organ_tags_partition_all_tags():
    assert set(ROW_LEVEL_TAGS) | set(ORGAN_LEVEL_TAGS) == set(ALL_TAGS)
    assert not set(ROW_LEVEL_TAGS) & set(ORGAN_LEVEL_TAGS)


# ── scoring_tags ────────────────────────────────────────────────────────────

def test_scoring_tags_are_positional_against_the_codes_given(data):
    codes = [c["code"] for c in data.centers_for_organ("intestine")]
    tags = scoring_tags("intestine", codes)
    assert len(tags) == len(codes)
    for code, got in zip(codes, tags):
        expected = [t for t in center_data_quality("intestine", code)
                    if t not in SCORING_EXCLUDE]
        assert got == expected


def test_scoring_tags_exclude_non_scoring_families(data):
    """Competing risks are not a scoring input, so they must not appear on a
    scored row — otherwise the badge claims the SCORE is degraded when only
    the simulation is."""
    codes = [c["code"] for c in data.centers_for_organ("pancreas")]
    flat = {t for tags in scoring_tags("pancreas", codes) for t in tags}
    for excluded in SCORING_EXCLUDE:
        assert excluded not in flat


def test_scoring_tags_are_not_vacuous(data):
    """Guard the guard: pancreas and intestine are known-degraded organs.

    If this ever returns nothing anywhere, the detectors have silently
    stopped detecting and every test above would still pass.
    """
    codes = [c["code"] for c in data.centers_for_organ("intestine")]
    degraded = [t for t in scoring_tags("intestine", codes) if t]
    assert degraded, "no intestine center flagged — detectors are inert"


# ── The summary and the rows must agree ─────────────────────────────────────

def test_summary_counts_match_the_per_center_tags(data):
    codes = [c["code"] for c in data.centers_for_organ("intestine")]
    tags = scoring_tags("intestine", codes)
    summary = scoring_summary("intestine", codes, tag_lists=tags)
    n_clean = sum(1 for t in tags if not t)
    assert summary["fully_center_level"] == n_clean
    assert summary["centers_total"] == len(codes)


@pytest.mark.parametrize("organ", ["pancreas", "intestine", "kidney"])
def test_row_level_degraded_counts_exactly_what_can_be_marked(data, organ):
    """The note tells the reader those centers are marked in the table, so
    the number it prints has to be the number of markers."""
    codes = [c["code"] for c in data.centers_for_organ(organ)]
    tags = scoring_tags(organ, codes)
    summary = scoring_summary(organ, codes, tag_lists=tags)
    # Deliberately NOT `sum(1 for t in tags if t)`: a center's tag list is the
    # complete picture, organ-wide entries included, because an API consumer
    # may want them. Only the row-level subset can be marked.
    markable = sum(1 for t in tags if any(x in t for x in ROW_LEVEL_TAGS))
    assert summary["row_level_degraded"] == markable


def test_row_level_degraded_differs_from_the_naive_count(data):
    """Guard the guard. If these ever coincide everywhere, the distinction is
    untested and someone will reasonably delete it.

    Pancreas is the case that motivated it: every one of its 99 centers
    carries the organ-wide reconstructed-median tag, so the naive difference
    says 99 while only 38 centers have anything a row marker can point at.
    """
    codes = [c["code"] for c in data.centers_for_organ("pancreas")]
    tag_lists = [center_data_quality("pancreas", c) for c in codes]
    summary = provenance.summarize(tag_lists)
    naive = summary["centers_total"] - summary["fully_center_level"]
    assert summary["row_level_degraded"] < naive


def test_precomputed_tag_lists_give_the_same_summary(data):
    """The router passes tags in to avoid a second sweep; that must be a pure
    optimization, not a behavior change."""
    codes = [c["code"] for c in data.centers_for_organ("pancreas")]
    fresh = scoring_summary("pancreas", codes)
    passed_in = scoring_summary("pancreas", codes,
                                tag_lists=scoring_tags("pancreas", codes))
    assert fresh == passed_in


# ── The endpoint ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("organ", ["intestine", "pancreas"])
def test_score_response_carries_per_center_data_quality(client, organ):
    r = client.post("/score", json={"organ": organ, "blood_type": "O+",
                                    "age": 50, "sex": "male", "urgency": 2})
    assert r.status_code == 200
    body = r.json()
    flagged = [c for c in body["centers"] if c.get("data_quality")]
    assert flagged, "no center carried per-center provenance"
    # The summary's own row-level count must equal the number of centers a
    # marker can point at — the note promises the reader exactly that.
    markable = sum(1 for c in body["centers"]
                   if any(t in ROW_LEVEL_TAGS for t in (c.get("data_quality") or [])))
    assert body["data_quality"]["row_level_degraded"] == markable


def test_clean_centers_omit_the_field_rather_than_sending_empty(client):
    r = client.post("/score", json={"organ": "kidney", "blood_type": "O+",
                                    "age": 50, "sex": "male", "urgency": 2})
    assert r.status_code == 200
    for c in r.json()["centers"]:
        assert c.get("data_quality") is None or c["data_quality"] != []


def test_score_explain_still_returns_centers(client):
    """The duplicate CenterScore block was collapsed into a helper; explain
    has no tag lists and must not break."""
    r = client.post("/score/explain?limit=3",
                    json={"organ": "kidney", "blood_type": "O+", "age": 50,
                          "sex": "male", "urgency": 2})
    assert r.status_code == 200
    assert r.json()["centers"]


# ── Cross-language drift: the JS label map is the user-visible half ─────────

def test_frontend_labels_every_row_level_tag_and_no_organ_level_one():
    """The badge only renders tags it can name. A tag with no label would be
    silently dropped — the exact failure mode #227 is about."""
    src = RESULTS_TABLE_JS.read_text(encoding="utf-8")
    start = src.index("var DQ_LABELS = {")
    body = src[start:src.index("};", start)]
    keys = set()
    for line in body.splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        keys.add(line.split(":")[0].strip().strip("'\""))
    assert keys == set(ROW_LEVEL_TAGS), (
        "results-table.js DQ_LABELS drifted from provenance.ROW_LEVEL_TAGS; "
        f"missing={set(ROW_LEVEL_TAGS) - keys} extra={keys - set(ROW_LEVEL_TAGS)}"
    )
