"""The landing page's claims about the model must be true of the model.

Same principle as test_equity_disclaimers.py (#235): these are not copy, they
are precise claims about what the tool does, and nothing verified them. Two
were false, on the highest-traffic page in the site.

  1. "The weights are not fixed. They adapt based on organ type, blood type,
     urgency tier, and clinical parameters."

     They are fixed. `DEFAULT_WEIGHTS` is one constant dict applied to every
     patient; the only thing that changes it is the user moving the sliders in
     the simulator's own panel. Nothing in scoring.py varies a weight by
     organ, blood type or urgency. The follow-on sentences described a heart
     patient's score weighting "heavily toward donor quality and center
     volume" against a kidney patient's — behaviour the model does not have.

     This mattered more than a normal copy error, because L-085 had already
     MEASURED that blood type cannot change which center is recommended: it
     reaches exactly one sub-score, and that sub-score is identical at every
     center. So the page promised precisely the personalisation the model had
     been shown not to do.

  2. "Each iteration draws on OPTN historical offer and acceptance rates."

     `model_acceptance` defaults to False, so acceptance thinning is off
     unless a user turns it on. The default run does not draw on acceptance
     rates at all.

Checked and NOT changed: "we run 1,000 simulation iterations" is accurate --
the simulator's iteration slider ships at 1000.
"""
import inspect
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import monte_carlo, scoring  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
INDEX = (REPO / "index.html").read_text(encoding="utf-8")


def _text():
    """Visible prose, tags stripped, whitespace collapsed."""
    body = re.sub(r"<[^>]+>", " ", INDEX)
    return re.sub(r"\s+", " ", body)


def test_the_page_does_not_claim_weights_adapt_to_the_patient():
    """The weights are a fixed constant. Only the user's own slider panel
    changes them, and saying otherwise promises personalisation the model has
    been measured not to perform (L-085)."""
    text = _text().lower()
    assert "weights are not fixed" not in text, (
        "index.html claims the scoring weights adapt to the patient; "
        "DEFAULT_WEIGHTS is a single constant dict"
    )
    for phrase in ("they adapt based on organ type",
                   "weight more toward wait-time probability"):
        assert phrase not in text, f"index.html still claims: {phrase!r}"


def test_the_weights_really_are_fixed():
    """The premise of the test above. If weights ever DO adapt, the claim
    becomes true and this file must be revisited rather than the page."""
    src = inspect.getsource(scoring)
    body = src[src.index("def score_center("):]
    body = body[:body.index("\ndef ", 1)]
    # The only permitted source of variation is the caller's custom_weights.
    assert "DEFAULT_WEIGHTS" in src
    for driver in ("blood_type", "urgency"):
        assert f"weights[{driver}" not in body, (
            f"weights now vary by {driver} — update the landing page, which "
            "was corrected on the basis that they do not"
        )


def test_acceptance_modelling_is_off_by_default():
    """The premise of the claim check below."""
    default = inspect.signature(monte_carlo.simulate).parameters[
        "model_acceptance"].default
    assert default is False, (
        "acceptance modelling now defaults on — the landing page text about "
        "offer/acceptance rates should be revisited"
    )


def test_the_page_does_not_overstate_acceptance_modelling():
    """Checked SENTENCE BY SENTENCE, not by substring.

    The first version of this test looked for two substrings anywhere on the
    page. That is not the claim: the page may mention acceptance freely, as
    long as no sentence presents it as part of the default run. The loose form
    also hid the fact that there were THREE such sentences, not one — the
    other two were in collapsed accordion panels that my first extraction pass
    never matched.
    """
    for sentence in re.findall(r"[^.]*\.", _text()):
        low = sentence.lower()
        if "acceptance" not in low:
            continue
        if any(k in low for k in ("off by default", "advanced option",
                                  "not modeled", "not in the baseline")):
            continue
        pytest.fail(
            "index.html presents acceptance modelling as part of the default "
            f"run, but model_acceptance defaults to False: {sentence.strip()!r}"
        )


def test_the_page_does_not_claim_unmodelled_mechanisms():
    """DCD/DBD donor mix, cold ischemia and 'procurement corridors' were all
    presented as things the model parameterizes per organ. None is in the
    baseline model: DCD exists only as a policy SCENARIO, policy_scenarios.py
    states outright that 'Cold ischemia time effects are not modeled', and
    nothing anywhere implements a procurement corridor."""
    # Narrow deliberately. The page may DESCRIBE the real-world domain --
    # "proximity to active organ procurement corridors is a real logistical
    # advantage" is a true statement about transplant logistics and must stay.
    # What it may not do is claim the MODEL parameterizes these things. A
    # first version of this test banned the phrase outright and would have
    # forced a bad edit to a legitimate background sentence.
    MECHANISMS = ("procurement corridor", "dcd", "dbd", "ischemia")
    MODEL_VERBS = ("we parameterize", "we model", "the model accounts for",
                   "each iteration accounts for", "we simulate")
    for sentence in re.findall(r"[^.]*\.", _text()):
        low = sentence.lower()
        if not any(m in low for m in MECHANISMS):
            continue
        if not any(v in low for v in MODEL_VERBS):
            continue          # describing the world, not the model
        assert " not " in low, (
            f"index.html claims the model parameterizes an unmodelled "
            f"mechanism: {sentence.strip()!r}"
        )


def test_cold_ischemia_is_still_documented_as_unmodelled():
    """Premise for the test above, read from the code rather than assumed."""
    src = (REPO / "backend" / "services" / "policy_scenarios.py").read_text(
        encoding="utf-8")
    assert "ischemia time effects are not modeled" in src, (
        "policy_scenarios.py no longer says cold ischemia is unmodelled — if "
        "it is now modelled, the landing page text can be revisited"
    )


def test_the_iteration_count_claim_is_still_accurate():
    """Checked and deliberately left. The claim is true, and a test that
    only ever removes text would not notice if it stopped being true."""
    simulator = (REPO / "simulator.html").read_text(encoding="utf-8")
    m = re.search(r'id="sim-iterations"[^>]*value="(\d+)"', simulator)
    assert m, "could not find the iteration slider's default"
    default = int(m.group(1))
    text = _text()
    claimed = re.search(r"([\d,]+) simulation iterations", text)
    assert claimed, "index.html no longer states an iteration count"
    assert int(claimed.group(1).replace(",", "")) == default, (
        f"index.html claims {claimed.group(1)} iterations; the slider ships at "
        f"{default}"
    )


def test_competing_risks_claim_holds():
    """The other half of the same sentence, which IS true: competing risks are
    always modelled, unlike acceptance."""
    text = _text().lower()
    assert "competing risks" in text
    src = inspect.getsource(monte_carlo)
    assert "competing" in src.lower()
