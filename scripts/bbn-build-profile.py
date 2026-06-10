#!/usr/bin/env python3
"""
BBN build-cost profiler — Step 0.5 of the BBN rebuild plan.

Measures the cost of building the BBN at each granularity (esp. "full" = 248
regions) to decide whether the 248-state model can be built in-function on
Vercel (cold start) or must be precomputed and shipped as an artifact.

Reports per granularity: cold build wall time, peak memory (tracemalloc),
summed CPT array bytes, and a single-query latency. Also projects the
CompetingOutcome CPT size *after* the planned Region->CompetingOutcome edge
(D2), since that is the structural change the rebuild adds.

Usage:
    cd TransPlan && .venv/bin/python scripts/bbn-build-profile.py
"""
import sys
import time
import tracemalloc
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from services.data_loader import load_all  # noqa: E402
from services import bayesian_network as bn  # noqa: E402
from services.bbn_parameterizer import build_all_cpts, get_regions  # noqa: E402
from models.schemas import PatientProfile  # noqa: E402


def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def profile_granularity(g: str) -> dict:
    n_regions = len(get_regions(g))

    # CPT bytes (build the raw CPT dict)
    cpts = build_all_cpts(g)
    cpt_bytes = sum(arr.nbytes for arr in cpts.values())
    largest = max(cpts.items(), key=lambda kv: kv[1].nbytes)

    # Cold build TIME — measured with tracemalloc OFF. (tracemalloc instruments
    # every allocation and slows allocation-heavy pure-Python builds ~5x, which
    # silently inflated an earlier measurement; never time under tracemalloc.)
    bn._MODEL_CACHE.clear()
    t0 = time.perf_counter()
    bn.build_model(g)
    build_s = time.perf_counter() - t0

    # Peak MEMORY — separate build under tracemalloc; ignore its (inflated) time.
    bn._MODEL_CACHE.clear()
    tracemalloc.start()
    bn.build_model(g)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Single-query latency (warm model)
    patient = PatientProfile(organ="kidney", blood_type="O+", age=50,
                             sex="male", urgency=2, cpra=20)
    setattr(patient, "bbn_granularity", g)
    t0 = time.perf_counter()
    bn.simulate_bbn(patient)
    query_s = time.perf_counter() - t0

    return {
        "granularity": g, "n_regions": n_regions, "build_s": build_s,
        "peak": peak, "cpt_bytes": cpt_bytes,
        "largest_cpt": (largest[0], largest[1].nbytes, largest[1].shape),
        "query_s": query_s,
    }


def main():
    load_all()
    print(f"{'granularity':<10} {'regions':>8} {'build':>9} {'peak mem':>11} "
          f"{'CPT bytes':>11} {'query':>9}")
    print("-" * 64)
    rows = []
    for g in ("classic", "state", "full"):
        r = profile_granularity(g)
        rows.append(r)
        print(f"{r['granularity']:<10} {r['n_regions']:>8} {r['build_s']*1000:>7.0f}ms "
              f"{fmt_bytes(r['peak']):>11} {fmt_bytes(r['cpt_bytes']):>11} "
              f"{r['query_s']*1000:>7.0f}ms")

    full = next(r for r in rows if r["granularity"] == "full")
    name, nb, shape = full["largest_cpt"]
    print(f"\nLargest CPT at full: {name} {shape} = {fmt_bytes(nb)}")

    # Project the rebuild's Region->CompetingOutcome edge (D2): CompetingOutcome
    # grows from (4,4,3,3) to (4,4,3,3,n_regions).
    co = build_all_cpts("full")["CompetingOutcome"]
    projected = co.nbytes * full["n_regions"]
    print(f"CompetingOutcome now: {co.shape} = {fmt_bytes(co.nbytes)}")
    print(f"CompetingOutcome after Region edge (D2): "
          f"(*, {full['n_regions']}) ≈ {fmt_bytes(projected)}")
    print(f"Projected total CPT bytes after D2: "
          f"≈ {fmt_bytes(full['cpt_bytes'] - co.nbytes + projected)}")

    # Decision hint
    print("\nDecision (plan §4): if cold full build > ~10s or peak > ~50% of the "
          "function memory limit, ship CPTs as a precomputed artifact instead of "
          "rebuilding in-function.")
    verdict = "IN-FUNCTION BUILD OK" if full["build_s"] < 10 else "PRECOMPUTE RECOMMENDED"
    print(f"Measured cold full build: {full['build_s']:.2f}s, peak {fmt_bytes(full['peak'])} "
          f"-> {verdict}")


if __name__ == "__main__":
    main()
