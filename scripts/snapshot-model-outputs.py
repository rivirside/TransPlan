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


_CR_KEYS = ("p_transplant_24mo", "p_mortality_24mo",
            "p_delisting_24mo", "p_still_waiting_24mo")


def _competing_risks(city) -> dict:
    """Extract the 24-month outcome vector, refusing to invent zeros.

    A missing key here previously became 0.0 silently (#137). A snapshot full
    of zeros looks like data and compares equal to another snapshot full of
    zeros, so the drift report said "unchanged" no matter what happened.
    """
    cr = city.competing_risks or {}
    missing = [k for k in _CR_KEYS if k not in cr]
    if missing:
        raise KeyError(
            f"competing_risks is missing {missing} for {city.center_code} — "
            f"got {sorted(cr)}. Recording zeros would make drift invisible."
        )
    return {k: round(float(cr[k]), 4) for k in _CR_KEYS}


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


def run_engine(patient_dict: dict, engine: str, n_iterations: int,
               seed: int | None = None) -> dict | None:
    """Run a single engine and return city probabilities."""
    from models.schemas import PatientProfile

    profile = PatientProfile(**patient_dict)

    try:
        if engine == "monte_carlo":
            from services.monte_carlo import simulate
            result = simulate(profile, n_iterations=n_iterations, seed=seed)
        elif engine == "bayesian":
            from services.bayesian_network import simulate_bbn
            result = simulate_bbn(profile)
        elif engine == "mcmc":
            from services.mcmc_inference import is_available, simulate_mcmc
            if not is_available(profile.organ):
                return None
            result = simulate_mcmc(profile, n_iterations=n_iterations, seed=seed)
        else:
            return None

        cities = {}
        for c in result.cities:
            cities[c.city] = {
                "p_transplant_24mo": round(c.p_transplant_24mo, 4),
                "median_wait_months": round(c.median_wait_months, 1),
                # The keys carry a _24mo suffix. Without it every snapshot
                # recorded 0/0/0 here, so the tool built to DETECT drift was
                # structurally blind to competing-risk drift -- it would have
                # reported "no change" through any shift in mortality or
                # removal. Fail loudly instead of defaulting to 0.
                "competing_risks": _competing_risks(c),
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
        result = simulate(profile, n_iterations=100, seed=20260827)  # scores only; seeded for reproducibility
        if result.deterministic_scores:
            return result.deterministic_scores
        return None
    except Exception as e:
        logger.warning("Scoring engine failed: %s", e)
        return None


# ──────────────────────────────────────────────────────────────────────
# Comparison (#137 part 2). The snapshot half of this issue shipped and
# worked; nothing ever consumed the snapshots, so drift between iterations
# was captured and never measured.
# ──────────────────────────────────────────────────────────────────────

def _profile_key(profile: dict) -> str:
    p = profile["patient"]
    return f"{p['organ']}/{p['blood_type']}/{p.get('age')}/{p.get('sex')}"


def _spearman(a: list[float], b: list[float]) -> float:
    """Rank correlation without a scipy dependency in a CLI script."""
    def ranks(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        i = 0
        while i < len(order):           # average ties, or correlations on
            j = i                        # near-constant vectors are wrong
            while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    n = len(ra)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((y - mb) ** 2 for y in rb) ** 0.5
    return num / (da * db) if da and db else 1.0


def compare_snapshots(old: dict, new: dict) -> dict:
    """Quantify what moved between two snapshots (#137's comparison metrics)."""
    old_by = {_profile_key(p): p for p in old["profiles"]}
    new_by = {_profile_key(p): p for p in new["profiles"]}
    shared = [k for k in new_by if k in old_by]

    report = {
        "from": old["_meta"].get("label"), "to": new["_meta"].get("label"),
        "from_commit": old["_meta"].get("git", {}).get("commit"),
        "to_commit": new["_meta"].get("git", {}).get("commit"),
        "profiles_compared": len(shared),
        "profiles_only_in_one": sorted(set(old_by) ^ set(new_by)),
        "by_profile": [],
    }

    for key in shared:
        entry = {"profile": key, "engines": {}}
        for engine in ("monte_carlo", "bayesian", "mcmc"):
            o = (old_by[key].get("engines") or {}).get(engine)
            n = (new_by[key].get("engines") or {}).get(engine)
            if not o or not n:
                continue
            oc, nc = o.get("cities") or {}, n.get("cities") or {}
            common = [c for c in nc if c in oc]
            if not common:
                continue
            op = [oc[c]["p_transplant_24mo"] for c in common]
            np_ = [nc[c]["p_transplant_24mo"] for c in common]
            deltas = [abs(x - y) for x, y in zip(op, np_)]
            o_rank = sorted(common, key=lambda c: -oc[c]["p_transplant_24mo"])
            n_rank = sorted(common, key=lambda c: -nc[c]["p_transplant_24mo"])
            # Competing risks: invisible before the key-name fix above.
            # A delta of 0 must mean "measured, unchanged" -- never "could
            # not compare". The first version of this returned 0.0 when the
            # two snapshots used different competing-risk key names, which is
            # the same silent-zero bug this script had in its extractor.
            cr_delta, cr_pairs = 0.0, 0
            for c in common:
                a_all = oc[c].get("competing_risks") or {}
                b_all = nc[c].get("competing_risks") or {}
                for k in set(a_all) & set(b_all):
                    cr_pairs += 1
                    cr_delta = max(cr_delta, abs(a_all[k] - b_all[k]))
            entry["engines"][engine] = {
                "centers": len(common),
                "spearman": round(_spearman(op, np_), 6),
                "mean_abs_delta_p24": round(sum(deltas) / len(deltas), 6),
                "max_abs_delta_p24": round(max(deltas), 6),
                "max_abs_delta_competing_risk":
                    round(cr_delta, 6) if cr_pairs else None,
                "competing_risk_fields_compared": cr_pairs,
                "top5_retained": len(set(o_rank[:5]) & set(n_rank[:5])),
                "top_center_changed": o_rank[0] != n_rank[0],
                "top_center": {"from": o_rank[0], "to": n_rank[0]},
            }
        report["by_profile"].append(entry)

    moved = [e for p in report["by_profile"] for e in p["engines"].values()
             if e["max_abs_delta_p24"] > 1e-9]
    report["summary"] = {
        "engine_runs_compared": sum(len(p["engines"]) for p in report["by_profile"]),
        "engine_runs_that_moved": len(moved),
        "worst_spearman": round(min([e["spearman"] for e in moved], default=1.0), 6),
        "largest_p24_shift": round(max([e["max_abs_delta_p24"] for e in moved], default=0.0), 6),
        "top_center_changes": sum(1 for e in moved if e["top_center_changed"]),
    }
    return report


def render_comparison(report: dict) -> str:
    s = report["summary"]
    lines = [
        f"Comparing {report['from']} ({report['from_commit']}) -> "
        f"{report['to']} ({report['to_commit']})",
        f"  profiles compared:      {report['profiles_compared']}",
        f"  engine runs compared:   {s['engine_runs_compared']}",
        f"  engine runs that moved: {s['engine_runs_that_moved']}",
        f"  worst Spearman:         {s['worst_spearman']}",
        f"  largest |delta p24|:    {s['largest_p24_shift']}",
        f"  top-center changes:     {s['top_center_changes']}",
        "",
    ]
    if report["profiles_only_in_one"]:
        lines.append(f"  NOT COMPARABLE (present in one snapshot only): "
                     f"{report['profiles_only_in_one']}")
        lines.append("")
    # Surface engines that MOVED, and separately engines where something
    # could not be compared at all. Only listing movers meant a run whose
    # competing-risk fields were incomparable printed as "identical" --
    # the third layer of the same silent-zero bug this change is about.
    incomparable = [
        (prof["profile"], engine)
        for prof in report["by_profile"]
        for engine, m in prof["engines"].items()
        if m["competing_risk_fields_compared"] == 0
    ]
    for prof in report["by_profile"]:
        moved = {k: v for k, v in prof["engines"].items()
                 if v["max_abs_delta_p24"] > 1e-9}
        if not moved:
            continue
        lines.append(f"  {prof['profile']}")
        for engine, m in moved.items():
            flag = "  <-- TOP CENTER CHANGED" if m["top_center_changed"] else ""
            lines.append(
                f"    {engine:12s} rho={m['spearman']:.4f} "
                f"mean|d|={m['mean_abs_delta_p24']:.4f} "
                f"max|d|={m['max_abs_delta_p24']:.4f} "
                f"cr|d|={('%.4f' % m['max_abs_delta_competing_risk']) if m['max_abs_delta_competing_risk'] is not None else 'n/a'} "
                f"top5={m['top5_retained']}/5{flag}")
        lines.append("")
    if incomparable:
        lines.append("  COMPETING RISKS NOT COMPARED (n/a) for "
                     f"{len(incomparable)} engine run(s) - the snapshots use "
                     "different key names:")
        for profile, engine in incomparable[:6]:
            lines.append(f"    {profile}  {engine}")
        lines.append("")

    if not any(p["engines"] for p in report["by_profile"]):
        lines.append("  (nothing comparable - check the profile sets match)")
    elif s["engine_runs_that_moved"] == 0 and not incomparable:
        lines.append("  No drift: every compared engine run is identical.")
    elif s["engine_runs_that_moved"] == 0:
        lines.append("  No p24 drift, but see the not-compared fields above.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Snapshot model outputs for comparison")
    parser.add_argument("--label", default=None, help="Human-readable label (e.g. 'post-phase-6b')")
    parser.add_argument("--iterations", type=int, default=1000, help="MC/MCMC iterations")
    parser.add_argument("--seed", type=int, default=20260827,
                        help="RNG seed for the stochastic engines. Snapshots taken "
                             "with different seeds are NOT comparable: unseeded, "
                             "run-to-run noise alone moved every profile and "
                             "changed the top center in 15 of 24 engine runs (#137).")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: data/snapshots/)")
    parser.add_argument("--copula", action="store_true", help="Enable Clayton copula (use_copula=True)")
    parser.add_argument("--cod", action="store_true", help="Enable COD multiplier (adjust_for_cause_of_death=True)")
    parser.add_argument("--compare", nargs=2, metavar=("OLD", "NEW"),
                        help="Compare two existing snapshots instead of taking one")
    parser.add_argument("--json", action="store_true", help="With --compare, emit JSON")
    args = parser.parse_args()

    if args.compare:
        old = json.loads(Path(args.compare[0]).read_text())
        new = json.loads(Path(args.compare[1]).read_text())
        report = compare_snapshots(old, new)
        print(json.dumps(report, indent=2) if args.json else render_comparison(report))
        return

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
            "seed": args.seed,
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
            result = run_engine(profile, engine, args.iterations, seed=args.seed)
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
