"""
Load all TransPlan data/ JSON files into memory at startup.
Mirrors the DEFAULTS pattern from data-loader.js but in Python.
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from config import DATA_DIR

logger = logging.getLogger(__name__)


@dataclass
class TransPlanData:
    # data/*.json
    air_quality: dict = field(default_factory=dict)
    cost_of_living: dict = field(default_factory=dict)
    donor_registration: dict = field(default_factory=dict)
    health_demographics: dict = field(default_factory=dict)
    hospital_quality: dict = field(default_factory=dict)
    traffic_fatalities: dict = field(default_factory=dict)
    # data/manual/*.json
    climate_scores: dict = field(default_factory=dict)
    policy_tiers: dict = field(default_factory=dict)
    socioeconomic: dict = field(default_factory=dict)
    srtr_reports: dict = field(default_factory=dict)
    # M2: Cause-of-death by region (organ-specific donor availability)
    cause_of_death: dict = field(default_factory=dict)
    # Phase 4 M2: Post-transplant graft/patient survival by center
    post_transplant_outcomes: dict = field(default_factory=dict)
    # Phase 4 M3: Historical SRTR trends for multi-year analysis
    historical_trends: dict = field(default_factory=dict)
    # Phase 5 M1: Wait-time distributions (log-normal params, blood type multipliers)
    wait_time_distributions: dict = field(default_factory=dict)
    # Phase 5 M1: Competing risks (mortality/delisting rates, multipliers)
    competing_risks: dict = field(default_factory=dict)
    # Phase 6B: Dense spatial data (county/monitor level)
    health_demographics_counties: dict = field(default_factory=dict)
    air_quality_monitors: dict = field(default_factory=dict)
    # Phase 6A: All SRTR centers (~250) with coordinates and organ programs
    all_centers: dict = field(default_factory=dict)
    # Phase 6A: Center-to-city mapping for 22 focus cities
    center_mapping: dict = field(default_factory=dict)
    # Phase 6A: Center-level data (all ~250 centers)
    center_wait_times: dict = field(default_factory=dict)
    center_competing_risks: dict = field(default_factory=dict)
    center_outcomes: dict = field(default_factory=dict)
    # Phase 7: Center contact info (address, phone, website) from SRTR report API
    center_contacts: dict = field(default_factory=dict)
    # freshness metadata keyed by logical name
    freshness: dict = field(default_factory=dict)

    @property
    def wait_time_factors(self) -> dict[str, float]:
        """Per-city wait time relative factors (from SRTR PSR Table B10)."""
        return self.srtr_reports.get("waitTimeFactors", {})

    @property
    def center_volumes(self) -> dict[str, dict[str, int]]:
        """Shortcut to organ → city → annual volume."""
        return self.srtr_reports.get("centerVolumes", {})

    @property
    def cities(self) -> list[dict[str, str]]:
        """
        The 22 focus cities as [{city, state}, ...].
        Derived from srtr-center-mapping.json at load time.
        """
        mapping = self.center_mapping.get("cities", {})
        if not mapping:
            return []
        return [{"city": city, "state": info["state"]} for city, info in mapping.items()]

    def centers_for_organ(self, organ: str) -> list[dict]:
        """Return centers that perform *organ*, sorted by code.

        Each dict has: code, name, state, state_abbr, lat, lon.
        """
        all_c = self.all_centers.get("centers", {})
        return sorted(
            [info for info in all_c.values() if organ in info.get("organs", [])],
            key=lambda c: c.get("code", ""),
        )

    @property
    def state_full_names(self) -> dict[str, str]:
        """
        State abbreviation → full name, derived from all_centers data.
        Used for cause-of-death lookups.
        """
        centers = self.all_centers.get("centers", {})
        return {c["state_abbr"]: c["state"] for c in centers.values() if "state_abbr" in c and "state" in c}


_DATA: TransPlanData | None = None


def _load_json(path: Path, name: str, data: TransPlanData) -> dict:
    """Load a single JSON file; log a warning and return {} on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        meta = raw.get("_meta", {})
        data.freshness[name] = meta.get("fetchedAt", "unknown")
        # Strip _meta so callers get clean dicts
        return {k: v for k, v in raw.items() if k != "_meta"}
    except FileNotFoundError:
        logger.warning("Data file not found: %s — using empty dict", path)
        data.freshness[name] = "missing"
        return {}
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error in %s: %s — using empty dict", path, exc)
        data.freshness[name] = "parse_error"
        return {}


