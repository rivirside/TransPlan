# MCMC 248-Center Refit — #207

2026-08-25, branch `backlog-2026-08`. Closes the first phase of epic #285 (retire
the 22-city basis): the MCMC engine's hierarchy now runs at `full` granularity —
one region per SRTR center — with traces fitted for all six organs.

## What changed in the model (`services/mcmc_survival.py`)

1. **Bug fix — disconnected scale priors.** The old model defined
   `sigma_city_mort` / `sigma_city_delist` HalfNormals and stacked them into
   `city_sd`, but the MvNormal offsets drew their covariance entirely from
   `LKJCholeskyCov`'s own `sd_dist` — the stack was dead code, so those two
   posteriors were pure prior. They are now Deterministics derived from the
   parameters that actually generate the offsets.

2. **Identifiability-honest reparameterization (MCMC-09).** With one observed
   aggregate factor per center, `obs_i ~ N(offset_i, σ_obs)` with
   `offset_i ~ N(0, σ_city)` identifies only `σ_city² + σ_obs²`; the split is
   prior-driven. Sampling the two sigmas separately put NUTS on that ridge —
   at 248 groups the kidney fit gave R-hat 1.07–1.08 / ESS ≈ 40 in both
   centered and non-centered forms. The model now samples the **identified
   total spread** (`sigma_total_*`, HalfNormal 0.5) and an **explicitly
   prior-driven signal fraction** (`frac_signal_*`, Beta(2,2)) per family
   (wait / mortality / delisting), with offsets kept centered (correct for
   strongly informative per-group likelihoods). The mort↔delist correlation
   keeps its LKJ(η=2) prior via the exact 2×2 identity ρ = 2·Beta(2,2) − 1,
   with an explicit Cholesky.

3. **Granularity-aware availability.** `is_available(organ, granularity)` now
   honors the full → state → classic fallback that trace loading actually
   performs (previously it looked only for the classic trace, so full-only
   traces 503'd), and the fit script calls `load_all()` (state/full region
   resolution crashed without it) and gained `--cores` (sequential sampling
   where parallel workers die).

## Fits (all organs, `full` granularity)

    .venv/bin/python scripts/fit-mcmc-model.py --all --granularity full \
        --cores 1 --chains 4 --tune 1500 --target-accept 0.95
    # liver/heart/lung refit at --tune 3000 --samples 3000 --target-accept 0.97

| Organ | Hyper R-hat (max) | Ranking-quantity R-hat (max) | Notes |
|---|---|---|---|
| kidney | 1.04 | ≤1.04 | converged |
| liver | 1.08 | **1.04** (ESS ≥ 93) | sticky variance-split only |
| heart | 1.07 | **1.03** (ESS ≥ 158) | sticky variance-split only |
| lung | 1.05 | ≤1.05 | converged |
| pancreas | 1.03 | ≤1.03 | converged |
| intestine | 1.02 | ≤1.02 | converged |

The parameters that stay above 1.05 for liver/heart are exactly the
variance-split fractions, which are weakly identified **by design** (the data
cannot separate center signal from observation noise; see MCMC-09). Everything
that determines center rankings and probabilities — per-center factors/offsets,
national parameters, blood-type/urgency multipliers — mixes cleanly.

Traces: `data/mcmc-traces/{organ}-full.nc` (~100 MB each, gitignored;
reproduce with the commands above; seed 42).

## Calibration (E5): MCMC-full vs observed SRTR 1-yr transplant rates

Reference patients as in `run-center-calibration.py`; cohorts n ≥ 10.

**Post-fix numbers** (see "Inference-side bug" below — the first measurement
ran before the region-mapping fix, when the per-center posterior effects were
silently unused):

| Organ | MCMC-full ρ | MC engine ρ (report) |
|---|---|---|
| kidney | 0.872 (n=218) | 0.890 |
| liver | 0.759 (n=135) | 0.722 |
| heart | 0.760 (n=130) | 0.755 |
| lung | 0.581 (n=61) | 0.703 |
| pancreas | 0.754 (n=6) | 0.459 |
| intestine | 0.679 (n=7) | 0.623 |

## Inference-side bug found post-fit

`simulate_mcmc` mapped every center through the **classic** city map
regardless of the trace's granularity, so state/full traces (whose regions
are state abbreviations / center codes) never matched and every center fell
back to region index 0 — the refit posterior's per-center effects were unused
and cross-center variation came only from the ratio adjustments. Fixed:
`_get_trace` returns the actual granularity, centers map at that granularity
(full → identity), full-mode ratio adjustments are pinned to 1.0 (anything
else double-counts), state-mode ratios use the true region-average reference,
and centers without a trace region are skipped rather than given a fabricated
index-0 posterior. Kidney calibration moved 0.796 → 0.872 with the fix.

MCMC ranks slightly below the MC engine for kidney/heart/lung — expected, since
posterior parameter draws add honest uncertainty to the point ranking — and
essentially matches elsewhere. Framing per #257: this is uncertainty
propagation over the same SRTR inputs, not independent validation.

## Follow-ups

- The 22-city ("classic") trace path retires with #293.
- CI bands from posterior draws are the honest headline benefit; the simulator
  already surfaces them in MCMC mode (local tier).
- Registered: MCMC-28 (Beta(2,2) signal-fraction prior — an explicit, honest
  assumption replacing the implicit prior-driven split).

## 2026-08-25 update: empirical signal-fraction priors (#317)

The Beta(2,2) signal-fraction prior (MCMC-09's honest-but-flat guess) is
replaced by per-(organ, metric) empirical priors measured from the
center x release panel (scripts/run-panel-variance.py, ~13 SRTR releases,
random-effects ANOVA with bootstrap CIs):

- wait factors: raw frac_signal 0.63-0.86 (kidney 0.86 [0.82, 0.89])
- mortality rates: 0.04-0.33 · delisting rates: 0.11-0.32

All six full-granularity traces refit under the new priors (2000 draws x 2
chains, max R-hat 1.05; intestine's wait fraction keeps Beta(2,2) — its
16-center panel is insufficient — and retains the expected identifiability
ridge). Calibration against observed transplant rates (n>=10 cohorts):

| organ  | rho (Beta(2,2) priors) | rho (empirical priors) |
|--------|------------------------|------------------------|
| kidney | 0.872                  | 0.889                  |
| liver  | —                      | 0.765                  |
| heart  | —                      | 0.768                  |
| lung   | —                      | 0.695                  |

Full method and caveats: docs/panel-variance-report.md.
