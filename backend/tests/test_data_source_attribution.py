"""Every data source the site credits must actually supply data.

The pages named eight "federal data sources": SRTR, OPTN, CDC, CMS, EPA, BLS,
NHTSA, HRSA. Checked against the `_meta.source` string every data file
carries:

  CMS  — nothing. No fetch script, no workflow, no data file. Hospital quality
         comes from SRTR Table C outcomes, not CMS Care Compare. The site
         credited it in FIVE places across three pages, including a data-source
         card on the Explorer promising "hospital quality ratings, patient
         safety indicators, and transplant program reputation scores ...
         updated quarterly".
  BLS  — nothing. Cost of living is BEA Regional Price Parities
         (apps.bea.gov MARPP/SARPP), stated outright in the fetcher and in
         cost-of-living.json's own provenance.
  OPTN — real, but narrow, and I had this wrong first. I asserted no data file
         cited it; cause-of-death-by-region.json does — "Intestine rates from
         OPTN 2023 OTPD ratio (intestine/pancreas=0.104)". One calibration
         ratio, not the "waiting list statistics and donor information ...
         updated monthly" its Explorer card advertised. The card was
         overstated, not fabricated, and the fix is proportionate to that.

Two sources that DO supply data were missing from the list: Census (6 files)
and BEA (1 file, and the one the "BLS" line was really describing).

This is the same class as the landing-page capability claims (#458) and the
equity disclaimers (#235) — a precise, checkable assertion that nothing
checked. Crediting a federal agency that supplied nothing is worse than a
vague overstatement: a reader weighing whether to trust the tool counts the
sources.

The check derives the true list from the data rather than hard-coding it, so
adding a genuine source needs no test edit and removing one fails loudly.
"""
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"

# Name -> pattern matching how that source identifies itself in _meta.source.
SOURCE_PATTERNS = {
    "SRTR": r"\bSRTR\b",
    "OPTN": r"\bOPTN\b",
    "CDC": r"\bCDC\b|\bPLACES\b",
    "CMS": r"\bCMS\b|Care Compare",
    "EPA": r"\bEPA\b|\bAQS\b",
    "BEA": r"\bBEA\b",
    "BLS": r"\bBLS\b",
    "NHTSA": r"\bNHTSA\b|\bFARS\b",
    "HRSA": r"\bHRSA\b",
    "Census": r"\bCensus\b",
}

PAGES = ["index.html", "faq.html", "explorer.html"]


def _sources_with_data():
    """Sources that at least one data file attributes itself to."""
    found = set()
    for path in sorted(DATA.glob("*.json")):
        try:
            meta = json.loads(path.read_text(encoding="utf-8")).get("_meta") or {}
        except (json.JSONDecodeError, OSError):
            continue
        blob = " ".join(str(v) for v in meta.values())
        for name, pattern in SOURCE_PATTERNS.items():
            if re.search(pattern, blob, re.I):
                found.add(name)
    return found


def test_the_provenance_scan_finds_sources():
    """Guard against a vacuous check: if _meta.source disappeared, every page
    claim below would fail for the wrong reason."""
    found = _sources_with_data()
    assert len(found) >= 5, f"only {sorted(found)} found in data/*.json _meta"
    assert "SRTR" in found


@pytest.mark.parametrize("page", PAGES)
def test_no_page_credits_a_source_that_supplies_nothing(page):
    """A reader weighing whether to trust the tool counts the sources."""
    html = (REPO / page).read_text(encoding="utf-8")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    real = _sources_with_data()

    # Only flag a source presented as one of OUR data sources, not a passing
    # domain mention: faq.html legitimately says a "worse than expected"
    # rating triggers additional CMS oversight, which is a fact about
    # transplant regulation, not a claim that we use CMS data.
    # NON-capturing group. With a capturing group, findall returns only the
    # group -- the trigger word alone -- so every span was ~10 characters and
    # matched nothing. The test passed while checking essentially nothing.
    CREDIT = re.compile(
        r"(?:data sources?|federal sources?|refresh|we pull from|draws on|"
        r"pipelines that refresh)[^.]{0,400}", re.I)

    offenders = []
    for span in CREDIT.findall(text):
        for name, pattern in SOURCE_PATTERNS.items():
            if name in real:
                continue
            if re.search(pattern, span, re.I):
                offenders.append((name, span.strip()[:110]))
    assert offenders == [], (
        f"{page} credits sources that supply no data: {offenders}"
    )


def test_cms_supplies_nothing():
    """The premise. If CMS data is ever added, the pages may credit it again
    and this file should be revisited rather than the pages."""
    assert "CMS" not in _sources_with_data(), (
        "a data file now cites CMS — the site may credit it again"
    )
    scripts = list((REPO / "scripts").glob("*hospital*")) + \
        list((REPO / "scripts").glob("*cms*"))
    assert scripts == [], f"a CMS/hospital-quality fetcher now exists: {scripts}"


def test_cost_of_living_is_bea_not_bls():
    """The specific mix-up: the 'BLS' credit was describing BEA's Regional
    Price Parities."""
    meta = json.loads((DATA / "cost-of-living.json").read_text(
        encoding="utf-8"))["_meta"]
    assert re.search(r"\bBEA\b", str(meta.get("source")), re.I)
    assert not re.search(r"\bBLS\b", str(meta.get("source")), re.I)


@pytest.mark.parametrize("page", PAGES)
def test_pages_do_not_overstate_the_source_count(page):
    """'8 federal sources' was wrong in both directions — it counted three
    that supply nothing and omitted two that do."""
    html = (REPO / page).read_text(encoding="utf-8")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    real = len(_sources_with_data())
    for m in re.finditer(r"(\d+) federal (?:data )?sources", text, re.I):
        claimed = int(m.group(1))
        assert claimed <= real, (
            f"{page} claims {claimed} federal sources; only {real} appear in "
            f"any data file's provenance"
        )


def test_the_explorer_card_grid_only_cards_real_sources():
    """The card grid is a data-source list by construction, so it needs its
    own check: the prose-triggered scan above never reaches it.

    A card may name an upstream registry (OPTN is where SRTR's data
    originates) as long as it says so rather than advertising a feed we do not
    consume — the OPTN card previously promised "waiting list statistics and
    donor information ... updated monthly", none of which is fetched.
    """
    html = (REPO / "explorer.html").read_text(encoding="utf-8")
    real = _sources_with_data()
    cards = re.findall(r'class="data-source-card".*?</a>', html, re.S)
    assert len(cards) >= 6, f"only {len(cards)} data-source cards found"

    for card in cards:
        text = re.sub(r"<[^>]+>", " ", card)
        for name, pattern in SOURCE_PATTERNS.items():
            if name in real or not re.search(pattern, text, re.I):
                continue
            # Permitted only if the card states the indirect relationship.
            assert re.search(r"upstream|rather than pulling|analyses of it",
                             text, re.I), (
                f"explorer.html cards {name}, which supplies no data, without "
                f"saying the relationship is indirect: {text.strip()[:120]!r}"
            )

