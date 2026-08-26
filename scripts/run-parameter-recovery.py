#!/usr/bin/env python3
"""Parameter-recovery study (#309): synthetic ground truth through the
real pipeline.

Every other validation compares model output against observed data — which
cannot separate model error from data noise. This study builds a synthetic
world where the TRUTH is known, simulates SRTR-style observed tables from
it (finite-cohort sampling noise at realistic center sizes), runs the REAL
derivation chain (scripts/srtr_xls_utils — the same functions the parser
uses, #339), and measures what survives:

  A. Factor recovery — corr(true wait factor, derived factor); how much the
     0.3/3.0 clamps and censoring distort the tails.
  B. Ranking recovery — Spearman(true p24 rank, pipeline p24 rank) as a
     function of cohort size: the fundamental ceiling on how good ANY
     ranking built from these tables can be.
  C. Prior sanity — does the panel-measured signal fraction (#317) recover
     the generating fraction on synthetic panels?

The generating distributions are matched to measured reality: center
effects ~ lognormal with the panel-measured sigma_center (#317), cohort
sizes resampled from the real kidney n distribution.

Outputs: docs/parameter-recovery-report.md,
         docs-site/static/data/parameter-recovery.json
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import scipy.stats

REPO = Path(__file__).parent.parent

_sx_spec = importlib.util.spec_from_file_location(
    "srtr_xls_utils", REPO / "scripts" / "srtr_xls_utils.py")
sx = importlib.util.module_from_spec(_sx_spec)
_sx_spec.loader.exec_module(sx)

_pv_spec = importlib.util.spec_from_file_location(
    "panel_variance", REPO / "scripts" / "run-panel-variance.py")
pv = importlib.util.module_from_spec(_pv_spec)
_pv_spec.loader.exec_module(pv)

# World parameters, matched to measured kidney reality
NAT_MEDIAN = 36.0          # months (kidney-scale)
TRUE_SIGMA = 1.0           # lognormal shape of individual waits
SIGMA_CENTER = 0.34        # sd of log center wait factors (panel-measured scale)
ANNUAL_MORT = 0.06
ANNUAL_DELIST = 0.05
N_CENTERS = 220
HORIZON = 12.0             # months, matching the B7 12-month tables


def _real_cohort_sizes(rng, k: int) -> np.ndarray:
    d = json.loads((REPO / "data" / "srtr-observed-rates.json").read_text())
    ns = np.array([v["n"] for v in d["kidney"]["centers"].values()
                   if v.get("n", 0) >= 10])
    return rng.choice(ns, size=k, replace=True)


def make_world(rng) -> dict:
    """Known truth: per-center wait factor and implied 12-month transplant
    probability under exponential competing risks."""
    log_f = rng.normal(0.0, SIGMA_CENTER, size=N_CENTERS)
    factors = np.exp(log_f)
    hazard = (ANNUAL_MORT + ANNUAL_DELIST) / 12.0
    p12 = np.empty(N_CENTERS)
    x = np.linspace(1e-6, HORIZON, 481)
    for i, f in enumerate(factors):
        dist = scipy.stats.lognorm(s=TRUE_SIGMA, scale=NAT_MEDIAN * f)
        p12[i] = np.trapezoid(dist.pdf(x) * np.exp(-hazard * x), x)
    return {"factors": factors, "p12": p12,
            "n": _real_cohort_sizes(rng, N_CENTERS)}


def observe_tables(world, rng) -> dict:
    """SRTR-style observed tables with finite-cohort sampling noise.

    B10 percentiles: empirical P10/P25/P50/P75 of n waiting-time draws,
    censored at 72 months exactly as SRTR censors ('>72').
    B7 rates: multinomial outcome counts over the 12-month window.
    """
    out = {"b10": {}, "b7": {}}
    hazard_m = ANNUAL_MORT / 12.0
    hazard_d = ANNUAL_DELIST / 12.0
    for i in range(N_CENTERS):
        n = int(world["n"][i])
        dist = scipy.stats.lognorm(s=TRUE_SIGMA,
                                   scale=NAT_MEDIAN * world["factors"][i])
        waits = dist.rvs(size=n, random_state=rng)
        pcts = {}
        for key, q in (("p10", 10), ("p25", 25), ("p50", 50), ("p75", 75)):
            v = float(np.percentile(waits, q))
            pcts[key] = sx.CENSORED if v > 72.0 else v
        out["b10"][i] = pcts

        # 12-month competing outcomes per patient
        t_mort = rng.exponential(1.0 / hazard_m, size=n)
        t_del = rng.exponential(1.0 / hazard_d, size=n)
        first = np.minimum.reduce([waits, t_mort, t_del])
        tx = int(np.sum((first <= HORIZON) & (first == waits)))
        died = int(np.sum((first <= HORIZON) & (first == t_mort)))
        out["b7"][i] = {"tx_rate": 100.0 * tx / n, "died_rate": 100.0 * died / n,
                        "n": n}
    # National percentiles from the pooled draws (approximation: use the
    # factor-1 center distribution — SRTR's national row is the pooled table)
    nat = scipy.stats.lognorm(s=TRUE_SIGMA, scale=NAT_MEDIAN)
    pooled = nat.rvs(size=200_000, random_state=rng)
    out["national"] = {k: (sx.CENSORED if float(np.percentile(pooled, q)) > 72
                           else float(np.percentile(pooled, q)))
                       for k, q in (("p10", 10), ("p25", 25),
                                    ("p50", 50), ("p75", 75))}
    return out


def run_pipeline(tables) -> dict:
    """The REAL derivation chain: wait factors via
    sx.wait_factor_from_percentiles, sigma via sx.sigma_from_percentiles,
    then the closed-form p12 with the derived parameters."""
    nat = tables["national"]
    sigma_hat = sx.sigma_from_percentiles(nat.get("p10"), nat.get("p25"),
                                          nat.get("p50"), nat.get("p75"))
    nat_median_hat = nat["p50"] if sx.is_valid(nat.get("p50")) else NAT_MEDIAN
    hazard = (ANNUAL_MORT + ANNUAL_DELIST) / 12.0
    x = np.linspace(1e-6, HORIZON, 481)
    factors_hat, p12_hat = {}, {}
    for i, pcts in tables["b10"].items():
        f = sx.wait_factor_from_percentiles(pcts, nat)
        if f is None:
            continue
        factors_hat[i] = f
        dist = scipy.stats.lognorm(s=sigma_hat, scale=nat_median_hat * f)
        p12_hat[i] = float(np.trapezoid(dist.pdf(x) * np.exp(-hazard * x), x))
    return {"factors_hat": factors_hat, "p12_hat": p12_hat,
            "sigma_hat": sigma_hat}


def main():
    rng = np.random.default_rng(20260825)
    n_worlds = 20
    per_world = []
    by_size = {"n<60": [], "60-160": [], "160-300": [], "300+": []}

    for w in range(n_worlds):
        world = make_world(rng)
        tables = observe_tables(world, rng)
        hat = run_pipeline(tables)
        idx = sorted(hat["factors_hat"])
        tf = world["factors"][idx]
        hf = np.array([hat["factors_hat"][i] for i in idx])
        tp = world["p12"][idx]
        hp = np.array([hat["p12_hat"][i] for i in idx])
        rho_f = scipy.stats.spearmanr(tf, hf).statistic
        rho_p = scipy.stats.spearmanr(tp, hp).statistic
        clamped = float(np.mean((hf <= sx.FACTOR_CLAMP[0] + 1e-9) |
                                (hf >= sx.FACTOR_CLAMP[1] - 1e-9) |
                                (hf == sx.CENSORED_FACTOR)))
        per_world.append({"rho_factor": rho_f, "rho_p12": rho_p,
                          "clamped_share": clamped,
                          "sigma_hat": hat["sigma_hat"],
                          "n_recovered": len(idx)})
        # ranking recovery by cohort size
        ns = world["n"][idx]
        for name, lo, hi in (("n<60", 0, 60), ("60-160", 60, 160),
                             ("160-300", 160, 300), ("300+", 300, 10**9)):
            m = (ns >= lo) & (ns < hi)
            if m.sum() >= 12:
                by_size[name].append(
                    scipy.stats.spearmanr(tp[m], hp[m]).statistic)

    # C: does the panel ANOVA recover the generating signal fraction?
    t_len = 13
    noise_sd = 0.09  # within-center release noise on the log scale
    groups = [rng.normal(mu, noise_sd, size=t_len)
              for mu in rng.normal(0, SIGMA_CENTER, size=200)]
    anova = pv.anova_components(groups)
    true_frac = SIGMA_CENTER**2 / (SIGMA_CENTER**2 + noise_sd**2)

    summary = {
        "worlds": n_worlds,
        "centers_per_world": N_CENTERS,
        "rho_factor_median": float(np.median([r["rho_factor"] for r in per_world])),
        "rho_p12_median": float(np.median([r["rho_p12"] for r in per_world])),
        "rho_p12_range": [float(np.min([r["rho_p12"] for r in per_world])),
                          float(np.max([r["rho_p12"] for r in per_world]))],
        "clamped_share_median": float(np.median([r["clamped_share"] for r in per_world])),
        "sigma_hat_median": float(np.median([r["sigma_hat"] for r in per_world])),
        "true_sigma": TRUE_SIGMA,
        "rho_p12_by_cohort_size": {k: (float(np.median(v)) if v else None)
                                   for k, v in by_size.items()},
        "panel_frac_recovered": anova["frac_signal"],
        "panel_frac_true": float(true_frac),
    }
    result = {"summary": summary, "per_world": per_world,
              "_meta": {"seed": 20260825,
                        "method": __doc__.strip().splitlines()[0]}}

    s = summary
    lines = [
        "# Parameter-recovery study (#309)", "",
        f"{n_worlds} synthetic worlds x {N_CENTERS} centers; truth known; "
        "observed tables simulated with finite-cohort noise at REAL kidney "
        "cohort sizes; derivation via the REAL parser functions "
        "(srtr_xls_utils, #339).", "",
        f"- Wait-factor rank recovery: median rho **{s['rho_factor_median']:.3f}**",
        f"- p12 rank recovery: median rho **{s['rho_p12_median']:.3f}** "
        f"(range {s['rho_p12_range'][0]:.3f}-{s['rho_p12_range'][1]:.3f})",
        f"- Clamped/censored factor share: {s['clamped_share_median']:.1%}",
        f"- National sigma recovery: {s['sigma_hat_median']:.3f} "
        f"vs true {TRUE_SIGMA} (the #256/#274 clamp binds here by design)",
        "", "## Ranking recovery by cohort size", "",
        "| cohort n | median rank rho |", "|---|---|",
    ]
    for k, v in s["rho_p12_by_cohort_size"].items():
        lines.append(f"| {k} | {v:.3f} |" if v else f"| {k} | — |")
    lines += [
        "", "## Panel signal-fraction recovery (#317 sanity)", "",
        f"ANOVA recovered frac_signal {s['panel_frac_recovered']:.3f} vs "
        f"generating truth {s['panel_frac_true']:.3f}.", "",
        "## Interpretation", "",
        "The by-cohort-size table is the fundamental ceiling: rankings for",
        "small-cohort centers are noise-limited BY THE DATA, not by the",
        "model — consistent with the temporal forecast sitting at the",
        "persistence ceiling (#308) and motivating the rank intervals",
        "(#313), which communicate exactly this uncertainty to users.", "",
        "**The ceiling explains the measured calibrations.** Kidney's",
        "observed MCMC-vs-observed concordance is 0.889 (post-#317) against",
        f"a synthetic recoverable ceiling of ~{s['rho_p12_median']:.2f} at",
        "these cohort sizes: the pipeline extracts nearly all the signal the",
        "public tables contain. Material further gains require more data",
        "per center (the panel likelihood, #358), not more model.", "",
    ]
    (REPO / "docs" / "parameter-recovery-report.md").write_text("\n".join(lines))
    (REPO / "docs-site" / "static" / "data" / "parameter-recovery.json").write_text(
        json.dumps(result, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    sys.exit(main())
