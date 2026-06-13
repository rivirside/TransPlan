"""#263: guard against drift between the JS and Python scoring constants.

The no-build-step architecture duplicates DEFAULT_WEIGHTS in algorithm.js and
services/scoring.py. This cross-language test fails the moment they diverge.
"""
import re
from pathlib import Path

from services.scoring import DEFAULT_WEIGHTS

ALGORITHM_JS = Path(__file__).resolve().parent.parent.parent / "algorithm.js"


def _parse_js_default_weights(text: str) -> dict[str, float]:
    block = re.search(r"const DEFAULT_WEIGHTS\s*=\s*\{([^}]*)\}", text)
    assert block, "DEFAULT_WEIGHTS object not found in algorithm.js"
    return {
        key: float(val)
        for key, val in re.findall(r"(\w+)\s*:\s*([0-9.]+)", block.group(1))
    }


def test_default_weights_match_between_js_and_python():
    js_weights = _parse_js_default_weights(ALGORITHM_JS.read_text())
    # Sanity: ensure the parse actually captured every category, so the test
    # cannot pass trivially on an empty/failed parse.
    assert len(js_weights) == len(DEFAULT_WEIGHTS) == 8
    assert js_weights == DEFAULT_WEIGHTS
