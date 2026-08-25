# Panel variance decomposition (#317 / MCMC-09)

How much of the cross-center wait-factor spread is real center
signal vs release-to-release noise? The single-release MCMC model
cannot identify this (frac_signal ~ Beta(2,2), mean 0.5, MCMC-34);
the release panel can.

| organ/metric | centers | obs | frac raw [95% CI] | frac detrended [95% CI] | prior mean |
|---|---|---|---|---|---|
| kidney/wait | 134 | 1072 | 0.860 [0.818, 0.893] | 0.864 [0.822, 0.897] | 0.5 |
| kidney/mort | 222 | 1776 | 0.174 [0.122, 0.241] | 0.214 [0.156, 0.281] | 0.5 |
| kidney/delist | 222 | 1776 | 0.315 [0.237, 0.390] | 0.391 [0.303, 0.469] | 0.5 |
| liver/wait | 99 | 792 | 0.772 [0.692, 0.830] | 0.925 [0.895, 0.946] | 0.5 |
| liver/mort | 135 | 1080 | 0.237 [0.113, 0.378] | 0.294 [0.155, 0.447] | 0.5 |
| liver/delist | 135 | 1080 | 0.286 [0.186, 0.389] | 0.342 [0.230, 0.463] | 0.5 |
| heart/wait | 125 | 1000 | 0.675 [0.589, 0.743] | 0.912 [0.879, 0.935] | 0.5 |
| heart/mort | 130 | 1040 | 0.126 [0.067, 0.186] | 0.165 [0.104, 0.228] | 0.5 |
| heart/delist | 130 | 1040 | 0.224 [0.160, 0.301] | 0.265 [0.194, 0.348] | 0.5 |
| lung/wait | 65 | 520 | 0.771 [0.660, 0.847] | 0.921 [0.880, 0.945] | 0.5 |
| lung/mort | 67 | 536 | 0.325 [0.132, 0.468] | 0.380 [0.174, 0.519] | 0.5 |
| lung/delist | 67 | 536 | 0.108 [0.012, 0.186] | 0.165 [0.045, 0.266] | 0.5 |
| pancreas/wait | 18 | 144 | 0.625 [0.396, 0.784] | 0.667 [0.442, 0.817] | 0.5 |
| pancreas/mort | 43 | 344 | 0.042 [0.000, 0.143] | 0.058 [0.000, 0.176] | 0.5 |
| pancreas/delist | 43 | 344 | 0.122 [0.006, 0.226] | 0.150 [0.028, 0.260] | 0.5 |
| intestine/wait | 12 | — | insufficient panel | — | 0.5 |
| intestine/mort | 15 | 120 | 0.099 [0.000, 0.270] | 0.162 [0.013, 0.318] | 0.5 |
| intestine/delist | 15 | 120 | 0.066 [0.000, 0.201] | 0.077 [0.000, 0.213] | 0.5 |

## Interpretation

- **raw** treats all within-center variation as noise — but part
  of it is real temporal drift, so raw UNDERSTATES the signal.
- **detrended** removes each center's linear drift first, so it
  attributes drift to signal-adjacent structure; closer to the
  quantity the single-release model needs.
- Where both bounds sit far from 0.5, the Beta(2,2) prior
  (MCMC-34) is measurably miscentered and should be replaced by
  an informative prior matched to these estimates (#317 next
  step: refit traces with the empirical priors).
