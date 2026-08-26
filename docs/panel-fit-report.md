# Panel-likelihood fit (#358, phase 1)

| organ | shrunk rho | raw-persistence rho | frac_signal post [95% CI] | max R-hat |
|---|---|---|---|---|
| kidney | 0.697 | 0.837 | 0.884 [0.858, 0.91] | 1.02 |
| liver | 0.441 | 0.634 | 0.816 [0.771, 0.859] | 1.01 |
| heart | 0.431 | 0.705 | 0.729 [0.671, 0.782] | 1.01 |
| lung | 0.374 | 0.561 | 0.809 [0.741, 0.864] | 1.01 |

## Verdict (phase 2 decision)

**Engine integration of long-run-shrunk factors is REJECTED by
the out-of-sample evidence**: raw single-release persistence
beats the panel-shrunk factors in every organ, by a wide margin.
The mechanism is the #311 drift finding in action — centers move,
so the latest release's factor embodies the center's CURRENT
state while exchangeable pooling shrinks toward a stale 7-year
mean. The engine's current single-release design is validated as
the right one.

What the fit DID deliver: frac_signal is now an identified
POSTERIOR (kidney 0.884 [0.858, 0.910]) — the MCMC-09 arc closes:
prior guess (Beta(2,2)) -> empirical prior (#317, mean 0.86) ->
identified posterior, and the #317 priors are confirmed
conservative in the right direction. Any future gain over
persistence would need CENTER-SPECIFIC dynamics (local-level
state-space), and the #309 recovery ceiling bounds how much that
could add.

## Reading

- 'shrunk' ranks centers by the panel model's posterior-mean
  center effect; 'raw' is the single-release persistence
  predictor the engine uses today, evaluated on the held-out
  final release's observed transplant rates.
