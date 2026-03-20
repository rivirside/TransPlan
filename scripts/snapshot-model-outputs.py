#!/usr/bin/env python3
"""
Snapshot model outputs for cross-iteration comparison (#137).

Runs a set of reference patient profiles through all available engines
(Monte Carlo, BBN, MCMC) and the Phase 1 scoring algorithm, then saves
a timestamped JSON snapshot for later comparison.

Usage:
    cd backend && python3 ../scripts/snapshot-model-outputs.py
    cd backend && python3 ../scripts/snapshot-model-outputs.py --label "post-phase-6b"
    cd backend && python3 ../scripts/snapshot-model-outputs.py --iterations 2000
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add backend/ to path so we can import services
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Reference patient profiles — representative spread of organs, blood types, acuity
REFERENCE_PROFILES = [
    {"organ": "kidney", "blood_type": "O+", "age": 45, "sex": "male", "urgency": 2, "cpra": 20},
    {"organ": "kidney", "blood_type": "B+", "age": 60, "sex": "female", "urgency": 3, "cpra": 85},
    {"organ": "liver", "blood_type": "A+", "age": 55, "sex": "male", "urgency": 2, "meld": 22},
    {"organ": "liver", "blood_type": "O-", "age": 40, "sex": "female", "urgency": 3, "meld": 35},
    {"organ": "heart", "blood_type": "A+", "age": 50, "sex": "male", "urgency": 2},
    {"organ": "lung", "blood_type": "O+", "age": 55, "sex": "female", "urgency": 2, "las": 45},
    {"organ": "pancreas", "blood_type": "B+", "age": 42, "sex": "male", "urgency": 2},
    {"organ": "intestine", "blood_type": "A+", "age": 35, "sex": "female", "urgency": 3},
]


def get_git_info() -> dict:
    """Get current git commit hash and branch."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = subprocess.call(
            ["git", "diff", "--quiet"], stderr=subprocess.DEVNULL
        ) != 0
        return {"commit": commit[:12], "branch": branch, "dirty": dirty}
    except Exception:
        return {"commit": "unknown", "branch": "unknown", "dirty": False}


def run_engine(patient_dict: dict, engine: str, n_iterations: int) -> dict | None:
    """Run a single engine and return city probabilities."""
    from models.schemas import PatientProfile

    profile = PatientProfile(**patient_dict)

    try:
        if engine == "monte_carlo":
            from services.monte_carlo import simulate
            result = simulate(profile, n_iterations=n_iterations)
        elif engine == "bayesian":
            from services.bayesian_network import simulate_bbn
            result = simulate_bbn(profile)
        elif engine == "mcmc":
            from services.mcmc_inference import is_available, simulate_mcmc
            if not is_available(profile.organ):
                return None
            result = simulate_mcmc(profile, n_iterations=n_iterations)
        else:
            return None

        cities = {}
        for c in result.cities:
            cities[c.city] = {
                "p_transplant_24mo": round(c.p_transplant_24mo, 4),
                "median_wait_months": round(c.median_wait_months, 1),
                "competing_risks": {
                    "p_transplant": round(c.competing_risks.get("p_transplant", 0), 4),
                    "p_mortality": round(c.competing_risks.get("p_mortality", 0), 4),
                    "p_delisting": round(c.competing_risks.get("p_delisting", 0), 4),
                },
                "ci_95": list(c.confidence_interval_95) if c.confidence_interval_95 else None,
            }

        # Ranked city list (by p24 descending)
        ranked = sorted(cities.keys(), key=lambda x: cities[x]["p_transplant_24mo"], reverse=True)

        return {
            "cities": cities,
            "ranking": ranked,
            "elapsed_seconds": round(result.elapsed_seconds, 3),
            "iterations": result.iterations,
        }
    except Exception as e:
        logger.warning("Engine %s failed for %s/%s: %s", engine, patient_dict["organ"], patient_dict["blood_type"], e)
        return None


