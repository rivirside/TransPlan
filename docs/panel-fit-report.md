# Panel-likelihood fit (#358, phase 1)

Crossed random-effects model with SUM-TO-ZERO effects
(obs_{c,t} ~ N(mu + center_c + release_t, sigma_obs)) over the real
center x release wait-factor panel; last release held out.

| organ | shrunk rho | raw-persistence rho | frac_signal post [95% CI] | max R-hat |
|---|---|---|---|---|
| kidney | 0.699 | 0.837 | 0.885 [0.856, 0.911] | 1.0 |
| liver | 0.442 | 0.634 | 0.816 [0.767, 0.862] | 1.0 |
| heart | 0.434 | 0.705 | 0.727 [0.671, 0.78] | 1.02 |
| lung | 0.376 | 0.561 | 0.809 [0.748, 0.867] | 1.01 |

## Verdict (phase 2 decision)

**Engine integration of long-run-shrunk factors is REJECTED by the
out-of-sample evidence**: raw single-release persistence beats the
panel-shrunk factors in every organ, by a wide margin (kidney
0.837 vs 0.699; heart 0.705 vs 0.434). The mechanism is the #311
drift finding in action — centers move, so the latest release's
factor embodies the center's CURRENT state while exchangeable
pooling shrinks toward a stale 7-year mean. The engine's existing
single-release design is thereby evidence-validated.

What the fit DID deliver: frac_signal is now an identified
POSTERIOR (kidney 0.885 [0.856, 0.911]), closing the MCMC-09 arc —
Beta(2,2) guess -> #317 empirical prior (0.86) -> posterior — and
confirming the #317 priors were conservative in the right
direction. Any future gain over persistence would need CENTER-
SPECIFIC dynamics (a local-level state-space per center rather
than exchangeable pooling), bounded by the #309 recovery ceiling.

## Model note (identifiability)

The first version left mu non-identified against the random-effect
means (only mu + center_c + release_t is identified), which CI
caught as R-hat 1.12-1.18 where a local run had passed by luck.
Sum-to-zero (ZeroSumNormal) effects remove that ridge: R-hat is now
1.00-1.02 with 1 divergence total across four organs, and the
conclusions above are unchanged under the corrected model.
