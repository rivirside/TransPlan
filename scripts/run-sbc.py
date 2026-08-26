#!/usr/bin/env python3
"""Simulation-based calibration for the MCMC model (#310).

The standard modern check for a Bayesian pipeline: draw parameters AND
synthetic observed data jointly from the model's own prior predictive,
refit the posterior on the synthetic data, and record where the true
parameter ranks within the posterior draws. Across replications the ranks
must be uniform; systematic clustering exposes a miscalibrated
prior/likelihood/sampler combination that R-hat and ESS cannot see.

Runs on the kidney state-granularity design (the real center structure)
with the quick-fit sampler config from the test suite. Focus parameters:
log_median_national, sigma_total_wait, frac_signal_wait, log_mort_national.

Usage: run from repo root; takes ~20-40 minutes for the default 24
replications (sequential quick fits).

Outputs: docs/sbc-report.md, docs-site/static/data/sbc.json
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "backend"))

import pymc as pm  # noqa: E402

from services.data_loader import load_all  # noqa: E402
from services.mcmc_survival import build_organ_model, load_organ_data  # noqa: E402

PARAMS = ["log_median_national", "sigma_total_wait", "frac_signal_wait",
          "log_mort_national"]
N_REPS = 24
DRAWS, TUNE, CHAINS = 150, 100, 1
SEED0 = 20260826

OBS_MAP = {  # observed RV name -> data key fed to build_organ_model
    "obs_city_wait": "city_wait_factors",
    "obs_city_mort": "city_mort_factors",
    "obs_city_delist": "city_delist_factors",
    "obs_bt": "bt_mults",
    "obs_urg": "urg_mults",
}


def main():
    load_all()
    base = load_organ_data("kidney", granularity="state")

    ranks = {p: [] for p in PARAMS}
    for rep in range(N_REPS):
        seed = SEED0 + rep
        # 1) Joint draw (theta, y) from the prior predictive
        with build_organ_model(base):
            prior = pm.sample_prior_predictive(draws=1, random_seed=seed)
        theta = {p: float(prior.prior[p].values.flatten()[0]) for p in PARAMS}

        # 2) Rebuild the model with the SYNTHETIC observations (exp: the
        # model logs its inputs, prior predictive emits the logged values)
        synth = dict(base)
        for rv, key in OBS_MAP.items():
            y = np.asarray(prior.prior_predictive[rv].values)
            synth[key] = np.exp(y.reshape(-1))

        # 3) Refit and rank the truth within the posterior
        with build_organ_model(synth):
            idata = pm.sample(draws=DRAWS, tune=TUNE, chains=CHAINS,
                              random_seed=seed, progressbar=False,
                              target_accept=0.9)
        for p in PARAMS:
            post = idata.posterior[p].values.flatten()
            ranks[p].append(int(np.sum(post < theta[p])))
        print(f"rep {rep+1}/{N_REPS}: " +
              ", ".join(f"{p}={ranks[p][-1]}" for p in PARAMS))

    L = DRAWS * CHAINS
    result = {"n_reps": N_REPS, "posterior_draws": L, "ranks": ranks,
              "_meta": {"design": "kidney/state, quick-fit "
                        f"({DRAWS}d/{TUNE}t/{CHAINS}c), seed base {SEED0}"}}
    lines = ["# Simulation-based calibration (#310)", "",
             f"{N_REPS} replications on the kidney state design; rank of the",
             f"true parameter within {L} posterior draws must be uniform.", "",
             "| parameter | KS p (uniformity) | mean rank/L | verdict |",
             "|---|---|---|---|"]
    from scipy.stats import kstest
    summary = {}
    for p in PARAMS:
        u = (np.array(ranks[p]) + 0.5) / (L + 1)
        ks = kstest(u, "uniform")
        verdict = ("consistent with calibrated" if ks.pvalue > 0.05
                   else "MISCALIBRATED — investigate")
        summary[p] = {"ks_p": round(float(ks.pvalue), 4),
                      "mean_u": round(float(u.mean()), 3),
                      "verdict": verdict}
        lines.append(f"| {p} | {ks.pvalue:.3f} | {u.mean():.3f} | {verdict} |")
        print(f"{p}: KS p={ks.pvalue:.3f} mean u={u.mean():.3f} -> {verdict}")
    result["summary"] = summary
    lines += ["", f"Caveat: {N_REPS} replications give modest power — this",
              "detects gross miscalibration, not subtle tail issues. The",
              "quick-fit sampler config trades some fidelity for runtime;",
              "a full-config SBC is the heavyweight follow-up.", ""]
    (REPO / "docs" / "sbc-report.md").write_text("\n".join(lines))
    (REPO / "docs-site" / "static" / "data" / "sbc.json").write_text(
        json.dumps(result, indent=1))
    print("Wrote report + JSON")


if __name__ == "__main__":
    sys.exit(main())
