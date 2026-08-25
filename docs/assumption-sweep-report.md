# Assumption Sensitivity Sweep — #294 (T6 gate)

Generated 2026-08-25T04:01:47Z by `scripts/run-assumption-sweep.py`.

Every hand-set assumption below was perturbed ±20% and the per-center
results recomputed. **min rank ρ** is the worst Spearman rank stability
across organs and directions (1.0 = center ordering completely unaffected);
**max Δ** columns show how far absolute values move (p12 for the simulation
engine, 0–100 points for the scoring engine). Gate: rank ρ > 0.9.

Interpretation: an assumption with rank ρ ≈ 1.0 cannot change which center
looks better — it only shifts absolute levels, which the tool already
presents with uncertainty. Those are demoted to rank-immaterial in the
register (their citations still matter for calibration, not for ranking).
Assumptions failing the gate are the real justification backlog.

## Knob summary (worst case across organs and ±20% directions)

| Engine | Assumption | Register | min rank ρ | max mean Δ | max Δ | Gate |
|---|---|---|---|---|---|---|
| simulation | clamped_wait_factors | DATA-24 | 0.9732 | 0.0178 | 0.0938 | ✅ |
| scoring | weight:waitTime | SCORE-01 | 0.9854 | 1.1536 | 2.8000 | ✅ |
| scoring | weight:hospitalQuality | SCORE-01 | 0.9906 | 0.6810 | 1.1000 | ✅ |
| simulation | log_sigma | SURV-13/DATA-07/#274 | 0.9929 | 0.0358 | 0.0532 | ✅ |
| scoring | weight:donorAvailability | SCORE-01 | 0.9932 | 0.3014 | 0.8000 | ✅ |
| scoring | weight:geographic | SCORE-01 | 0.9981 | 0.3162 | 0.7000 | ✅ |
| simulation | base_delisting_rate | SURV-03 | 0.9982 | 0.0049 | 0.0131 | ✅ |
| simulation | clamped_competing_factors | DATA-25 | 0.9984 | 0.0015 | 0.0133 | ✅ |
| scoring | weight:healthDemographics | SCORE-01 | 0.9984 | 0.3155 | 0.6000 | ✅ |
| simulation | clinical_multipliers | DATA-02/03/04 | 0.9988 | 0.0121 | 0.0289 | ✅ |
| simulation | base_mortality_rate | SURV-02 | 0.9991 | 0.0020 | 0.0067 | ✅ |
| scoring | weight:policy | SCORE-01 | 0.9996 | 0.0952 | 0.2000 | ✅ |
| scoring | weight:medicalCompatibility | SCORE-01 | 0.9998 | 1.0723 | 1.9000 | ✅ |
| scoring | weight:socioeconomic | SCORE-01 | 0.9998 | 0.0476 | 0.2000 | ✅ |
| simulation | blood_type_multipliers | DATA-01 | 0.9999 | 0.0099 | 0.0198 | ✅ |
| simulation | urgency_mortality_multipliers | DATA-05/GEN-12 | 1.0000 | 0.0000 | 0.0000 | ✅ |
| simulation | age_sex_multiplier | #48 demographics | 1.0000 | 0.0020 | 0.0032 | ✅ |

## Verdict

**All swept assumptions pass the rank-stability gate** — at ±20% none of them changes the center ordering materially. The hand-set magnitudes affect absolute probabilities (see Δ columns), not which centers rank highest.

## Scope and honesty

- Patient-level multiplier tables (ABO/cPRA/MELD/LAS) are center-invariant
  by construction, so their rank ρ = 1.0 is a structural fact, now proven
  rather than assumed. Their magnitudes still matter for absolute
  probabilities — calibration (see center-calibration/temporal-forecast
  reports) is the check on levels.
- Clamp-bound knobs (DATA-24/25) move only the values sitting AT the parse
  clamps, simulating an unclamped truth 20% beyond the bound.
- Not swept (code-structural, need dedicated experiments): copula θ (#255,
  off in the closed form), SUPPLY_WAIT_ELASTICITY (COD path off for the
  reference patient), BBN CPT internals (#213/#214), spatial/equity-specific
  constants (EQSP-*), acceptance-rate composite (DATA-20/21).
- Full sweep rows (per organ × direction) in
  `docs-site/static/data/assumption-sweep.json`.
