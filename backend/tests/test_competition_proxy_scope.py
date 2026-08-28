"""#299 / L-064: the competition proxy must stay out of the scoring path.

The Explorer tells users, next to the numbers:

    "These figures describe the map, not your odds, and do not affect the
     center rankings or probabilities anywhere else in this tool."

That is true today — `scoring.py` never imports `allocation_geography`, and
the only consumers are two `/spatial` endpoints. It is also exactly the kind
of claim that silently stops being true when someone wires the proxy into a
score, at which point the disclosure becomes a lie rather than a caveat.

Validation measured 2026-08-27 (docs/allocation-competition-validation.md):
against observed SRTR transplant rates the proxy shows no detectable
relationship — 7 of 8 comparisons negative but only one at p < 0.05 out of
eight tests, which does not survive correction. So the honest handling is
disclosure, and disclosure needs a guard.
"""
import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent

# Modules that compute a patient-facing score, probability or ranking.
SCORING_PATH = [
    "services/scoring.py",
    "services/scoring_explain.py",
    "services/monte_carlo.py",
    "services/bayesian_network.py",
    "services/bbn_parameterizer.py",
    "services/mcmc_inference.py",
    "services/equity.py",
    "services/what_if.py",
]

PROXY_MODULE = "allocation_geography"
PROXY_NAMES = {"allocation_circles", "distance_score", "AVG_CENTERS_250NM",
               "CIRCLE_500_RATIO"}


def _imports(path: Path):
    """(module, name) pairs imported by a file, via AST rather than grep so a
    line-wrapped or aliased import cannot slip past."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append((a.name, None))
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                out.append((node.module or "", a.name))
    return out


@pytest.mark.parametrize("rel", SCORING_PATH)
def test_scoring_path_does_not_import_the_competition_proxy(rel):
    path = BACKEND / rel
    if not path.exists():
        pytest.skip(f"{rel} not present")
    for module, name in _imports(path):
        assert PROXY_MODULE not in (module or ""), (
            f"{rel} now imports {module} — the Explorer tells users the "
            "competition proxy does not affect rankings or probabilities. "
            "Either revert, or update that disclosure and "
            "docs/allocation-competition-validation.md, which says the proxy "
            "is not detectably related to observed outcomes."
        )
        assert name not in PROXY_NAMES, f"{rel} imports {name} from {module}"


def test_the_guard_is_not_vacuous():
    """Every file it claims to check must exist and be parseable — a typo in
    SCORING_PATH would silently check nothing."""
    present = [r for r in SCORING_PATH if (BACKEND / r).exists()]
    assert len(present) >= 6, f"only {present} found; SCORING_PATH has drifted"
    for rel in present:
        assert _imports(BACKEND / rel), f"{rel} parsed to zero imports"


def test_the_proxy_module_still_defines_what_the_guard_watches():
    """If these were renamed, the name check above would pass by watching
    nothing."""
    src = (BACKEND / "services" / "allocation_geography.py").read_text(encoding="utf-8")
    for name in PROXY_NAMES:
        assert name in src, f"{name} no longer exists in allocation_geography"


def test_the_explorer_disclosure_is_present():
    """The claim and the guard have to ship together."""
    html = (REPO / "explorer.html").read_text(encoding="utf-8")
    assert "score-card-note" in html
    assert "do not affect the center rankings" in html
    assert "no detectable relationship" in html
    # Deliberately NOT linking to the validation doc: the docs site builds to
    # routes like /architecture/overview, so a raw .md path from the app root
    # 404s. A caveat that sends the reader nowhere is worse than one that
    # stands on its own.
    assert 'href="docs/' not in html
