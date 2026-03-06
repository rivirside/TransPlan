"""
Wait-time distribution models per organ/blood type/city (Milestone 2).
# FIXME (Milestone 2): Replace stubs with log-normal distribution engine.
"""
import numpy as np
import scipy.stats


def get_wait_time_distribution(
    organ: str,
    blood_type: str,
    city: str,
    cpra: int | None = None,
) -> scipy.stats.rv_continuous:
    """
    Return a log-normal distribution for wait time in months.
    Stub: returns a generic log-normal(mu=ln(24), sigma=0.8).
    # FIXME (Milestone 2): Load from data/wait-time-distributions.json.
    """
    mu = np.log(24.0)   # placeholder 24-month median
    sigma = 0.8
    return scipy.stats.lognorm(s=sigma, scale=np.exp(mu))
