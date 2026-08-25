# Master Backlog — August 2026 Sweep

Consolidated from the 2026-08-24 full-project review (22-city inventory + validation/model
review). This doc maps every identified item to its GitHub issue and records phase ordering.
Update the Status column as work lands. Issue numbers marked *(new)* were filed 2026-08-24.

Ordering rationale: fix what is broken first (A), then remove silent skew (B) since every
later validation number is polluted by it, then build the fixed external benchmark (E33)
so all model work (F) is judged against it, then data replacement (C), cleanup (D),
robustness (G), assumption triage (H), features (I), docs (J).

## Phase A — Broken bugs (do first)

| # | Item | Issue | Status |
|---|------|-------|--------|
| A1 | scenarios.html posts center *names* as `city` → 400 for ~226/248 centers | #286 | ✅ 2026-08-24 |
| A2 | brier_score.py drops `center_code`; analytical baseline national vs MC center-adjusted | #287 | ✅ 2026-08-24 |
| A3 | BBN time-horizon probabilities inflate for long-wait organs | #244 | ✅ 2026-08-24 (+ L-073 filed) |
| A4 | Equity Gini circularity + age/sex input inconsistency | #254 | ✅ 2026-08-24 |
| A5 | dark-mode.js loaded twice (was scenarios.html by Aug 2026) | #261 | ✅ 2026-08-24 |

## Phase B — Silent 22-city result skew (epic #285)

| # | Item | Issue | Status |
|---|------|-------|--------|
| B1 | Trends cover 52/248 centers; BBN legacy map defaults to Nashville | #288 | ✅ 2026-08-25 (BBN map retires w/ #293) |
| B2 | Climate layer interpolated from 22 points (35% of geo score) | #289 | |
| B3 | Trauma layer + accident hotspots from 22 points | #290 | |
| B4 | policy_scenarios.py 22-city end to end | #285 | ✅ travel per-center via RPP; size-based waits on #275 |
| B5 | what_if.py city validation; travel-subsidy iterates 22 | #285 | ✅ 2026-08-25 |
| B6 | MCMC city-level hierarchy (classic trace default) | #207 | |
| B7 | BBN "classic" 22-city mode selectable in web tier | #293 | |
| B8 | Silent 1.0-multiplier fallbacks in distributions/competing_risks | see G1 | |
| B9 | api-client.js sensitivity() 'Nashville' default | fix inline w/ A | ✅ 2026-08-24 |

## Phase E — Validation harness (before model work)

| # | Item | Issue | Status |
|---|------|-------|--------|
| E1 | Per-release Table B10 parse → fit-on-N/predict-N+k forecast test | #237 | ✅ 2026-08-24 |
| E2 | Assumption sensitivity sweep (T6): ±20% perturbation, rank stability | #294 | ✅ 2026-08-25 |
| E3 | Decile calibration (T-calibration): predicted vs observed mortality | #295 | ✅ 2026-08-25 |
| E4 | Cross-iteration model comparison | #137 | |
| E5 | MCMC calibration via run-center-calibration after #207 | #207 | |
| E6 | Reframe MCMC as calibrated-uncertainty, not validation (L-061) | #257 | |
| E7 | Close #269 COMET-Lung (infeasible, documented) | #269 ✅ CLOSED | |
| E8 | MCMC-09/27 framing fixes | #257 | |

## Phase F — Model improvements (judged by Phase E numbers)

| # | Item | Issue | Status |
|---|------|-------|--------|
| F1 | MCMC 248-center refit | #207 | |
| F2 | Continuous BBN latents (replace terciles) | #236 | |
| F3 | Patient-specific competing-risk split (L-072) | #238 | |
| F4 | log_sigma clamp ceiling 1.2 (SURV-13/DATA-07) | #274 | |
| F5 | Clamp-bound cluster: 538+ values on bounds (DATA-24/25) | #294 | measured: ρ 0.973 worst (passes) |
| F6 | Hierarchical partial pooling (needs F7) | #268 | |
| F7 | Per-center transplant volume data | #275 | |
| F8 | Kriging/GP interpolation with prediction variance | #266 | |
| F9 | 2SFCA + travel-time isochrones | #267 | |
| F10 | Exponential hazard / probability-as-rate (SURV-01/25) | #259 | |
| F11 | CPT-parameter MC credible intervals | #296 | |
| F12 | BBN Step 6: regress ds/wait-delist multipliers from data | #297 | |
| F13 | Donor-supply discretization probabilities | #213 | |
| F14 | CPT empirical grounding + citations | #214 / #233 | |
| F15 | BBN guards: BBN-17 fallback, BBN-22 pediatric clamp, atol gate | #298 | |
| F16 | REMREC → "removed without transplant, other causes" relabel | (inline) | |
| F17 | L-064 allocation-circle competition proxy | #299 | |
| F18 | Long-term: #135 spatial econometrics, #142 equilibrium, L-066 surface | parked | |