def run_scoring_engine(patient_dict: dict) -> dict | None:
    """
    Run the Phase 1 deterministic scoring engine via a Monte Carlo call
    and extract deterministic_scores from the result.
    """
    from models.schemas import PatientProfile
    profile = PatientProfile(**patient_dict)
    try:
        from services.monte_carlo import simulate
        result = simulate(profile, n_iterations=100)  # minimal iterations, we just want scores
        if result.deterministic_scores:
            return result.deterministic_scores
        return None
    except Exception as e:
        logger.warning("Scoring engine failed: %s", e)
        return None


def main():
    parser = argparse.ArgumentParser(description="Snapshot model outputs for comparison")
    parser.add_argument("--label", default=None, help="Human-readable label (e.g. 'post-phase-6b')")
    parser.add_argument("--iterations", type=int, default=1000, help="MC/MCMC iterations")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: data/snapshots/)")
    parser.add_argument("--copula", action="store_true", help="Enable Clayton copula (use_copula=True)")
    parser.add_argument("--cod", action="store_true", help="Enable COD multiplier (adjust_for_cause_of_death=True)")
    args = parser.parse_args()

    # Initialize data loader
    from services.data_loader import load_all
    load_all()

    git_info = get_git_info()
    timestamp = datetime.now(timezone.utc).isoformat()
    engines = ["monte_carlo", "bayesian", "mcmc"]

    snapshot = {
        "_meta": {
            "timestamp": timestamp,
            "git": git_info,
            "label": args.label or f"snapshot-{git_info['commit']}",
            "iterations": args.iterations,
            "num_profiles": len(REFERENCE_PROFILES),
            "engines_attempted": engines,
            "flags": {
                "use_copula": args.copula,
                "adjust_for_cause_of_death": args.cod,
            },
        },
        "profiles": [],
    }

    total_start = time.perf_counter()

    for i, base_profile in enumerate(REFERENCE_PROFILES):
        # Apply flags to patient profile
        profile = {**base_profile}
        if args.copula:
            profile["use_copula"] = True
        if args.cod:
            profile["adjust_for_cause_of_death"] = True

        logger.info(
            "[%d/%d] Running %s / %s (copula=%s, cod=%s)...",
            i + 1, len(REFERENCE_PROFILES), profile["organ"], profile["blood_type"],
            args.copula, args.cod,
        )
        profile_result = {
            "patient": profile,
            "engines": {},
            "deterministic_scores": None,
        }

        # Run each engine
        for engine in engines:
            result = run_engine(profile, engine, args.iterations)
            if result:
                profile_result["engines"][engine] = result
                logger.info("  %s: %d cities, %.2fs", engine, len(result["cities"]), result["elapsed_seconds"])
            else:
                logger.info("  %s: skipped/failed", engine)

        # Run deterministic scoring
        scores = run_scoring_engine(profile)
        if scores:
            profile_result["deterministic_scores"] = scores

        snapshot["profiles"].append(profile_result)

    total_elapsed = time.perf_counter() - total_start
    snapshot["_meta"]["total_elapsed_seconds"] = round(total_elapsed, 2)

    # Count engines that ran
    engines_succeeded = set()
    for p in snapshot["profiles"]:
        engines_succeeded.update(p["engines"].keys())
    snapshot["_meta"]["engines_succeeded"] = sorted(engines_succeeded)

    # Write snapshot
    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent.parent / "data" / "snapshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    label = args.label or git_info["commit"]
    filename = f"snapshot-{label}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output_path = output_dir / filename

    with open(output_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    logger.info("Snapshot saved: %s (%.1fs total)", output_path, total_elapsed)
    logger.info("Profiles: %d, Engines: %s", len(REFERENCE_PROFILES), sorted(engines_succeeded))
    print(f"\n{output_path}")


if __name__ == "__main__":
    main()
