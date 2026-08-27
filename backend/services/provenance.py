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
# #376/L-080: SRTR censors this organ's national median (">72 months") and
# publishes no value, so the median every displayed wait derives from is
# RECONSTRUCTED from P25 rather than observed. Affects pancreas only. Without
# this the reconstructed figure is indistinguishable from the five organs
# whose medians SRTR does publish and which are stored verbatim.
TAG_MEDIAN_RECONSTRUCTED = "wait_median_reconstructed"

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
    TAG_MEDIAN_RECONSTRUCTED: ("wait_median", "published", "reconstructed"),
}

ALL_TAGS = list(FAMILIES)

# Tags whose detector ignores center_code — they are properties of the ORGAN,
# so every center in a run carries them or none does. Surfaces that mark
# individual rows must skip these: a badge on all 99 pancreas rows says
# nothing about which row differs, and both already have their own dedicated
# note (#227/#228). test_provenance_row_tags pins the center-invariance so a
# future detector cannot quietly join this set by becoming per-center.
ORGAN_LEVEL_TAGS = (TAG_MEDIAN_RECONSTRUCTED, TAG_PEDIATRIC_UNCALIBRATED)

# The complement: tags that can differ from one center to the next, and are
# therefore worth marking per row.
ROW_LEVEL_TAGS = tuple(t for t in ALL_TAGS if t not in ORGAN_LEVEL_TAGS)

# Competing risks and trend series are not scoring inputs (#219). Shared by
# scoring_tags and scoring_summary so the per-row tags and the summary they
# roll up into cannot disagree about what counts.
SCORING_EXCLUDE = (TAG_RISK, TAG_TRENDS)


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


def _check_median_reconstructed(data, organ: str, center_code: str) -> bool:
    """True when this organ's national median is reconstructed, not published.

    Organ-level rather than center-level: every center of a censored organ
    inherits the reconstruction, because each displayed median is the national
    median times that center's factor.
    """
    try:
        params = (data.wait_time_distributions or {}).get(organ) or {}
    except AttributeError:
        return False
    return bool(params.get("median_censored"))


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
    if _check_median_reconstructed(data, organ, center_code):
        tags.append(TAG_MEDIAN_RECONSTRUCTED)
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
    # How many centers a per-row marker can actually point at (#227). This is
    # NOT centers_total - fully_center_level: that difference also counts the
    # organ-wide tags, which are true of every center at once and are
    # disclosed by their own note instead. For pancreas the two differ 99 vs
    # 38, so a headline built from the difference would promise 99 daggers
    # and render 38.
    row_relevant = [t for t in ROW_LEVEL_TAGS if t not in exclude]
    out["row_level_degraded"] = sum(
        1 for t in tag_lists if any(tag in t for tag in row_relevant))
    return out


def summarize_cities(city_results: list, exclude: tuple[str, ...] = ()) -> dict | None:
    """The engine epilogue (#340): one call instead of the copy-pasted
    summarize([c.data_quality or [] ...]) block in every engine."""
    if not city_results:
        return None
    return summarize([c.data_quality or [] for c in city_results], exclude=exclude)


def scoring_tags(organ: str, center_codes: list[str]) -> list[list[str]]:
    """Per-center degraded-input tags for /score, in the order given (#227).

    The response-level summary says "6 of 233 centers use national defaults"
    but not WHICH — so a reader cannot tell whether the degraded center is the
    one ranked first or the one ranked 200th. Measured 2026-08-27: for pancreas
    that is 10 of the top 10, and for intestine 6 of the top 10.
    """
    return [[t for t in center_data_quality(organ, code)
             if t not in SCORING_EXCLUDE]
            for code in center_codes]


def scoring_summary(organ: str, center_codes: list[str],
                    spatial_layers_unavailable: list[str] | None = None,
                    tag_lists: list[list[str]] | None = None) -> dict | None:
    """Summary for /score (#219): competing risks and trend series are not
    scoring inputs, and scoring adds the spatial-layer fallback list.

    Callers that already built the per-center tags (the router needs them for
    CenterScore.data_quality) pass them in rather than paying for a second
    248-center sweep. Pre-filtered lists are fine: `summarize` skips excluded
    families either way.
    """
    if not center_codes:
        return None
    if tag_lists is None:
        tag_lists = [center_data_quality(organ, code) for code in center_codes]
    out = summarize(tag_lists, exclude=SCORING_EXCLUDE)
    out["spatial_layers_unavailable"] = spatial_layers_unavailable or []
    return out
