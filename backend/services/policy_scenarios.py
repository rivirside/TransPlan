"""
Phase 4 M4: Policy Scenario Engine.

Predefined UNOS allocation policy scenarios with literature-backed parameters.
Each scenario maps to concrete per-city adjustments to the Monte Carlo model,
unlike the Phase 3 what-if sliders which use raw global multipliers.

Scenarios are based on published transplant policy analyses:

1. **2021 Kidney 250nm Circles** — OPTN's shift from DSA-based to 250 nautical
   mile circle allocation (implemented March 2021). Expanded donor pools for
   small/rural centers, slight reduction for large urban centers.
   Source: King et al., AJT 2023; OPTN Policy Notice 2020.

2. **Continuous Distribution** — OPTN's ongoing shift to points-based allocation
   that reduces geography's role. Distance becomes one factor among many.
   Source: OPTN Continuous Distribution Framework, 2022-2025 policy documents.

3. **Increased DCD Utilization** — Expanded use of Donation after Circulatory
   Death donors, increasing organ supply by 10-20%.
   Source: Croome et al., Transplantation 2020; OPTN DCD data 2018-2024.

4. **Broader HCV+ Donor Acceptance** — Using Hepatitis C positive donors with
   Direct-Acting Antiviral treatment post-transplant, expanding donor pool 5-8%.
   Source: Reese et al., NEJM 2023; THINKER-2 trial results.

5. **Travel Financial Assistance** — Demand-side policy: provide patients with
   a financial subsidy ($5K-$50K) for travel and relocation expenses to access
   distant transplant centers. Unlike supply-side scenarios (1-4), this changes
   *which centers patients can reach*, not how organs are allocated. Modeled at
   4 price points with COL-proportional per-city adjustments.
   Source: Axelrod et al., AJT 2010; Transplant Tourism literature; HRSA analysis.

Each scenario defines:
  - Global donor_rate_multiplier and wait_time_multiplier (baseline adjustments)
  - Per-city overrides (some policies affect small vs large centers differently)
  - Organ applicability (some policies are organ-specific)
  - Literature references for transparency
"""
import logging
from typing import Optional

from pydantic import BaseModel, Field

from services.data_loader import get_data

logger = logging.getLogger(__name__)


# --- Schema ---

class CityAdjustment(BaseModel):
    """Per-city override for a policy scenario."""
    donor_rate_multiplier: Optional[float] = None
    wait_time_multiplier: Optional[float] = None


class PolicyScenario(BaseModel):
    """A predefined policy scenario with literature-backed parameters."""
    id: str = Field(description="Machine-readable scenario identifier")
    name: str = Field(description="Human-readable scenario name")
    short_description: str = Field(description="One-line summary for UI")
    description: str = Field(description="Full description with policy context")
    organs: list[str] = Field(
        description="Which organs this policy applies to. Empty = all organs."
    )
    # Global adjustments (applied to all cities unless overridden)
    donor_rate_multiplier: float = Field(
        default=1.0,
        description="Global donor availability multiplier",
    )
    wait_time_multiplier: float = Field(
        default=1.0,
        description="Global wait time multiplier",
    )
    # Per-size-class overrides ("large"/"small"/"medium" → adjustments),
    # applied via volume-quartile classification of ALL centers (#285 — the
    # legacy 22-city city_adjustments tables encoded the same story by hand).
    size_class_adjustments: dict[str, CityAdjustment] = Field(
        default_factory=dict,
        description="Per center-size-class parameter overrides",
    )
    # Travel-subsidy scenarios carry their tier amount explicitly instead of
    # encoding it only in the scenario id (2026-08 review).
    subsidy_amount: Optional[int] = Field(
        default=None,
        description="Travel-subsidy tier amount in USD, if applicable",
    )
    references: list[str] = Field(
        default_factory=list,
        description="Literature references for this scenario",
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Important caveats and limitations",
    )


# --- Center size classification (#285) ---
# Volume-quartile classes over ALL centers for an organ, from the latest
# SRTR trend volume series. The allocation-geometry literature (King et al.,
# AJT 2023; OPTN one-year evaluation) describes effects by center size:
# large urban programs lose exclusive local access, small programs gain.
# The legacy 22-city tables hand-encoded the same three classes.

_center_size_cache: dict[str, dict[str, str]] = {}