## Phase C — City-keyed data replacement (never-shrink guards on every file)

| # | Item | Issue | Status |
|---|------|-------|--------|
| C1 | climate-scores.json → per-center NOAA/county | = B2 | |
| C2 | hospital-quality.json → CMS facility + SRTR volumes | #291 | |
| C3 | traffic-fatalities.json → FARS | = B3 | |
| C4 | donor-registration.json → state registry rates | #292 | |
| C5 | Retire city fallback blocks (health-demographics, air-quality) | #293 | |
| C6 | Retire city-wait-time-factors + city_* SRTR blocks | #293 | |
| C7 | Delete cost-of-living legacy cities block | #293 | |
| C8 | Per-center trends from srtr-observed-rates-historical | = B1 | ✅ 2026-08-25 |
| C9 | Retire srtr-center-mapping.json | #293 | |

## Phase D — Dead code / scaffolding removal

| # | Item | Issue | Status |
|---|------|-------|--------|
| D1 | Retire algorithm.js, DEFAULTS, CITIES, checkCityCoverage, classic mode | #293 | |
| D2 | Dead frontend: charts.js, url-sharing.js, donation-banner.js | #260 | |
| D3 | Delete old pages: find-centers, wait-estimator, data, spatial .html | #293 | |
| D4 | _FALLBACK_CITIES + unused CITIES imports | #293 | |
| D5 | Close #206 (done — CLOSED 2026-08-24), prune stale golden tests as files retire | #206 ✅ | |

## Phase G — Data quality / robustness / security

| # | Item | Issue | Status |
|---|------|-------|--------|
| G1 | `data_quality` provenance field in API responses (visible fallbacks) | #300 (refs #212/#227/#228) | |
| G2 | Inconsistent fallback patterns / error handling | #219 / #220 | |
| G3 | Synthetic-baseline guard (GEN-13/14/15) | #300 | |
| G4 | OPO-level cause-of-death proportions | #301 | |
| G5 | Data vintage refresh (CDC 2017, donor reg 2018) | #302 | |
| G6 | LAS → CAS migration (lung allocation, 2023) | #303 | |
| G7 | Tier caps on /score, /score/explain | #249 | |
| G8 | Security headers + exact pins | #250 | |
| G9 | Circular import bbn_parameterizer ↔ bayesian_network (L-070) | #298 | |

## Phase H — Assumption justification (triaged by E2 sweep)

SCORE-01/03/18/24; DATA-01→05/11/12; #255 copula θ; EQSP-05/19/22/23;
DATA-16/18/20/21/29; GEN-07/08/12/20. Worked as follow-ups to E2 results —
assumptions the sweep shows immaterial get demoted with evidence; material ones
get sourced or refit. Register updated per item.

## Phase I — Features

| # | Item | Issue | Status |
|---|------|-------|--------|
| I1 | User-defined center sets (L-067) | #304 | |
| I2 | Rh factor input | #180 | |
| I3 | Mobile responsiveness w/ large results | #224 | |
| I4 | Print button scope / methodology linking | #197 / #198 | |
| I5 | Physician directory | #162 | |
| I6 | v2 viz (glyphs, patterned choropleths, what-if sliders) | #181–183 | |

## Phase J — Documentation

| # | Item | Issue | Status |
|---|------|-------|--------|
| J1 | 22-city docs sweep (L-071) + status.md staleness + docs-site algorithm.js claim | #305 | |
| J2 | Inference-mode availability docs | #232 | |
| J3 | Equity disclaimers hardcoded | #235 | |
| J4 | BBN docstrings claim pgmpy | #258 | |
| J5 | Refactors: patient_dict dedup, slim routers | #262 / #264 | |

## Parked (cannot do solo)

- L-060 patient-level SRTR (DUA) · #107 faculty review · #179 BMC account (blocks part of #260)
