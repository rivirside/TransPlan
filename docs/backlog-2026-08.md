# Master Backlog — August 2026 Sweep

Consolidated from the 2026-08-24 full-project review (22-city inventory + validation/model
review). This doc maps every identified item to its GitHub issue and records phase ordering.
Update the Status column as work lands. Issue numbers marked *(new)* were filed 2026-08-24.

Ordering rationale: fix what is broken first (A), then remove silent skew (B) since every
later validation number is polluted by it, then build the fixed external benchmark (E33)
so all model work (F) is judged against it, then data replacement (C), cleanup (D),
robustness (G), assumption triage (H), features (I), docs (J).

> **Reconciled 2026-08-26.** This sweep's branch (`backlog-2026-08`) was merged
> and closed long ago; the doc had gone stale relative to what has since landed
> on main. Rows completed by PR #370 are marked below. The genuinely open
> remainder is the F (model research), G (robustness), I (features) and J (docs)
> rows without a status.

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
| B2 | Climate layer interpolated from 22 points (35% of geo score) | #289 | ✅ 2026-08-25 |
| B3 | Trauma layer + accident hotspots from 22 points | #290 | ✅ 2026-08-25 |
| B4 | policy_scenarios.py 22-city end to end | #285 | ✅ travel per-center via RPP; size-based waits on #275 |
| B5 | what_if.py city validation; travel-subsidy iterates 22 | #285 | ✅ 2026-08-25 |
| B6 | MCMC city-level hierarchy (classic trace default) | #207 | ✅ full traces fitted; classic retires w/ #293 |
| B7 | BBN "classic" 22-city mode selectable in web tier | #293 | ✅ removed from tiers/UI 2026-08-25 |
| B8 | Silent 1.0-multiplier fallbacks in distributions/competing_risks | see G1 | visible via #300 on /simulate |
| B9 | api-client.js sensitivity() 'Nashville' default | fix inline w/ A | ✅ 2026-08-24 |

## Phase E — Validation harness (before model work)

| # | Item | Issue | Status |
|---|------|-------|--------|
| E1 | Per-release Table B10 parse → fit-on-N/predict-N+k forecast test | #237 | ✅ 2026-08-24 |
| E2 | Assumption sensitivity sweep (T6): ±20% perturbation, rank stability | #294 | ✅ 2026-08-25 |
| E3 | Decile calibration (T-calibration): predicted vs observed mortality | #295 | ✅ 2026-08-25 |
| E4 | Cross-iteration model comparison | #137 | |
| E5 | MCMC calibration via run-center-calibration after #207 | #207 | ✅ ρ 0.64–0.80 (docs/mcmc-248-refit-report.md) |
| E6 | Reframe MCMC as calibrated-uncertainty, not validation (L-061) | #257 | ✅ docs/UI reframed 2026-08-25 (#257 stays open for the remaining statistical-validity items) |
| E7 | Close #269 COMET-Lung (infeasible, documented) | #269 ✅ CLOSED | ✅ 2026-08-26 — #269 closed: COMET is population-level and does not rank centers, so SRTR per-center calibration is the substitute|
| E8 | MCMC-09/27 framing fixes | #257 | ✅ (validation.html header) — #257 stays open for the rest of the MCMC-09/27 framing set |

## Phase F — Model improvements (judged by Phase E numbers)

