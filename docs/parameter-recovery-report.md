# Parameter-recovery study (#309)

20 synthetic worlds x 220 centers; truth known; observed tables simulated with finite-cohort noise at REAL kidney cohort sizes; derivation via the REAL parser functions (srtr_xls_utils, #339).

- Wait-factor rank recovery: median rho **0.916**
- p12 rank recovery: median rho **0.916** (range 0.869-0.944)
- Clamped/censored factor share: 0.5%
- National sigma recovery: 1.003 vs true 1.0 (the #256/#274 clamp binds here by design)

## Ranking recovery by cohort size

| cohort n | median rank rho |
|---|---|
| n<60 | 0.764 |
| 60-160 | 0.931 |
| 160-300 | 0.969 |
| 300+ | 0.978 |

## Panel signal-fraction recovery (#317 sanity)

ANOVA recovered frac_signal 0.932 vs generating truth 0.935.

## Interpretation

The by-cohort-size table is the fundamental ceiling: rankings for
small-cohort centers are noise-limited BY THE DATA, not by the
model — consistent with the temporal forecast sitting at the
persistence ceiling (#308) and motivating the rank intervals
(#313), which communicate exactly this uncertainty to users.

**The ceiling explains the measured calibrations.** Kidney's
observed MCMC-vs-observed concordance is 0.889 (post-#317) against
a synthetic recoverable ceiling of ~0.92 at
these cohort sizes: the pipeline extracts nearly all the signal the
public tables contain. Material further gains require more data
per center (the panel likelihood, #358), not more model.
