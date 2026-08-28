"""The never-shrink guard protects the wrong files.

Found 2026-08-28, pulling the thread from the synthetic-generator guard. The
2026-08-05 incident rule in CLAUDE.md says every generated data file needs a
never-shrink guard, and `parse-srtr-reports.py` grew `_write_guarded` in
response. But mapping which writes actually route through it turns up a clean
inversion:

    GUARDED   competing-risks.json                      3K   legacy 22-city
    GUARDED   post-transplant-outcomes.json             2K   legacy 22-city
    GUARDED   wait-time-distributions.json              4K   legacy 22-city
    RAW       competing-risks-centers.json             70K   248 centers
    RAW       wait-time-distributions-centers.json     20K   248 centers
    RAW       post-transplant-outcomes-centers.json   247K   243 centers
    RAW       srtr-historical.json                    278K   15 releases

The guarded files are the small legacy aggregates that existed when the guard
was written. The unguarded ones are the center-level files added later in
Phase 6A — the files `data_loader` actually loads, and the ones the model runs
on. `validate-data.js` has no floor on any of them either.

**Reusing `_write_guarded` unchanged would not have fixed this.** It counts
organ blocks among the TOP-LEVEL keys, and these files have none — their top
level is `_meta` plus a single container (`center_adjustments`) holding 248
center codes, each of which then holds the organs. So the existing guard sees
0 organs before and 0 after, finds no dropped section, and waves through a
write that takes 248 centers down to 3. A guard that passes on the exact
failure it is named for is the pattern this codebase keeps getting bitten by,
so the tests below pin the *center-count* dimension specifically.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "parse-srtr-reports.py"

CENTER_FILES = {
    "competing-risks-centers.json": "center_adjustments",
    "wait-time-distributions-centers.json": "center_wait_time_factors",
    "post-transplant-outcomes-centers.json": "center_outcomes",
}


def _load_script():
    # The script imports its siblings by bare name (`import eb_shrinkage`),
    # so scripts/ has to be importable before it will load.
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location("parse_srtr", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(REPO / "scripts"))


@pytest.fixture(scope="module")
def parser():
    return _load_script()


@pytest.mark.parametrize("fname,container", sorted(CENTER_FILES.items()))
def test_center_files_route_through_the_guard(fname, container):
    """Every center-level output must be written by `_write_guarded`, not a
    bare `open(..., "w")`."""
    src = SCRIPT.read_text(encoding="utf-8")
    const = {
        "competing-risks-centers.json": "CENTERS_COMPETING_OUT",
        "wait-time-distributions-centers.json": "CENTERS_WAIT_OUT",
        "post-transplant-outcomes-centers.json": "CENTERS_OUTCOMES_OUT",
    }[fname]
    assert f'open({const}, "w")' not in src, (
        f"{const} is written with a raw open(); a degraded parse silently "
        f"replaces {fname}"
    )
    assert f"_write_guarded({const}" in src


def test_historical_routes_through_the_guard():
    src = SCRIPT.read_text(encoding="utf-8")
    assert 'open(HISTORICAL_OUT, "w")' not in src, (
        "srtr-historical.json is written unguarded; a parse that discovers "
        "only the current release would drop 14 of 15 SRTR releases"
    )
    assert "_write_guarded(HISTORICAL_OUT" in src


@pytest.mark.parametrize("fname,container", sorted(CENTER_FILES.items()))
def test_the_guard_catches_a_center_count_collapse(parser, tmp_path, fname, container):
    """The dimension that matters for these files, and the one the original
    guard is blind to."""
    existing = json.loads((REPO / "data" / fname).read_text(encoding="utf-8"))
    n = len(existing[container])
    assert n >= 200, f"{fname} unexpectedly holds only {n} centers"

    target = tmp_path / fname
    target.write_text(json.dumps(existing), encoding="utf-8")

    collapsed = {
        "_meta": dict(existing["_meta"]),
        container: dict(list(existing[container].items())[:3]),
    }
    parser._write_guarded(str(target), collapsed)

    after = json.loads(target.read_text(encoding="utf-8"))
    assert len(after[container]) == n, (
        f"guard allowed {fname} to shrink {n} -> 3 centers"
    )


def test_the_guard_catches_a_release_collapse(parser, tmp_path):
    """srtr-historical's shrink dimension is releases, not centers: the parse
    always appends the current release, so a run with the historical/ dir
    absent yields a truthy 1-release dict that would overwrite 15."""
    existing = json.loads(
        (REPO / "data" / "srtr-historical.json").read_text(encoding="utf-8"))
    n = len(existing["_meta"]["releases"])
    assert n >= 10

    target = tmp_path / "srtr-historical.json"
    target.write_text(json.dumps(existing), encoding="utf-8")

    thin = json.loads(json.dumps(existing))
    thin["_meta"]["releases"] = existing["_meta"]["releases"][-1:]
    for organ in thin["national"].values():
        for k, v in organ.items():
            if isinstance(v, list):
                organ[k] = v[-1:]
    parser._write_guarded(str(target), thin)

    after = json.loads(target.read_text(encoding="utf-8"))
    assert len(after["_meta"]["releases"]) == n, (
        f"guard allowed srtr-historical to shrink {n} -> 1 release"
    )


@pytest.mark.parametrize("fname,container", sorted(CENTER_FILES.items()))
def test_the_guard_still_permits_a_legitimate_rewrite(parser, tmp_path, fname, container):
    """The other half. A guard that refuses everything is as useless as one
    that refuses nothing, and would block every future data refresh."""
    existing = json.loads((REPO / "data" / fname).read_text(encoding="utf-8"))
    target = tmp_path / fname
    target.write_text(json.dumps(existing), encoding="utf-8")

    same = json.loads(json.dumps(existing))
    same["_meta"]["fetchedAt"] = "2030-01-01T00:00:00Z"
    parser._write_guarded(str(target), same)

    after = json.loads(target.read_text(encoding="utf-8"))
    assert after["_meta"]["fetchedAt"] == "2030-01-01T00:00:00Z", (
        "guard blocked an identical-coverage refresh"
    )
    assert len(after[container]) == len(existing[container])


def test_growth_is_permitted(parser, tmp_path):
    """Adding a center must not be mistaken for corruption."""
    fname, container = "competing-risks-centers.json", "center_adjustments"
    existing = json.loads((REPO / "data" / fname).read_text(encoding="utf-8"))
    target = tmp_path / fname
    target.write_text(json.dumps(existing), encoding="utf-8")

    grown = json.loads(json.dumps(existing))
    probe = next(iter(existing[container].values()))
    grown[container]["ZZZZ"] = json.loads(json.dumps(probe))
    parser._write_guarded(str(target), grown)

    after = json.loads(target.read_text(encoding="utf-8"))
    assert "ZZZZ" in after[container], "guard blocked a legitimate new center"