| # | Item | Issue | Status |
|---|------|-------|--------|
| F1 | MCMC 248-center refit | #207 | ✅ 2026-08-25 |
| F2 | Continuous BBN latents (replace terciles) | #236 | |
| F3 | Patient-specific competing-risk split (L-072) | #238 | ✅ 2026-08-26 — #238 closed|
| F4 | log_sigma clamp ceiling 1.2 (SURV-13/DATA-07) | #274 | ✅ 2026-08-26 — measured, not built: raising the ceiling degrades calibration on every assessable organ (kidney 0.8882→0.8843). DATA-07 heuristic_clamp→data_derived|
| F5 | Clamp-bound cluster: 538+ values on bounds (DATA-24/25) | #294 | ✅ 2026-08-26 — measured: worst ρ 0.973 across the ±20% sweep (passes) |
| F6 | Hierarchical partial pooling (needs F7) | #268 | ✅ 2026-08-27 — #402: EB shrinkage before the clamp, KIDNEY ONLY (pinned 60→0, top-10 tiny cohorts 4→1). heart/liver excluded by measurement (degrades calibration −0.0342/−0.0119, also on n≥10); lung/pancreas/intestine not estimable|
| F7 | Per-center transplant volume data | #275 | |
| F8 | Kriging/GP interpolation with prediction variance | #266 | ✅ 2026-08-26 (#370 exposed kriging in Explorer w/ per-point GP variance + extrapolation flag; projection clause measured-and-rejected, EQSP-34) |
| F9 | 2SFCA + travel-time isochrones | #267 | demand side unblocked 2026-08-26 (county population, #336); drive-time half blocked on a self-hosted OSRM build |
| F10 | Exponential hazard / probability-as-rate (SURV-01/25) | #259 | partial — probability-as-rate FIXED (multipliers now applied in hazard space; also fixed liver p=1.1734 > 1). Weibull half NOT done and #259's shape>1 is contradicted by #297: hazard FALLS with time for 4 of 6 organs |
| F11 | CPT-parameter MC credible intervals | #296 | |
| F12 | BBN Step 6: regress ds/wait-delist multipliers from data | #297 | ✅ 2026-08-26 — measured: hazard FALLS with waiting time for 4 of 6 organs, so the shipped multipliers have the wrong sign, not magnitude (L-081). Replacement tracked as #380|
| F13 | Donor-supply discretization probabilities | #213 | ✅ 2026-08-26 — measured: swung 90/9/1→50/35/15, worst ρ 0.9987; not load-bearing. BBN-01 medium→low|
| F14 | CPT empirical grounding + citations | #214 / #233 | |
| F15 | BBN guards: BBN-17 fallback, BBN-22 pediatric clamp, atol gate | #298 | ✅ 2026-08-26 — #298 closed (BBN-22 pediatric clamp retired via #370 with measured per-organ multipliers) |
| F16 | REMREC → "removed without transplant, other causes" relabel | (inline) | |
| F17 | L-064 allocation-circle competition proxy | #299 | partial — normalizers MEASURED and corrected (kidney 15→25.6; score averaged 1.71 not 1.0); 500nm 2.5x ratio measured sound and kept. Proxy itself still crude — issue stays open|
| F18 | Long-term: #135 spatial econometrics, #142 equilibrium, L-066 surface | parked | |

## Phase C — City-keyed data replacement (never-shrink guards on every file)

| # | Item | Issue | Status |
|---|------|-------|--------|
| C1 | climate-scores.json → per-center (NASA POWER) | = B2 | ✅ |
| C2 | hospital-quality.json → SRTR per-center volumes (was 22-city + hash-fabricated) | #291 | ✅ 2026-08-25 |
| C3 | traffic-fatalities.json → FARS | = B3 | ✅ |
| C4 | donor-registration.json → per-center SRTR living-donor data | #292 | ✅ 2026-08-25 |
| C5 | City fallback blocks (health-demographics, air-quality) | #285 | ✅ #285 closed; fetchers keep the city blocks only as spatial fallback |
| C6 | Retire city_* SRTR blocks | #293 | ✅ 2026-08-25 |
| C7 | Delete cost-of-living legacy cities block | #293 | ✅ 2026-08-25 — #293 closed with the 22-city frontend retirement|
| C8 | Per-center trends from srtr-observed-rates-historical | = B1 | ✅ 2026-08-25 |
| C9 | srtr-center-mapping.json: API/loader consumers retired; file stays (feeds srtr-historical generation) | #293 | ✅ 2026-08-25 |

## Phase D — Dead code / scaffolding removal

| # | Item | Issue | Status |
|---|------|-------|--------|
| D1 | Retire algorithm.js, DEFAULTS, CITIES, checkCityCoverage, classic mode | #293 | ✅ CLOSED 2026-08-25 (fetcher CITIES → #285) |
| D2 | Dead frontend: charts.js, url-sharing.js, donation-banner.js | #260 | partial — charts.js and url-sharing.js are already ABSENT; donation-banner.js is deliberately dormant pending #179 (line 11 returns immediately) yet still fetched by 14 pages |
| D3 | Old pages already deleted; 17 broken links to them FIXED 2026-08-25 | #293 | ✅ |
| D4 | _FALLBACK_CITIES + unused CITIES imports | #293 | ✅ 2026-08-25 |
| D5 | Close #206 (done — CLOSED 2026-08-24), prune stale golden tests as files retire | #206 ✅ | ✅ 2026-08-24 — #206 closed|

## Phase G — Data quality / robustness / security

| # | Item | Issue | Status |
|---|------|-------|--------|
| G1 | `data_quality` provenance field in API responses (visible fallbacks) | #300 (refs #212/#227/#228) | ✅ 2026-08-25 (simulate/what-if/sensitivity + UI); #212/#227/#228 stay open for the remaining fallback sites |
| G2 | Inconsistent fallback patterns / error handling | #219 / #220 | ✅ major fixes + /score provenance + spatial/tier consistency; residue documented on issues |
| G3 | Synthetic-baseline guard (GEN-13/14/15) | #300 | ✅ #300 closed; covered by _write_guarded + validate-data organ-block errors |
| G4 | OPO-level cause-of-death proportions | #301 | |
| G5 | Data vintage refresh (CDC 2017, donor reg 2018) | #302 | |
| G6 | LAS → CAS migration (lung allocation, 2023) | #303 | ✅ 2026-08-26 — `cas` field ships and is exposed in the simulator and the shared patient form (#370); LAS retained as documented legacy |
| G7 | Tier caps on /score, /score/explain | #249 | ✅ 2026-08-25 |
| G8 | Security headers + exact pins | #250 | |
| G9 | Circular import bbn_parameterizer ↔ bayesian_network (L-070) | #298 | ✅ 2026-08-26 — #298 closed|

