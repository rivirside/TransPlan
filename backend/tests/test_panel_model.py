"""Panel-likelihood MCMC model (#358, phase 1).

obs_{c,t} ~ N(mu + center_c + release_t, sigma_obs) over the release panel:
with ~13 replicate observations per center, ALL variance components are
identified from data — the single-release model's prior-driven signal split
(MCMC-09, empirically informed by #317) becomes a posterior.

These tests verify the builder on synthetic panels with known truth before
the real fit means anything.
"""
import numpy as np
import pytest

pymc = pytest.importorskip("pymc")

from services.mcmc_survival import build_panel_model


def _synthetic_panel(k=60, t=10, sigma_c=0.3, sigma_r=0.08, sigma_e=0.12,
                     mu=0.05, seed=7):
    rng = np.random.default_rng(seed)
    center = rng.normal(0, sigma_c, size=k)
    release = rng.normal(0, sigma_r, size=t)
    obs, c_idx, r_idx = [], [], []
    for i in range(k):
        for j in range(t):
            obs.append(mu + center[i] + release[j] + rng.normal(0, sigma_e))
            c_idx.append(i)
            r_idx.append(j)
    return {
        "obs": np.array(obs), "center_idx": np.array(c_idx),
        "release_idx": np.array(r_idx), "n_centers": k, "n_releases": t,
        "centers": [f"C{i}" for i in range(k)],
        "releases": [f"r{j}" for j in range(t)],
        "_truth": {"mu": mu, "sigma_center": sigma_c,
                   "sigma_release": sigma_r, "sigma_obs": sigma_e,
                   "center_effects": center},
    }


@pytest.fixture(scope="module")
def fitted():
    panel = _synthetic_panel()
    with build_panel_model(panel):
        # 300/300 was borderline for sigma_center (R-hat ~1.12 on slower CI
        # hardware; it passed locally by luck). Longer tuning + higher
        # target_accept fixes the sampling geometry rather than relaxing the
        # convergence bar, which is the assertion that carries the value.
        idata = pymc.sample(draws=600, tune=1000, chains=2, random_seed=1,
                            progressbar=False, target_accept=0.95)
    return panel, idata


class TestPanelModel:
    def test_variance_components_recovered(self, fitted):
        panel, idata = fitted
        post = idata.posterior
        truth = panel["_truth"]
        # A single-seed 95%-CI coverage assertion fails ~5% of the time by
        # construction (calibration is SBC's job, #310) — assert accuracy
        # instead: posterior mean within 15% of truth and 99.9% CI covers.
        for name in ("sigma_center", "sigma_release", "sigma_obs"):
            draws = post[name].values.flatten()
            lo, hi = np.percentile(draws, [0.05, 99.95])
            assert lo <= truth[name] <= hi, (
                f"{name}: true {truth[name]} outside 99.9% CI [{lo:.3f}, {hi:.3f}]"
            )
            assert draws.mean() == pytest.approx(truth[name], rel=0.15), name

    def test_frac_signal_is_a_posterior_not_a_prior(self, fitted):
        """The quantity the single-release model could only guess must now be
        identified: the posterior must be far tighter than the Beta(2,2)-era
        prior sd (~0.22) and cover the generating truth."""
        panel, idata = fitted
        post = idata.posterior
        sc = post["sigma_center"].values.flatten()
        se = post["sigma_obs"].values.flatten()
        frac = sc**2 / (sc**2 + se**2)
        t = panel["_truth"]
        true_frac = t["sigma_center"]**2 / (t["sigma_center"]**2 + t["sigma_obs"]**2)
        lo, hi = np.percentile(frac, [2.5, 97.5])
        assert lo <= true_frac <= hi
        assert frac.std() < 0.10, f"frac posterior sd {frac.std():.3f} not identified"

    def test_center_effects_shrunk_and_correlated(self, fitted):
        panel, idata = fitted
        post_centers = idata.posterior["center_effect"].values.mean(axis=(0, 1))
        truth = panel["_truth"]["center_effects"]
        corr = np.corrcoef(post_centers, truth)[0, 1]
        assert corr > 0.9, f"center-effect recovery corr {corr:.3f}"
        # shrinkage: posterior means less dispersed than raw center means
        assert post_centers.std() <= truth.std() * 1.1

    def test_convergence(self, fitted):
        import arviz as az
        _, idata = fitted
        summ = az.summary(idata, var_names=["sigma_center", "sigma_release",
                                            "sigma_obs", "mu"])
        assert float(summ["r_hat"].max()) < 1.05
