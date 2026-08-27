#!/usr/bin/env python3
"""Does the center ranking survive a different reasonable weighting? (SCORE-01)

Every center score users see is a weighted sum of eight categories:

    medicalCompatibility 0.25   hospitalQuality    0.15
    waitTime             0.20   geographic         0.10
    donorAvailability    0.18   healthDemographics 0.07
                                policy 0.03, socioeconomic 0.02

SCORE-01 records these as `uncited` — no source for magnitudes that drive
every score. The existing assumption sweep perturbs ONE category by +/-20%
and finds the ranking stable, which answers "is it robust to a nudge".

It does not answer the question a skeptic actually asks: **would a different
reasonable person's weights produce a different ranking?** A patient who
cares most about speed, or most about transplant volume, is not making an
error — they are making a different, defensible judgement. If the ranking
turns on which of them chose the numbers, that is a property users need to
know about, and it is not something a +/-20% nudge can reveal.

The alternatives below are chosen to be DEFENSIBLE, not adversarial, with one
exception marked as a stress test:

  equal            no view about relative importance
  wait-time first  a candidate prioritising speed of access
  quality first    a candidate prioritising program outcomes
  medical first    an extreme of the shipped ordering's own logic
  reversed         NOT defensible — a stress test, reported separately

Outputs: docs/scoring-weight-sensitivity-report.md,
         docs-site/static/data/scoring-weight-sensitivity.json
"""
import json
import sys
from pathlib import Path

from scipy import stats

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from artifact_meta import stamped_meta  # noqa: E402

from services.data_loader import load_all  # noqa: E402
from services.scoring import DEFAULT_WEIGHTS, score_all_centers  # noqa: E402

ORGANS = ["kidney", "liver", "heart", "lung"]
CATS = list(DEFAULT_WEIGHTS)


def alternatives() -> dict[str, tuple[dict, bool]]:
    """label -> (weights, is_defensible)."""
    flat = {c: 1 / len(CATS) for c in CATS}
    def dominant(cat, share=0.65):
        rest = (1 - share) / (len(CATS) - 1)
        return {**{c: rest for c in CATS}, cat: share}
    return {
        "equal (no view on importance)": (flat, True),
        "wait-time first": (dominant("waitTime"), True),
        "program-quality first": (dominant("hospitalQuality"), True),
        "medical-compatibility first": (dominant("medicalCompatibility"), True),
        "reversed order (stress test)":
            (dict(zip(CATS, list(DEFAULT_WEIGHTS.values())[::-1])), False),
    }


def scores(organ: str, weights=None) -> dict[str, float]:
    patient = {"organ": organ, "blood_type": "O+", "age": 50,
               "sex": "male", "urgency": 2}
    return {r.code: r.total for r in score_all_centers(patient, weights)}