## Phase H — Assumption justification (triaged by E2 sweep)

SCORE-01/03/18/24; DATA-01→05/11/12; #255 copula θ; EQSP-05/19/22/23;
DATA-16/18/20/21/29; GEN-07/08/12/20. Worked as follow-ups to E2 results —
assumptions the sweep shows immaterial get demoted with evidence; material ones
get sourced or refit. Register updated per item.

## Phase I — Features

| # | Item | Issue | Status |
|---|------|-------|--------|
| I1 | User-defined center sets (L-067) | #304 | ✅ CLOSED 2026-08-25 (backend + UI + share URLs) |
| I2 | Rh factor input | #180 | |
| I3 | Mobile responsiveness w/ large results | #224 | ✅ 2026-08-27 — tested at 375×812 with 233 centers: layout passes (no overflow, table fits, pagination works). Tap targets below-AA 31/48 → 1/51; sliders 6px→24px hit box with the thin track preserved; nav toggle 30×34→44×44. #224 stays open until this lands; the one remaining target is WCAG's documented inline exemption|
| I4 | Print button scope / methodology linking | #197 / #198 | |
| I5 | Physician directory | #162 | |
| I6 | v2 viz (glyphs, patterned choropleths, what-if sliders) | #181–183 | |

## Phase J — Documentation

| # | Item | Issue | Status |
|---|------|-------|--------|
| J1 | 22-city docs sweep (L-071) + status.md staleness + docs-site algorithm.js claim | #305 | ✅ 2026-08-25 |
| J2 | Inference-mode availability docs | #232 | |
| J3 | Equity disclaimers hardcoded | #235 | |
| J4 | BBN docstrings claim pgmpy | #258 | ✅ 2026-08-27 — docstrings were already correct; the real defect was two user-facing strings blaming pgmpy on ImportError (#258 stays open only if more is wanted) |
| J5 | Refactors: patient_dict dedup, slim routers | #262 ✅ / #264 ✅ | ✅ #262 and #264 both closed |

## Parked (cannot do solo)

- L-060 patient-level SRTR (DUA) · #107 faculty review · #179 BMC account (blocks part of #260)

## Phase K — Pre-merge self-review (2026-08-25)

Full 8-angle code review of `main...backlog-2026-08` (line-by-line diff scan,
removed-behavior audit, cross-file tracer, reuse, simplification, efficiency,
altitude, CLAUDE.md conventions). 10 confirmed findings reported and ALL fixed:

| # | Finding | Fix commit |
|---|---------|-----------|
| K1 | BBN dropped computed data_quality tags → false "fully center-level" claim | engine-parity commit |
| K2 | MCMC engine never migrated to center-code outcomes/trends (national survival, null trends) | engine-parity commit |
| K3 | center_codes shortlist ignored by MCMC, silently dropped by BBN on no-match | engine-parity commit |
| K4 | posterior_checks/convergence missed -full.nc traces (validation said "no trace" while /simulate worked) | find_fitted_granularity |
| K5 | kidney_250nm/continuous per-city adjustments dead in production → volume-quartile size classes for ALL centers | policy size-class commit |
| K6 | npm fetch:all invoked deleted fetch-hospital-quality.js | scripts commit |
| K7 | 4 maintenance scripts broken by the 22-city retirement (srtr-comparison, sensitivity-report, clinical-backtest, bbn-build-profile) | scripts commit |
| K8 | City-keyed weekly data files lost never-shrink guards | validate-data floors |
| K9 | Equity 48-profile loop ~3.5s CPU/request → vectorized to 0.23s (get_wait_time_params) | equity perf commit |
| K10 | Schemas advertised the retired city-only mode (Nashville default → guaranteed 400) | schema-required commit |

Cleanup batch alongside: survival_source "mixed" honesty, PolicyScenarioResult
data_quality/seed_used passthrough, travel-subsidy baseline computed once per
center, granularity coercion parity (state, not full), NASA POWER -999 guard
(and OHCM lung 0.0-survival artifact scrubbed + parser filter), trends
projection lru_cache, register duplicate-ID/format fixes (EQSP-32, MCMC-34),
scoring-constants.js IIFE, dead _CLASSIC_REGIONS/get_city_multipliers/22-city
machinery deleted, last "22 cities" strings retired.

Known deferred (documented, not blocking merge): shared srtr_xls_utils module
for the parser/forecast script duplication; centralized provenance assembly
layer; test suites pin live-data center codes (fixture hardening); state
population table dedup (fetch-trauma vs fetch-traffic).
