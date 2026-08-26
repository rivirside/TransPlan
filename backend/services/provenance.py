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
TAG_PEDIATRIC_SPARSE = "pediatric_small_cohort"
# #335: an organ with no adult-fitted rate->probability conversion (pancreas
# and intestine have too few adult centers with both a rate and a published
# median to fit one). The center SET is pediatric but the wait numbers fall
# back to adult, which must be visible rather than reported as adequate.
TAG_PEDIATRIC_UNCALIBRATED = "pediatric_wait_uncalibrated"

# tag -> (summary family key, center-level count label, degraded count label)
FAMILIES = {
    TAG_WAIT: ("wait_time_factors", "center_level", "national_default"),
    TAG_RISK: ("competing_risks", "center_level", "national_default"),
    TAG_OUTCOMES: ("observed_outcomes", "available", "missing"),
    TAG_ACCEPTANCE: ("acceptance_rates", "center_level", "national_default"),
    TAG_TRENDS: ("trend_series", "available", "missing"),
    TAG_PEDIATRIC_SPARSE: ("pediatric_cohort", "adequate", "small"),
    # Label the "good" side neutrally: an ADULT run has no pediatric tag, so
    # it counts as good — and "pediatric: 233" would have been a nonsense
    # line on an adult response.
    TAG_PEDIATRIC_UNCALIBRATED: ("pediatric_wait_model", "modeled", "adult_fallback"),
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
    # #320: the observed OARR (Table B11) is the preferred center-level
    # source; the volume-proxy composite is the fallback
    oar = (data.offer_acceptance.get(organ, {}).get("centers", {})
           .get(code, {}).get("oar"))
    if isinstance(oar, (int, float)):
        return False
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


def _check_pediatric_sparse(data, organ: str, code: str) -> bool:
    """Pediatric cohorts are small by nature; below ~10 person-years the
    center's own rate carries little information and the engine shrinks it
    toward the national pediatric baseline (#335)."""
    rec = data.pediatric.get(organ, {}).get("centers", {}).get(code, {})
    if not rec:
        return True
    return (rec.get("person_years") or 0.0) < 10.0


def _check_pediatric_uncalibrated(data, organ: str, center_code: str) -> bool:
    """True when this organ has no fitted rate->probability conversion, so the
    center's pediatric wait numbers are the adult distribution unchanged."""
    try:
        block = (data.pediatric or {}).get(organ) or {}
    except AttributeError:
        return True
    return not ((block.get("calibration") or {}).get("k"))


def center_data_quality(organ: str, center_code: str,
                        pediatric: bool = False) -> list[str]:
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
    tags = [tag for tag, check in _DETECTORS.items()
            if check(data, organ, center_code)]
    # The pediatric family only applies to pediatric runs; adult responses
    # must not sprout a pediatric column.
    if pediatric:
        if _check_pediatric_sparse(data, organ, center_code):
            tags.append(TAG_PEDIATRIC_SPARSE)
        if _check_pediatric_uncalibrated(data, organ, center_code):
            tags.append(TAG_PEDIATRIC_UNCALIBRATED)
    return tags


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
