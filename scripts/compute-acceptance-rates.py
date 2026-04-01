"""
Compute per-center organ acceptance rate factors from SRTR data.

Blends two signals into a composite acceptance factor per center/organ:

1. Volume factor (weight 0.6): n_1yr transplant volume from
   post-transplant-outcomes-centers.json, normalized against the organ
   median. Higher volume → higher factor (center completes more transplants).

2. Utilization factor (weight 0.4): derived from competing-risks-centers.json.
   Centers with lower mortality_factor and lower delisting_factor relative to
   peers are more aggressive acceptors (patients leave the list via transplant
   rather than death/delisting). Computed as 1/(mortality * delisting),
   normalized against the organ median.

When both signals are available the composite is 0.6*vol + 0.4*util.
When only volume is available, pure volume factor is used.

Output: data/acceptance-rates-centers.json
"""
import json
import statistics
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# National average offer acceptance rates from SRTR data and literature.
# These represent the fraction of organ offers a center accepts on average.
# Source: Hart et al. AJKD 2021 (kidney), SRTR annual reports 2023.
NATIONAL_ACCEPTANCE_RATES = {
    "kidney": 0.20,
    "liver": 0.30,
    "heart": 0.40,
    "lung": 0.45,
    "pancreas": 0.20,
    "intestine": 0.30,
}

ORGANS = list(NATIONAL_ACCEPTANCE_RATES.keys())

# Weights for composite factor
VOLUME_WEIGHT = 0.6
UTILIZATION_WEIGHT = 0.4


def main():
    # --- Load volume data ---
    outcomes_path = DATA_DIR / "post-transplant-outcomes-centers.json"
    with open(outcomes_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    center_outcomes = raw.get("center_outcomes", {})

    # --- Load competing-risks data ---
    cr_path = DATA_DIR / "competing-risks-centers.json"
    with open(cr_path, "r", encoding="utf-8") as f:
        cr_raw = json.load(f)

    center_adjustments = cr_raw.get("center_adjustments", {})

    # --- Collect n_1yr volumes per organ across all centers ---
    organ_volumes: dict[str, list[tuple[str, float]]] = {o: [] for o in ORGANS}

    for code, organs_data in center_outcomes.items():
        for organ in ORGANS:
            organ_data = organs_data.get(organ, {})
            n_1yr = organ_data.get("n_1yr")
            if n_1yr is not None and n_1yr > 0:
                organ_volumes[organ].append((code, n_1yr))

    # --- Collect raw utilization values per organ across all centers ---
    # utilization = 1 / (mortality_factor * delisting_factor)
    # Higher utilization → center moves patients to transplant rather than
    # death/delisting (i.e. more aggressive acceptor).
    organ_utilizations: dict[str, list[tuple[str, float]]] = {o: [] for o in ORGANS}

    for code, organs_data in center_adjustments.items():
        for organ in ORGANS:
            organ_data = organs_data.get(organ, {})
            mort = organ_data.get("mortality_factor")
            delist = organ_data.get("delisting_factor")
            if mort is not None and delist is not None and mort > 0 and delist > 0:
                util = 1.0 / (mort * delist)
                organ_utilizations[organ].append((code, util))

    # --- Compute medians ---
    organ_volume_medians: dict[str, float] = {}
    for organ in ORGANS:
        volumes = [v for _, v in organ_volumes[organ]]
        organ_volume_medians[organ] = statistics.median(volumes) if volumes else 1.0

    organ_util_medians: dict[str, float] = {}
    for organ in ORGANS:
        utils = [u for _, u in organ_utilizations[organ]]
        organ_util_medians[organ] = statistics.median(utils) if utils else 1.0

    # --- Build lookup for utilization by (code, organ) ---
    util_lookup: dict[tuple[str, str], float] = {}
    for organ in ORGANS:
        median_util = organ_util_medians[organ]
        for code, raw_util in organ_utilizations[organ]:
            util_factor = raw_util / median_util
            util_lookup[(code, organ)] = util_factor

    # --- Compute per-center composite acceptance factors ---
    center_acceptance_factors: dict[str, dict[str, float]] = {}
    composite_count = 0
    volume_only_count = 0

    for organ in ORGANS:
        median_vol = organ_volume_medians[organ]
        for code, vol in organ_volumes[organ]:
            vol_factor = vol / median_vol

            util_factor = util_lookup.get((code, organ))
            if util_factor is not None:
                factor = VOLUME_WEIGHT * vol_factor + UTILIZATION_WEIGHT * util_factor
                composite_count += 1
            else:
                factor = vol_factor
                volume_only_count += 1

            # Clamp to [0.3, 3.0] to prevent extreme values
            factor = max(0.3, min(3.0, factor))
            # Round to 3 decimal places
            factor = round(factor, 3)

            if code not in center_acceptance_factors:
                center_acceptance_factors[code] = {}
            center_acceptance_factors[code][organ] = factor

    # Sort by center code
    center_acceptance_factors = dict(sorted(center_acceptance_factors.items()))

    # Count centers per organ
    counts = {o: len(organ_volumes[o]) for o in ORGANS}
    util_counts = {o: len(organ_utilizations[o]) for o in ORGANS}

    output = {
        "_meta": {
            "source": "Derived from SRTR n_1yr volumes (post-transplant-outcomes-centers.json) "
                      "and competing risks (competing-risks-centers.json)",
            "method": (
                f"Composite: {VOLUME_WEIGHT}*volume_factor + {UTILIZATION_WEIGHT}*utilization_factor, "
                "clamped to [0.3, 3.0]. "
                "volume_factor = n_1yr / organ_median_n_1yr. "
                "utilization_factor = (1 / (mortality_factor * delisting_factor)) / organ_median_utilization. "
                "Falls back to pure volume_factor when competing-risks data unavailable."
            ),
            "volume_medians": {o: round(organ_volume_medians[o], 1) for o in ORGANS},
            "utilization_medians": {o: round(organ_util_medians[o], 3) for o in ORGANS},
            "centers_per_organ": counts,
            "utilization_centers_per_organ": util_counts,
            "composite_entries": composite_count,
            "volume_only_entries": volume_only_count,
            "notes": "Factor > 1.0 = more aggressive acceptor than median. "
                     "Factor < 1.0 = more selective than median. "
                     "National acceptance rates from SRTR/literature.",
        },
        "national_acceptance_rates": NATIONAL_ACCEPTANCE_RATES,
        "center_acceptance_factors": center_acceptance_factors,
    }

    out_path = DATA_DIR / "acceptance-rates-centers.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Written {out_path}")
    print(f"  Volume medians: {organ_volume_medians}")
    print(f"  Utilization medians: {organ_util_medians}")
    print(f"  Centers per organ (volume): {counts}")
    print(f"  Centers per organ (utilization): {util_counts}")
    print(f"  Composite entries: {composite_count}, volume-only entries: {volume_only_count}")
    print(f"  Total unique centers: {len(center_acceptance_factors)}")


if __name__ == "__main__":
    main()
