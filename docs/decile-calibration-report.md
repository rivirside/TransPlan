# Decile Calibration Report — #295 (T-calibration gate)

Generated 2026-08-25T04:03:33Z by `scripts/run-decile-calibration.py`.

Centers are bucketed into deciles of the model's prediction; each decile's
mean prediction is compared with its mean observed SRTR rate. Predictions
are reference-patient quantities and observed rates are case-mix population
rates, so **levels are not expected to match** — the check is monotonic
proportionality: do centers the model calls slower/riskier actually
transplant less / lose more patients, decile by decile?

## Transplant calibration

| Organ | Centers | Decile Spearman ρ | OLS slope | Deciles monotone? |
|---|---|---|---|---|
| kidney | 218 | 1.0 | 0.9774 | yes |
| liver | 135 | 0.9879 | 0.581 | no (noisy) |
| heart | 130 | 0.9879 | 0.8396 | no (noisy) |
| lung | 61 | 0.9636 | 2.8729 | no (noisy) |

_Columns: predicted p12 (reference patient) vs observed 1-yr transplant rate; per-decile detail in the JSON._

## Mortality calibration

| Organ | Centers | Decile Spearman ρ | OLS slope | Deciles monotone? |
|---|---|---|---|---|
| kidney | 218 | 0.997 | 1.2211 | no (noisy) |
| liver | 135 | 0.997 | 1.1143 | no (noisy) |
| heart | 130 | 1.0 | 1.3454 | yes |
| lung | 61 | 1.0 | 1.1528 | yes |

_Columns: model annual mortality (center-adjusted) vs observed 1-yr waitlist death rate; per-decile detail in the JSON._

**Not covered:** pancreas, intestine — fewer than 30 centers with cohort n ≥ 10; deciles would be noise.

See also: `docs/center-calibration-report.md` (per-center scatter),
`docs/temporal-forecast-report.md` (out-of-sample forecast),
`docs/assumption-sweep-report.md` (rank robustness).
