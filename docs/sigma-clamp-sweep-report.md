# log_sigma clamp ceiling sweep (#274 / DATA-07)

The wait-time lognormal sigma is clamped to [0.3, 1.2]. Measured
against the raw Table B10 national percentiles, that ceiling
**binds on five of six organs** — kidney's IQR-implied sigma is
2.53, more than double the cap.

Whether raising it *helps* is a separate question, because sigma
fattens both tails and the competing-risks integral is not
monotone in it. So each ceiling is scored by the same calibration
metric the published center-calibration report uses.

| organ | raw sigma | stored | binds? | ρ @1.2 | best ceiling | ρ @best | change |
|---|---|---|---|---|---|---|---|
| kidney | 2.529 | 1.2 | yes | 0.8882 | 1.2 | 0.8882 | +0.0000 |
| liver | 1.509 | 1.2 | yes | 0.7931 | 1.2 | 0.7931 | +0.0000 |
| heart | 1.509 | 1.2 | yes | 0.6883 | 1.2 | 0.6883 | +0.0000 |
| lung | 1.142 | 1.14 | no | 0.7755 | 1.2 | 0.7755 | +0.0000 |
| pancreas | 2.247 | 0.8 | yes | — | None | — | — |
| intestine | 2.121 | 1.2 | yes | — | None | — | — |

## Verdict

**Raising the ceiling does not help — it hurts.** On every organ
where the metric is computable, calibration is best at the
CURRENT 1.2 ceiling and degrades as the cap is lifted:

| organ | ρ @1.2 | ρ uncapped | change |
|---|---|---|---|
| kidney | 0.8882 | 0.8843 | -0.0039 |
| liver | 0.7931 | 0.7916 | -0.0015 |
| heart | 0.6883 | 0.6767 | -0.0116 |
| lung | 0.7755 | 0.7755 | +0.0000 |

That is the opposite of what #274 expected, and it makes sense on
reflection: SRTR's published percentiles describe a distribution
already truncated by competing risks and censoring, so the
'unclamped' sigma is not the true dispersion of the wait — it is
the dispersion of a censored observation of it. The 1.2 ceiling
acts as a crude but effective regularizer against that.

So DATA-07 stays clamped, and #274's proposed raise to ~1.8-2.0
is rejected on evidence rather than left open on suspicion.

### What could not be measured

- **pancreas**: no center has an observed cohort of 25+ (largest is 16), so the calibration metric cannot be computed at any ceiling.
- **intestine**: no center has an observed cohort of 25+ (largest is 20), so the calibration metric cannot be computed at any ceiling.

These organs are excluded from the verdict rather than
assumed to follow it.


## A second, separate defect

**pancreas** store sigma 0.8 rather than any clamp
value. `fit_lognormal` returns early with a hardcoded 0.8 whenever
the median is censored (`>72`), discarding P10 and P25 that are
present and valid. For pancreas the chain would have produced
2.247 from real percentiles.
That is independent of the ceiling and should be fixed regardless
of what this sweep concludes about the cap.

