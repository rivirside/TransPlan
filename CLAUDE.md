# TransPlan — Claude Session Guide

## What This Is

Transplant center analysis tool at transplant.today. Python/FastAPI backend + vanilla JS frontend on Vercel. 248 SRTR centers, Monte Carlo/BBN/MCMC inference, equity analysis, policy scenarios, spatial interpolation.

## Current State: Rebuild Complete ✅

All 8 rebuild phases (0-7) are done. The structural overhaul that started March 30, 2026 is finished.

**What's next:** See "Post-Rebuild Priorities" below.

### What the Rebuild Accomplished

| Phase | What |
|-------|------|
| 0: Seed & Reproducibility | `seed` param on all simulation endpoints, `seed_used` in responses |
| 1: Nav Restructure | "For Patients" / "For Professionals" mega-dropdowns |
| 2: Simulator Rebuild | 6 modules in `simulator/`, 5 in `shared/`, `simulator.html` rewritten |
| 3: Page Merges | 3 centers pages → 1 tabbed page, 2 explorer pages → 1 tabbed page |
| 4: Model Validation | `validation.html` with 7 analysis sections |
| 5: Inter-tool Linking | URL params + continue buttons across all tools |
| 6: Tier System | Hide unavailable features instead of greyed-out |
| 7: Cleanup & Polish | `script.js` (4889 lines) + `data-explorer.js` (1420 lines) deleted |

### Post-Rebuild Priorities

