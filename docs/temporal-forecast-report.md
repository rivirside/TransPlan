# Temporal Forecast Validation (fit-on-N / predict-N+k) — #237

Generated 2026-08-25T03:42:07Z by `scripts/run-temporal-forecast.py`.

**What this is.** The genuinely out-of-sample forecast test: the model's
center-ranking core is re-fit from each archived SRTR release's inputs
(Table B10 wait-time percentiles, Table B7/B6 competing-risk rates) and its
predicted per-center p12 ranking is scored against the observed 1-yr
transplant rates of every LATER release. The training release never saw the
test release. This completes the follow-up left open by
`docs/temporal-validation-report.md` and addresses #251's core critique.

**Reading the numbers.** `rho_forecast` is the model's forward Spearman;
`rho_persistence` is the observed-rate autocorrelation on the same centers —
the practical ceiling (no wait-time-based model can beat simply knowing the
outcome variable's own past). A forecast near the ceiling means the model's
inputs (wait times + competing risks) carry most of the persistent signal;
the gap is what better inputs could still recover.

## Median Spearman ρ by organ × forecast horizon

| Organ | Horizon | ρ forecast | ρ persistence (ceiling) | pairs | median centers |
|---|---|---|---|---|---|
| kidney | 6mo | 0.862 | 0.923 | 13 | 220 |
| kidney | 12mo | 0.846 | 0.84 | 13 | 220 |
| kidney | 24mo | 0.789 | 0.786 | 24 | 219 |
| kidney | 36-48mo | 0.708 | 0.708 | 34 | 217 |
| kidney | >48mo | 0.613 | 0.599 | 21 | 216 |
| liver | 6mo | 0.836 | 0.899 | 13 | 133 |
| liver | 12mo | 0.794 | 0.808 | 13 | 133 |
| liver | 24mo | 0.716 | 0.741 | 24 | 133 |
| liver | 36-48mo | 0.588 | 0.606 | 34 | 131 |
| liver | >48mo | 0.463 | 0.463 | 21 | 131 |
| heart | 6mo | 0.743 | 0.808 | 13 | 123 |
| heart | 12mo | 0.704 | 0.61 | 13 | 124 |
| heart | 24mo | 0.608 | 0.557 | 24 | 123 |
| heart | 36-48mo | 0.456 | 0.448 | 34 | 120 |
| heart | >48mo | 0.344 | 0.339 | 21 | 120 |
| lung | 6mo | 0.745 | 0.835 | 13 | 62 |
| lung | 12mo | 0.638 | 0.656 | 13 | 61 |
| lung | 24mo | 0.577 | 0.533 | 24 | 61 |
| lung | 36-48mo | 0.447 | 0.439 | 34 | 60 |
| lung | >48mo | 0.337 | 0.265 | 21 | 59 |
| pancreas | 6mo | 0.803 | 0.914 | 6 | 9 |
| pancreas | 12mo | 0.812 | 0.733 | 7 | 9 |
| pancreas | 24mo | 0.743 | 0.758 | 13 | 9 |
| pancreas | 36-48mo | 0.691 | 0.571 | 14 | 9 |
| pancreas | >48mo | 0.731 | 0.548 | 2 | 9 |

## Headline: earliest release → latest release

| Organ | Train | Test | Lag (months) | ρ forecast | ρ persistence | centers |
|---|---|---|---|---|---|---|
| kidney | 1811 | 2511 | 84 | 0.5367 | 0.4248 | 215 |
| liver | 1811 | 2511 | 84 | 0.3716 | 0.3597 | 129 |
| heart | 1811 | 2511 | 84 | 0.1588 | 0.1918 | 119 |
| lung | 1811 | 2511 | 84 | 0.1637 | 0.2664 | 57 |

**Not covered:** intestine — fewer than 8 centers with cohort n ≥ 10 in overlapping releases, so no correlation is reportable. This is an explicit data-sparsity exclusion, not an omission.

## Honest scope

- The reduced core (wait factor + competing-risk ratios → closed-form p12)
  produces the same cross-center ranking as the full MC engine for a
  reference patient: patient-level multipliers are center-invariant.
  Acceptance-rate thinning and score drift are excluded (as in the
  calibration harness).
- Ground truth is the SRTR observed 1-yr transplant rate over each center's
  real case mix; predictions are reference-patient probabilities — hence
  rank correlation, not calibration, is the metric.
- Cohorts with n<10 are excluded from ground truth. Centers must appear in
  both train inputs and test outcomes.
- Prediction inputs (B10/B7) and ground-truth outcomes (B7 transplant rate)
  come from the same instrument in different years; the transplant-rate
  column itself is never used as a prediction input.

See also: `docs/temporal-validation-report.md` (persistence + backward
concordance), `docs/center-calibration-report.md` (within-release
calibration).
