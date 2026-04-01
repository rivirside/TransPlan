"""
Compute per-center organ acceptance rate factors from SRTR n_1yr volume data.

Reads post-transplant-outcomes-centers.json and derives acceptance factors
by normalizing each center's transplant volume against the national median
for that organ. Higher volume → higher acceptance factor (more aggressive
center that accepts more offers).

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


def main():
    outcomes_path = DATA_DIR / "post-transplant-outcomes-centers.json"
    with open(outcomes_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    center_outcomes = raw.get("center_outcomes", {})

    # Collect n_1yr volumes per organ across all centers
    organ_volumes: dict[str, list[tuple[str, float]]] = {o: [] for o in ORGANS}

    for code, organs_data in center_outcomes.items():
        for organ in ORGANS:
            organ_data = organs_data.get(organ, {})
            n_1yr = organ_data.get("n_1yr")
            if n_1yr is not None and n_1yr > 0:
                organ_volumes[organ].append((code, n_1yr))

    # Compute median volume per organ
    organ_medians: dict[str, float] = {}
    for organ in ORGANS:
        volumes = [v for _, v in organ_volumes[organ]]
        if volumes:
            organ_medians[organ] = statistics.median(volumes)
        else:
            organ_medians[organ] = 1.0  # fallback

    # Compute per-center acceptance factors
    center_acceptance_factors: dict[str, dict[str, float]] = {}

    for organ in ORGANS:
        median_vol = organ_medians[organ]
        for code, vol in organ_volumes[organ]:
            factor = vol / median_vol
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

    output = {
        "_meta": {
            "source": "Derived from SRTR n_1yr volumes (post-transplant-outcomes-centers.json)",
            "method": "center_volume / national_median_volume, clamped to [0.3, 3.0]",
            "medians": {o: round(organ_medians[o], 1) for o in ORGANS},
            "centers_per_organ": counts,
            "notes": "Factor > 1.0 = higher volume than median (more accepting). "
                     "Factor < 1.0 = lower volume (more selective). "
                     "National acceptance rates from SRTR/literature.",
        },
        "national_acceptance_rates": NATIONAL_ACCEPTANCE_RATES,
        "center_acceptance_factors": center_acceptance_factors,
    }

    out_path = DATA_DIR / "acceptance-rates-centers.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Written {out_path}")
    print(f"  Organ medians: {organ_medians}")
    print(f"  Centers per organ: {counts}")
    print(f"  Total unique centers: {len(center_acceptance_factors)}")


if __name__ == "__main__":
    main()
