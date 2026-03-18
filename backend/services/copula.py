"""
Clayton copula for correlated competing risks (Phase 5 M2).

The current Monte Carlo engine draws mortality and delisting times as
independent exponentials.  In reality, a patient whose health is
declining faces *both* higher mortality AND higher delisting risk
simultaneously — positive lower-tail dependence.

The Clayton copula captures exactly this pattern:
  - Strong positive dependence in the lower tail (both events happen
    sooner when health deteriorates).
  - Asymmetric: upper-tail dependence is weaker (being very healthy
    doesn't equally de-couple the events).

Sampling uses the *conditional method* (Nelsen, 2006 §4.2):
  1. Draw u1, t ~ Uniform(0, 1) independently.
  2. Compute u2 = (u1^(-θ) · (t^(-θ/(θ+1)) − 1) + 1)^(-1/θ)
  3. (u1, u2) is a bivariate draw from Clayton(θ).

Then map through the exponential inverse CDF:
  time_i = -scale_i · ln(1 − u_i)

θ > 0 controls dependence strength:
  - θ → 0⁺ : independence (reverts to current model)
  - θ = 1  : moderate positive dependence (Kendall's τ ≈ 0.33)
  - θ = 2  : strong positive dependence  (Kendall's τ = 0.50)
  - θ → ∞  : comonotonicity (perfect dependence)

Default θ = 1.0 is a conservative choice supported by SRTR registry
analyses showing moderate mortality–delisting correlation.
"""
from __future__ import annotations

import numpy as np
from numpy.random import Generator


def sample_clayton_bivariate(
    n: int,
    theta: float,
    rng: Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Draw *n* bivariate samples from a Clayton(θ) copula.

    Parameters
    ----------
    n : int
        Number of samples.
    theta : float
        Copula parameter.  Must be > 0.  Values near 0 approximate
        independence; larger values increase lower-tail dependence.
    rng : numpy.random.Generator
        Random number generator for reproducibility.

    Returns
    -------
    u1, u2 : ndarray of shape (n,)
        Marginally Uniform(0, 1) with Clayton dependence structure.

    Raises
    ------
    ValueError
        If theta <= 0 or n <= 0.
    """
    if theta <= 0:
        raise ValueError(f"Clayton θ must be > 0, got {theta}")
    if n <= 0:
        raise ValueError(f"n must be > 0, got {n}")

    u1 = rng.uniform(size=n)
    t = rng.uniform(size=n)

    # Conditional inverse:  u2 | u1  via Clayton conditional CDF
    # u2 = (u1^(-θ) · (t^(-θ/(θ+1)) − 1) + 1)^(-1/θ)
    exponent = -theta / (theta + 1.0)
    inner = np.power(u1, -theta) * (np.power(t, exponent) - 1.0) + 1.0

    # Numerical guard: inner must be > 0 for the power to be real
    inner = np.maximum(inner, 1e-300)

    u2 = np.power(inner, -1.0 / theta)

    # Clip to valid (0, 1) range for downstream inverse-CDF safety
    u2 = np.clip(u2, 1e-15, 1.0 - 1e-15)
    u1 = np.clip(u1, 1e-15, 1.0 - 1e-15)

    return u1, u2


def draw_correlated_competing_risks(
    mort_scale: float,
    delist_scale: float,
    n: int,
    theta: float,
    rng: Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Draw correlated mortality and delisting times using Clayton copula.

    Maps Clayton-coupled uniform marginals through the exponential
    inverse CDF:  time = -scale · ln(1 − u)

    Parameters
    ----------
    mort_scale : float
        Exponential scale for mortality (mean time to death in months).
    delist_scale : float
        Exponential scale for delisting (mean time to delisting in months).
    n : int
        Number of Monte Carlo iterations.
    theta : float
        Clayton copula parameter (>0).
    rng : numpy.random.Generator
        Random number generator.

    Returns
    -------
    mortality_times, delisting_times : ndarray of shape (n,)
        Correlated event times in months.
    """
    u1, u2 = sample_clayton_bivariate(n, theta, rng)

    # Inverse CDF of Exponential(scale):  F⁻¹(u) = -scale · ln(1 − u)
    mortality_times = -mort_scale * np.log(1.0 - u1)
    delisting_times = -delist_scale * np.log(1.0 - u2)

    return mortality_times, delisting_times


def kendall_tau(theta: float) -> float:
    """Kendall's τ for Clayton(θ): τ = θ / (θ + 2)."""
    if theta <= 0:
        raise ValueError(f"Clayton θ must be > 0, got {theta}")
    return theta / (theta + 2.0)


def theta_from_tau(tau: float) -> float:
    """Invert Kendall's τ to get Clayton θ: θ = 2τ / (1 − τ)."""
    if tau <= 0 or tau >= 1:
        raise ValueError(f"Kendall's τ must be in (0, 1), got {tau}")
    return 2.0 * tau / (1.0 - tau)
