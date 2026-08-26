"""The clinical-assumptions register's header counts must match its rows.

Nothing recomputed them before #335, and they drifted badly: the header
claimed 129 assumptions / 39 unjustified while the file held 221 / 128. The
register is the document reviewers use to judge what is and isn't grounded,
so a stale header understates the outstanding work by a factor of three.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "check-register.py"


def test_register_summary_matches_rows():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"register header is stale:\n{result.stderr or result.stdout}")


def test_every_row_has_a_known_status():
    """A typo'd status silently drops a row out of the unjustified count."""
    sys.path.insert(0, str(REPO / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_register", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assumptions, evidence = mod.parse(SCRIPT.parent.parent.joinpath(
        "docs", "clinical-assumptions-register.md").read_text())
    known = {"uncited", "assumed", "heuristic_clamp", "data_derived",
             "literature", "partially_cited", "cited", "validated", "resolved"}
    bad = {rid: r["status"] for rid, r in {**assumptions, **evidence}.items()
           if r["status"] not in known}
    assert not bad, f"unknown status values (typo?): {bad}"
