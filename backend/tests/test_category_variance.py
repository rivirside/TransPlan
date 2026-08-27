"""A quarter of the composite score is inert for ranking (L-084).

`medicalCompatibility` carries the largest weight (0.25) and is identical at
every center, so it cannot reorder anything. These tests pin that as a
POSITIVE assertion of the defect: if the sub-score ever becomes
center-specific, they fail and L-084 should be closed rather than left
standing as a stale disclosure.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

ARTIFACT = REPO / "docs-site" / "static" / "data" / "category-variance.json"


@pytest.fixture(scope="module")
def report():
    if not ARTIFACT.exists():
        pytest.skip("category-variance.json not generated")
    return json.loads(ARTIFACT.read_text())["organs"]


def test_medical_compatibility_takes_no_center_argument():
    """The structural cause, checked at the source rather than via data.

    The measurement below could in principle read ~0 because the reference
    patients happen to hit a flat region. This cannot: the function has no
    way to know which center it is scoring.
    """
    import inspect
    from services import scoring
    params = list(inspect.signature(scoring._medical_compatibility).parameters)
    assert params == ["patient"], (
        f"_medical_compatibility now takes {params} — if it became "
        "center-aware, L-084 and docs/category-variance-report.md are stale")


def test_the_largest_weight_is_the_inert_one(report):
    from services.scoring import DEFAULT_WEIGHTS
    heaviest = max(DEFAULT_WEIGHTS, key=DEFAULT_WEIGHTS.get)
    assert heaviest == "medicalCompatibility"
    for organ, r in report.items():
        cat = r["categories"]["medicalCompatibility"]
        assert cat["inert"], (
            f"{organ}: medicalCompatibility now varies between centers "
            f"(sd={cat['between_center_sd']}) — close L-084")
        assert cat["rank_driving_share"] == 0.0


def test_inert_weight_mass_is_a_quarter(report):
    for organ, r in report.items():
        assert r["inert_weight_mass"] == pytest.approx(0.25), organ


def test_wait_time_is_what_actually_drives_the_ranking(report):
    """The headline substitution: advertised primary vs actual primary."""
    for organ in ("kidney", "liver", "heart", "pancreas", "intestine"):
        share = report[organ]["categories"]["waitTime"]["rank_driving_share"]
        assert share > 0.45, (
            f"{organ}: waitTime drives {share} of the ranking, no longer the "
            "dominant term — docs/category-variance-report.md is stale")


def test_lung_is_the_organ_without_a_dominant_driver(report):
    """The mechanism behind L-083, pinned alongside the symptom.

    Lung is the only organ where hospitalQuality rivals waitTime. That is why
    its top center is undetermined; if the two separate, L-083 should be
    rechecked too.
    """
    lung = report["lung"]["categories"]
    gap = abs(lung["waitTime"]["rank_driving_share"]
              - lung["hospitalQuality"]["rank_driving_share"])
    assert gap < 0.10, (
        f"lung's two dominant drivers now differ by {gap} — the mechanism "
        "documented for L-083 no longer holds")


def test_changing_the_inert_weight_cannot_reorder_centers():
    """The user-facing consequence, measured end to end.

    Tolerance is not 1.0 because `total` is rounded to one decimal, which
    reshuffles near-ties; the point is that nothing beyond that noise moves.
    """
    from reference_patients import reference_patient_kwargs
    from services.data_loader import load_all
    from services.scoring import DEFAULT_WEIGHTS, score_all_centers
    load_all()
    patient = reference_patient_kwargs("kidney")

    def ranked(weights):
        return [r.code for r in sorted(score_all_centers(patient, weights),
                                       key=lambda r: -r.total)]

    base = ranked(DEFAULT_WEIGHTS)
    pos = {c: i for i, c in enumerate(base, 1)}
    zeroed = dict(DEFAULT_WEIGHTS, medicalCompatibility=0.0)
    alt = ranked(zeroed)
    rho = float(np.corrcoef([pos[c] for c in base], [pos[c] for c in alt])[0, 1])
    assert rho > 0.999, (
        f"zeroing the largest weight moved the ranking (rho={rho}) — it is no "
        "longer inert, so L-084 should be revisited")
