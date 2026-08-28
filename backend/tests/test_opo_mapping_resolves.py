"""Every center resolves to a named OPO.

`allocation_geography` reaches the OPO layer through three chained lookups,
each of which degrades quietly rather than raising:

    center_opo = mapping.get("centerOpoMap", {})          # missing -> {}
    ...
    "opo_name": (mapping.get("opos", {}).get(opo) or {}).get("name")

A center absent from `centerOpoMap` gets no OPO and drops out of the
competition calculation; an OPO code present in the map but absent from
`opos` yields `opo_name: None`, which renders as an unlabelled area rather
than an error. Neither announces itself.

Swept 2026-08-28: clean. 248/248 centers map, every mapped code resolves to a
NAMED OPO, no orphan codes, and `opo_competition` resolves for all 496
center-organ pairs.

`opo-mapping.json` gained entry floors in #445, but a floor counts rows — it
cannot see a center that maps to a code nothing defines. This checks the join
rather than the size.

Not a defect, checked: 56 OPOs are referenced of 60 defined. Four serve areas
with no transplant center, which is expected and must not be flagged.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import allocation_geography as ag  # noqa: E402
from services.data_loader import load_all, get_data  # noqa: E402


@pytest.fixture(scope="module")
def mapping():
    load_all()
    return ag._opo_data()


@pytest.fixture(scope="module")
def centers():
    load_all()
    return get_data().all_centers.get("centers", {})


def test_the_mapping_is_populated(mapping, centers):
    """Guard against a vacuous sweep: an empty map would make every join
    check below pass trivially."""
    assert len(mapping.get("centerOpoMap", {})) >= 200
    assert len(mapping.get("opos", {})) >= 40
    assert len(centers) >= 200


def test_every_center_maps_to_an_opo(mapping, centers):
    cmap = mapping.get("centerOpoMap", {})
    unmapped = sorted(c for c in centers if c not in cmap)
    assert unmapped == [], (
        f"{len(unmapped)} centers have no OPO and drop out of the competition "
        f"calculation silently: {unmapped[:6]}"
    )


def test_every_mapped_opo_code_resolves_to_a_named_opo(mapping):
    """The join, not the row count. A code in centerOpoMap that `opos` does
    not define yields opo_name None, which renders as an unlabelled area."""
    cmap = mapping.get("centerOpoMap", {})
    opos = mapping.get("opos", {})
    broken = sorted({(code, opo) for code, opo in cmap.items()
                     if not (opos.get(opo) or {}).get("name")})
    assert broken == [], (
        f"{len(broken)} centers map to an OPO code with no name: {broken[:5]}"
    )


def test_no_orphan_opo_codes(mapping):
    cmap = mapping.get("centerOpoMap", {})
    orphans = sorted(set(cmap.values()) - set(mapping.get("opos", {})))
    assert orphans == [], f"OPO codes referenced but never defined: {orphans}"


def test_unused_opos_are_not_treated_as_an_error(mapping):
    """The counterweight. Some OPOs serve areas with no transplant center, so
    defined-but-unreferenced is expected — a test demanding every OPO be used
    would fail on correct data."""
    cmap = mapping.get("centerOpoMap", {})
    unused = set(mapping.get("opos", {})) - set(cmap.values())
    assert len(unused) < len(mapping.get("opos", {})) * 0.5, (
        f"{len(unused)} of {len(mapping.get('opos', {}))} OPOs are unreferenced "
        "— that is more than service-area geography explains"
    )


@pytest.mark.parametrize("organ", ["kidney", "liver"])
def test_opo_competition_resolves_for_every_center(organ, centers):
    """End to end through the public entry point, not just the raw tables."""
    unresolved = []
    for code, c in centers.items():
        try:
            result = ag.opo_competition(c["lat"], c["lon"], organ)
        except Exception as exc:                       # noqa: BLE001
            unresolved.append((code, repr(exc)[:60]))
            continue
        if result is None or result.get("opo") is None:
            unresolved.append((code, "no opo"))
    assert unresolved == [], (
        f"{organ}: {len(unresolved)} centers get no OPO competition: "
        f"{unresolved[:4]}"
    )