**Done in the June 2026 session** (see `docs/bbn-rebuild-plan.md`, `docs/limitations.md`):
- **#206 BBN 248-center rebuild — DONE.** CompetingOutcome now grounded in observed SRTR Table B7 rates (not magic numbers); hybrid p24 (WaitCategory timing × observed competing-loss drain) keeps blood-type sensitivity. Closed #209, #210, #211, #226; advanced #214. Full build 11.5s→0.39s (vectorized). Known trade-off tracked: L-072 / #238 (competing-risk split is center-average, not patient-specific).
- **Security/stats audit:** closed #215 (CORS), #218 (X-Forwarded-For), #225 (Gini validation), #229 (zero-rate fallback).
- **Validation:** SRTR per-center calibration (`scripts/run-center-calibration.py`) — Spearman ρ 0.70–0.89. COMET-Lung comparison found infeasible (COMET is population-level, doesn't rank centers) — SRTR calibration is the substitute. Historical SRTR data (2018–2025) retrieved + archived (`data/srtr-archive/`).
- **CI:** green again (was red since March — `netCDF4` missing + SHUTDOWN_TOKEN bug).

**Still open:**
1. **#207** MCMC 248-center refit (BBN done; MCMC not)
2. **#208 audit** — remaining sub-issues (BBN CPT empirical grounding #213/#214 deepening). Closed this session: #216 (equity now closed-form, full 248 centers), #217 (innerHTML XSS).
3. **#237** temporal validation — done as out-of-sample persistence + model concordance (`docs/temporal-validation-report.md`); full fit-on-N/predict-N+k forecast is the remaining follow-up. **#236** continuous BBN latents, **#238** revisit BBN hybrid.
4. **Papers** — owner-driven; do NOT work on `papers/` (rigor/usability/validation work is pre-approved instead)
5. **Old page cleanup — DONE.** `find-centers.html`, `wait-estimator.html`, `data.html` and `spatial.html` are all absent as of 2026-08-28 (verified). What they left behind is CSS: 59 of 196 `@media` selectors reference removed markup, ratcheted by `__tests__/media-selector-rot.test.js` so the rot cannot grow

## Architecture

```
backend/               Python FastAPI (uvicorn, port 8002)
  main.py              Entry point, CORS, static file serving
  routers/             simulate, score, sensitivity, equity, spatial, etc.
  services/            monte_carlo, scoring, bbn_inference, mcmc_inference, etc.
simulator/             Modular JS (IIFE pattern, no build step)
  index.js             Entry point — form → API → table/map
  map.js               Leaflet map with center markers
  tier-panel.js        Fetches GET /tier, applies caps
  form-helpers.js      Home center dropdown, slider wiring
  results.js           Orchestrator (runScoring, runSimulation)
  results-table.js     Sortable table renderer
shared/                Cross-page utilities
  api-client.js        All API calls (TransPlanAPI namespace)
  export-handler.js    PDF/CSV/JSON/RunArtifact export
  data-loader.js       Runtime JSON loader
  continue-buttons.js  Inter-tool linking buttons
  geo-utils.js         Haversine, geocoding
  weight-config.js     Scoring weight sliders
components/
  site-chrome.js       Nav + footer (injected into all pages)
centers-page.js        Centers tabbed page (Find/Browse/Estimate)
explorer/              Explorer tabbed page (Data Layers/Spatial Analysis)
  index.js             Entry point + tab switching
  data-layers.js       Choropleth/heatmap data visualization
  spatial-analysis.js  Spatial interpolation + environmental layers
```

### Pages

| Page | File | Purpose |
|------|------|---------|
| Landing | `index.html` | Hero + feature cards + CTA |
| Simulator | `simulator.html` | Main tool — score + simulate centers |
| Centers | `centers.html` | Find / Browse / Estimate (tabbed) |
| Explorer | `explorer.html` | Data Layers / Spatial Analysis (tabbed) |
| Validation | `validation.html` | 7-section model validation |
| Sensitivity | `sensitivity.html` | Parameter sensitivity analysis |
| Scenarios | `scenarios.html` | Policy scenario comparison |
| Equity | `equity.html` | Demographic equity auditing |
| Center Detail | `center.html` | Single-center deep dive |
| Patient Resources | `checklist.html`, `education.html`, `faq.html`, `organ-guides.html`, `support.html`, `advocacy.html` | Patient-facing content |

## Dev Server

```bash
# Backend (serves API + static files)
cd /Volumes/Lab/GitHub/TransPlan
source .venv/bin/activate          # local .venv is Python 3.12.11; .python-version is "3.12" (major.minor only — a patch pin like 3.12.11 breaks Vercel's uv runtime, which can't fetch exact patches)
uvicorn backend.main:app --port 8002 --reload

# Or use .claude/launch.json preset:
# preview_start with name "backend"
```

## Key Patterns

- **IIFE modules:** All JS uses `(function() { 'use strict'; ... window.ModuleName = { ... }; })()` pattern
- **No build step:** Vanilla JS, loaded via `<script>` tags at bottom of `<body>`
- **DOMContentLoaded fix:** Use `if (document.readyState === 'loading') { addEventListener... } else { init(); }` because scripts at bottom of body run after DOMContentLoaded fires
- **Tier system:** `GET /tier` returns caps; `tier-panel.js` hides/caps UI controls server-side
- **URL params:** Tools pass patient profile via `?organ=kidney&bt=O%2B&age=45&sex=male&urg=2`
- **Two buttons:** "Score Centers" (POST /score, instant) + "Run Simulation" (POST /simulate, Monte Carlo)

## Tests

```bash
# Python tests — must run from backend/ so services imports resolve
cd backend && python -m pytest -q         # all tests (requires .venv active)
cd backend && ../.venv/bin/python -m pytest -q  # without activating venv
# 838 pass on pymc 6.0.1, including the MCMC suites. (The MCMC tests need the
# netCDF4/h5netcdf backends in requirements.txt to serialize traces — without
# them they error out, which looks like a pymc-version problem but isn't.)

npm test                                  # 44 Jest tests (from repo root)
```

## Inference Modes

`docs/inference-modes.md` — which engine runs where and what each needs.
Availability is **three-way**, not two: web (monte_carlo + bayesian), a fresh
local clone (same — the 285MB MCMC traces are gitignored), and local after
`scripts/fit-mcmc-model.py --all` (~15-30 min). The BBN uses the in-house
`bbn_lite.py`, **not pgmpy**. Pinned against `tier_config.py` by
`backend/tests/test_inference_mode_docs.py`.

## Landscape & Benchmarking

See `docs/landscape/` for 7 tool profiles (SRTR, KPSAM/LSAM/TSAM, COMET, LivSim, TransplantCenterSearch, statistical packages) and the comparison matrix. Benchmarking plan: COMET-Lung rank comparison is Priority 1.

## Clinical Assumptions Register

`docs/clinical-assumptions-register.md` — the living catalog of **every point where a clinical/medical judgment is encoded or clinically-derived data is used** (scoring weights, ABO/MELD/LAS multipliers, hazard model, copula θ, BBN CPTs, MCMC priors, equity/spatial/policy assumptions, the data files + generation clamps). Each entry has a stable ID, location, justification status, and risk. **227 assumptions tracked; 129 still need justification; 57 high-risk** (counts AND the priority shortlist are regenerated by `scripts/check-register.py`, pinned by `backend/tests/test_register_counts.py` — before #335 the header had drifted to 129/37/45 and the shortlist named 5 rows that no longer qualified while missing 11 that did, because nothing recomputed either) — see the "Priority to justify" shortlist at the bottom. **Keep it updated:** add/adjust a row whenever a clinical value or assumption is introduced, changed, or finally cited.

## Open Issues

Snapshot **Aug 28, 2026** — 58 open. **Closed Aug 27-28** (13 PRs, #411-#423): #227/#228 (per-center provenance), #180 + #413 (Rh), #302-partial, #232 (inference-mode docs), #235 (equity disclaimers), #197/#198 (print + methodology), #137 (drift comparison), #296-partial, #299-partial, #233-partial.

**Pre-rebuild issues: verify the target before trusting the content.** Four issues this sweep described pages or lists that the Phase 3 merge removed — #180 (`find-centers.html`), #183 and #181 (`data.html`), #162 (the 22-city list). Each was filed before the rebuild and read as current. All 58 open issues were scanned on 2026-08-28 for references to removed pages; **only #181 remains**, and it is flagged in-thread. Worth re-running that scan after any future page merge rather than discovering it one issue at a time.

**The pattern in that sweep is worth carrying forward.** Of twelve items picked up, **nine had a materially wrong premise**, and in three the requested change would have made the tool worse:

| item | asked for | measured |
|---|---|---|
| #180 | add an Rh input | already present, and the model *over*-applied Rh by ~3 months of kidney wait |
| #296 | Dirichlet credible intervals | **narrower** than the shipped binomial band — would have reduced disclosed uncertainty |
| #235 | externalise disclaimers to config | would move claims *further* from the code that makes them true |
| #299 | validate or downgrade the proxy's weight | it has **no weight** — scoring never imports it |
| #233 | add literature citations | the constant needed *scope*: it cannot affect p24 at all, but is a 4x lever on displayed mortality |

**Four defects reached real users, and none were what the issue described:** a printout for a care team carried **no medical disclaimer** (dead `::after` selector after the rebuild); Rh-negative candidates saw **+2.74 months** of kidney wait from a hand-set constant; a center with a **2-patient** cohort got the same confidence interval as one with 833; and rows ranked on national averages carried no indication.

**The recurring failure mode: things that cannot fail read as coverage.** The print stylesheet's dead selectors, the snapshot tool's 0/0/0 competing risks, the CI that ignored cohort size, two stale equity disclaimers — all green, all inert. Twice the same bug was reproduced *in the fix for it* (the comparator and then the renderer both reported 0 for "could not compare"). **A zero meaning "not measured" must be `None`, and must be said out loud.**

**Corollary, learned the hard way twice:** before believing a null result, force the input to an extreme and confirm the metric moves. BBN-19's first sweep reported worst Spearman 1.00000 across 32 comparisons — a flawless null produced by a metric that was *algebraically* blind to the thing being swept.

Snapshot Aug 26, 2026. **Closed in #370** with evidence: #335 (pediatric mode), #328 (model card + docs-site routing), #350 (parameter audit), #336 (county trauma), #337 (waitlist-composition equity weights), #113 (coverage gaps).

**Opened by that work:**
- **#371:** BBN and MCMC have no pediatric wait model (L-079) — they restrict to pediatric centers but return adult numbers, currently disclosed via a `pediatric_wait_model` provenance family rather than fixed
- **#372:** PELD mapped onto MELD's thresholds without a published equivalence (SCORE-31 / L-078)
- **#373:** Remaining unexposed API parameters after the #350 audit

**Closed by measurement, Aug 26 (second wave).** Six modeling issues resolved by measuring rather than building — and the measurement was cheaper than the implementation every time:

| issue | verdict |
|---|---|
| **#266** kriging projection | Albers changes RMSE by **0.2%** — projection clause rejected, not built |
| **#274** log_sigma clamp | raising the 1.2 ceiling makes calibration **worse** on every assessable organ; DATA-07 `heuristic_clamp`→`data_derived` |
| **#297** delisting multipliers | hazard **FALLS** with waiting time for 4 of 6 organs — shipped values have the wrong **sign**, not magnitude (L-081, replacement filed as #380) |
| **#213** BBN discretization | swung 90/9/1 → 50/35/15, worst ρ **0.9987** — not load-bearing; BBN-01 medium→low |
| **#214** donor-supply multiplier | **removing the effect entirely** leaves ρ 0.9957. Sensitivity half closed; the ad-hoc-formula and MortalityRisk-interaction halves stay OPEN |
| **#376** pancreas median | raising it toward SRTR's censored ">72" **degrades** calibration (1.11×→1.40×) — fixed by disclosure, not substitution |

**The one that was NOT inert — and it is the headline output.** SCORE-01's eight scoring weights: under *defensible* alternative weightings the worst rank correlation is **0.624**, top-10 overlap falls to **3/10**, and **the top-ranked center changes in 13 of 16 comparisons**. The existing ±20% single-category sweep missed this because it tests robustness to a nudge, not dependence on whose judgement set the numbers. Now L-082 (HIGH), a model-card section, and a note in the simulator's weights panel. #386 tracks the harder fix: the score ranking has **no** uncertainty interval, and the #313 intervals rank by `p24` while holding weights fixed — so they omit the largest source.

**Aug 27 — pulling that thread found what the ranking is really made of.** Closing #386 (`/weight-range`, rank span across the app's four presets) led to a chain where each measurement exposed the next, and the result reframes L-082 rather than confirming it:

| finding | evidence |
|---|---|
| **L-082 was about the ORDERING, not the magnitudes** | holding the category order fixed and sampling the ordered simplex — no spread parameter, sampler verified against the closed-form order statistics — gives worst ρ **0.905**, vs 0.624 when categories are *reordered*. Reordering is a genuine preference the presets already expose |
| **L-084: a quarter of the score cannot reorder anything** | `medicalCompatibility` carries the **largest** weight (0.25) and is identical at every center (SD 2.8e-14) — `_medical_compatibility()` takes only the patient profile. `waitTime` actually carries ~half the rank-driving variation |
| **the null above is partly an artifact** | the inert term sits in the slot that absorbs the most sampled mass, so the sampling is less potent than it looks. Both reports and L-082 carry this caveat rather than claiming a clean null |
| **L-083 explained, not just observed** | lung's undetermined top is the one organ where no category dominates (hospitalQuality 33.2% vs waitTime 31.4%). Symptom and mechanism agree |
| **L-085: blood type produces a literally identical ranking** | it reaches exactly one sub-score — the inert one. O− and AB+ give the *same list* for every organ, while simulation correctly shifts p24 by **+0.2524**. Magnitudes personalised, ranking not |
| **the defect is the asymmetry** | cPRA reorders at ρ 0.760, blood type at ρ 1.000 — two immunological access constraints treated differently with nothing documenting why (#394) |
| **the two engines disagree** | kidney cPRA: scoring ρ 0.760, simulation ρ 0.996, both shown in the same table |

`weight x between-center SD` (what the ranking is *made of*) and per-input reachability are cheap diagnostics worth running early — see `scripts/run-category-variance.py` and `scripts/run-patient-sensitivity.py`. Open: **#390** (should the sub-score be center-specific? a measurement, not a relabelling), **#394**.

**Also fixed by measuring rather than assuming (#391):** `test_two_runs_within_tolerance` was filed as an unseeded flake; measurement showed the premise was too kind — it ran at ~89% of its own hand-set tolerance with p95 already over it. Now derived from the binomial SE, *verified* not assumed (empirical/binomial SD 0.995), Bonferroni-corrected across 233 centers, and validated in both directions (0/25 seed pairs fail at 61% margin; still flags 27 centers when genuinely unstable).

**Blocked on environment, not effort:** #323 (drive-time matrix) needs a self-hosted OSRM build — Docker daemon plus a ~10GB US OSM extract and hours of preprocessing. #267 (2SFCA) waits on it; its demand side is unblocked now that county population exists. `scripts/run-coverage-gaps.py` is written so swapping the distance function is the only change required.

**Still open from before:**
- **#285:** Epic — retire the 22-city list (inventory + phased plan; supersedes #205/#234 remainders; #207 is its first phase)
- **#270:** 2026-06 code-review epic — still-real remainder: #244 (BBN horizon), #249 (tier caps on /score), #251/#252/#254/#257/#258/#259 (statistical validity), #262/#264 (refactors), #260 (donation-banner, blocked on #179), #250 (exact dependency pins)
- **#207:** MCMC 248-center refit (BBN #206 done)
- **#236/#237/#238, #275:** BBN latents / temporal validation / BBN hybrid / volume data (#274 closed by measurement)
- **#107:** Face validity review with transplant faculty
- **Model limitations:** see `docs/limitations.md` — 98 entries. **Highest-consequence open:** **L-095** (the BBN's displayed waitlist mortality is a 4x lever on an uncited hazard-shape constant, and #297 suggests the shipped value overstates it — #233), **L-089** (2018 donor-registration data decides the top-ranked center; no machine-readable source, #302), **L-087** (centers missing SRTR data are ranked on national averages — marked `†` per row since #412, but still ranked), **L-085** (blood type cannot change which center is recommended — the ABO fix was measured and rejected, #405), **L-084** (a quarter of the score is a constant that cannot reorder), **L-086** (small-cohort clamping — FIXED for kidney in #402, open for the other five), L-082 (the ranking turns on the weight *ordering*), L-079, L-081, L-080, L-078, L-076/L-077, L-083. **Fixed Aug 27-28:** L-088 (Rh penalty removed, #415), L-090 (freshness measured script runs not data age, #416), L-091 (equity disclaimers unverified; two had gone stale, #418), L-092 (print stylesheet 20/24 dead — the medical disclaimer never printed, #419), L-093 (the Monte Carlo "95% CI" was simulation error and shrank with iterations, #420), L-094 (the drift detector recorded zeros for the vector it watched, #421).

**Data-pipeline lesson (2026-08-05 incident):** the SRTR workflow once overwrote three model files with organ-less shells because `data/srtr-raw/` is absent in CI. Every generated data file must have a never-shrink guard (`_write_guarded` in parse-srtr-reports.py, dead-data guards in fetch-cost-of-living.js, organ-block checks in validate-data.js).

**Aug 28 — that rule was followed, and still missed almost everything (#444, #445).** A guard can be real, correct, and pointed at something that no longer matters. Asking *"what protects the data this thing runs on?"* produced a chain where every answer was one level up:

| | |
|---|---|
| `_write_guarded` covered the three legacy 22-city aggregates (2–4K) and **none** of the four center-level files (20–278K) the model runs on | the guard predates Phase 6A |
| it could not have seen them anyway — it counts organ blocks at *top level*, and those files keep organs below a container of 248 center codes | **248 → 3 passes clean** |
| `srtr-all-centers.json`, the master center list, appeared in validation only as the **denominator** of another file's check | coverage by coincidence |
| `srtr-tiers-centers.json` was floored on **kidney alone** | a floor on one organ reads as a floor on the file |
| `srtr-observed-rates.json` — the calibration **ground truth**, read by 15 modules — had no floor, and the join silently skips unmatched centers | a truncated ground truth makes calibration agree with itself and report a healthy ρ |
| `run-center-calibration.py --organ kidney` **deleted** the other five organs from the committed report | not stale — gone |
| `unparsed_rows()` in check-backlog.py, whose docstring names this exact hazard, was **never called** | |

**Three habits that did the work.** Ask what protects the data a gate measures *against*, not its output. Sweep for the **pattern** — "takes a subset argument, writes a whole shared artifact" found the calibration report *and* the fetcher for its ground truth. And prefer **"no entry = error"** over a lenient default in any coverage table: the matched-center floor first had `.get(organ, 10)`, and deleting lung's floor left the suite green because the fallback swallowed the negative test for its own absence.

Durable parts, since fixing the files is not the point: `tests/data-file-floors.test.js` (every per-center container floored *by name*, with its own detector check so it cannot pass vacuously), `tests/data-file-coverage.test.js` (every file in `data/` validated or exempt, exemptions capped and reasoned), and `backend/tests/test_row_disclosure_matches_data.py` (every national substitute a patient sees is marked, checked against the source files rather than the engine's own tags — 0 undisclosed, 0 spurious).

**Aug 28 (second half) — the same question asked of the SCORING path (#446, #448).** "What protects the data this runs on?" has a sibling: *what does the code do when the data is absent?* Two defects in one function, both patient-facing, neither pinned by any of the 1542 tests:

| | |
|---|---|
| `_hospital_quality` looked up SRTR's rating in a table keyed `lower_than_expected`; the parser emits `worse_than_expected` | **22 centers SRTR flagged as statistically underperforming were never penalised** — they took the default 70, above the intended 55. One lung center ranked **#3** |
| `scoring_explain` rendered users a row labelled "Underperforms benchmark" on that same dead key | the UI documented a penalty the model could not apply |
| a center with **no** outcomes record was scored as though SRTR rated it `as_expected` | SRTR publishes `insufficient_data` for exactly this, and 154 records already carry it |
| `n_1yr` defaults to **0** — 40% of the category — for 91 center-organ pairs (33% of pancreas, 43% of intestine), all scoring exactly 46.8 | undisclosed: `TAG_OUTCOMES` reads `srtr-observed-rates.json`, a *different* file |

**The zero was measured and deliberately kept.** Centers missing post-transplant outcomes have a median waitlist cohort of **17 vs 166** (kidney), **9 vs 92** (liver) — SRTR suppresses small programs, so the zero is directionally right and a national-median substitute would promote genuinely tiny programs ~90 category places. Fixed by disclosure, per #274/#376.

**A rescoring of 113 center-organ records broke zero tests.** That is the finding, not the relief.

**Two failure modes only the browser found**, with the backend correct and green: `results-table.js` silently drops any tag missing from `DQ_LABELS`, so all 91 rows were tagged and *nothing rendered*; and the tooltip then said "the national average is used instead" where the model actually substitutes **zero**. **A fallback message wrong in the reassuring direction is worse than none** — "national average" sounds like an estimate, "counted as zero" is a claim about the center. Drive the DOM and read the rendered text; and note that a test helper which re-derives un-exported logic is checking its own copy (collapsing a branch in the shipped code left one green).

**Check your expectation before calling something a bug.** That last one took three wrong expectations first: `TAG_OUTCOMES` reads `srtr-observed-rates.json`, not the similarly-named `post-transplant-outcomes-centers.json`, and the acceptance tag is absent because acceptance modelling is off by default. Each wrong source made correct machinery look broken — in both directions.

**Aug 27 (second wave) — the approved plan ran end to end.** Phases 0-4 of
`~/.claude/plans/clever-purring-sedgewick.md`. What shipped, and what did not:

| phase | outcome |
|---|---|
| **1a #268** | EB shrinkage before the clamp. Kidney centers pinned to a bound **60 → 0**; tiny cohorts in the top 10 **4 → 1**. **Kidney only** — heart (−0.0342) and liver (−0.0119) *degraded* calibration, measured in a controlled all-organ comparison |
| **1b L-083** | The table now says "N centers could be ranked #1" (lung 3, heart 7, liver 7, kidney 10) |
| **1c #224** | Layout passes at 375px with 233 centers. Tap targets below WCAG AA **31/48 → 1/51**; sliders 153×**6** → 24 |
| **2 #390/#394** | ABO-by-center term built, gated, and **rejected** — premise unsupported, term degraded agreement |
| **3 #250** | 51 pieces of inline JS removed, then a **strict CSP with no `script-src 'unsafe-inline'`**; all 8 CDN resources pinned + SRI |
| **4** | #301 closed, #236/#275 retitled, #259/#260 dispositioned |

**Gates lie in specific ways — check they can see your change.** Three times
this wave a green gate was meaningless: `run-center-calibration.py` defaults to
`--organ lung`, so five of six organs were never recomputed; a committed
baseline predated a same-day merge and conflated two changes; and the
calibration metric correlates p24 from the Monte Carlo path, so it is
*structurally blind* to any scoring-path change (forcing the ABO factor to its
bound moved p24 by exactly 0.000000). Before trusting "no degradation",
perturb the input to its bound and confirm the metric moves at all.

**Static analysis cannot find CSS-referenced resources.** The first strict CSP
blocked every Leaflet map marker, because `leaflet.css` references its icons
from inside the stylesheet — no HTML mentions them, so a scan of the markup
reported the policy complete. Visible to a user, invisible to the test suite.

**Measure before you build.** Six of the modeling issues closed on Aug 26 were resolved by measuring the concern rather than implementing the requested fix, and in two cases the requested fix would have made the model *worse* (#274's clamp raise, #376's median substitution). Before implementing an issue that proposes a specific change to a constant, sweep it and check the change actually helps. Every such measurement ships with a test that fails if the finding stops holding, so the conclusion can be re-opened by evidence rather than inherited on authority. The reverse also applies: a constant recorded as a mere provenance nit (SCORE-01) turned out to drive the headline output.

**Guard lesson (#370):** a guard that cannot fail is worse than none, because it reads as coverage. Two shipped in this state — `parse-waitlist-composition.py` checked that a vector summed to 1 *after normalizing over whatever survived*, so a renamed SRTR column would have produced "the kidney waitlist is 100% male" and passed; and `fetch-trauma-counties.py` silently dropped two centers because both fallback branches were conditional. **Negative-test every new guard** by breaking the data on purpose and confirming it fails with the remedy in the message.
