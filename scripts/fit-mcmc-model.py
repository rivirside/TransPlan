#!/usr/bin/env python3
"""
Offline MCMC model fitting script — Phase 5 M3.

Fits a PyMC hierarchical survival model for one or all organs and saves
the posterior trace to data/mcmc-traces/{organ}.nc.

Usage:
    # Fit a single organ (quick test)
    python scripts/fit-mcmc-model.py --organ kidney --samples 500 --chains 2

    # Fit all 6 organs (production)
    python scripts/fit-mcmc-model.py --all --samples 2000 --chains 4

    # Quick smoke test (50 draws, 1 chain)
    python scripts/fit-mcmc-model.py --organ kidney --quick

Typical runtimes (M1 Mac):
    --quick:  ~5s per organ
    Default:  ~2-5 min per organ
    --all:    ~15-30 min total
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add backend/ to path so we can import services
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import arviz as az

from services.mcmc_survival import (
    ORGANS,
    fit_organ_model,
    load_organ_data,
    save_trace,
    trace_path,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("fit-mcmc")


def fit_and_save(
    organ: str,
    n_samples: int,
    n_chains: int,
    n_tune: int,
    target_accept: float,
    strict: bool = False,
    granularity: str = "classic",
) -> None:
    """Fit model for one organ and save the trace."""
    logger.info("=" * 60)
    logger.info("Fitting %s (%s): %d samples × %d chains, %d tune", organ, granularity, n_samples, n_chains, n_tune)
    logger.info("=" * 60)

    t0 = time.perf_counter()

    # Load data for diagnostics
    data = load_organ_data(organ, granularity=granularity)
    logger.info(
        "Data: %d cities, national_median=%.1f, mort_rate=%.4f, delist_rate=%.4f",
        data["n_cities"], data["national_median"],
        data["national_mort_rate"], data["national_delist_rate"],
    )

    # Fit the model
    trace = fit_organ_model(
        organ=organ,
        n_samples=n_samples,
        n_chains=n_chains,
        n_tune=n_tune,
        target_accept=target_accept,
        granularity=granularity,
    )

    # Save trace
    path = save_trace(organ, trace, granularity=granularity)
    elapsed = time.perf_counter() - t0

    # Print diagnostics
    logger.info("Trace saved to %s (%.1f MB)", path, path.stat().st_size / 1e6)
    logger.info("Total time: %.1fs", elapsed)

    # Check convergence
    summary = az.summary(
        trace,
        var_names=["log_median_national", "log_sigma", "log_mort_national",
                    "sigma_city_wait", "sigma_city_mort"],
    )
    logger.info("Convergence diagnostics:\n%s", summary.to_string())

    # Check R-hat
    rhats = summary["r_hat"].values
    max_rhat = float(max(rhats))
    if max_rhat > 1.05:
        logger.warning("R-hat > 1.05 detected (max=%.3f). Consider more samples/tune.", max_rhat)
    else:
        logger.info("All R-hat values <= 1.05 (max=%.3f). Convergence OK.", max_rhat)

    # Check ESS
    ess_vals = summary["ess_bulk"].values
    min_ess = float(min(ess_vals))
    logger.info("Min ESS (bulk): %.0f", min_ess)

    # Strict mode: block saving if convergence criteria not met
    if strict:
        if max_rhat >= 1.01:
            logger.error("--strict: R-hat %.4f >= 1.01. Deleting trace.", max_rhat)
            path.unlink(missing_ok=True)
            raise RuntimeError(f"--strict: R-hat {max_rhat:.4f} >= 1.01 for {organ}")
        if min_ess < 400:
            logger.error("--strict: min ESS %.0f < 400. Deleting trace.", min_ess)
            path.unlink(missing_ok=True)
            raise RuntimeError(f"--strict: min ESS {min_ess:.0f} < 400 for {organ}")


def main():
    parser = argparse.ArgumentParser(description="Fit MCMC hierarchical survival model")
    parser.add_argument("--organ", choices=ORGANS, help="Organ to fit")
    parser.add_argument("--all", action="store_true", help="Fit all 6 organs")
    parser.add_argument("--samples", type=int, default=2000, help="Posterior draws per chain (default: 2000)")
    parser.add_argument("--chains", type=int, default=2, help="Number of MCMC chains (default: 2)")
    parser.add_argument("--tune", type=int, default=1000, help="Tuning samples per chain (default: 1000)")
    parser.add_argument("--target-accept", type=float, default=0.90, help="NUTS target acceptance (default: 0.90)")
    parser.add_argument("--quick", action="store_true", help="Quick mode: 100 samples, 1 chain, 50 tune")
    parser.add_argument("--strict", action="store_true", help="Block trace save if R-hat >= 1.01 or ESS < 400")
    parser.add_argument("--granularity", choices=["classic", "state", "full"], default="classic",
                        help="Region granularity (classic=22 cities, state=~50, full=~248)")

    args = parser.parse_args()

    if not args.organ and not args.all:
        parser.error("Specify --organ <name> or --all")

    if args.quick:
        args.samples = 100
        args.chains = 1
        args.tune = 50

    organs = ORGANS if args.all else [args.organ]
    total_start = time.perf_counter()

    for organ in organs:
        fit_and_save(
            organ=organ,
            n_samples=args.samples,
            n_chains=args.chains,
            n_tune=args.tune,
            target_accept=args.target_accept,
            strict=args.strict,
            granularity=args.granularity,
        )

    total_elapsed = time.perf_counter() - total_start
    logger.info("All done! %d organ(s) fitted in %.1fs", len(organs), total_elapsed)


if __name__ == "__main__":
    main()