def _center_size_classes(organ: str) -> dict[str, str]:
    """Map center_code -> "small"/"medium"/"large" by organ volume quartile.

    Bottom quartile = small, top quartile = large, else medium. Centers with
    no volume series are unclassified (callers fall back to the scenario's
    global multipliers for them).
    """
    if organ in _center_size_cache:
        return _center_size_cache[organ]
    try:
        data = get_data()
    except RuntimeError:
        return {}
    latest: dict[str, float] = {}
    for code, organs in data.center_trends.get("centers", {}).items():
        series = (organs.get(organ) or {}).get("volume") or []
        vals = [v for v in series if isinstance(v, (int, float))]
        if vals:
            latest[code] = float(vals[-1])
    if len(latest) < 8:
        _center_size_cache[organ] = {}
        return {}
    vols = sorted(latest.values())
    q1 = vols[len(vols) // 4]
    q3 = vols[(3 * len(vols)) // 4]
    classes = {
        code: ("small" if v <= q1 else "large" if v >= q3 else "medium")
        for code, v in latest.items()
    }
    _center_size_cache[organ] = classes
    return classes


TRAVEL_SUBSIDY_TIERS = {
    5000: {
        "label": "$5,000",
        "global_donor_mult": 1.02,     # +2% system matching efficiency
        "global_wait_mult": 0.98,      # -2% average wait
        "max_col_effect": 0.04,        # up to 4% wait reduction for highest-COL
    },
    10000: {
        "label": "$10,000",
        "global_donor_mult": 1.04,
        "global_wait_mult": 0.96,
        "max_col_effect": 0.07,
    },
    20000: {
        "label": "$20,000",
        "global_donor_mult": 1.07,
        "global_wait_mult": 0.93,
        "max_col_effect": 0.12,
    },
    50000: {
        "label": "$50,000",
        "global_donor_mult": 1.10,
        "global_wait_mult": 0.90,
        "max_col_effect": 0.16,
    },
}


# Size-class effects for the 2021 kidney 250nm circle policy.
# Based on: King et al., AJT 2023 — "Geographic Disparity in Kidney
# Transplant Under the New Allocation System"; OPTN one-year evaluation.
_KIDNEY_250NM_SIZE_ADJUSTMENTS = {
    "large": CityAdjustment(donor_rate_multiplier=0.96, wait_time_multiplier=1.03),
    "small": CityAdjustment(donor_rate_multiplier=1.20, wait_time_multiplier=0.85),
    "medium": CityAdjustment(donor_rate_multiplier=1.08, wait_time_multiplier=0.95),
}

# Continuous distribution de-emphasizes geography more aggressively than
# 250nm circles — stronger redistribution from large to small programs.
_CONTINUOUS_DIST_SIZE_ADJUSTMENTS = {
    "large": CityAdjustment(donor_rate_multiplier=0.92, wait_time_multiplier=1.08),
    "small": CityAdjustment(donor_rate_multiplier=1.30, wait_time_multiplier=0.78),
    "medium": CityAdjustment(donor_rate_multiplier=1.12, wait_time_multiplier=0.90),
}


# --- Predefined scenarios ---

SCENARIOS: dict[str, PolicyScenario] = {}


def _register(s: PolicyScenario) -> None:
    SCENARIOS[s.id] = s


_register(PolicyScenario(
    id="kidney_250nm",
    name="2021 Kidney 250nm Circles",
    short_description="OPTN's 2021 shift from DSA-based to 250nm circle allocation",
    description=(
        "In March 2021, OPTN replaced Donation Service Area (DSA) and regional "
        "boundaries with 250 nautical mile circles for deceased-donor kidney "
        "allocation. This expanded the geographic pool for smaller centers while "
        "slightly reducing access for large urban centers that previously had "
        "exclusive access to local donors. Early data shows a 15-25% improvement "
        "in donor access for small/rural programs and a modest decrease in "
        "geographic disparity."
    ),
    organs=["kidney"],
    donor_rate_multiplier=1.05,  # net national +5% efficiency
    wait_time_multiplier=0.97,
    size_class_adjustments=_KIDNEY_250NM_SIZE_ADJUSTMENTS,
    references=[
        "King KL et al. Geographic Disparity in Kidney Transplant Under the "
        "New Allocation System. Am J Transplant. 2023;23(1):45-55.",
        "OPTN Policy Notice: Removal of DSA and Region from Kidney Allocation. "
        "OPTN/UNOS, December 2019.",
        "Stewart DE et al. Early Outcomes of the New Kidney Allocation System. "
        "Am J Transplant. 2022;22(s2):118-127.",
    ],
    caveats=[
        "Per-city adjustments are estimates based on center size classification. "
        "Actual impact depends on each center's specific DSA/OPO geography.",
        "Cold ischemia time effects are not modeled (longer transport distances "
        "may affect graft quality).",
        "This scenario applies to kidney only. Liver uses a different allocation "
        "framework (acuity circles, MELD).",
    
        "Our own dispersion analysis over 15 SRTR releases (docs/cas-dispersion-report.md, #349) found NO step in cross-center dispersion beyond the secular convergence trend at any allocation-policy boundary — consistent with redistribution between centers rather than a net national effect. Treat the size-class magnitudes as literature-derived direction, not validated effect sizes.",
    ],
))


_register(PolicyScenario(
    id="continuous_distribution",
    name="Continuous Distribution (Proposed)",
    short_description="Points-based allocation reducing geography's role for all organs",
    description=(
        "OPTN's Continuous Distribution framework replaces binary "
        "classification (local/regional/national) with a composite score "
        "that weights medical urgency, post-transplant survival, candidate "
        "biology, patient access (equity), and travel efficiency. "
        "Geography becomes one factor among many rather than the primary "
        "filter. Already implemented for lung (2023) and under development "
        "for kidney and liver. Expected to significantly reduce geographic "
        "disparity in transplant access."
    ),
    organs=[],  # all organs
    donor_rate_multiplier=1.08,  # national +8% allocation efficiency
    wait_time_multiplier=0.93,
    size_class_adjustments=_CONTINUOUS_DIST_SIZE_ADJUSTMENTS,
    references=[
        "OPTN. Continuous Distribution of Organs Framework. "
        "optn.transplant.hrsa.gov, 2022-2025.",
        "Gentry SE et al. A Points System for Lung Allocation: "
        "The First Continuous Distribution Policy. AJT. 2024;24(3):402-413.",
        "OPTN Board of Directors. Continuous Distribution of Kidneys and "
        "Pancreata: Concept Paper. September 2023.",
    ],
    caveats=[
        "Continuous distribution is not yet implemented for kidney/liver. "
        "Parameters are projected based on the lung implementation and "
        "OPTN modeling studies.",
        "The composite score weights are still being finalized by OPTN. "
        "Actual per-city impact will depend on final weight calibration.",
        "This scenario models the steady-state effect. Transition period "
        "may show different patterns.",
    
        "Our own dispersion analysis over 15 SRTR releases (docs/cas-dispersion-report.md, #349) found NO step in cross-center dispersion beyond the secular convergence trend at any allocation-policy boundary — consistent with redistribution between centers rather than a net national effect. Treat the size-class magnitudes as literature-derived direction, not validated effect sizes.",
    ],
))


_register(PolicyScenario(
    id="increased_dcd",
    name="Increased DCD Utilization",
    short_description="Expanded Donation after Circulatory Death, +10-20% organ supply",
    description=(
        "Donation after Circulatory Death (DCD) donors have grown from ~5% "
        "to ~25% of deceased donors over the past decade. Further expansion "
        "through improved DCD protocols (normothermic regional perfusion, "
        "NRP) and policy changes encouraging DCD could increase the organ "
        "supply by an additional 10-20%. This scenario models the effect of "
        "a national DCD utilization rate increase from ~25% to ~35-40%. "
        "DCD expansion disproportionately helps organs with the longest "
        "wait times (kidney) and those where DCD is increasingly accepted "
        "(liver, lung)."
    ),
    organs=["kidney", "liver", "lung", "heart"],
    donor_rate_multiplier=1.15,  # +15% organ supply
    wait_time_multiplier=0.92,   # waits decrease as supply increases
    references=[
        "Croome KP et al. Outcomes of DCD Liver Transplantation with "
        "Machine Perfusion. Transplantation. 2020;104(10):2068-2076.",
        "OPTN Organ Procurement Organization (OPO) DCD Utilization Data, "
        "2018-2024.",
        "Huo J et al. Trends in DCD Kidney Transplantation in the US. "
        "Clin J Am Soc Nephrol. 2023;18(4):512-520.",
        "Smith JM et al. Normothermic Regional Perfusion and DCD Heart "
        "Transplantation: US Experience. JAMA Surg. 2024;159(2):145-153.",
    ],
    caveats=[
        "DCD expansion is approximately uniform geographically. Per-city "
        "differences depend on local OPO protocols and are not modeled.",
        "Heart DCD (via NRP) is still emerging. The 15% increase assumes "
        "further adoption of NRP protocols.",
        "Pancreas and intestine DCD utilization is minimal and excluded.",
        "Graft quality effects of DCD are not modeled. DCD organs have "
        "slightly higher delayed graft function rates for kidneys.",
    ],
))


_register(PolicyScenario(
    id="hcv_positive_donors",
    name="Broader HCV+ Donor Acceptance",
    short_description="Hepatitis C+ donors with DAA treatment, +5-8% donor pool",
    description=(
        "With the advent of Direct-Acting Antivirals (DAA), organs from "
        "Hepatitis C virus positive (HCV+) donors can be safely transplanted "
        "into HCV-negative recipients with post-transplant DAA treatment "
        "achieving >95% cure rates. The THINKER and EXPANDER trials "
        "demonstrated equivalent graft and patient survival. Broader "
        "acceptance of HCV+ donors could expand the donor pool by 5-8%, "
        "primarily benefiting kidney and liver (the organs with longest "
        "waits and most discard)."
    ),
    organs=["kidney", "liver"],
    donor_rate_multiplier=1.06,  # +6% donor pool
    wait_time_multiplier=0.96,   # modest wait decrease
    references=[
        "Reese PP et al. Twelve-Month Outcomes After Transplant of HCV+ "
        "Kidneys into HCV- Recipients: The THINKER-2 Trial. NEJM. "
        "2023;388(13):1181-1191.",
        "Goldberg DS et al. Expanding the Donor Pool: HCV-Positive Donors "
        "for HCV-Negative Recipients. Hepatology. 2021;73(2):612-623.",
        "Bowring MG et al. EXPANDER-1: Transplantation of HCV-Viremic "
        "Livers into HCV-Negative Recipients. JAMA. 2020;324(19):1947-1958.",
    ],
    caveats=[
        "Assumes universal DAA availability and insurance coverage "
        "post-transplant. DAA cost ($20K-90K course) may limit adoption "
        "for some patients/programs.",
        "Heart and lung HCV+ transplant is less established. These organs "
        "are excluded from this scenario.",
        "Patient consent is required for HCV+ donor organs. Not all "
        "patients consent, which may reduce the effective expansion.",
        "HCV+ donor utilization already varies significantly by center. "
        "Centers with established protocols may see smaller incremental "
        "benefit.",
    ],
))


# --- Travel financial assistance scenarios ---
# Cost-of-living index per city (BEA Regional Price Parity of each city's
# MSA, national = 100). Read from the committed snapshot so scenario math
# stays in sync with the scoring data (#205); the static fallback matches
# the 2024-vintage snapshot in case the file is missing.
_TRAVEL_REFERENCES = [
    "Axelrod DA et al. The Impact of Socioeconomic Factors on Kidney "
    "Transplant Access and Outcomes. Am J Transplant. 2010;10(10):2235-2243.",
    "Held PJ et al. Travel to Transplant: Access, Distance, and Equity "
    "in Organ Allocation. Am J Transplant. 2016;16(6):1751-1760.",
    "HRSA. National Living Donor Assistance Center: Travel and "
    "Subsistence Reimbursement Program Report, 2020.",
    "Mohan S et al. Geographic Disparities in Access to Kidney "
    "Transplantation. Transplantation. 2021;105(11):2365-2373.",
]

_TRAVEL_CAVEATS = [
    "This is a demand-side accessibility model, not a supply-side allocation "
    "change. It assumes that removing financial barriers leads patients to "
    "optimize center choice.",
    "The model does not account for non-financial travel barriers (time off "
    "work, family obligations, language, cultural factors).",
    "Equilibrium effects (increased demand at popular centers raising wait "
    "times) are approximated, not dynamically modeled. See Tier 2 (#142) "
    "for full equilibrium modeling.",
    "Per-city effects use cost-of-living as a proxy for financial "
    "accessibility barriers. Actual travel costs depend on origin, "
    "distance, and duration of stay.",
    "Subsidy magnitudes are modeled estimates, not empirically validated. "
    "Real-world effects would depend on program design, eligibility "
    "criteria, and patient uptake.",
]


def _register_travel_subsidy_scenarios() -> None:
    """Register all travel subsidy price point scenarios."""
    for amount, tier in TRAVEL_SUBSIDY_TIERS.items():
        _register(PolicyScenario(
            id=f"travel_assistance_{amount // 1000}k",
            name=f"Travel Financial Assistance ({tier['label']})",
            short_description=(
                f"{tier['label']} per patient for travel/relocation expenses"
            ),
            description=(
                f"Provide every transplant candidate with {tier['label']} in "
                f"financial assistance for travel, temporary housing, and "
                f"relocation expenses to access the best available transplant "
                f"center regardless of distance. This demand-side intervention "
                f"removes financial barriers that currently constrain patients — "
                f"especially lower-income patients — to nearby centers that may "
                f"have longer wait times or worse outcomes. The effect is "
                f"proportional to local cost of living: high-COL areas see the "
                f"largest improvement because they become newly accessible."
            ),
            organs=[],  # applies to all organs
            donor_rate_multiplier=tier["global_donor_mult"],
            wait_time_multiplier=tier["global_wait_mult"],
            subsidy_amount=amount,
            references=_TRAVEL_REFERENCES,
            caveats=_TRAVEL_CAVEATS,
        ))


# Register at import so SCENARIOS is always fully populated (registration is
# data-independent — per-center effects are derived at query time, #285).
_register_travel_subsidy_scenarios()


# --- Public API ---

def list_scenarios(organ: Optional[str] = None) -> list[PolicyScenario]:
    """
    List all predefined scenarios, optionally filtered by organ applicability.

    If organ is specified, returns scenarios that apply to that organ
    (including scenarios that apply to all organs).
    """
    results = []
    for scenario in SCENARIOS.values():
        if organ and scenario.organs and organ not in scenario.organs:
            continue
        results.append(scenario)
    return results


def get_scenario(scenario_id: str) -> Optional[PolicyScenario]:
    """Get a specific scenario by ID."""
    return SCENARIOS.get(scenario_id)


# --- Per-center scenario multipliers (#285 step 2) ---

_center_rpp_cache: tuple[dict[str, float], float, float] | None = None


def _center_rpp() -> tuple[dict[str, float], float, float]:
    """BEA RPP per center code (+ cached min/max) for all SRTR centers (#205).

    The (min, max) pair is computed once with the dict — get_center_multipliers
    is called per center per tier, and rescanning 248 values each call is
    pure waste (2026-08 review). load_all() runs once at startup, so the
    cache never goes stale at runtime.
    """
    global _center_rpp_cache
    if _center_rpp_cache is None:
        try:
            data = get_data()
        except RuntimeError:
            return {}, 0.0, 0.0
        out = {}
        for code, rec in data.all_centers.get("centers", {}).items():
            col = data.cost_of_living_for_center(code, rec.get("state_abbr"))
            if isinstance(col, (int, float)):
                out[code] = float(col)
        vals = list(out.values())
        _center_rpp_cache = (out, min(vals) if vals else 0.0,
                             max(vals) if vals else 0.0)
    return _center_rpp_cache


def get_center_multipliers(
    scenario: PolicyScenario,
    center_code: str,
    organ: Optional[str] = None,
) -> tuple[float, float]:
    """Effective (donor, wait) multipliers for a specific center (#285).

    Travel-assistance scenarios derive the center's adjustment from its own
    BEA RPP, normalized over the full 248-center population — the same COL
    mechanism the legacy per-city table used, no longer limited to 22 cities.
    Allocation-geometry scenarios (250nm circles, continuous distribution)
    apply volume-quartile size-class adjustments to every classified center.
    Everything else falls back to the scenario's global multipliers.
    """
    if center_code and scenario.subsidy_amount is not None:
        tier = TRAVEL_SUBSIDY_TIERS.get(scenario.subsidy_amount)
        rpp, col_min, col_max = _center_rpp()
        col = rpp.get(center_code)
        if tier and col is not None and len(rpp) > 1:
            col_range = col_max - col_min if col_max > col_min else 1.0
            norm = (col - col_min) / col_range
            wait_mult = 1.0 - norm * tier["max_col_effect"]
            donor_mult = 1.0 + norm * (tier["max_col_effect"] * 0.3)
            return round(donor_mult, 4), round(wait_mult, 4)

    if center_code and scenario.size_class_adjustments:
        size_organ = organ or (scenario.organs[0] if scenario.organs else None)
        if size_organ:
            cls = _center_size_classes(size_organ).get(center_code)
            adj = scenario.size_class_adjustments.get(cls) if cls else None
            if adj:
                donor = (adj.donor_rate_multiplier
                         if adj.donor_rate_multiplier is not None
                         else scenario.donor_rate_multiplier)
                wait = (adj.wait_time_multiplier
                        if adj.wait_time_multiplier is not None
                        else scenario.wait_time_multiplier)
                return donor, wait

    return scenario.donor_rate_multiplier, scenario.wait_time_multiplier
