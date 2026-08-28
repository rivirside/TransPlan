"""A synthetic generator must not be able to silently replace real data.

Found 2026-08-28 while asking which register rows can actually reach a
reader. `scripts/generate-srtr-historical.py` (register rows GEN-13/14/15,
all high-risk, all "SYNTHETIC") writes to `data/srtr-historical.json`
unconditionally, and is invoked by no npm script, CI job or make target.

The shipped file at that path is **real**: a per-year extraction from SRTR
Tables B10/B7/C-series across 15 releases (1811-2511). `data_loader` reads
it, `trends.py` turns it into the `trends` field of every simulation
response. So running the script — a reasonable thing to try, given it sits in
`scripts/` beside the real fetchers — would have put fabricated numbers in
front of every user, with nothing to stop it.

**A never-shrink count guard could not catch this.** Both the real and the
synthetic file carry the same 22 keys, because the real extraction predates
the 22-city retirement too. The distinguishing property is provenance, so
provenance is what the guard checks. That is the point worth remembering: a
guard has to test the property that actually differs.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "generate-srtr-historical.py"
TARGET = REPO / "data" / "srtr-historical.json"


def test_the_shipped_history_is_real_not_synthetic():
    """The premise. If this file ever becomes synthetic, the guard below is
    guarding nothing and the trends shown to users are fabricated."""
    meta = json.loads(TARGET.read_text(encoding="utf-8"))["_meta"]
    assert "Synthetic" not in meta.get("source", ""), (
        "data/srtr-historical.json is now synthetic — every center's trend "
        "line is fabricated"
    )
    assert len(meta.get("releases", [])) >= 10, (
        f"only {len(meta.get('releases', []))} SRTR releases; the real "
        "extraction spans 15"
    )


def test_the_generator_refuses_to_clobber_real_data():
    """Run it for real. The file must survive untouched and the exit be
    non-zero, so a caller in a pipeline notices."""
    before = TARGET.read_bytes()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
    )
    assert TARGET.read_bytes() == before, (
        "the synthetic generator modified real historical data"
    )
    assert proc.returncode != 0, "refusal must exit non-zero"
    assert "REFUSING" in proc.stderr
    # The message has to say what to do, not just that it stopped.
    assert "--force" in proc.stderr


def test_the_guard_names_the_evidence_it_refused_on():
    """A refusal a reader cannot check is hard to trust or override."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
    )
    assert "releases:" in proc.stderr
    assert "source:" in proc.stderr


def test_a_count_guard_would_not_have_caught_this():
    """Guard-choice rationale, pinned so nobody 'simplifies' it to a floor.

    Real and synthetic both carry 22 keys — the real extraction predates the
    22-city retirement as well — so counting entries cannot distinguish them.
    """
    real = json.loads(TARGET.read_text(encoding="utf-8"))
    assert len(real.get("cities", {})) == 22, (
        "the real file's key count changed; re-check whether a count-based "
        "guard would now be sufficient"
    )
    src = SCRIPT.read_text(encoding="utf-8")
    synthetic_cities = src[src.index("CITIES = ["):]
    synthetic_cities = synthetic_cities[:synthetic_cities.index("]")]
    assert synthetic_cities.count('"') // 2 == 22


def test_the_generator_is_still_unreferenced():
    """Its only safe status is 'nothing runs it automatically'. If a workflow
    or npm script starts invoking it, the guard becomes load-bearing in CI
    rather than a backstop against a manual mistake."""
    hits = []
    for rel in ("package.json", ".github/workflows"):
        target = REPO / rel
        if target.is_dir():
            for f in target.rglob("*"):
                if f.is_file() and "generate-srtr-historical" in f.read_text(
                        encoding="utf-8", errors="ignore"):
                    hits.append(str(f.relative_to(REPO)))
        elif target.exists() and "generate-srtr-historical" in target.read_text(
                encoding="utf-8"):
            hits.append(rel)
    assert hits == [], f"now invoked automatically by {hits}; re-assess the guard"
