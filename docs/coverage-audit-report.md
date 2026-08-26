# Interval coverage audit (#311)

Do 95% data-sampling intervals cover the next release's observed
rates? Under-coverage = intervals too tight (drift ignored).

| organ | lag-1 coverage | lag-2 | lag>=4 | n pairs (lag-1) |
|---|---|---|---|---|
| kidney | 89.3% | 71.9% | 54.5% | 3057 |
| liver | 90.3% | 73.7% | 53.8% | 1827 |
| heart | 90.9% | 77.5% | 63.2% | 1662 |
| lung | 88.5% | 71.0% | 56.8% | 846 |
| pancreas | 88.1% | 72.1% | 61.4% | 101 |

## Empirical inflation factors (multiplier on the
binomial half-width to reach nominal 95%)

| organ | lag-1 | lag-2 | lag>=4 |
|---|---|---|---|
| kidney | 1.25 | 2.0 | 3.36 |
| liver | 1.18 | 1.88 | 3.5 |
| heart | 1.16 | 1.77 | 2.33 |
| lung | 1.28 | 2.22 | 3.28 |
| pancreas | 1.34 | 4.11 | 7.43 |

## Interpretation

- Lag-1 coverage near 95% would mean binomial sampling noise
  fully explains release-to-release variation. Coverage BELOW
  95% quantifies the real drift the interval ignores — and the
  gap should WIDEN with lag if drift accumulates.
- Consequence for the product: the #226-style data-sampling
  intervals (BBN CI, rank-stability bootstrap) are honest about
  sampling noise but NOT total predictive uncertainty; a
  drift-inflated interval (scaling with horizon) would be the
  upgrade, tracked with #358's release-effect modeling.
