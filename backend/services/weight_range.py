"""Rank range across the app's own weighting presets (#386 / L-082).

L-082 measured that the eight scoring category weights are load-bearing: under
defensible alternative weightings the top-ranked center changes in 13 of 16
comparisons. The rank intervals that already exist (#313) do not cover this —
they bootstrap the PROBABILITY estimates and rank by p24, varying the data
while holding the weights fixed. So the score ranking, which is what the
results table sorts by, carries no interval at all.

The hard part of quantifying it is deciding which weightings count as
reasonable, and that is a judgement rather than a measurement. Inventing a
neighbourhood here would just move the uncited constant somewhere less
visible.

So the neighbourhood is the app's OWN presets — Balanced, Clinical Focus,
Speed Priority, Quality of Life. The product already offers these to users as
reasonable ways to weigh the same evidence, so the range they span is the
product's own statement of how much the ranking depends on that choice. If a
preset is added or changed, this interval changes with it, which is the
correct behaviour.

What the ranges look like (kidney, 233 centers): the top is stable — the same
center leads under all four presets — while the MEDIAN center moves 34
positions and the worst moves 107. That asymmetry is the useful part: it says
a top-5 placement means something and a 40th-vs-70th comparison does not.
"""
import logging
import time

from services.scoring import DEFAULT_WEIGHTS, score_all_centers

logger = logging.getLogger(__name__)

# Mirrors weight-config.js WEIGHT_PRESETS. Kept in sync deliberately rather
# than imported: the frontend copy is the user-facing definition, and a test
# asserts the two agree so a silent divergence is impossible.
PRESETS: dict[str, dict[str, float]] = {
    "balanced": dict(DEFAULT_WEIGHTS),
    "clinical": {
        "medicalCompatibility": 0.35, "waitTime": 0.15,
        "donorAvailability": 0.10, "hospitalQuality": 0.25,
        "geographic": 0.05, "healthDemographics": 0.05,
        "policy": 0.03, "socioeconomic": 0.02,
    },
    "speed": {
        "medicalCompatibility": 0.15, "waitTime": 0.30,
        "donorAvailability": 0.25, "hospitalQuality": 0.10,
        "geographic": 0.08, "healthDemographics": 0.05,
        "policy": 0.05, "socioeconomic": 0.02,
    },
    "qol": {
        "medicalCompatibility": 0.15, "waitTime": 0.15,
        "donorAvailability": 0.10, "hospitalQuality": 0.10,
        "geographic": 0.20, "healthDemographics": 0.10,
        "policy": 0.05, "socioeconomic": 0.15,
    },
}

PRESET_LABELS = {
    "balanced": "Balanced (Default)",
    "clinical": "Clinical Focus",
    "speed": "Speed Priority",
    "qol": "Quality of Life",
}


def compute_weight_range(patient: dict) -> dict:
    """Rank each center under every preset; return the span.

    Returns per-center `rank_balanced`, `rank_min`, `rank_max`, `rank_spread`
    and the per-preset ranks, plus summary statistics.
    """
    start = time.perf_counter()

    ranks: dict[str, dict[str, int]] = {}
    names: dict[str, str] = {}
    for preset, weights in PRESETS.items():
        rows = sorted(score_all_centers(patient, weights),
                      key=lambda r: -r.total)
        for position, row in enumerate(rows, 1):
            ranks.setdefault(row.code, {})[preset] = position
            names.setdefault(row.code, row.name)

    if not ranks:
        raise ValueError("No centers could be scored for this patient.")

    centers = []
    for code, by_preset in ranks.items():
        # A center missing from a preset's ranking would silently narrow its
        # span; every preset scores the same set, so this should not happen —
        # but a partial record must not masquerade as a tight interval.
        if len(by_preset) != len(PRESETS):
            continue
        lo, hi = min(by_preset.values()), max(by_preset.values())
        centers.append({
            "center_code": code,
            "center_name": names.get(code, code),
            "rank_balanced": by_preset["balanced"],
            "rank_min": lo,
            "rank_max": hi,
            "rank_spread": hi - lo,
            "ranks_by_preset": by_preset,
        })
    centers.sort(key=lambda c: c["rank_balanced"])

    spreads = sorted(c["rank_spread"] for c in centers)
    median_spread = spreads[len(spreads) // 2] if spreads else 0
    elapsed = time.perf_counter() - start
    logger.info("weight-range %s: %d centers, median spread %d, %.2fs",
                patient.get("organ"), len(centers), median_spread, elapsed)

    return {
        "organ": patient.get("organ"),
        "presets": PRESET_LABELS,
        "centers": centers,
        "n_centers": len(centers),
        "median_rank_spread": median_spread,
        "max_rank_spread": spreads[-1] if spreads else 0,
        "elapsed_seconds": round(elapsed, 3),
        "note": (
            "Rank range across the four weighting presets this tool offers. "
            "It reflects how much the ordering depends on which weighting you "
            "choose — a judgement about what matters to you, not a measurement "
            "error. It is a separate and generally larger source of "
            "uncertainty than the sampling intervals on transplant "
            "probability, which hold the weights fixed."
        ),
    }
