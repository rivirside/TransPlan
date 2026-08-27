"""The 22-city climate fallback must not activate silently (#285 / #302).

`spatial_interpolation` builds the climate surface from the 248 per-center
NASA POWER scores (#289). If `climate-scores-centers.json` is ever absent or
truncated it silently falls back to 23 hardcoded cities — which is exactly the
2026-08-05 incident shape, where generated data files were overwritten with
organ-less shells and nothing noticed.

A silent reversion to 22-city data is the specific thing the project has been
working to eliminate (#285), so it must be loud. These tests pin both halves:
the fallback still EXISTS (it is a real safety net, not dead code), and it
cannot fire without saying so.
"""
import pytest

from services import spatial_interpolation as si
from services.data_loader import get_data


def test_climate_surface_is_built_from_all_centers(data):
    """The live path: 248 centers, not 23 cities."""
    surface = si.get_surface("climate")
    assert surface is not None
    n = getattr(surface, "_n_points", None)
    assert n is not None and n > 200, (
        f"climate surface has {n} source points — it should be per-center "
        "(#289). Fewer than ~200 means the 22-city fallback is active.")


def test_fallback_still_exists_as_a_safety_net(data):
    """Not dead code: if the per-center file is lost, something must serve.

    Deleting the fallback would trade a silent wrong answer for a hard outage,
    which is not obviously better. The fix is to make it audible, not absent.
    """
    assert get_data().climate_scores, (
        "the legacy climate fallback data is gone — if that was deliberate, "
        "this test and CLIMATE_FALLBACK_TAG should go with it")


def test_fallback_is_flagged_when_it_fires(data, monkeypatch):
    """The actual guard. Simulate the incident: per-center data goes missing."""
    d = get_data()
    monkeypatch.setattr(d, "center_climate", {}, raising=False)
    si.clear_cache()

    with pytest.warns(UserWarning, match="22-city|legacy climate"):
        surface = si.get_surface("climate")

    assert si.climate_surface_is_degraded() is True, (
        "the climate surface fell back to city data without recording it")
    assert surface is not None, "the fallback should still produce a surface"
    si.clear_cache()


def test_not_flagged_on_the_normal_path(data):
    """Negative half: the flag must not be permanently on, or it means nothing."""
    si.clear_cache()
    si.get_surface("climate")
    assert si.climate_surface_is_degraded() is False
