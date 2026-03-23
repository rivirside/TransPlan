"""GET /centers — List all transplant centers and focus cities.
GET /centers/{code} — Detail for a single center (#160).
"""
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from services.data_loader import get_data
from utils import haversine_distance

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Live contact fetch with in-memory cache ---
_SRTR_API = "https://reportapi.srtr.org/psr/{code}TX1"
_CONTACT_CACHE: dict[str, tuple[dict, float]] = {}  # code → (contact_dict, fetched_at)
_CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours


def _fetch_live_srtr(code: str) -> dict | None:
    """Fetch contact info + waitlist/volume summary from the SRTR report API.

    Returns a dict with 'contact' and 'waitlist' keys on success, None on failure.
    Cached in-memory for 24 hours.
    """
    cached, ts = _CONTACT_CACHE.get(code, ({}, 0.0))
    if cached and (time.time() - ts) < _CACHE_TTL_SECONDS:
        return cached

    url = _SRTR_API.format(code=code)
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "TransPlan/1.0 (patient decision support tool)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data: dict[str, Any] = json.loads(resp.read())

        detail = data.get("centerDetail", {})
        if not detail:
            return None

        contact = {
            "code": code,
            "address": detail.get("address", "").strip(),
            "city": detail.get("city", "").strip(),
            "state": detail.get("state", "").strip(),
            "zip": detail.get("zipCode", "").strip(),
            "phone": detail.get("phoneNumber", "").strip(),
            "website": (detail.get("url") or "").strip(),
        }

        # Parse waitlist overview per organ
        # SRTR uses "{organ}Data" keys inside waitlistOverview
        organ_map = {"kiData": "kidney", "liData": "liver", "hrData": "heart",
                     "luData": "lung", "paData": "pancreas", "kpData": "kidney-pancreas"}
        waitlist: dict[str, Any] = {}
        for srtr_organ, our_organ in organ_map.items():
            wla = data.get("waitlistOverview", {}).get(srtr_organ, {})
            if wla:
                waitlist[our_organ] = {
                    "currently_waiting": wla.get("wla_end_nc2"),
                    "added_last_year": wla.get("wla_addcen_nc2"),
                    "transplanted_cadaveric": wla.get("wla_remtxc_nc2"),
                    "transplanted_living": wla.get("wla_remtxl_nc2"),
                    "removed_died": wla.get("wla_remdied_nc2"),
                    "removed_deteriorated": wla.get("wla_remdet_nc2"),
                }

        result = {"contact": contact, "waitlist": waitlist}
        _CONTACT_CACHE[code] = (result, time.time())
        return result
    except Exception as exc:
        logger.debug("Live SRTR fetch failed for %s: %s", code, exc)
        return None


@router.get("/centers")
def list_centers(
    organ: str | None = Query(default=None, description="Filter by organ program"),
    focus_only: bool = Query(default=False, description="Return only the 22 focus cities"),
):
    """Return all SRTR transplant centers with coordinates and organ programs."""
    data = get_data()
    all_centers = data.all_centers.get("centers", {})
    mapping = data.center_mapping.get("cities", {})

    if focus_only:
        # Return just the 22 focus cities with their primary/alternate centers
        cities = []
        for city, info in mapping.items():
            codes = [info["primary"]] + info.get("alternates", [])
            center_details = []
            for code in codes:
                c = all_centers.get(code)
                if c:
                    center_details.append(c)
            cities.append({
                "city": city,
                "state": info["state"],
                "centers": center_details,
            })
        return {"cities": cities, "total": len(cities)}

    # Return all centers, optionally filtered by organ
    centers = []
    for code, center in all_centers.items():
        if organ and organ not in center.get("organs", []):
            continue
        centers.append(center)

    return {"centers": centers, "total": len(centers)}


@router.get("/centers/{code}")
def get_center_detail(
    code: str,
    nearby_radius_miles: float = Query(default=250, ge=0, le=1000, description="Radius for nearby centers"),
):
    """Return detailed data for a single transplant center (#160).

    Includes basic info, organ-specific wait time factors, competing risks
    adjustments, post-transplant outcomes, nearby centers, and contact info.
    Contact info is fetched live from SRTR with fallback to cached static data.
    """
    data = get_data()
    all_centers = data.all_centers.get("centers", {})

    # Find center (case-insensitive code match)
    center = all_centers.get(code) or all_centers.get(code.upper())
    if not center:
        raise HTTPException(status_code=404, detail=f"Center '{code}' not found")

    code_key = center["code"]

    # Wait time factors per organ
    wait_factors = {}
    wt_data = getattr(data, 'center_wait_times', None)
    if wt_data:
        center_factors = wt_data.get("center_wait_time_factors", {})
        wait_factors = center_factors.get(code_key, {})

    # Competing risks adjustments per organ
    risk_factors = {}
    cr_data = getattr(data, 'center_competing_risks', None)
    if cr_data:
        center_adj = cr_data.get("center_adjustments", {})
        risk_factors = center_adj.get(code_key, {})

    # Post-transplant outcomes per organ
    outcomes = {}
    oc_data = getattr(data, 'center_outcomes', None)
    if oc_data:
        center_oc = oc_data.get("center_outcomes", {})
        outcomes = center_oc.get(code_key, {})

    # Contact info + waitlist: try live SRTR API first, fall back to static file
    contact_live = True
    srtr_live = _fetch_live_srtr(code_key)
    if srtr_live:
        contact = srtr_live["contact"]
        waitlist_overview = srtr_live["waitlist"]
    else:
        contact_live = False
        waitlist_overview = {}
        cc_data = getattr(data, 'center_contacts', None)
        if cc_data:
            contact = cc_data.get("contacts", {}).get(code_key, {})
        else:
            contact = {}

    # Nearby centers within radius
    nearby = []
    if center.get("lat") and center.get("lon"):
        for other_code, other in all_centers.items():
            if other_code == code_key:
                continue
            if not other.get("lat") or not other.get("lon"):
                continue
            dist = haversine_distance(
                center["lat"], center["lon"],
                other["lat"], other["lon"],
            )
            if dist <= nearby_radius_miles:
                nearby.append({
                    "code": other["code"],
                    "name": other["name"],
                    "state_abbr": other.get("state_abbr", ""),
                    "organs": other.get("organs", []),
                    "distance_miles": round(dist, 1),
                })
        nearby.sort(key=lambda x: x["distance_miles"])

    return {
        "center": center,
        "contact": contact,
        "contact_live": contact_live,
        "waitlist_overview": waitlist_overview,
        "wait_time_factors": wait_factors,
        "competing_risks": risk_factors,
        "outcomes": outcomes,
        "nearby_centers": nearby[:20],  # cap at 20 nearest
        "srtr_url": f"https://www.srtr.org/interactive-report?center={code_key}&type=TX1&organ=KI",
    }
