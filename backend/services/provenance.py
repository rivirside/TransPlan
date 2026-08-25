"""Data-provenance helpers (#300): make silent fallbacks visible.

The center-level getters default missing data to national factors (1.0)
without telling anyone — which is how bugs like #287 stayed invisible. Every
result surface should be able to say which inputs were genuinely center-level.
"""
from services.data_loader import get_data

TAG_WAIT = "wait_time_national_default"
TAG_RISK = "competing_risks_national_default"
TAG_OUTCOMES = "no_observed_outcomes"


def center_data_quality(organ: str, center_code: str) -> list[str]:
    """Degraded-input tags for one center. Empty list = fully center-level."""
    if not center_code:
        return []
    tags: list[str] = []
    try:
        data = get_data()
    except RuntimeError:
        return []
    wt = data.center_wait_times.get("center_wait_time_factors", {}).get(center_code, {})
    if not isinstance(wt.get(organ), (int, float)):
        tags.append(TAG_WAIT)
    cr = (data.center_competing_risks.get("center_adjustments", {})
          .get(center_code, {}).get(organ))
    if not cr:
        tags.append(TAG_RISK)
    if data.observed_outcome(organ, center_code) is None:
        tags.append(TAG_OUTCOMES)
    return tags


def summarize(tag_lists: list[list[str]]) -> dict:
    """Response-level summary over per-center tag lists."""
    n = len(tag_lists)
    def count(tag: str) -> int:
        return sum(1 for t in tag_lists if tag in t)
    n_wait, n_risk, n_obs = count(TAG_WAIT), count(TAG_RISK), count(TAG_OUTCOMES)
    return {
        "centers_total": n,
        "wait_time_factors": {"center_level": n - n_wait, "national_default": n_wait},
        "competing_risks": {"center_level": n - n_risk, "national_default": n_risk},
        "observed_outcomes": {"available": n - n_obs, "missing": n_obs},
        "fully_center_level": sum(1 for t in tag_lists if not t),
    }
