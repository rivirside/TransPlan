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
    # freshness metadata keyed by logical name
    freshness: dict = field(default_factory=dict)

    @property
    def wait_time_factors(self) -> dict[str, float]:
        """
        Per-city wait time relative factors.
        FIXME (Milestone 2): Currently hardcoded in algorithm.js (cityWaitTimeFactors).
        Move to data/wait-time-distributions.json in Milestone 2.
        """
        return self.srtr_reports.get("waitTimeFactors", {})

    @property
    def center_volumes(self) -> dict[str, dict[str, int]]:
        """Shortcut to organ → city → annual volume."""
        return self.srtr_reports.get("centerVolumes", {})


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

    loaded = sum(1 for v in data.freshness.values() if v not in ("missing", "parse_error"))
    logger.info("TransPlan data loaded: %d/%d files OK", loaded, len(data.freshness))

    _DATA = data
    return data


def get_data() -> TransPlanData:
    """Return the singleton; raises RuntimeError if load_all() was never called."""
    if _DATA is None:
        raise RuntimeError("Data not loaded — call load_all() at startup")
    return _DATA
