"""#232: keep docs/inference-modes.md true.

A documentation page describing which engines run where is worth nothing if a
tier change can silently invalidate it — and this project has been bitten by
exactly that shape before: five caps existed in TierConfig but were never sent
by /tier, and the frontend defaulted silently every time (#350).

So the doc's availability table is checked against tier_config, and its
dependency claims against the actual requirements files.
"""
import re
from pathlib import Path

import pytest

from tier_config import LOCAL_TIER, WEB_TIER

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "inference-modes.md"
MODES = ("monte_carlo", "bayesian", "mcmc")


@pytest.fixture(scope="module")
def doc():
    return DOC.read_text(encoding="utf-8")


def _row(doc_text: str, mode_label: str) -> str:
    """The availability-table row for one mode."""
    for line in doc_text.splitlines():
        if line.startswith(f"| `{mode_label}`"):
            return line
    raise AssertionError(f"no availability row for {mode_label}")


@pytest.mark.parametrize("mode,label", [
    ("monte_carlo", "monte_carlo"),
    ("bayesian", "bayesian"),
    ("mcmc", "mcmc"),
])
def test_web_column_matches_the_web_tier(doc, mode, label):
    """Column 2 of the table is the web tier's allowed_inference_modes."""
    row = _row(doc, label)
    web_cell = row.split("|")[2]
    allowed = mode in WEB_TIER.allowed_inference_modes
    marked_available = "✅" in web_cell
    assert marked_available == allowed, (
        f"docs/inference-modes.md says web {'allows' if marked_available else 'blocks'} "
        f"{mode}, but WEB_TIER.allowed_inference_modes is "
        f"{WEB_TIER.allowed_inference_modes}"
    )


@pytest.mark.parametrize("mode", MODES)
def test_local_after_fitting_column_matches_the_local_tier(doc, mode):
    """The last column is local-with-everything-present, which is exactly
    LOCAL_TIER.allowed_inference_modes."""
    row = _row(doc, mode)
    last_cell = row.rstrip("|").split("|")[-1]
    assert ("✅" in last_cell) == (mode in LOCAL_TIER.allowed_inference_modes), (
        f"{mode}: doc's local column disagrees with "
        f"{LOCAL_TIER.allowed_inference_modes}"
    )


def test_the_table_is_not_vacuous(doc):
    """Guard the guard. If the rows stopped being found, every parametrized
    check above would still need to fail loudly — but a table that lost its
    distinctions (all ✅, or all ❌) would pass the web checks by accident
    only if the tiers happened to agree. They must not."""
    assert WEB_TIER.allowed_inference_modes != LOCAL_TIER.allowed_inference_modes, (
        "the tiers now allow the same modes, so these tests no longer "
        "distinguish anything — rewrite them or drop the doc's table"
    )
    marks = [_row(doc, m).count("✅") for m in MODES]
    assert len(set(marks)) > 1, "every mode has identical availability in the doc"


def test_mcmc_traces_are_gitignored_as_the_doc_claims():
    """The doc's central practical point: a fresh clone has no traces."""
    ignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert any(line.strip().rstrip("/") == "data/mcmc-traces"
               for line in ignore.splitlines()), (
        "data/mcmc-traces is no longer gitignored — if traces now ship, "
        "docs/inference-modes.md's 'fresh local clone' column is wrong"
    )


def test_production_requirements_exclude_the_mcmc_stack(doc):
    """The doc says pymc/arviz are dev-only. If they reach the Vercel bundle
    that claim is false — and the 250MB Lambda limit makes it likely someone
    would notice the hard way instead."""
    prod = (REPO / "requirements.txt").read_text(encoding="utf-8")
    installed = {ln.split("=")[0].split(">")[0].split("#")[0].strip().lower()
                 for ln in prod.splitlines()
                 if ln.strip() and not ln.strip().startswith("#")}
    for pkg in ("pymc", "arviz", "pgmpy"):
        assert pkg not in installed, (
            f"{pkg} is now a production dependency; docs/inference-modes.md "
            "says the MCMC stack is dev-only and the BBN uses no pgmpy"
        )


def test_the_doc_does_not_repeat_the_pgmpy_claim(doc):
    """#232 itself said 'pgmpy for BBN'. The engine is bbn_lite (#401), so a
    page written to correct that must not reintroduce it."""
    for line in doc.splitlines():
        if "pgmpy" not in line.lower():
            continue
        # Mentioning it to say it is NOT used is the point of the page.
        assert re.search(r"does not use pgmpy|no pgmpy|stale|replaced", line, re.I), (
            f"unqualified pgmpy claim reintroduced: {line.strip()}"
        )
