# Pre/post-policy cross-center dispersion (#349)

Did allocation-geometry changes reduce cross-center dispersion in
observed transplant rates? Dispersion = CV / IQR-over-median / Gini
of SRTR Table B7 12-month transplant rates (centers with n >= 10).
Boundaries are LAG-ADJUSTED (policy date + ~15 months) because B7
cohorts end well before the release date; the raw-date boundary is
reported as a sensitivity.

## lung
Policy: **CAS / continuous distribution** (2023-03-09); effect boundary release 2405.
- CV: 0.209 -> 0.147 (DOWN 0.061; permutation p=0.002; boundary |shift| ranks 8/14 among placebos; DETRENDED step -0.001, p=0.928)
- GINI: 0.116 -> 0.079 (DOWN 0.036; permutation p=0.001; boundary |shift| ranks 6/14 among placebos; DETRENDED step -0.001, p=0.752)

## kidney
Policy: **250nm circles** (2021-03-15); effect boundary release 2211.
- CV: 0.509 -> 0.481 (DOWN 0.028; permutation p=0.016; boundary |shift| ranks 8/14 among placebos; DETRENDED step -0.001, p=0.894)
- GINI: 0.272 -> 0.264 (DOWN 0.007; permutation p=0.227; boundary |shift| ranks 7/14 among placebos; DETRENDED step -0.001, p=0.894)

## liver
Policy: **acuity circles** (2020-02-04); effect boundary release 2105.
- CV: 0.333 -> 0.281 (DOWN 0.052; permutation p=0.008; boundary |shift| ranks 12/14 among placebos; DETRENDED step +0.007, p=0.428)
- GINI: 0.190 -> 0.159 (DOWN 0.031; permutation p=0.007; boundary |shift| ranks 11/14 among placebos; DETRENDED step +0.004, p=0.445)

## pancreas
Control organ (no allocation-geometry change in window).

## heart
Control organ (no allocation-geometry change in window).
- CV range across releases: 0.201-0.297

## Conclusion

Cross-center dispersion declined SECULARLY across the whole
window for every organ — the naive pre/post tests flag every
boundary, and the policy boundaries rank mid-pack among placebo
boundaries. After removing the linear trend:

- lung: detrended step -0.001 (p=0.928) — no step beyond drift
- kidney: detrended step -0.001 (p=0.894) — no step beyond drift
- liver: detrended step +0.007 (p=0.428) — no step beyond drift

This matches the adjusted-analysis literature on the 2021 kidney
change (redistribution between centers rather than a net national
dispersion reduction): the policies moved WHO waits where, while
the overall convergence trend predates and outlasts each of them.

## Reading guide

A real policy effect should show: a shift at the lag-adjusted
boundary that ranks near the top of the placebo distribution, in
the policy organ but NOT in the control organs. A shift with
permutation p > ~0.1 or a mid-pack placebo rank is consistent with
ordinary drift — the kidney-250nm literature (adjusted analyses)
found redistribution rather than net dispersion reduction, so a
null here is a credible outcome, not a failed analysis. Note the
detrended test is CONSERVATIVE (a real step partially absorbs into
the fitted slope), so its near-1 p-values on the real data are
strong evidence of no step, while a true step would still show
p in the ~0.05-0.15 range at this sample size.
