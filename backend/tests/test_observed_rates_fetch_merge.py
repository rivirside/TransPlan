"""Fetching one organ's observed rates must not drop the other five.

Same defect as the calibration report, one level upstream, found by sweeping
for the pattern rather than the instance: a script that takes a subset
argument and writes a whole shared artifact from that subset alone.

`fetch-srtr-observed-rates.py --organ kidney` built its output dict from the
selected organs only and wrote it over data/srtr-observed-rates.json. That
file is the ground truth for every calibration gate and is read by fifteen
modules, so a per-organ fetch would have left five organs with no observed
data at all. The line doing it carries the comment "preserves the calibration
input", which is what it does only when no --organ is passed.

The floors added alongside this would catch the result in CI. Catching it is
worth having, but not writing it is better: the floors fire after a developer
has already replaced their working data.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "fetch-srtr-observed-rates.py"
TARGET = REPO / "data" / "srtr-observed-rates.json"
ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]


def test_the_shipped_ground_truth_has_every_organ():
    """The premise. Calibration silently skips centers it cannot match, so a
    missing organ block does not announce itself downstream."""
    data = json.loads(TARGET.read_text(encoding="utf-8"))
    missing = [o for o in ORGANS if o not in data]
    assert not missing, f"srtr-observed-rates.json is missing {missing}"
    for organ in ORGANS:
        assert data[organ].get("centers"), f"{organ} has no centers block"


def test_a_single_organ_fetch_merges_rather_than_replaces():
    """Static check of the write path: the output must be seeded from the
    existing file when only some organs were fetched."""
    src = SCRIPT.read_text(encoding="utf-8")
    body = src[src.index("def main("):]
    assert "OUT_PATH.write_text" in body
    write_region = body[:body.index("OUT_PATH.write_text")]
    assert re.search(r"merge_with_existing\(", write_region), (
        "main() writes OUT_PATH without routing through merge_with_existing() "
        "— a --organ fetch would replace the whole ground-truth file with just "
        "that organ"
    )


def test_the_merge_preserves_untouched_organs(tmp_path, monkeypatch):
    """Behavioural: exercise the merge helper against a real prior file."""
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_obs", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(REPO / "scripts"))

    assert hasattr(mod, "merge_with_existing"), (
        "expected a merge_with_existing() helper so the behaviour is testable "
        "without a network fetch"
    )

    existing = json.loads(TARGET.read_text(encoding="utf-8"))
    prior = tmp_path / "srtr-observed-rates.json"
    prior.write_text(json.dumps(existing), encoding="utf-8")

    fresh = {
        "_meta": {"source": "test", "fetchedAt": "2030-01-01T00:00:00Z"},
        "kidney": {"centers": {"ZZZZ": {"transplant_rate": 1.0}}, "national": {}},
    }
    merged = mod.merge_with_existing(fresh, ["kidney"], prior)

    assert set(ORGANS) <= set(merged), (
        f"merge dropped {set(ORGANS) - set(merged)}"
    )
    assert merged["kidney"]["centers"] == {"ZZZZ": {"transplant_rate": 1.0}}, (
        "the fetched organ must be replaced wholesale, not merged center-wise: "
        "a center that genuinely left the release should disappear"
    )
    for organ in ORGANS:
        if organ != "kidney":
            assert merged[organ] == existing[organ], f"{organ} was altered"


def test_a_full_fetch_does_not_resurrect_a_removed_organ(tmp_path):
    """The counterweight. Merging must not make it impossible to drop an
    organ deliberately -- a full fetch is authoritative."""
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_obs2", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(REPO / "scripts"))

    existing = json.loads(TARGET.read_text(encoding="utf-8"))
    prior = tmp_path / "srtr-observed-rates.json"
    prior.write_text(json.dumps(existing), encoding="utf-8")

    fresh = {"_meta": {"source": "test"},
             **{o: {"centers": {"ZZZZ": {}}, "national": {}} for o in ORGANS[:5]}}
    merged = mod.merge_with_existing(fresh, ORGANS, prior)

    assert "intestine" not in merged, (
        "a fetch covering all organs is authoritative; merging must not "
        "resurrect an organ the release genuinely dropped"
    )
