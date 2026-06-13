"""
MCMC convergence diagnostics — R-hat, ESS, autocorrelation.

Requires pymc/arviz. Returns a safe "not available" response when
MCMC traces haven't been generated yet.
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParameterDiagnostic:
    name: str
    r_hat: float           # Gelman-Rubin statistic (< 1.01 = converged)
    ess_bulk: float        # Bulk effective sample size
    ess_tail: float        # Tail ESS (for quantile estimates)
    autocorr_lag1: float   # Lag-1 autocorrelation


@dataclass
class ConvergenceDiagnostics:
    organ: str
    available: bool
    parameters: list[ParameterDiagnostic]
    n_chains: int
    n_draws: int
    max_r_hat: float            # Worst-case R-hat across all params
    min_ess: float              # Worst-case ESS
    converged: bool             # True if max_r_hat < 1.01 and min_ess > 400
    notes: list[str]


def get_convergence_diagnostics(organ: str) -> ConvergenceDiagnostics:
    """
    Load MCMC trace for *organ* and compute convergence diagnostics.
    Returns available=False if no trace exists or arviz/pymc not installed.
    """
    # Use the SAME trace location mcmc_survival writes to (MCMC-19): traces are
    # saved at data/mcmc-traces/{organ}.nc, not data/mcmc_traces/{organ}_trace.nc.
    from services.mcmc_survival import trace_path as _resolve_trace_path
    trace_file = _resolve_trace_path(organ)

    if not trace_file.exists():
        return ConvergenceDiagnostics(
            organ=organ,
            available=False,
            parameters=[],
            n_chains=0,
            n_draws=0,
            max_r_hat=float("nan"),
            min_ess=float("nan"),
            converged=False,
            notes=[
                f"No MCMC trace found at {trace_file}. "
                f"Run: python scripts/fit-mcmc-model.py --organ {organ}"
            ],
        )

    try:
        import arviz as az
        import numpy as np

        trace = az.from_netcdf(str(trace_file))
        summary = az.summary(trace, round_to=4)

        params: list[ParameterDiagnostic] = []
        for param_name, row in summary.iterrows():
            # Compute lag-1 autocorrelation from posterior samples
            try:
                samples = trace.posterior[param_name].values.flatten()
                if len(samples) > 2:
                    autocorr = float(
                        az.autocorr(trace.posterior[param_name].values.reshape(-1))
                        [1]
                    )
                else:
                    autocorr = float("nan")
            except Exception:
                autocorr = float("nan")

            params.append(ParameterDiagnostic(
                name=str(param_name),
                r_hat=float(row.get("r_hat", float("nan"))),
                ess_bulk=float(row.get("ess_bulk", float("nan"))),
                ess_tail=float(row.get("ess_tail", float("nan"))),
                autocorr_lag1=autocorr,
            ))

        valid_r_hats = [p.r_hat for p in params if not (p.r_hat != p.r_hat)]  # exclude nan
        valid_ess = [p.ess_bulk for p in params if not (p.ess_bulk != p.ess_bulk)]

        max_r_hat = max(valid_r_hats) if valid_r_hats else float("nan")
        min_ess = min(valid_ess) if valid_ess else float("nan")

        n_chains = int(trace.posterior.dims.get("chain", 0))
        n_draws = int(trace.posterior.dims.get("draw", 0))

        converged = (
            max_r_hat < 1.01 and min_ess > 400
            if (max_r_hat == max_r_hat and min_ess == min_ess)
            else False
        )

        notes = []
        if max_r_hat >= 1.01:
            notes.append(f"R-hat {max_r_hat:.3f} >= 1.01 — chains may not have converged")
        if min_ess < 400:
            notes.append(f"Min ESS {min_ess:.0f} < 400 — consider more draws")

        return ConvergenceDiagnostics(
            organ=organ,
            available=True,
            parameters=params,
            n_chains=n_chains,
            n_draws=n_draws,
            max_r_hat=max_r_hat,
            min_ess=min_ess,
            converged=converged,
            notes=notes,
        )

    except ImportError:
        return ConvergenceDiagnostics(
            organ=organ,
            available=False,
            parameters=[],
            n_chains=0,
            n_draws=0,
            max_r_hat=float("nan"),
            min_ess=float("nan"),
            converged=False,
            notes=["arviz not installed — run: pip install arviz"],
        )
    except Exception as e:
        logger.exception("Error loading MCMC trace for %s", organ)
        return ConvergenceDiagnostics(
            organ=organ,
            available=False,
            parameters=[],
            n_chains=0,
            n_draws=0,
            max_r_hat=float("nan"),
            min_ess=float("nan"),
            converged=False,
            notes=[f"Error loading trace: {e}"],
        )
