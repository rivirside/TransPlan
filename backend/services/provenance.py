"""Data-provenance helpers (#300, centralized per #340): make silent
fallbacks visible.

The center-level getters default missing data to national factors (1.0)
without telling anyone — which is how bugs like #287 stayed invisible. Every
result surface should be able to say which inputs were genuinely center-level.

The tag registry is data-driven: adding a family means one detector function
and one FAMILIES row — summaries, engine epilogues, and the frontend note all
follow automatically. Consumers must never mutate a summary in place; use
the `exclude` parameter (or scoring_summary) instead.
"""
from services.data_loader import get_data

TAG_WAIT = "wait_time_national_default"
TAG_RISK = "competing_risks_national_default"
TAG_OUTCOMES = "no_observed_outcomes"
TAG_ACCEPTANCE = "acceptance_rate_national_default"
TAG_TRENDS = "no_trend_series"

# tag -> (summary family key, center-level count label, degraded count label)
FAMILIES = {
    TAG_WAIT: ("wait_time_factors", "center_level", "national_default"),
    TAG_RISK: ("competing_risks", "center_level", "national_default"),
    TAG_OUTCOMES: ("observed_outcomes", "available", "missing"),
    TAG_ACCEPTANCE: ("acceptance_rates", "center_level", "national_default"),
    TAG_TRENDS: ("trend_series", "available", "missing"),
}

ALL_TAGS = list(FAMILIES)


def _check_wait(data, organ: str, code: str) -> bool:
    wt = data.center_wait_times.get("center_wait_time_factors", {}).get(code, {})
    return not isinstance(wt.get(organ), (int, float))


def _check_risk(data, organ: str, code: str) -> bool:
    cr = (data.center_competing_risks.get("center_adjustments", {})
          .get(code, {}).get(organ))
    return not cr


def _check_outcomes(data, organ: str, code: str) -> bool:
    return data.observed_outcome(organ, code) is None


def _check_acceptance(data, organ: str, code: str) -> bool:
    ar = data.acceptance_rates
    if not ar.get("national_acceptance_rates"):
        return True  # file missing → thinning disabled entirely
    return organ not in ar.get("center_acceptance_factors", {}).get(code, {})


def _check_trends(data, organ: str, code: str) -> bool:
    series = data.center_trends.get("centers", {}).get(code, {}).get(organ, {})
    return not series.get("years")


_DETECTORS = {
    TAG_WAIT: _check_wait,
    TAG_RISK: _check_risk,
    TAG_OUTCOMES: _check_outcomes,
    TAG_ACCEPTANCE: _check_acceptance,
    TAG_TRENDS: _check_trends,
}


def center_data_quality(organ: str, center_code: str) -> list[str]:
    """Degraded-input tags for one center. Empty list = fully center-level.

    #219: with no center_code (or data not loaded) NOTHING is center-level,
    so all tags apply — an empty list here would assert the opposite.
    """
    if not center_code:
        return list(ALL_TAGS)
    try:
        data = get_data()
    except RuntimeError:
        return list(ALL_TAGS)
    return [tag for tag, check in _DETECTORS.items()
            if check(data, organ, center_code)]


def summarize(tag_lists: list[list[str]], exclude: tuple[str, ...] = ()) -> dict:
    """Response-level summary over per-center tag lists.

    `exclude` drops whole families (by tag) for surfaces where they are not
    an input — instead of consumers mutating the shared result (#340).
    """
    n = len(tag_lists)
    out: dict = {"centers_total": n}
    for tag, (family, ok_label, bad_label) in FAMILIES.items():
        if tag in exclude:
            continue
        bad = sum(1 for t in tag_lists if tag in t)
        out[family] = {ok_label: n - bad, bad_label: bad}
    relevant = [t for t in ALL_TAGS if t not in exclude]
    out["fully_center_level"] = sum(
        1 for t in tag_lists if not any(tag in t for tag in relevant))
    return out


def summarize_cities(city_results: list, exclude: tuple[str, ...] = ()) -> dict | None:
    """The engine epilogue (#340): one call instead of the copy-pasted
    summarize([c.data_quality or [] ...]) block in every engine."""
    if not city_results:
        return None
    return summarize([c.data_quality or [] for c in city_results], exclude=exclude)


def scoring_summary(organ: str, center_codes: list[str],
                    spatial_layers_unavailable: list[str] | None = None) -> dict | None:
    """Summary for /score (#219): competing risks and trend series are not
    scoring inputs, and scoring adds the spatial-layer fallback list."""
    if not center_codes:
        return None
    tag_lists = [center_data_quality(organ, code) for code in center_codes]
    out = summarize(tag_lists, exclude=(TAG_RISK, TAG_TRENDS))
    out["spatial_layers_unavailable"] = spatial_layers_unavailable or []
    return out
