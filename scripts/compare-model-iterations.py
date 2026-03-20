#!/usr/bin/env python3
"""
Compare model iteration snapshots (#137).

Loads 2+ snapshots produced by snapshot-model-outputs.py and computes:
  - Rank stability (Kendall's tau, Spearman's rho)
  - Score magnitude changes (mean/max delta)
  - Top-5 / bottom-5 city stability
  - Per-city score deltas
  - Spatial convergence (if applicable)

Usage:
    python3 scripts/compare-model-iterations.py data/snapshots/snapshot-A.json data/snapshots/snapshot-B.json
    python3 scripts/compare-model-iterations.py data/snapshots/*.json --engine monte_carlo
    python3 scripts/compare-model-iterations.py data/snapshots/*.json --markdown
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import kendalltau, spearmanr


def load_snapshot(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def extract_rankings(snapshot: dict, engine: str) -> dict[str, dict[str, list[str]]]:
    """Extract organ → ranking from a snapshot for a given engine."""
    rankings = {}
    for profile in snapshot["profiles"]:
        organ = profile["patient"]["organ"]
        bt = profile["patient"]["blood_type"]
        key = f"{organ}/{bt}"
        eng_data = profile["engines"].get(engine)
        if eng_data:
            rankings[key] = eng_data["ranking"]
    return rankings


def extract_p24_maps(snapshot: dict, engine: str) -> dict[str, dict[str, float]]:
    """Extract organ/bt → {city: p24} from a snapshot."""
    maps = {}
    for profile in snapshot["profiles"]:
        organ = profile["patient"]["organ"]
        bt = profile["patient"]["blood_type"]
        key = f"{organ}/{bt}"
        eng_data = profile["engines"].get(engine)
        if eng_data:
            maps[key] = {
                city: data["p_transplant_24mo"]
                for city, data in eng_data["cities"].items()
            }
    return maps


def extract_scores(snapshot: dict) -> dict[str, dict[str, float]]:
    """Extract organ/bt → {city: deterministic_score}."""
    scores = {}
    for profile in snapshot["profiles"]:
        organ = profile["patient"]["organ"]
        bt = profile["patient"]["blood_type"]
        key = f"{organ}/{bt}"
        det = profile.get("deterministic_scores")
        if det:
            scores[key] = det
    return scores


def compare_rankings(rank_a: list[str], rank_b: list[str]) -> dict:
    """Compare two city rankings."""
    common = sorted(set(rank_a) & set(rank_b))
    if len(common) < 3:
        return {"error": "too few common cities", "common": len(common)}

    # Map to ordinal positions for correlation
    pos_a = {city: i for i, city in enumerate(rank_a)}
    pos_b = {city: i for i, city in enumerate(rank_b)}
    vals_a = [pos_a[c] for c in common]
    vals_b = [pos_b[c] for c in common]

    tau, tau_p = kendalltau(vals_a, vals_b)
    rho, rho_p = spearmanr(vals_a, vals_b)

    top5_a = set(rank_a[:5])
    top5_b = set(rank_b[:5])
    bot5_a = set(rank_a[-5:])
    bot5_b = set(rank_b[-5:])

    # Cities that moved the most
    moves = [(c, abs(pos_a[c] - pos_b[c])) for c in common]
    moves.sort(key=lambda x: x[1], reverse=True)

    return {
        "kendall_tau": round(float(tau), 4),
        "kendall_p": round(float(tau_p), 6),
        "spearman_rho": round(float(rho), 4),
        "spearman_p": round(float(rho_p), 6),
        "top5_overlap": len(top5_a & top5_b),
        "top5_a": list(top5_a),
        "top5_b": list(top5_b),
        "bottom5_overlap": len(bot5_a & bot5_b),
        "biggest_movers": [{"city": c, "positions_moved": m} for c, m in moves[:5]],
        "num_cities": len(common),
    }


def compare_p24(map_a: dict[str, float], map_b: dict[str, float]) -> dict:
    """Compare p24 values between two snapshots."""
    common = sorted(set(map_a.keys()) & set(map_b.keys()))
    if not common:
        return {"error": "no common cities"}

    deltas = {c: round(map_b[c] - map_a[c], 4) for c in common}
    abs_deltas = [abs(d) for d in deltas.values()]

    return {
        "mean_abs_delta": round(float(np.mean(abs_deltas)), 4),
        "max_abs_delta": round(float(np.max(abs_deltas)), 4),
        "mean_delta": round(float(np.mean(list(deltas.values()))), 4),
        "max_increase_city": max(deltas, key=deltas.get),
        "max_increase": deltas[max(deltas, key=deltas.get)],
        "max_decrease_city": min(deltas, key=deltas.get),
        "max_decrease": deltas[min(deltas, key=deltas.get)],
        "per_city_deltas": dict(sorted(deltas.items(), key=lambda x: abs(x[1]), reverse=True)),
    }


def format_markdown(report: dict) -> str:
    """Format comparison report as markdown."""
    lines = []
    lines.append("# Model Iteration Comparison Report\n")

    meta = report["metadata"]
    lines.append(f"**Generated:** {meta.get('generated', 'N/A')}")
    lines.append(f"**Engine:** {meta['engine']}")
    lines.append(f"**Snapshots compared:** {meta['num_snapshots']}\n")

    for s in meta["snapshots"]:
        lines.append(f"- **{s['label']}** (`{s['commit']}`, {s['timestamp'][:10]})")
    lines.append("")

    # Summary table
    lines.append("## Rank Stability Summary\n")
    lines.append("| Profile | Kendall's τ | Spearman ρ | Top-5 Overlap | Biggest Mover |")
    lines.append("|---------|------------|------------|---------------|---------------|")

    for comp in report.get("comparisons", []):
        profile = comp["profile"]
        rank = comp.get("ranking", {})
        if "error" in rank:
            lines.append(f"| {profile} | — | — | — | {rank['error']} |")
            continue
        mover = rank["biggest_movers"][0] if rank["biggest_movers"] else {"city": "—", "positions_moved": 0}
        lines.append(
            f"| {profile} | {rank['kendall_tau']:.3f} | {rank['spearman_rho']:.3f} "
            f"| {rank['top5_overlap']}/5 | {mover['city']} ({mover['positions_moved']} pos) |"
        )
    lines.append("")

    # Probability deltas
    lines.append("## Probability Changes (p_transplant_24mo)\n")
    lines.append("| Profile | Mean |Δ| | Max |Δ| | Direction | Max ↑ City | Max ↓ City |")
    lines.append("|---------|---------|---------|-----------|------------|------------|")

    for comp in report.get("comparisons", []):
        p24 = comp.get("p24_comparison", {})
        if "error" in p24:
            continue
        direction = "↑" if p24["mean_delta"] > 0 else "↓" if p24["mean_delta"] < 0 else "→"
        lines.append(
            f"| {comp['profile']} | {p24['mean_abs_delta']:.4f} | {p24['max_abs_delta']:.4f} "
            f"| {direction} {abs(p24['mean_delta']):.4f} "
            f"| {p24['max_increase_city']} (+{p24['max_increase']:.3f}) "
            f"| {p24['max_decrease_city']} ({p24['max_decrease']:.3f}) |"
        )
    lines.append("")

    # Overall assessment
    taus = [c["ranking"]["kendall_tau"] for c in report.get("comparisons", [])
            if "ranking" in c and "error" not in c["ranking"]]
    if taus:
        avg_tau = np.mean(taus)
        lines.append("## Assessment\n")
        if avg_tau > 0.9:
            lines.append(f"Rankings are **highly stable** (avg τ = {avg_tau:.3f}). Model changes preserved city ordering.")
        elif avg_tau > 0.7:
            lines.append(f"Rankings are **moderately stable** (avg τ = {avg_tau:.3f}). Some meaningful reordering occurred.")
        elif avg_tau > 0.5:
            lines.append(f"Rankings show **moderate change** (avg τ = {avg_tau:.3f}). Model iteration shifted priorities.")
        else:
            lines.append(f"Rankings are **substantially different** (avg τ = {avg_tau:.3f}). Major model change detected.")

        abs_deltas = [c["p24_comparison"]["mean_abs_delta"] for c in report.get("comparisons", [])
                      if "p24_comparison" in c and "error" not in c["p24_comparison"]]
        if abs_deltas:
            avg_delta = np.mean(abs_deltas)
            lines.append(f"\nMean probability shift: **{avg_delta:.4f}** ({avg_delta*100:.2f} percentage points).")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare model iteration snapshots")
    parser.add_argument("snapshots", nargs="+", help="Snapshot JSON files (2+ required)")
    parser.add_argument("--engine", default="monte_carlo", help="Engine to compare (default: monte_carlo)")
    parser.add_argument("--markdown", action="store_true", help="Output as markdown")
    parser.add_argument("--output", default=None, help="Save report to file")
    args = parser.parse_args()

    if len(args.snapshots) < 2:
        print("Error: need at least 2 snapshots to compare", file=sys.stderr)
        sys.exit(1)

    snapshots = []
    for path in args.snapshots:
        snap = load_snapshot(path)
        snapshots.append(snap)

    # Compare the first and last snapshots (earliest vs latest)
    snap_a = snapshots[0]
    snap_b = snapshots[-1]

    label_a = snap_a["_meta"].get("label", "A")
    label_b = snap_b["_meta"].get("label", "B")
    engine = args.engine

    report = {
        "metadata": {
            "engine": engine,
            "num_snapshots": len(snapshots),
            "snapshots": [
                {
                    "label": s["_meta"].get("label", "?"),
                    "commit": s["_meta"]["git"]["commit"],
                    "timestamp": s["_meta"]["timestamp"],
                }
                for s in snapshots
            ],
        },
        "comparisons": [],
    }

    # Extract data from both snapshots
    rankings_a = extract_rankings(snap_a, engine)
    rankings_b = extract_rankings(snap_b, engine)
    p24_a = extract_p24_maps(snap_a, engine)
    p24_b = extract_p24_maps(snap_b, engine)

    # Compare each matching profile
    common_profiles = sorted(set(rankings_a.keys()) & set(rankings_b.keys()))
    if not common_profiles:
        print(f"Error: no common profiles with engine '{engine}' in both snapshots", file=sys.stderr)
        print(f"  Snapshot A engines: {snap_a['_meta'].get('engines_succeeded', [])}")
        print(f"  Snapshot B engines: {snap_b['_meta'].get('engines_succeeded', [])}")
        sys.exit(1)

    for profile_key in common_profiles:
        comparison = {
            "profile": profile_key,
            "ranking": compare_rankings(rankings_a[profile_key], rankings_b[profile_key]),
        }
        if profile_key in p24_a and profile_key in p24_b:
            comparison["p24_comparison"] = compare_p24(p24_a[profile_key], p24_b[profile_key])
        report["comparisons"].append(comparison)

    # Also compare across engines within the latest snapshot if multiple engines available
    all_engines = snap_b["_meta"].get("engines_succeeded", [])
    if len(all_engines) > 1:
        report["cross_engine"] = []
        for i, eng_a in enumerate(all_engines):
            for eng_b in all_engines[i + 1:]:
                p24_ea = extract_p24_maps(snap_b, eng_a)
                p24_eb = extract_p24_maps(snap_b, eng_b)
                common = sorted(set(p24_ea.keys()) & set(p24_eb.keys()))
                for profile_key in common:
                    rank_ea = extract_rankings(snap_b, eng_a).get(profile_key, [])
                    rank_eb = extract_rankings(snap_b, eng_b).get(profile_key, [])
                    if rank_ea and rank_eb:
                        report["cross_engine"].append({
                            "profile": profile_key,
                            "engine_a": eng_a,
                            "engine_b": eng_b,
                            "ranking": compare_rankings(rank_ea, rank_eb),
                            "p24_comparison": compare_p24(p24_ea[profile_key], p24_eb[profile_key]),
                        })

    if args.markdown:
        output = format_markdown(report)
    else:
        output = json.dumps(report, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report saved: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
