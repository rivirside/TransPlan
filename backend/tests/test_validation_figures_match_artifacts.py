"""The validation page's headline figures must match the artifacts.

`validation.html` presents the model's external-facing evidence in one
sentence, with three numbers. The model card renders its numbers live from
these same artifacts and therefore cannot drift; this sentence is prose and
had drifted.

  1. "per-center SRTR calibration (Spearman rho 0.70-0.89)"  -- WRONG.
     The artifacts say 0.4719 to 0.8956. The stated range silently drops the
     three weakest organs: pancreas 0.4719, intestine 0.6154, lung 0.6808.
     Wrong in the reassuring direction, on the page whose purpose is to let a
     reader judge whether the model is trustworthy -- and pancreas at 0.47 is
     a materially different claim from "0.70 at worst".

  2. "kidney 12-month rho 0.85"                              -- correct
     (temporal-forecast.json kidney/12mo median_rho_forecast = 0.846), and the
     accompanying "at the persistence ceiling" holds: 0.846 forecast against
     0.840 persistence.

  3. "decile calibration (rho 0.96-1.0)"                     -- correct
     (decile_spearman spans 0.9636 to 1.0 across both panels).

Two of three were right, which is why this checks all three rather than
deleting the sentence: the fix is a wrong number, not an unreliable page.

Ranges are DERIVED from the artifacts here, so re-running an analysis that
moves a rho fails this test instead of silently making the page wrong.
"""
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "docs-site" / "static" / "data"
VALIDATION = (REPO / "validation.html").read_text(encoding="utf-8")


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _calibration_rhos():
    out = {}
    for path in ARTIFACTS.glob("center-calibration-*.json"):
        organ = path.stem.replace("center-calibration-", "")
        data = json.loads(path.read_text(encoding="utf-8"))
        rho = data.get("stats", {}).get("spearman_p12_vs_txrate", {}).get("rho")
        if rho is not None:
            out[organ] = rho
    return out


def test_the_artifacts_are_present():
    """Otherwise every comparison below passes vacuously."""
    rhos = _calibration_rhos()
    assert len(rhos) >= 5, f"only {sorted(rhos)} calibration artifacts found"
    assert (ARTIFACTS / "temporal-forecast.json").exists()
    assert (ARTIFACTS / "decile-calibration.json").exists()


def test_the_stated_calibration_range_covers_every_organ():
    """The defect. A range that excludes the weakest organs is not a range."""
    rhos = _calibration_rhos()
    lo, hi = min(rhos.values()), max(rhos.values())

    m = re.search(r"SRTR calibration \(Spearman ρ ([\d.]+)[–-]([\d.]+)",
                  _text(VALIDATION))
    assert m, "validation.html no longer states a calibration range"
    stated_lo, stated_hi = float(m.group(1)), float(m.group(2))

    outside = {o: r for o, r in rhos.items() if r < stated_lo - 5e-3}
    assert not outside, (
        f"validation.html claims rho {stated_lo}-{stated_hi}, but "
        f"{ {k: v for k, v in sorted(outside.items(), key=lambda x: x[1])} } "
        f"fall below it. True range: {lo}-{hi}"
    )
    assert stated_hi >= hi - 5e-3, (
        f"stated upper bound {stated_hi} is below the observed {hi}"
    )


def test_the_temporal_figure_matches():
    data = json.loads((ARTIFACTS / "temporal-forecast.json").read_text(
        encoding="utf-8"))
    kidney = data["summary"]["kidney"]["12mo"]
    forecast = kidney["median_rho_forecast"]

    m = re.search(r"kidney 12-month ρ ([\d.]+)", _text(VALIDATION))
    assert m, "validation.html no longer states the kidney 12-month figure"
    assert abs(float(m.group(1)) - forecast) < 0.01, (
        f"page says {m.group(1)}, artifact says {forecast}"
    )
    # The sentence also claims this sits "at the persistence ceiling".
    assert forecast >= kidney["median_rho_persistence"] - 0.02, (
        f"forecast {forecast} is now well below persistence "
        f"{kidney['median_rho_persistence']} — the 'persistence ceiling' "
        "wording no longer holds"
    )


def test_the_decile_figure_matches():
    data = json.loads((ARTIFACTS / "decile-calibration.json").read_text(
        encoding="utf-8"))
    rhos = [organ["decile_spearman"]
            for panel in ("transplant", "mortality")
            for organ in data[panel].values()
            if isinstance(organ, dict) and "decile_spearman" in organ]
    assert rhos, "no decile_spearman values in the artifact"

    m = re.search(r"decile calibration against observed rates \(ρ "
                  r"([\d.]+)[–-]([\d.]+)", _text(VALIDATION))
    assert m, "validation.html no longer states the decile range"
    stated_lo = float(m.group(1))
    assert min(rhos) >= stated_lo - 5e-3, (
        f"page claims decile rho from {stated_lo}; lowest artifact value is "
        f"{min(rhos)}"
    )


@pytest.mark.parametrize("doc", ["CLAUDE.md", "docs/status.md"])
def test_internal_docs_state_the_same_range(doc):
    """Both repeat the figure. A number corrected in one place and left in
    two others is the drift this file exists to stop."""
    text = (REPO / doc).read_text(encoding="utf-8")
    rhos = _calibration_rhos()
    lo = min(rhos.values())
    # Not [^.\n]: CLAUDE.md writes "calibration (`scripts/run-center-
    # calibration.py`) — Spearman ρ ...", and excluding dots skipped it, so
    # the file that repeats the figure most prominently went unchecked.
    for m in re.finditer(r"calibration[^\n]{0,90}?Spearman ρ ([\d.]+)[–-]([\d.]+)",
                         text):
        stated_lo = float(m.group(1))
        assert stated_lo <= lo + 5e-3, (
            f"{doc} claims calibration rho from {stated_lo}; pancreas is {lo}"
        )
