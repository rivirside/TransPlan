# Simulation-based calibration (#310)

24 replications on the kidney state design; rank of the
true parameter within 150 posterior draws must be uniform.

| parameter | KS p (uniformity) | mean rank/L | verdict |
|---|---|---|---|
| log_median_national | 0.570 | 0.459 | consistent with calibrated |
| sigma_total_wait | 0.476 | 0.549 | consistent with calibrated |
| frac_signal_wait | 0.408 | 0.553 | consistent with calibrated |
| log_mort_national | 0.519 | 0.551 | consistent with calibrated |

Caveat: 24 replications give modest power — this
detects gross miscalibration, not subtle tail issues. The
quick-fit sampler config trades some fidelity for runtime;
a full-config SBC is the heavyweight follow-up.