def load_all() -> TransPlanData:
    """Load all data files and return a TransPlanData singleton."""
    global _DATA
    data = TransPlanData()

    data.air_quality        = _load_json(DATA_DIR / "air-quality.json",         "air_quality",        data)
    data.cost_of_living     = _load_json(DATA_DIR / "cost-of-living.json",      "cost_of_living",     data)
    data.donor_registration = _load_json(DATA_DIR / "donor-registration.json",  "donor_registration", data)
    data.health_demographics= _load_json(DATA_DIR / "health-demographics.json", "health_demographics",data)
    data.hospital_quality   = _load_json(DATA_DIR / "hospital-quality.json",    "hospital_quality",   data)
    data.traffic_fatalities = _load_json(DATA_DIR / "traffic-fatalities.json",  "traffic_fatalities", data)
    data.climate_scores     = _load_json(DATA_DIR / "manual/climate-scores.json",  "climate_scores",  data)
    data.policy_tiers       = _load_json(DATA_DIR / "manual/policy-tiers.json",    "policy_tiers",    data)
    data.socioeconomic      = _load_json(DATA_DIR / "manual/socioeconomic.json",   "socioeconomic",   data)
    data.srtr_reports       = _load_json(DATA_DIR / "manual/srtr-reports.json",    "srtr_reports",    data)
    data.cause_of_death     = _load_json(DATA_DIR / "cause-of-death-by-region.json", "cause_of_death", data)
    data.post_transplant_outcomes = _load_json(DATA_DIR / "post-transplant-outcomes.json", "post_transplant_outcomes", data)
    data.historical_trends = _load_json(DATA_DIR / "srtr-historical.json", "historical_trends", data)
    data.wait_time_distributions = _load_json(DATA_DIR / "wait-time-distributions.json", "wait_time_distributions", data)
    data.competing_risks = _load_json(DATA_DIR / "competing-risks.json", "competing_risks", data)
    # Phase 6B: Dense spatial data (county/monitor level)
    data.health_demographics_counties = _load_json(DATA_DIR / "health-demographics-counties.json", "health_demographics_counties", data)
    data.air_quality_monitors = _load_json(DATA_DIR / "air-quality-monitors.json", "air_quality_monitors", data)
    # Phase 6A: All centers + center mapping + center-level data
    data.all_centers = _load_json(DATA_DIR / "srtr-all-centers.json", "all_centers", data)
    data.center_mapping = _load_json(DATA_DIR / "srtr-center-mapping.json", "center_mapping", data)
    data.center_wait_times = _load_json(DATA_DIR / "wait-time-distributions-centers.json", "center_wait_times", data)
    data.center_competing_risks = _load_json(DATA_DIR / "competing-risks-centers.json", "center_competing_risks", data)
    data.center_outcomes = _load_json(DATA_DIR / "post-transplant-outcomes-centers.json", "center_outcomes", data)
    data.center_contacts = _load_json(DATA_DIR / "center-contacts.json", "center_contacts", data)

    loaded = sum(1 for v in data.freshness.values() if v not in ("missing", "parse_error"))
    logger.info("TransPlan data loaded: %d/%d files OK", loaded, len(data.freshness))

    _DATA = data
    return data


def get_data() -> TransPlanData:
    """Return the singleton; raises RuntimeError if load_all() was never called."""
    if _DATA is None:
        raise RuntimeError("Data not loaded — call load_all() at startup")
    return _DATA