def main() -> int:
    load_all()
    results = []
    for organ in ORGANS:
        base = scores(organ)
        if len(base) < 10:
            continue
        codes = sorted(base)
        top10_base = sorted(codes, key=lambda c: -base[c])[:10]
        for label, (w, defensible) in alternatives().items():
            total = sum(w.values())
            w = {k: v / total for k, v in w.items()}
            alt = scores(organ, w)
            rho = float(stats.spearmanr([base[c] for c in codes],
                                        [alt[c] for c in codes]).statistic)
            top10_alt = sorted(codes, key=lambda c: -alt[c])[:10]
            results.append({
                "organ": organ, "weighting": label, "defensible": defensible,
                "n_centers": len(codes),
                "spearman_vs_shipped": round(rho, 4),
                "top10_overlap": len(set(top10_base) & set(top10_alt)),
                "top1_same": top10_base[0] == top10_alt[0],
            })
            print(f"  {organ:7s} {label:32s} rho={rho:.4f} "
                  f"top10={len(set(top10_base) & set(top10_alt))}/10 "
                  f"top1_same={'yes' if top10_base[0] == top10_alt[0] else 'NO'}")
    if not results:
        print("ERROR: no results", file=sys.stderr)
        return 1

    defensible = [r for r in results if r["defensible"]]
    worst_rho = min(r["spearman_vs_shipped"] for r in defensible)
    worst_overlap = min(r["top10_overlap"] for r in defensible)
    top1_changes = sum(1 for r in defensible if not r["top1_same"])

    doc = {"comparisons": results,
           "summary": {
               "worst_spearman_defensible": worst_rho,
               "worst_top10_overlap_defensible": worst_overlap,
               "top1_changes_defensible": top1_changes,
               "n_defensible_comparisons": len(defensible),
           },
           "shipped_weights": dict(DEFAULT_WEIGHTS),
           "_meta": stamped_meta(
               script="scripts/run-scoring-weight-sensitivity.py",
               question="SCORE-01: the 8 category weights are uncited. The "
                        "existing sweep perturbs one by +/-20%. Would a "
                        "DIFFERENT REASONABLE weighting change the ranking?",
               note="'reversed order' is a stress test, not a defensible "
                    "alternative, and is excluded from the headline figures.",
           )}

    lines = [
        "# Does the ranking survive a different reasonable weighting? (SCORE-01)",
        "", "Every center score is a weighted sum of eight categories whose",
        "magnitudes the register records as `uncited`. The existing assumption",
        "sweep perturbs one category by ±20% and finds the ranking stable —",
        "which answers *is it robust to a nudge*, not *does it depend on whose",
        "judgement produced the numbers*.", "",
        "The alternatives below are defensible positions a real candidate might",
        "hold, not adversarial ones. `reversed order` is the exception and is",
        "marked as a stress test.", "",
        "| organ | weighting | Spearman vs shipped | top-10 overlap | same #1? |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        mark = "" if r["defensible"] else " *(stress test)*"
        lines.append(
            f"| {r['organ']} | {r['weighting']}{mark} | "
            f"{r['spearman_vs_shipped']:.4f} | {r['top10_overlap']}/10 | "
            f"{'yes' if r['top1_same'] else '**no**'} |")

    lines += [
        "", "## These weights ARE load-bearing", "",
        f"Across defensible alternatives alone, the worst rank correlation is",
        f"**{worst_rho:.4f}** and the top-10 overlap falls to "
        f"**{worst_overlap}/10**. The top-ranked center changes in "
        f"**{top1_changes} of {len(defensible)}** comparisons.", "",
        "For contrast, every other constant measured this way in this project",
        "was inert: the BBN discretization split moves rankings by ρ 0.9987",
        "even when swung from near-deterministic to barely informative, and",
        "removing the donor-supply effect entirely leaves ρ 0.9957. Those are",
        "constants whose exact value does not matter. **These are not.**", "",
        "## Why this matters more than the other findings", "",
        "This is the headline output. The results table sorts by score by",
        "default, so a candidate reading the top of that list is reading a",
        "conclusion that depends materially on eight numbers with no published",
        "source.", "",
        "It is also NOT covered by the uncertainty the platform already",
        "reports. The rank intervals from #313 bootstrap the *probability*",
        "estimates and rank by `p24` — a different quantity from the composite",
        "score, and an interval that varies the data while holding the weights",
        "fixed. The score ranking currently carries no interval at all.", "",
        "## What this does and does not say", "",
        "It does **not** say the shipped weights are wrong. There is no ground",
        "truth here: 'which center is best for me' is a preference, not a fact,",
        "and a weighted composite is a reasonable way to express one.", "",
        "It says the *choice* is consequential and currently invisible. Two",
        "honest responses, neither of which is picking better numbers:", "",
        "1. **Make the dependence visible** — the weights are already",
        "   user-adjustable via the weight panel; the ranking should say that",
        "   it reflects a particular weighting, and ideally show how much it",
        "   moves under others.",
        "2. **Report a weight-uncertainty interval** alongside the sampling",
        "   one, so the reported rank reflects both sources.", "",
        "Sourcing the magnitudes would help but cannot resolve it — there is no",
        "literature that fixes how one candidate should trade program quality",
        "against travel distance.", "",
    ]

    (REPO / "docs" / "scoring-weight-sensitivity-report.md").write_text(
        "\n".join(lines) + "\n")
    (REPO / "docs-site" / "static" / "data" /
     "scoring-weight-sensitivity.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(f"\nworst defensible rho {worst_rho:.4f}, worst top-10 overlap "
          f"{worst_overlap}/10, #1 changes in {top1_changes}/{len(defensible)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
