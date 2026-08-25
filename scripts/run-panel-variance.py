#!/usr/bin/env python3
"""Panel variance decomposition for the MCMC signal fraction (#317, MCMC-09).

The hierarchical MCMC model has one aggregate observation per center, so the
split of cross-center spread into real signal vs measurement noise is
unidentified and currently prior-driven: frac_signal ~ Beta(2,2), mean 0.5
(register MCMC-34). But the SRTR archive gives ~13 REPLICATE observations
per center (one per release), which identifies the split empirically.

Method: per organ, log wait factor log(center_median / national_median) per
(center, release). One-way random-effects ANOVA (unbalanced,
method-of-moments) decomposes variance into between-center (signal) and
within-center (noise) components:

    frac_signal = sigma_center^2 / (sigma_center^2 + sigma_within^2)

Honest caveat: within-center variation across releases includes REAL
temporal drift (the #288 trends), not just measurement noise — so the raw
frac_signal is a LOWER bound on the true signal share. A per-center linear
detrend removes drift and gives the complementary (upper-ish) estimate;
both are reported, and the recommended prior is centered between them.

Bootstrap (resampling centers) gives a CI on each estimate.

Outputs:
  docs/panel-variance-report.md
  docs-site/static/data/panel-variance.json
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
TRENDS = REPO / "data" / "srtr-trends-centers.json"

ORGANS = ["kidney", "liver", "heart", "lung", "pancreas", "intestine"]
MIN_OBS_PER_CENTER = 8
MIN_CENTERS = 15


METRICS = {
    # metric key in srtr-trends-centers.json -> transform
    # wait medians: log ratio to the per-release national median
    # rates: log1p ratio (zeros are common and meaningful)
    "median_wait_months": "log_ratio",
    "mortality_rate": "log1p_ratio",
    "delisting_rate": "log1p_ratio",
}


def build_panel(centers: dict, organ: str,
                metric: str = "median_wait_months") -> dict[str, np.ndarray]:
    """center -> vector of transformed factors (aligned per release-year)."""
    transform = METRICS[metric]
    by_year: dict[float, dict[str, float]] = {}
    for code, organs in centers.items():
        s = organs.get(organ)
        if not s:
            continue
        for yr, val in zip(s.get("years", []), s.get(metric, [])):
            if val is not None and (val > 0 or transform == "log1p_ratio"):
                by_year.setdefault(yr, {})[code] = float(val)

    nat = {yr: np.median(list(vals.values())) for yr, vals in by_year.items()
           if len(vals) >= MIN_CENTERS}

    panel: dict[str, list[float]] = {}
    for yr, vals in by_year.items():
        ref = nat.get(yr)
        if ref is None:
            continue
        for code, val in vals.items():
            if transform == "log_ratio":
                if ref <= 0:
                    continue
                panel.setdefault(code, []).append(np.log(val / ref))
            else:
                panel.setdefault(code, []).append(np.log1p(val) - np.log1p(ref))
    return {c: np.array(v) for c, v in panel.items()
            if len(v) >= MIN_OBS_PER_CENTER}


def anova_components(groups: list[np.ndarray]) -> dict:
    """Unbalanced one-way random-effects ANOVA (method of moments)."""
    k = len(groups)
    ns = np.array([len(g) for g in groups], dtype=float)
    N = ns.sum()
    grand = np.concatenate(groups).mean()
    means = np.array([g.mean() for g in groups])

    ss_within = sum(((g - m) ** 2).sum() for g, m in zip(groups, means))
    ss_between = (ns * (means - grand) ** 2).sum()
    ms_within = ss_within / (N - k)
    ms_between = ss_between / (k - 1)
    n0 = (N - (ns ** 2).sum() / N) / (k - 1)  # unbalanced correction

    sigma2_within = ms_within
    sigma2_between = max(0.0, (ms_between - ms_within) / n0)
    total = sigma2_between + sigma2_within
    return {
        "sigma_center": float(np.sqrt(sigma2_between)),
        "sigma_within": float(np.sqrt(sigma2_within)),
        "frac_signal": float(sigma2_between / total) if total > 0 else 0.0,
        "n_centers": int(k),
        "n_obs": int(N),
    }


def detrend(groups: list[np.ndarray]) -> list[np.ndarray]:
    """Remove each center's linear release trend (keeps the center mean)."""
    out = []
    for g in groups:
        x = np.arange(len(g), dtype=float)
        coef = np.polyfit(x, g, 1)
        resid = g - np.polyval(coef, x)
        out.append(resid + g.mean())
    return out


