#!/usr/bin/env python3
"""How much does the ranking depend on the weight MAGNITUDES? (L-082 remedy 2)

#386 shipped the first half of L-082's remedy: the results table now shows
each center's rank span across the app's four presets. That is honest but it
is a lower bound, not an interval — four points chosen by the same authors as
the shipped weights.

The remaining question is what a weight-uncertainty interval should even be,
because any sampling neighbourhood needs a spread parameter, and inventing one
just relocates the uncited constant. This script avoids that entirely by
separating two different claims inside `DEFAULT_WEIGHTS`:

    medicalCompatibility .25 > waitTime .20 > donorAvailability .18 >
    hospitalQuality .15 > geographic .10 > healthDemographics .07 >
    policy .03 > socioeconomic .02

The ORDERING is defensible and checkable — a reader can agree or disagree that
medical compatibility should outrank travel. The MAGNITUDES are what the
register marks uncited: nothing fixes .25 rather than .30, or .07 rather
than .05.

So: keep the ordering, admit total ignorance of the magnitudes, and measure
what the ranking does. The set of weight vectors consistent with that state of
knowledge is the ordered simplex

    W = { w : w_1 >= w_2 >= ... >= w_8 >= 0,  sum w = 1 }

and the uniform distribution on W is sampled EXACTLY by drawing a uniform
point on the simplex (Dirichlet with all-ones concentration) and sorting it
descending. No tuning constant, no prior to argue about, no arbitrary radius.
This is the standard ordinal-weight ("rank-order") robustness setting in
multi-criteria decision analysis.

Two reference points are reported alongside:

  * the SHIPPED weights, and
  * the rank-order centroid (ROC), w_i = (1/n) * sum_{j=i..n} 1/j, which is
    the centroid of W and hence the canonical point estimate when only the
    ordering is known.

If the shipped ranking sits near the middle of the sampled distribution and
close to ROC, the shipped magnitudes are unremarkable for their ordering, and
the ordering is doing the work. If it is an outlier, the specific magnitudes
are, and that is a much stronger version of L-082 than currently documented.

Usage:
    python scripts/run-ordinal-weight-robustness.py [--samples N] [--seed S]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from artifact_meta import stamped_meta  # noqa: E402
from reference_patients import ORGANS, reference_patient_kwargs  # noqa: E402
from services.data_loader import load_all  # noqa: E402
from services.scoring import DEFAULT_WEIGHTS, score_all_centers  # noqa: E402

CATEGORIES = list(DEFAULT_WEIGHTS)


def _assert_ordering_holds() -> None:
    """The whole method rests on the shipped weights being ordered.

    If someone reorders DEFAULT_WEIGHTS, sampling the ordered simplex no
    longer describes 'the shipped ordering with unknown magnitudes' and every
    number below silently means something else. Fail loudly instead.
    """
    values = [DEFAULT_WEIGHTS[c] for c in CATEGORIES]
    if values != sorted(values, reverse=True):
        raise SystemExit(
            "DEFAULT_WEIGHTS is no longer in descending order: "
            f"{DEFAULT_WEIGHTS}. This script assumes the ordering is the "
            "defensible content and the magnitudes are not; rewrite it "
            "before trusting any output."
        )


def roc_weights() -> dict[str, float]:
    """Rank-order centroid — the centroid of the ordered simplex."""
    n = len(CATEGORIES)
    w = [sum(1.0 / j for j in range(i, n + 1)) / n for i in range(1, n + 1)]
    return dict(zip(CATEGORIES, w))


def sample_ordered_simplex(rng: np.random.Generator, n_samples: int) -> np.ndarray:
    """Uniform draws from {w_1 >= ... >= w_k >= 0, sum w = 1}.

    A Dirichlet(1,...,1) draw is uniform on the simplex; sorting each draw
    descending maps it into the ordered region, and because sorting sends
    equal-volume pieces of the simplex onto that region exactly once, the
    result is uniform there.
    """
    draws = rng.dirichlet(np.ones(len(CATEGORIES)), size=n_samples)
    return -np.sort(-draws, axis=1)


def _ranked_codes(patient: dict, weights: dict[str, float]) -> list[str]:
    rows = sorted(score_all_centers(patient, weights), key=lambda r: -r.total)
    return [r.code for r in rows]


def _ranks(codes: list[str]) -> dict[str, int]:
    return {code: i for i, code in enumerate(codes, 1)}


def _spearman(a: list[float], b: list[float]) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def analyze(organ: str, n_samples: int, rng: np.random.Generator) -> dict:
    patient = reference_patient_kwargs(organ)

    shipped_codes = _ranked_codes(patient, DEFAULT_WEIGHTS)
    shipped = _ranks(shipped_codes)
    order = shipped_codes  # canonical center order for vectorised comparison
    shipped_vec = [shipped[c] for c in order]

    roc = roc_weights()
    roc_ranks = _ranks(_ranked_codes(patient, roc))
    roc_vec = [roc_ranks[c] for c in order]

    samples = sample_ordered_simplex(rng, n_samples)
    rank_matrix = np.empty((n_samples, len(order)), dtype=np.int32)
    rhos = []
    top_center_counts: dict[str, int] = {}

    for i, row in enumerate(samples):
        weights = dict(zip(CATEGORIES, row.tolist()))
        codes = _ranked_codes(patient, weights)
        r = _ranks(codes)
        vec = [r[c] for c in order]
        rank_matrix[i] = vec
        rhos.append(_spearman(shipped_vec, vec))
        top_center_counts[codes[0]] = top_center_counts.get(codes[0], 0) + 1

    lo = np.percentile(rank_matrix, 5, axis=0)
    hi = np.percentile(rank_matrix, 95, axis=0)
    width = hi - lo

    shipped_top = shipped_codes[0]
    top_share = top_center_counts.get(shipped_top, 0) / n_samples

    # Where does the shipped ranking sit inside the sampled cloud? If the
    # magnitudes were unremarkable, its rho against the samples should look
    # like a sample's rho against the samples.
    return {
        "organ": organ,
        "n_centers": len(order),
        "n_samples": n_samples,
        "shipped_top_center": shipped_top,
        "shipped_top_center_share": round(top_share, 4),
        "distinct_top_centers": len(top_center_counts),
        "rho_vs_shipped_min": round(float(np.min(rhos)), 4),
        "rho_vs_shipped_median": round(float(np.median(rhos)), 4),
        "roc_rho_vs_shipped": round(_spearman(shipped_vec, roc_vec), 4),
        "roc_top_center": _ranked_codes(patient, roc)[0],
        "median_90pct_rank_width": float(np.median(width)),
        "max_90pct_rank_width": float(np.max(width)),
        "top10_median_90pct_width": float(np.median(width[:10])),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20260826)
    ap.add_argument("--organs", nargs="*", default=ORGANS)
    args = ap.parse_args()

    _assert_ordering_holds()
    load_all()
    rng = np.random.default_rng(args.seed)

    results = [analyze(organ, args.samples, rng) for organ in args.organs]

    out = REPO / "docs-site" / "static" / "data" / "ordinal-weight-robustness.json"
    payload = {
        "organs": {r["organ"]: r for r in results},
        "_meta": stamped_meta(
            script="scripts/run-ordinal-weight-robustness.py",
            seed=args.seed,
            samples=args.samples,
            method=(
                "uniform on the ordered simplex w1>=...>=w8, sum=1 "
                "(Dirichlet(1,...,1) sorted descending); no spread parameter"
            ),
        ),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")

    hdr = f"{'organ':<10} {'top stable':>11} {'rho min':>8} {'rho med':>8} {'ROC rho':>8} {'med 90% width':>14} {'top10 width':>12}"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        print(f"{r['organ']:<10} {r['shipped_top_center_share']:>11.2f} "
              f"{r['rho_vs_shipped_min']:>8.4f} {r['rho_vs_shipped_median']:>8.4f} "
              f"{r['roc_rho_vs_shipped']:>8.4f} "
              f"{r['median_90pct_rank_width']:>14.1f} {r['top10_median_90pct_width']:>12.1f}")
    print(f"\nwrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