def bootstrap_frac(groups: list[np.ndarray], n_boot: int = 2000,
                   seed: int = 42, detrended: bool = False) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    fracs = []
    src = detrend(groups) if detrended else groups
    for _ in range(n_boot):
        idx = rng.integers(0, len(src), size=len(src))
        fracs.append(anova_components([src[i] for i in idx])["frac_signal"])
    return float(np.percentile(fracs, 2.5)), float(np.percentile(fracs, 97.5))


def main():
    centers = json.loads(TRENDS.read_text())["centers"]
    result = {"organs": {}, "_meta": {
        "method": "Unbalanced one-way random-effects ANOVA on log wait factors "
                  "(center x release panel from srtr-trends-centers.json); "
                  "raw = lower bound on signal (within includes real drift); "
                  "detrended = per-center linear drift removed.",
    }}
    lines = ["# Panel variance decomposition (#317 / MCMC-09)", "",
             "How much of the cross-center wait-factor spread is real center",
             "signal vs release-to-release noise? The single-release MCMC model",
             "cannot identify this (frac_signal ~ Beta(2,2), mean 0.5, MCMC-34);",
             "the release panel can.", "",
             "| organ/metric | centers | obs | frac raw [95% CI] | frac detrended [95% CI] | prior mean |",
             "|---|---|---|---|---|---|"]

    for organ in ORGANS:
        result["organs"][organ] = {}
        for metric in METRICS:
            panel = build_panel(centers, organ, metric)
            key = metric.replace("median_wait_months", "wait")\
                        .replace("mortality_rate", "mort")\
                        .replace("delisting_rate", "delist")
            if len(panel) < MIN_CENTERS:
                lines.append(f"| {organ}/{key} | {len(panel)} | — | insufficient panel | — | 0.5 |")
                result["organs"][organ][key] = {"insufficient": True,
                                                "n_centers": len(panel)}
                continue
            groups = list(panel.values())
            raw = anova_components(groups)
            det = anova_components(detrend(groups))
            raw_ci = bootstrap_frac(groups, detrended=False)
            det_ci = bootstrap_frac(groups, detrended=True)
            result["organs"][organ][key] = {
                "raw": raw, "raw_ci_95": raw_ci,
                "detrended": det, "detrended_ci_95": det_ci,
            }
            lines.append(
                f"| {organ}/{key} | {raw['n_centers']} | {raw['n_obs']} "
                f"| {raw['frac_signal']:.3f} [{raw_ci[0]:.3f}, {raw_ci[1]:.3f}] "
                f"| {det['frac_signal']:.3f} [{det_ci[0]:.3f}, {det_ci[1]:.3f}] | 0.5 |")
            print(f"{organ}/{key}: raw {raw['frac_signal']:.3f} "
                  f"[{raw_ci[0]:.3f},{raw_ci[1]:.3f}] det {det['frac_signal']:.3f}")

    lines += ["",
              "## Interpretation", "",
              "- **raw** treats all within-center variation as noise — but part",
              "  of it is real temporal drift, so raw UNDERSTATES the signal.",
              "- **detrended** removes each center's linear drift first, so it",
              "  attributes drift to signal-adjacent structure; closer to the",
              "  quantity the single-release model needs.",
              "- Where both bounds sit far from 0.5, the Beta(2,2) prior",
              "  (MCMC-34) is measurably miscentered and should be replaced by",
              "  an informative prior matched to these estimates (#317 next",
              "  step: refit traces with the empirical priors).", ""]

    (REPO / "docs" / "panel-variance-report.md").write_text("\n".join(lines))
    out = REPO / "docs-site" / "static" / "data" / "panel-variance.json"
    out.write_text(json.dumps(result, indent=1))
    print(f"Wrote report + {out}")


if __name__ == "__main__":
    sys.exit(main())
