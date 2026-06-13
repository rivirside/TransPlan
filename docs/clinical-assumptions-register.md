# TransPlan Clinical-Assumptions Register

## Purpose

This register tracks **every point in TransPlan where a clinical or medical judgment is encoded, or where clinically-derived data is used** — i.e. everything that would need justification for peer review or clinical use. That includes scoring weights, blood-type/severity-score multipliers, hazard models, copula dependence, Bayesian-network conditional-probability tables, MCMC priors, equity/spatial/policy assumptions, the clinical data files, and the scripts that generate them. Fallback defaults, numerical clamps, and validation thresholds are included where they shape a clinically-meaningful output.

This is a **LIVING document.** Maintain it as follows:
- **Add a row** whenever a clinical value or assumption is introduced or changed in code, data, or a generation script. Give it the next stable ID in its subsystem (e.g. `SURV-NN`).
- **Update the `Status`** when a citation lands (→ `cited`/`partially_cited`), when a value becomes data-fit (→ `data_derived`), or when a placeholder is replaced.
- **Update `Risk`** if downstream sensitivity analysis changes how much the value matters.
- Keep `Source / Notes` honest: record both what backs the *form/direction* of an assumption and what is still hand-set (magnitudes, clamps, fallbacks).

## Status legend

| Status | Meaning |
|--------|---------|
| `cited` | Backed by a specific external source (paper, registry table, policy document). |
| `partially_cited` | The form/direction is cited or policy-grounded, but exact magnitudes are hand-set/estimated. |
| `data_derived` | Fit or computed from real data (usually SRTR/CDC); not externally validated against outcomes. |
| `assumed` | Hand-set with stated reasoning but no external source. |
| `uncited` | Hand-set with no source and no documented rationale. |
| `heuristic_clamp` | A numerical floor/ceiling/cap/guard or fixed-band heuristic, not a clinical estimate. |

**Summary:** **120** assumptions tracked after dedupe. **38** still need justification (`uncited` + `assumed` + `heuristic_clamp`). **45** are flagged **high-risk** (`risk_if_wrong = high`); the high-risk entries that are also unjustified form the priority shortlist at the end.

**Recent updates:** PR #279 resolved **MCMC-19** (convergence trace-path bug — diagnostics now run on real fitted traces) and relabeled the MCMC internal-consistency cluster (**MCMC-21/23/24**) with honest "not external validation" framing pointing to the SRTR per-center calibration. The underlying assumptions persist (status unchanged) but the misleading framing is addressed.

---

## 1. Scoring (location-suitability engine)

| ID | Location | Assumption | Clinical basis | Status | Risk | Source / Notes |
|----|----------|------------|----------------|--------|------|----------------|
| SCORE-01 | scoring.py:20-29 | 8-category top-level weights (medCompat 0.25, wait 0.20, donor 0.18, hospQual 0.15, geo 0.10, health 0.07, policy 0.03, socio 0.02) | Relative clinical importance of each factor cluster | uncited | high | Duplicated in algorithm.js:26-35; no ADR/citation for magnitudes; exposed as sliders but defaults unsourced |
| SCORE-02 | weight-config.js:22-45 | Weight presets Clinical / Speed / Quality-of-Life | Each preset encodes a patient-priority stance | uncited | medium | Hand-set alternative vectors, no rationale |
| SCORE-03 | scoring.py:85-89 | ABO blood-type compatibility scores (O- 70 … AB+ 100; fallback 85) | Proxies donor-compatibility breadth / waitlist competition by ABO/Rh; 40% of medCompat | uncited | high | Direction sensible, magnitudes hand-set. Dup algorithm.js:105-114, scoring_explain.py:69-95 (self-labeled "compatibility proxy") |
| SCORE-04 | scoring.py:92-105 | Age scoring brackets (<18:115 … else 75); 25% of medCompat | Younger tolerate transplant better / pediatric priority | assumed | medium | scoring_explain.py:130-134 self-documents as heuristic. Dup algorithm.js:118-126 |
| SCORE-05 | scoring.py:108-112 | Thoracic sex/size penalty (heart/lung female 95 else 100) | Smaller female body narrows thoracic donor pool | assumed | medium | L-005 (FIXED e6f5d10) made it organ-specific; 5% magnitude uncited |
| SCORE-06 | scoring.py:115-125 | BMI size-match scores (thoracic only): <18.5→85, >35→80, normal→100 | Under/overweight harder to size-match heart/lung | partially_cited | medium | WHO BMI cutoffs 18.5/35 standard; 85/80/100 magnitudes uncited. Dup algorithm.js:138-146 |
| SCORE-07 | scoring.py:135-144 | Kidney cPRA wait-time multiplier curve (up to ~5.0x) | Sensitization lengthens kidney wait | partially_cited | high | data-provenance Phase2: OPTN cPRA point tiers; multiplier magnitudes hand-fit. Dup algorithm.js:70-77 |
| SCORE-08 | scoring.py:146-154 | Liver MELD wait multiplier bands (≥35:0.15x … else 2.0x) | Higher MELD = sicker = faster transplant | partially_cited | high | OPTN MELD policy (Phase2, L-002); cutoffs/magnitudes hand-set. Dup algorithm.js:78-84 |
| SCORE-09 | scoring.py:156-162 | Lung LAS wait multiplier bands (≥50:0.3x … else 1.2x) | Higher LAS = faster transplant | partially_cited | high | OPTN LAS policy (Phase2, L-003); magnitudes hand-set. NOTE: LAS replaced by CAS in 2023. Dup algorithm.js:85-90 |
| SCORE-10 | scoring.py:164-165 | Default urgency multiplier table {1:0.3,2:0.6,3:1.0,4:1.4} | Acuity proxy for organs without standardized score | uncited | medium | L-002/L-003 note 1-4 scale is oversimplified. Dup algorithm.js:91-92 |
| SCORE-11 | scoring.py:33-40 | BASE_WAIT_TIMES per-organ min/max years | Baseline national expected-wait windows | partially_cited | high | Aligns with SRTR national medians; specific ranges not directly cited. Dup algorithm.js:53-60 |
| SCORE-12 | scoring.py:179 | max_wait normalizer = organ max × 1.5 | Wait length mapping to score 0 | heuristic_clamp | medium | Arbitrary 1.5x headroom. Dup algorithm.js:167 |
| SCORE-13 | scoring.py:213-216 | State donor-registration normalization (÷69, fallback 35); 39% of donorAvail | Higher registration = larger deceased-donor pool | cited | medium | Donate Life America 2019 (2018 DDR), L-033; /69 = Colorado anchor. 39% raised from 35% per L-008 (uncited reallocation) |
| SCORE-14 | scoring.py:220-235 | State population-proxy score table (NY 100 … MS 50; fallback 60); 25% of donorAvail | Deceased-donor pool by state population/metro density | assumed | medium | ADR (adr-log:183-185)+L-033: manually curated by design. JS uses city-keyed, Python re-keyed to states |
| SCORE-15 | scoring.py:238-245 | Living-donor program strength (substring state match, fallback 75); 28% of donorAvail | Living-donor program strength affects availability | assumed | medium | L-033 manual estimates; substring-in-state matching is a fragile fallback (data city-keyed). 28% raised from 25% per L-008 |
| SCORE-16 | scoring.py:247-249 | Trauma/donor-pool proxy weight 8% + fallback 65 | MVA/trauma fatalities as deceased-donor proxy | partially_cited | low | L-008 (FIXED) cites modern donor epidemiology for 15%→8% cut; 8% & 65 hand-set. Traffic data NHTSA FARS |
| SCORE-17 | scoring.py:185-205 | Cause-of-death organ-availability multiplier | Donor availability by regional COD mix × per-organ recovery rates | cited | medium | organRecoveryRates PMC10329409 (Sundaram 2023) x-val vs OPTN 2023 (ADR-017); state COD CDC 2017. Toggle default OFF. Dup algorithm.js:182-199 |
| SCORE-18 | scoring.py:44-47 | VOLUME_THRESHOLDS high-volume cutoffs; 40% of hospQual | Volume-outcome relationship | assumed | high | scoring_explain.py:472-474 asserts relationship "well-established" but no citation for thresholds. n_1yr real SRTR; cutoffs hand-set |
| SCORE-19 | scoring.py:276-282 | SRTR performance-rating score map (100/80/55/70) | Maps SRTR categorical tiers to 0-100 | partially_cited | medium | Ratings real SRTR PSRs; numeric encoding (esp. 55/70) hand-set |
| SCORE-20 | scoring.py:285-292 | 1-yr graft-survival normalization (80%→0, 100%→100; fallback 70) | Linear remap of graft survival | assumed | medium | graft_survival_1yr real SRTR; 80/100 window & fallback hand-set; below 80% scores 0 |
| SCORE-21 | scoring.py:294-300 | Insurance-acceptance penalty (base 85; medicaid ×0.85, uninsured ×0.70) | Medicaid/uninsured access barriers | assumed | medium | L-006 (FIXED 520b13a) wired at 15%; penalty magnitudes uncited; base 85 flat hand-set |
| SCORE-22 | scoring.py:312-314 | Cost-of-living normalization window [80,200]; 40% of geo | Lower COL better | heuristic_clamp | low | algorithm.js:349-350 marks 80/200 FIXME. JS derives min/max dynamically; Python static window more brittle |
| SCORE-23 | scoring.py:317-324 | Geographic climate (35%, fb 70) & air-quality (25%, fb 70) sub-weights | Recovery environment | uncited | low | Climate "Derived from NOAA/historical" (loose); sub-weights/fallbacks hand-set. Dup algorithm.js:355-362 |
| SCORE-24 | scoring.py:335-348 | Health-demographics penalty coefficients & baselines (diabetes-7×2, etc.); 7% category | Regional disease prevalence implies worse donor pool | uncited | high | Disease rates CDC PLACES; baselines (7,25,11,27,13) & multipliers (2,1.5,2.5,1.0,1.5) uncited. Dup algorithm.js:387-391 |
| SCORE-25 | scoring.py:348 | Health-demographics score floor (30) | Prevents category dropping below 30 | heuristic_clamp | low | Arbitrary floor |
| SCORE-26 | scoring.py:353-357 | State policy-tier scores (fallback 70); 3% category | State donation laws/Medicaid/mandates as 0-100 tiers | assumed | low | data/manual/policy-tiers.json from HRSA+state legislation review (manual). L-024 fixed CA/WA drift vs algorithm.js:401-411 |
| SCORE-27 | scoring.py:369-384 | State socioeconomic support index (51 rows; fallback 75); 2% category | Transplant-specific support (housing/financial/groups/caregiver/literacy) | assumed | low | ADR-009 (L-022) documents rubric; values hand-assigned. Python state-keyed vs algorithm.js:421-430 city-keyed (different granularity) |
| SCORE-28 | scoring.py:443-455 | Custom-weight normalization gate (silent fallback to defaults) | Whether a user reweighting is honored | assumed | low | Silent fallback could mask intent. Mirrors algorithm.js:437-452 |
| SCORE-29 | scoring.py:67,168-180 | Generic spatial-interpolation fallback default 50.0 | Mid-scale neutral for missing surface | heuristic_clamp | low | Callers override with topic-specific fallbacks |

---

## 2. Survival & Competing Risks

| ID | Location | Assumption | Clinical basis | Status | Risk | Source / Notes |
|----|----------|------------|----------------|--------|------|----------------|
| SURV-01 | competing_risks.py:4-9 | Independent exponential competing-risks hazard model (constant hazard) | Memoryless waitlist mortality/delisting; no Weibull/time-varying | assumed | high | L-058 (independence optimistic); no source for exponential-vs-Weibull. Clayton copula mitigates dependence but hazard shape stays exponential |
| SURV-02 | competing_risks.py:163 | Fallback annual mortality 0.08 (unknown organ) | Default waitlist mortality | uncited | medium | Hand-set, fires only for unrecognized organ |
| SURV-03 | competing_risks.py:197 | Fallback annual delisting 0.05 (unknown organ) | Default delisting rate | uncited | medium | Hand-set, no source |
| SURV-04 | competing-risks.json:11-76 | Per-organ annual mortality & delisting base rates | Core competing-risk hazards | data_derived | high | SRTR PSR Table B7, Jan 2025. Died-on-waitlist = mortality proxy; removals (worsened+other+refused) = delisting proxy |
| SURV-05 | competing-risks.json:14-75 | Urgency mortality multipliers per organ | Higher urgency status → higher waitlist mortality | partially_cited | high | data-provenance "Manual; literature-derived"; SRTR 2023 ADR Table 5.3 for form; magnitudes hand-set |
| SURV-06 | competing-risks.json:30-35 | Liver MELD mortality multipliers ({6-14:0.5 … 36-40:3.5}) | MELD predicts waitlist mortality | partially_cited | high | data-provenance "literature-derived"; 0.5/2.0/3.5 hand-set |
| SURV-07 | competing-risks.json:77-167 | City-level mortality & delisting adjustment factors (22 cities) | Region relative mortality/delisting vs national | data_derived | medium | SRTR Table B7, averaged across organs; 22-city fallback path only |
| SURV-08 | competing_risks.py:65-97 | Gamma-Poisson empirical-Bayes shrinkage of per-center rates | Shrinks noisy small-center rates toward national mean | data_derived | medium | #268 (replaces old [0.3,3.0] clamp); DerSimonian-Laird. Exposure E_i=n_i/100 is an assumption; σ²≤1e-12 numerical clamp |
| SURV-09 | competing_risks.py:139-141 | Stored clamped center-ratio fallback (legacy [0.3,3.0]) | Per-center factor when EB table has no row | heuristic_clamp | medium | #268; unobserved centers still carry the clamp floor/ceiling |
| SURV-10 | distributions.py:62-87 | _age_sex_multiplier wait adjustment (age<35 ×0.95, ≥55 ×1.10; kidney M ×1.05/F ×0.95) | Demographic effect on wait via size-match/comorbidity | partially_cited | medium | Docstring cites OPTN/SRTR 2023 ADR (#48); no table/figure; magnitudes hand-set. Only kidney gets sex effect |
| SURV-11 | distributions.py:137-138 | Fallback wait distribution lognorm(s=0.8, scale=24.0) (unknown organ) | Default wait dist | uncited | low | Hand-set, logged; fires only for unrecognized organ |
| SURV-12 | wait-time-distributions.json:13-118 | Per-organ national median wait (months) | Median time-to-transplant; log-normal scale param | data_derived | high | SRTR PSR Table B10 fit by parse-srtr-reports.py; mu=ln(median) from P50 |
| SURV-13 | wait-time-distributions.json:14-117 | log_sigma per organ (clamped [0.3,1.2]; 4 organs at 1.2 ceiling) | Dispersion → right-tail / long-wait probabilities | heuristic_clamp | high | #256 IQR method then clamp; ceiling acknowledged to likely understate dispersion (true σ exceeds 1.2). Affects tail tx probabilities |
| SURV-14 | wait-time-distributions.json:15-120 | ABO blood-type wait multipliers per organ | O waits longest, AB shortest | partially_cited | high | data-provenance: literature-derived; Table B10 doesn't stratify by blood type. Ordering standard, magnitudes estimated |
| SURV-15 | wait-time-distributions.json:25-91 | cPRA/MELD/LAS clinical wait multiplier bands | Severity scores drive priority/match | partially_cited | high | data-provenance: based on cPRA/MELD/LAS allocation rules; magnitudes hand-set (e.g. cPRA 98-100 → 5x) |
| SURV-16 | wait-time-distributions.json:123-147 | City wait-time factors (22 cities) | Regional wait multiplier vs national | data_derived | medium | SRTR Table B10, avg center-median/national-median; 22-city fallback path |
| SURV-17 | distributions.py:147-150 | Per-center wait-factor fallback default 1.0 | Neutral when center/organ missing | assumed | low | Reasonable but unstated |
| SURV-18 | config.py:41-44 | Score drift rates (MELD +2.5/yr; LAS -1.0/yr) | Disease scores worsen over wait | partially_cited | medium | Cites Volk 2006/Bambha 2008 (MELD), "estimates" (LAS) — NONE in paper.bib; cannot verify magnitude tie |
| SURV-19 | config.py:45-48 | Score-drift caps (MELD ceiling 40, LAS floor 0) | Scale bounds | cited | low | MELD true scale ceiling; LAS floor reasonable |
| SURV-20 | config.py:50-52 | Piecewise drift interval boundaries [0,6,12,18,24,36] mo | Resolution for time-varying drift | assumed | low | Modeling-resolution choice; distributions.py:282 hardcodes max_months=60 |
| SURV-21 | config.py:15 | SUPPLY_WAIT_ELASTICITY = 0.65 | Sublinear queuing response of wait to donor supply | partially_cited | medium | L-056: queuing theory + SRTR empirical range 0.5-0.8; 0.65 within-range pick, not fit |
| SURV-22 | config.py:20 | COPULA_THETA global default 1.0 (Kendall τ ~0.33) | Lower-tail dependence mortality↔delisting | partially_cited | medium | ADR-025/L-058 "conservative from SRTR analyses"; no magnitude citation. Form (Clayton) clinically justified |
| SURV-23 | config.py:29-36 | Per-organ Clayton copula theta (kidney 0.8 … heart 1.8) | High-acuity organs assumed stronger correlation | assumed | medium | Comment candid: clinical-acuity heuristic ordering, not calibrated (L-059/#255/ADR-025); absolute τ illustrative |
| SURV-24 | copula.py:38-88 | Clayton conditional-sampling form + numerical clamps | Simultaneous death/delisting acceleration under decline | cited | low | Nelsen 2006 (paper.bib nelsen2006). Clamps 1e-300/1e-15 are numerical guards |
| SURV-25 | stats_utils.py:44-58 | rate_to_exponential_scale (scale = 12/rate; zero→1e6) | Annual rate as constant exponential hazard | assumed | high | #229 for zero handling; conversion standard given exponential assumption. 1e6 is a "never fires" guard |
| SURV-26 | monte_carlo.py:104-179 | COD organ-supply multiplier | Donor availability by state COD mix × recovery rates | data_derived | medium | Recovery rates PMC10329409 (Sundaram 2023) x-val vs OPTN 2023; state proportions CDC |
| SURV-27 | monte_carlo.py:158-168 | Beta concentration KAPPA=50 for stochastic recovery rates | Uncertainty in recovery rates | assumed | low | L-053: chosen for ~3.5% CV / plausible variance; no external source |
| SURV-28 | monte_carlo.py:213-223 | Acceptance-rate thinning + national defaults + factor fallback | Centers accepting fewer offers → longer effective wait | data_derived | medium | acceptance-rates-centers.json composite 0.6·vol+0.4·util, [0.3,3.0]. Code default 0.25 (line 221) differs from data-file nationals |
| SURV-29 | monte_carlo.py:336-338 | COD multiplier elasticity + zero-guard | Sublinear supply effect on wait | partially_cited | low | L-056 elasticity; 1.0 fallback when multiplier non-positive |
| SURV-30 | monte_carlo.py:350-365 | Score-drift mortality coupling (liver) | Rising MELD raises waitlist mortality | partially_cited | medium | Compounds uncited drift rate (SURV-18) with partially-cited MELD multipliers (SURV-06) |
| SURV-31 | monte_carlo.py:391-394 | First-event-wins competing-risks resolution (argmin) | Whichever competing event occurs first | assumed | medium | Structurally standard; depends on underlying hazard assumptions |
| SURV-32 | outcomes.py:20-21,101 | MIN_SURVIVAL_PCT = 50.0 compound floor | Graft survival <50% treated as suspect | heuristic_clamp | low | Inline "below this, data is suspect" |
| SURV-33 | outcomes.py:90-103 | Compound success = P(tx≤24mo) × (graft_1yr/100) | Combines access prob with graft survival, assumes independence | assumed | medium | Multiplicative independence is an assumption; pancreas falls back to patient survival |
| SURV-34 | outcomes.py:50-87 | National-baseline survival fallback | Center survival defaults to national avg | data_derived | low | SRTR PSR Tables C5-C20; fallback policy reasonable |
| SURV-35 | config.py:8 | SIMULATION_ITERATIONS = 1000 | MC sampling resolution | assumed | low | Affects MC noise (~±3% per ADR-020), not clinical |

---

## 3. Bayesian Belief Network (BBN)

| ID | Location | Assumption | Clinical basis | Status | Risk | Source / Notes |
|----|----------|------------|----------------|--------|------|----------------|
| BBN-01 | bbn_parameterizer.py:40-42 | _CPT_STRONG/MEDIUM/WEAK ordinal triples (70/25/5) | Tercile→ordinal latent mapping; 5% off-diagonal misclassification tolerance | cited | medium | Druzdzel & van der Gaag IEEE TKDE 2000 (ADR-028). NOTE: not in paper.bib — JOSS citation gap. Backs FORM; exact magnitudes conventional |
| BBN-02 | bbn_parameterizer.py:54 | _GRAFT_POOR_MARGIN = 3.0 pp | Center "poor" if graft survival >3pp below national | assumed | medium | ADR-028 attributes form to SRTR flagging criteria; 3.0pp magnitude hand-set |
| BBN-03 | bbn_parameterizer.py:59,371-378 | _DONOR_SUPPLY_WAIT_MULT [1.2,1.0,0.8] | Higher supply shortens wait; ±20% effect | assumed | low | #213/#214: documented directional, regressing would be circular. T6 sweep confirms not ranking-driving |
| BBN-04 | bbn_parameterizer.py:552 | wait_delist_mults [0.5,0.8,1.2,1.8] | Longer wait raises delisting risk | assumed | low | #213/#214 directional. DelistingRisk now summary-only node (post #211) |
| BBN-05 | bbn_parameterizer.py:465 | base annual_mortality_rate fallback 0.03 | Default waitlist mortality if missing | data_derived | medium | Primary from competing-risks.json (SRTR B7); 0.03 uncited fallback |
| BBN-06 | bbn_parameterizer.py:558 | base annual_delisting_rate fallback 0.05 | Default delisting if missing | data_derived | low | Primary SRTR; 0.05 uncited fallback |
| BBN-07 | bbn_parameterizer.py:391 | national_median_months fallback 12.0 | Default median wait for log-normal CDF | data_derived | medium | Primary from wait-time-distributions.json (SRTR); 12.0 uncited fallback |
| BBN-08 | bbn_parameterizer.py:392 | log_sigma fallback 1.0 | Log-normal wait spread default | data_derived | medium | Per-organ σ SRTR-fit; log-normal FORM is assumption; 1.0 fallback uncited |
| BBN-09 | bbn_parameterizer.py:345-351,409-411 | WaitCategory 6/12/24-mo boundaries | Discretization aligned to registry tiers + 24mo horizon | partially_cited | low | #210: 6/12mo SRTR PSR intervals; 24mo headline horizon. Not fitted |
| BBN-10 | bbn_parameterizer.py:419 | WaitCategory probability floor 0.001 | Avoid exact-zero categories | heuristic_clamp | low | Numerical positivity guard |
| BBN-11 | bbn_parameterizer.py:301-322,495-513,576-591 | Per-organ tercile (33.3/66.7) discretization | Bucket continuous scores into Low/Med/High within-organ | assumed | medium | #59/#209: avoids cross-organ contamination; reasoning given, uncited |
| BBN-12 | bbn_parameterizer.py:783 | GraftSurvival _GOOD/_MODERATE triples (0.75/0.20/0.05; 0.20/0.65/0.15) | Confidence of graft-class → latent state | assumed | medium | _POOR reuses cited _CPT_WEAK; _GOOD/_MODERATE NOT covered by Druzdzel citation, hand-set |
| BBN-13 | bbn_parameterizer.py:798-805 | Graft HR significance classification (CI vs 1.0) | Significance test of graft-failure HR vs national | data_derived | low | #214; HR CIs from SRTR C-series. Replaces old arbitrary 0.8/1.2 cutoffs. Full granularity only |
| BBN-14 | bbn_parameterizer.py:145,815,827 | graft_survival_1yr default 90.0 / moderate prior on missing | Baseline graft survival + neutral class when no data | assumed | low | Hand-set defaults with stated "no data → moderate" reasoning |
| BBN-15 | bbn_parameterizer.py:877-887 | CompoundSuccess CPT (tx×graft combinations) | Tx occurrence × graft quality → success/partial/failure | uncited | medium | "Near-deterministic" composition; no citation; not covered by ADR-028 |
| BBN-16 | bbn_parameterizer.py:890 | CompoundSuccess positivity floor 0.001 | Keep CPT strictly positive | heuristic_clamp | low | Stale comment references pgmpy (engine is bbn_lite) |
| BBN-17 | bbn_parameterizer.py:662-664 | National competing-outcome synthetic fallback 50/5/5 | Synthetic split if srtr-observed-rates.json fails to load | assumed | high | Code WARNs; if triggered it ungrounds the only fully data-grounded node |
| BBN-18 | bbn_parameterizer.py:670-699 | Dirichlet concentration k (EB shrinkage; clip [2,400], default 25, all-noise 400) | How hard sparse centers shrink to national | data_derived | medium | #211 Beta-moment EB; clip bounds, 25.0 default, 400.0 all-noise are hand-set anchors within data-derived procedure |
| BBN-19 | bbn_parameterizer.py:702-715 | 12mo→24mo extension (constant 2nd-year hazard; S(24)=S(12)²) | Project observed 12mo vector to 24mo headline | assumed | medium | #211: documented hazard-shape assumption, simplex-preserving |
| BBN-20 | bbn_parameterizer.py:749 | CompetingOutcome positivity floor 0.001 | Numerical floor | heuristic_clamp | low | Engine safeguard |
| BBN-21 | bbn_parameterizer.py:626,642 | Observed-rate volume weighting (n, or 1 if missing), /100 scaling | Per-center→region aggregation; non-tx exit composition | data_derived | medium | SRTR PSR Table B7; removed-other = REMDET+REMREC+REFTX. "weight=1 if n missing" minor heuristic |
| BBN-22 | bbn_parameterizer.py:993-994 | Pediatric age clamping to 18-34 | Treat pediatric candidates as youngest adult group | assumed | high | Pediatric allocation/outcomes differ substantially; clamping systematically misrepresents them |
| BBN-23 | bbn_parameterizer.py:67-68 | AGE_GROUPS / URGENCY_LEVELS band definitions | Discretize age (4 bands) and urgency (1-4) | partially_cited | medium | Age-mortality multipliers SRTR-anchored (ADR-024); band cut points hand-chosen convention |
| BBN-24 | bayesian_network.py:372 | Wait-category representative months [3,9,18,36] | Point estimates collapsing categorical → median wait | assumed | low | 3/9/18 ≈ midpoints; 36 for open-ended >24mo tail hand-set |
| BBN-25 | bayesian_network.py:376-389 | Time-horizon CDF interpolation (p36 = p24 + very_long×0.5) | Spread of >24mo mass to estimate tx-by-36mo | assumed | low | p6/p12/p24 exact cumulatives; only ×0.5 p36 split assumed |
| BBN-26 | bayesian_network.py:439-441,446-452 | Hybrid p24 = timing × (1−q) competing-loss drain | Combine patient timing with center-AVERAGE competing-risk split | assumed | high | L-072 (OPEN, #238); high-acuity patients get the average death/delist split. Validated ρ 0.80-0.99 |
| BBN-27 | bayesian_network.py:412-414 | Time-horizon monotonicity clamps (p6≤p12≤p24≤p36) | Cumulative tx probs monotone | heuristic_clamp | low | #244; logically necessary guard |
| BBN-28 | bayesian_network.py:474-492 | Data-uncertainty CI half-width (binomial SE, clip [0.01,0.30], n=0→0.20) | Width of reported 95% interval on p24 | data_derived | medium | #226 (replaces old heuristic); clip & n=0 band are heuristic anchors; 1.96 = normal quantile |
| BBN-29 | bayesian_network.py:93-94,612,651 | Unmapped-center region fallback (Nashville / regions[0]) | Which region an unmappable center inherits | uncited | medium | Arbitrary geographic fallback, no rationale |
| BBN-30 | bayesian_network.py:103-137 | DAG structure (19 edges/12 nodes); CompetingOutcome reparented to (Organ,Region) | Causal independence/dependence among nodes | assumed | medium | ADR-024 + #206/#211 option A; deliberate structural decision |
| BBN-31 | bbn_parameterizer.py:903-926 | Uniform evidence-node priors | Prior over patient characteristics (no base-rate weighting) | assumed | low | Inconsequential: all five always set as evidence |
| BBN-32 | bbn_lite.py:204 | CPT normalization tolerance ATOL=1e-6 | Strictness of CPT normalization | assumed | low | #208 build-time guard; tightened from 0.05 |
| BBN-33 | adr-log.md:678 | BBN CPT monthly rate anchors (SRTR 2023 Tables 1.4/1.7/5.2) | Monthly transition rates grounded in SRTR | cited | medium | ADR-028; cross-check constants in bbn_parameterizer.py |

---

## 4. MCMC

| ID | Location | Assumption | Clinical basis | Status | Risk | Source / Notes |
|----|----------|------------|----------------|--------|------|----------------|
| MCMC-01 | mcmc_survival.py:196-200 | log_median_national prior Normal(log(median), σ=0.3) | National median-wait belief; posterior tightness | partially_cited | medium | ADR-026; mean SRTR-anchored; σ=0.3 hand-set. HONESTY NOTE (#257): tight σ pins posterior near MC — does NOT independently validate MC |
| MCMC-02 | mcmc_survival.py:201-207 | log_sigma TruncatedNormal(μ=data, σ=0.15, [0.3,2.5]) | Log-normal wait shape param | partially_cited | medium | Mean SRTR percentile-fit; σ=0.15 & bounds uncited clamps |
| MCMC-03 | mcmc_survival.py:210-219 | log_mort/delist_national priors Normal(log(rate), σ=0.3) | National annual mortality/delisting rates | partially_cited | high | Means from competing-risks.json (SRTR); σ=0.3 uncited. Directly affects patient-facing competing-risk probs |
| MCMC-04 | mcmc_survival.py:230-236 | sigma_city_wait HalfNormal(0.4) | Partial-pooling shrinkage of city wait factors | assumed | medium | ADR-026; 0.4 hand-set |
| MCMC-05 | mcmc_survival.py:239-240 | sigma_city_mort/delist HalfNormal(0.4) | Shrinkage of city mortality/delisting offsets | assumed | medium | ADR-026/027; 0.4 reused |
| MCMC-06 | mcmc_survival.py:244-250 | LKJ-Cholesky correlation prior eta=2.0 | Mortality↔delisting shared-frailty correlation, learned | partially_cited | medium | ADR-027 (Lewandowski 2009 in paper.bib); eta=2 conventional weakly-informative. MCMC analog of Clayton copula |
| MCMC-07 | mcmc_survival.py:274-289 | sigma_bt HalfNormal(0.3) / sigma_urg HalfNormal(0.4) | Spread of blood-type & urgency effects | assumed | medium | ADR-026; bt/urg point values literature-derived; hyperprior scales hand-set |
| MCMC-08 | mcmc_survival.py:295-299 | Observation-noise HalfNormal (0.15 / 0.10) | SRTR estimates as noisy observations | assumed | medium | ADR-026; scales hand-set. One observation per latent → posterior pinned near MC inputs |
| MCMC-09 | mcmc_survival.py:178-184,301-331 | Gaussian likelihood on log-transformed aggregate factors | Multiplicative effects log-normal; aggregate factors = observable | assumed | high | KEY HONESTY ISSUE (lines 187-193): one aggregate obs per latent, NOT event/censoring data. Parameter-uncertainty propagation, not independent survival fit |
| MCMC-10 | mcmc_survival.py:87-93 | age_mortality_multipliers fallback (0.4/0.7/1.0/1.9) | Waitlist mortality rises with age | assumed | medium | Primary from competing-risks.json; hardcoded fallbacks uncited |
| MCMC-11 | mcmc_survival.py:80,84,103,107 | Multiplier fallback default 1.0 (bt/urg/city mort/delist) | Missing entity = neutral national-average risk | heuristic_clamp | low | Pervasive fallback-1.0 pattern |
| MCMC-12 | mcmc_survival.py:351-355 | Sampler defaults (draws 2000, chains 2, tune 1000, seed 42, target_accept 0.90) | Posterior quality/convergence | assumed | medium | ADR-026; chains=2 low for robust R-hat; target 0.90 above PyMC default |
| MCMC-13 | mcmc_inference.py:260-262 | N_PARAM_DRAWS = min(50, n_iterations) | CI resolution from posterior draws | heuristic_clamp | medium | 95% CI from ≤50 points — coarse tail estimation; hand-set |
| MCMC-14 | mcmc_inference.py:286-287 | Blood-type/urgency index fallbacks (unknown→A+ / urgency 2) | Default patient when input invalid | assumed | medium | Silently applied for out-of-range inputs |
| MCMC-15 | mcmc_inference.py:463-476 | External copula suppression threshold (|learned_corr|<0.01) | Whether LKJ frailty supersedes Clayton theta | heuristic_clamp | low | ADR-027; 0.01 cutoff hand-set |
| MCMC-16 | mcmc_inference.py:137-146,290 | Clinical (cPRA/MELD/LAS) multiplier via Nashville/A+ reference probe | Deterministic severity adjustment outside Bayesian model | assumed | medium | Comment: too few data points for Bayesian estimation. Severity NOT learned in MCMC; Nashville/A+ arbitrary reference |
| MCMC-17 | mcmc_inference.py:338,341 | Center→region Nashville fallback | Unmapped center inherits Nashville's posterior params | heuristic_clamp | medium | Silent geographic fallback; could misassign real centers |
| MCMC-18 | convergence.py:35,101-111 | Convergence thresholds (R-hat<1.01, ESS>400) | Gatekeeper for posterior trustworthiness | assumed | medium | Match Vehtari 2021 standards but uncited in repo |
| MCMC-19 | convergence.py:42-43 | Convergence trace-path mismatch (mcmc_traces/_trace.nc vs mcmc-traces/{organ}.nc) | Whether diagnostics ever load real traces | resolved | high | ✅ FIXED (PR #279): now resolves via mcmc_survival.trace_path() (single source of truth); tests/test_convergence.py added (was zero coverage) |
| MCMC-20 | posterior_checks.py:117-273 | Posterior-check pass thresholds (disc <0.20/0.15/0.25, calibration ≥0.60, ρ>0.7, overall ≥70%) | What counts as "adequately capturing" SRTR data | heuristic_clamp | medium | All hand-set, no source. 0.60 calibration explicitly relaxed from 0.90 ideal |
| MCMC-21 | posterior_checks.py:1-15,95-97 | Posterior checks are internal self-consistency | Reproduces own training inputs, not real outcomes | assumed | high | Framing addressed (PR #279): docstring now states in-sample internal-consistency, NOT external validation, and points to SRTR calibration. Underlying single-obs-per-latent limitation remains |
| MCMC-22 | posterior_checks.py:178-184 | city_factor_calibration target 0.90 / pass 0.60 | City-posterior calibration | heuristic_clamp | low | 0.90 correct in principle; 0.60 pass bar arbitrary relaxation |
| MCMC-23 | cross_validation.py:1-19,196-200 | Cross-engine "validation" is internal-consistency only | MC/BBN/MCMC agree with each other, not reality | assumed | high | #251: module name misleading. All three share SRTR inputs → agreement expected. ρ<0.5 flag hand-set |
| MCMC-24 | temporal_validation.py:23,48-127 | Temporal walk-forward uses synthetic trend perturbation | Compares run to trend-shifted version of itself | assumed | high | Framing addressed (PR #279): docstring now flags the synthetic fallback as near-tautological / not a true holdout, points to #237. Real out-of-sample temporal validation still outstanding. baseline_median fallback 24.0 hand-set |
| MCMC-25 | temporal_validation.py:83-84 | Fold seed offset 7919 | RNG decorrelation between folds | heuristic_clamp | low | Arbitrary prime multiplier |
| MCMC-26 | brier_score.py:11-15 | Brier interpretation thresholds (BS<0.05 excellent, <0.20 "FDA SaMD") | Acceptable calibration quality; invokes FDA SaMD | uncited | medium | "roadmap target" only; no regulatory citation. BS=0.25 no-skill is standard |
| MCMC-27 | brier_score.py:1-10,51-89 | Brier check is self-consistency (MC vs analytical, same params) | MC matches own analytical expectation, not outcomes | assumed | high | Independence baked into integrand (no copula) → penalizes MC if copula on. External Brier deferred to Phase 4 IRB |
| MCMC-28 | brier_score.py:79-89 | Exponential competing-risk survival in analytical Brier (monthly = annual/12) | Constant memoryless mortality/delisting hazards | assumed | medium | Same exponential-over-Weibull assumption as MCMC forward sim |
| MCMC-29 | brier_score.py:109-163 | Brier representative patient profiles (age 45, male, urgency 2; per-organ cPRA/MELD/LAS) | "Representative" patient defining what gets validated | assumed | low | Hand-chosen, not from cohort distribution |
| MCMC-30 | adr-log.md:614 | MCMC informative priors anchored to SRTR point estimates | Wait-time log-normal location prior | data_derived | medium | L-061: means SRTR-derived, σ=0.3 hand-set; posteriors won't deviate far ("better calibrated, not more accurate") |

---

## 5. Equity / Spatial / Policy

| ID | Location | Assumption | Clinical basis | Status | Risk | Source / Notes |
|----|----------|------------|----------------|--------|------|----------------|
| EQSP-01 | equity.py:30-38 | 48-profile matrix (8 ABO × 3 age × 2 sex); rep ages 26/45/62 | Which demographic axes vary (race/insurance/SES excluded); rep ages | assumed | medium | ADR-019; rep ages hand-chosen midpoints, not population-weighted. EQUITY_DISCLAIMERS note omissions |
| EQSP-02 | equity.py:159-237 | Equal-weighting of 48 profiles in Gini | Each ABO/age/sex cell equally prevalent | assumed | medium | adr-log:358-386: measures model-response inequality, not population-experienced (Disclaimer 4) |
| EQSP-03 | equity.py:75,251,284 | Gini as inequality metric (vs Theil) | Choice of equity measure | assumed | low | adr-log:364: interpretability/MVP reasoning, not equity-theory |
| EQSP-04 | equity.py:116,126-129 | Closed-form p24 integration grid + [0,1] clamp | 24mo horizon; independent exponential competing risks | assumed | low | #216; copula deliberately omitted (Disclaimer 5) |
| EQSP-05 | equity.py:228-229,191 | Age/sex enters only via median-wait multiplier, not p24 | Demographic effect purely via wait scaling; mortality NOT stratified | assumed | high | EQUITY_DISCLAIMERS[1] flags missing demographic mortality stratification; understates older-patient disparity |
| EQSP-06 | bias_audit.py:193-203 | Bias-warning thresholds (disparity ratio >2.0, Cohen's d >0.8) | When to flag disparity & attribute to ABO biology vs bias | assumed | medium | Cohen's 0.8 conventional but uncited; 2.0 uncited. "ABO biology not systemic bias" is strong unsourced claim shown to users |
| EQSP-07 | bias_audit.py:93,172 | Disparity ratio = max/min mean (inf if min=0) | Disparity metric & degenerate behavior | heuristic_clamp | low | Inf fallback can dominate national warnings; no floor on min_p |
| EQSP-08 | sensitivity.py:135-179 | Sensitivity sweep extremes (cPRA 0-98, MELD 7-38, LAS 20-85, urgency 1-4; baselines MELD 15/LAS 40) | Clinically meaningful range of each allocation score | partially_cited | medium | data-provenance:40-42 OPTN rules; bands not individually cited; baselines hand-set |
| EQSP-09 | sensitivity.py:68-73 + what_if.py:110-120 | Exponential competing-risks draws + optional copula theta | Constant-hazard mortality/delisting + Clayton dependence | assumed | medium | config.py sets values; no citation in slice. Copula omitted in equity (Disclaimer 5) |
| EQSP-10 | what_if.py:92,98 + config.py:15 | SUPPLY_WAIT_ELASTICITY = 0.65 (supply→wait) | 10% more donors → ~6.5% shorter waits | partially_cited | high | L-056: queuing theory + SRTR range 0.5-0.8; 0.65 midpoint pick (see SURV-21) |
| EQSP-11 | what_if.py:64-80 | Wait/donor multipliers scale lognormal median | Log-normal wait dist; proportional policy-lever mechanics | partially_cited | medium | Lognormal not cited within slice. what_if omits center_code/age/sex (city-only) — modeling inconsistency vs sensitivity |
| EQSP-12 | what_if.py:134-139 | Bootstrap CI fixed at 200 resamples | CI stability of reported uncertainty | heuristic_clamp | low | 200 hand-set; small for stable tail percentiles |
| EQSP-13 | policy_scenarios.py:124-149 | 2021 kidney 250nm per-city multipliers (large -4%/+3%w, small +20%/-15%w) | March-2021 250nm policy redistribution by center size | partially_cited | high | King 2023 / OPTN 2019 / Stewart 2022 for direction & +15-25% small-center range; per-city values interpolated. Backtest only checks directionality |
| EQSP-14 | policy_scenarios.py:95-103 | Center-size classification (>200/yr large, <100 small) | Volume tier → policy multiplier | assumed | medium | Comment "Kidney volume from SRTR data" (approximate); cutpoints & Palo-Alto-to-large hand-set |
| EQSP-15 | policy_scenarios.py:167-191,256-258 | Continuous-distribution per-city multipliers (large -8%, small +30%) | Unimplemented points-based allocation de-emphasizing geography | assumed | high | OPTN CD framework + Gentry 2024 (lung) for concept; kidney/liver magnitudes projected/uncalibrated per caveats |
| EQSP-16 | policy_scenarios.py:294-297 | Increased DCD: +15% supply, -8% wait, uniform | DCD protocol growth (~25%→35-40%) | partially_cited | medium | Croome 2020 / Huo 2023 / Smith 2024 support +10-20%; 1.15/0.92 chosen within. Graft-quality/DGF unmodeled |
| EQSP-17 | policy_scenarios.py:335-337 | Broader HCV+: +6% pool, -4% wait, kidney/liver | DAA-enabled HCV+ → HCV- transplantation | partially_cited | medium | Reese THINKER-2 2023 / Goldberg 2021 / Bowring EXPANDER-1 2020 support 5-8%; 1.06/0.96 chosen |
| EQSP-18 | policy_scenarios.py:365-372 | Per-city cost-of-living index (BLS CPI-U, US=100) | Financial-accessibility proxy in travel-subsidy scenario | data_derived | medium | BLS CPI-U; L-014: 7/22 cities fixed-ratio estimates, stale. Embedded copy may drift from cost-of-living.json |
| EQSP-19 | policy_scenarios.py:408-433 | Travel-subsidy tier effects ($5K-$50K → donor/wait/maxCOL) | Demand-side accessibility gains from removing travel barriers | assumed | high | Axelrod 2010 / Held 2016 / HRSA 2020 / Mohan 2021 for direction; tier magnitudes explicitly "not empirically validated" (_TRAVEL_CAVEATS) |
| EQSP-20 | policy_scenarios.py:488-501 | Travel-subsidy COL-proportional formula + 0.3 donor-boost ratio | Linear benefit-with-COL; donor boost = 30% of wait effect | assumed | medium | 0.3 ("patients add to pool, not organs") hand-set with rationale, no source |
| EQSP-21 | allocation_geography.py:20-21 | UNOS allocation circle radii 250nm / 500nm | Geographic competition/donor-pool windows | partially_cited | medium | 250nm = OPTN 2021 kidney policy; 500nm not tied to a specific policy. L-064 flags model as simplified |
| EQSP-22 | allocation_geography.py:94-110 | Per-organ avg-centers-within-250nm normalizers + 500nm 2.5x | What counts as high vs low competition | uncited | high | L-064: "~15 kidney centers within 250nm … not empirically validated". intestine:2/lung:5 round-number guesses; 2.5x arbitrary |
| EQSP-23 | allocation_geography.py:140-160 | distance_score weights (0.40/0.35/0.25) + logistic transforms | How proximity/competition/donor-pool matter; decay shape | uncited | high | No citation/ADR for weights, /75^1.5, ×0.5, ×200. L-064: directional only |
| EQSP-24 | spatial_interpolation.py:21-44 | Hardcoded 22-city coordinate table (fallback nodes) | Spatial support of interpolated surfaces | data_derived | medium | L-063: sparse city data; thin-plate spline edge artifacts. Choice of 22 cities is a coverage assumption |
| EQSP-25 | spatial_interpolation.py:205-298 | RBF thin-plate smoothing=1.0; IDW power=2.0 | Local fidelity vs smoothness of clinical surfaces | heuristic_clamp | medium | Standard defaults, uncited, not tuned/validated for these layers |
| EQSP-26 | spatial_interpolation.py:193-273,295 | Output clamped to observed [vmin,vmax]; +std on extrapolation | No location more extreme than observed; inflate uncertainty outside hull | heuristic_clamp | medium | #253/#266 validity clamp; +1·std penalty hand-set. Suppresses gradient at extremes |
| EQSP-27 | spatial_interpolation.py:239-250 | Kriging GP kernel (RBF length_scale 2.0/2.0, MAX_FIT=800, noise 1.0) | Smoothness/uncertainty of kriged surfaces | assumed | medium | Hand-set inits (learned, so matter less); MAX_FIT=800 & seed 0 arbitrary |
| EQSP-28 | spatial_interpolation.py:168 | Minimum 3-point requirement per layer | Data-density floor below which surface suppressed | heuristic_clamp | low | Bare minimum for 2D surface |

---

## 6. Data files (clinical)

| ID | Location | Assumption | Clinical basis | Status | Risk | Source / Notes |
|----|----------|------------|----------------|--------|------|----------------|
| DATA-01 | wait-time-distributions.json:14-32 | Kidney ABO wait multipliers (O+ 1.3 … AB+ 0.55) | ABO drives kidney wait | partially_cited | high | _meta: literature-derived (B10 not stratified); OPTN form, no author/year for magnitudes |
| DATA-02 | wait-time-distributions.json:25-31 | Kidney cPRA wait multipliers (0-20:1.0 … 98-100:5.0) | Sensitization is dominant kidney wait factor | partially_cited | high | data-provenance:40 OPTN cPRA tiers; 5x cap at 98-100 hand-set |
| DATA-03 | wait-time-distributions.json:47-53 | Liver MELD wait multipliers (6-14:2.0 … 36-40:0.2) | MELD-based allocation; higher MELD shorter wait | partially_cited | high | data-provenance:41 OPTN MELD; magnitudes hand-set |
| DATA-04 | wait-time-distributions.json:85-90 | Lung LAS wait multipliers (0-39:2.0 … 70-100:0.2) | LAS drives lung priority | partially_cited | high | data-provenance:42 OPTN LAS; LAS replaced by CAS 2023 — may be outdated |
| DATA-05 | wait-time-distributions.json:37-120 | Liver/heart/lung/pancreas/intestine ABO multipliers | Organ-specific ABO sensitivity | partially_cited | high | Decreasing ABO spread (kidney>pancreas>liver>heart>intestine>lung) itself an uncited clinical assumption |
| DATA-06 | wait-time-distributions.json:14-109 | National median wait times by organ | mu of log-normal wait model | data_derived | high | SRTR PSR Table B10 (Jan 2025), fit by parse-srtr-reports.py |
| DATA-07 | wait-time-distributions.json:14-109 | log_sigma clamped at 1.2 ceiling (kidney/liver/heart/intestine) | σ controls right-tail / long-wait probs | heuristic_clamp | high | #256: IQR method clamped [0.3,1.2]; "ceiling likely understates dispersion", should be re-evaluated |
| DATA-08 | wait-time-distributions.json:124-146 | City wait-time factors (22 cities) | Geographic wait multiplier | data_derived | medium | SRTR Table B10, avg center-median/national across organs (collapses organ-specific variation) |
| DATA-09 | competing-risks.json:12-67 | Annual waitlist mortality rates by organ | Waitlist death hazard | data_derived | high | SRTR PSR Table B7 (Jan 2025); 12-mo died-on-waitlist as annual proxy |
| DATA-10 | competing-risks.json:13-68 | Annual delisting rates by organ | Removal-from-waitlist hazard | data_derived | high | SRTR Table B7; removals (worsened+other+refused) proxy — grouping is a judgment call |
| DATA-11 | competing-risks.json:14-75 | Urgency mortality multipliers (status 1-4) by organ | Higher urgency → higher death hazard | partially_cited | high | _meta "literature estimates"; limitations:564 names SRTR 2023 ADR Table 5.3; per-status magnitudes hand-set |
| DATA-12 | competing-risks.json:30-35 | Liver MELD mortality multipliers (6-14:0.5 … 36-40:3.5) | MELD predicts waitlist mortality | partially_cited | high | data-provenance:47 OPTN MELD; 3.5x cap hand-set |
| DATA-13 | competing-risks.json:79-166 | City mortality/delisting adjustment factors (22 cities) | Geographic hazard multipliers | data_derived | medium | _meta: SRTR Table B7, avg across organs; small-N noisy |
| DATA-14 | cause-of-death-by-region.json:8-50 | Organ recovery rates by COD (6×5 matrix) | Fraction of donors usable per organ by COD | cited | high | PMC10329409 (Sundaram 2023, OPTN 2005-2019); 15/30 cells x-val vs OPTN 2023; anoxia split estimated; intestine via OTPD 0.104 |
| DATA-15 | cause-of-death-by-region.json:52-410 | State COD proportions (51 jurisdictions) | Donor-eligible deaths by cause per state | data_derived | medium | CDC 2017 mortality with donor-eligibility calibration; 2017 vintage (L-051); state as OPO proxy (L-050) |
| DATA-16 | cause-of-death-by-region.json:5-6 | Donor-eligibility calibration weights (Nelder-Mead: trauma 0.31 … drug_intox 0.721) | Convert general-pop COD → donor-eligible shares | data_derived | high | _meta: fitted via Nelder-Mead (#16/#14); optimization target/validation not cited; CV 0.062 vs drug 0.721 spread impactful, unvalidated |
| DATA-17 | post-transplant-outcomes.json:11-46 | National graft & patient survival by organ (1yr/3yr) | Post-transplant survival benchmarks | data_derived | medium | SRTR PSR Tables C5-C20 (Jan 2025); pancreas graft null is real data gap |
| DATA-18 | post-transplant-outcomes.json:9 + ratings | Performance rating from 1yr HR CI vs 1.0 | Center quality flag shown to patients | data_derived | high | _meta:9 follows SRTR convention; labeling "worse than expected" from 1yr HR alone is consequential; threshold logic in code |
| DATA-19 | post-transplant-outcomes.json:52-64 | Center graft/patient HRs and CIs (22 cities) | Risk-adjusted center outcome HRs | data_derived | medium | SRTR Bayesian hierarchical C-series; low-volume → wide CIs land "as_expected" (known limitation) |
| DATA-20 | acceptance-rates-centers.json:41-48 | National organ acceptance rates (kidney 0.2 … lung 0.45) | Baseline fraction of offers accepted | uncited | high | _meta "SRTR/literature" (no specific cite); NOT in data-provenance tables; round numbers effectively hand-set |
| DATA-21 | acceptance-rates-centers.json:4 | Acceptance composite formula (0.6·vol+0.4·util, clamp [0.3,3.0]) | Center accept-aggressiveness proxy | heuristic_clamp | high | Weights & clamp hand-chosen; inverse mortality×delisting as "utilization" is unvalidated assumption. 17 volume-only fallbacks |
| DATA-22 | acceptance-rates-centers.json:5-20 | Acceptance volume & utilization medians (normalizers) | Per-organ 1.0-center definition | data_derived | medium | Derived from n_1yr & competing-risks-centers.json; intestine medians from only 5 centers (fragile) |
| DATA-23 | acceptance-rates-centers.json:49+ | Per-center acceptance factors clamped [0.3,3.0] | Center accept-aggressiveness | heuristic_clamp | medium | 28 of 540 entries sit exactly on a clamp bound |
| DATA-24 | competing-risks-centers.json:8+ | Per-center mortality/delisting factors clamped [0.3,3.0] | Center death/delisting hazard multipliers | heuristic_clamp | high | 538 factor cells (292+39+170+37) on a clamp bound — clamp dominates distribution; rationale undocumented; small-N driven to extremes |
| DATA-25 | wait-time-distributions-centers.json:8+ | Per-center wait-time factors clamped [0.3,3.0] | Center wait multipliers | heuristic_clamp | high | 95 cells (36+59) on clamp bound; ALCH kidney 0.3 + heart 3.0 (10x within one center) signals noisy small-N. Rationale undocumented |
| DATA-26 | donor-registration.json:220-243 | livingDonorProgramStrength (per-city 80-95) | Living-donor program strength/reputation | uncited | medium | L-033: manually curated by design (no public dataset); L-025 historical dup-Cleveland bug |
| DATA-27 | donor-registration.json:244-267 | populationFactors (per-city 58-100) | Relative population/donor-pool size | uncited | medium | L-033: manual by design |
| DATA-28 | donor-registration.json:8-219 | stateRegistrationRates / EDDR proxy | Donor designation rate per state | cited | medium | Donate Life America 2019 (2018 DDR, p.27); 2018 vintage stale; EDDR-as-DDR for 13 states is an assumption |
| DATA-29 | hospital-quality.json:138-161 | centerReputation (per-city 80-99) | Subjective center-reputation ranking → Hospital Quality | uncited | high | _meta claims CMS API but L-046 shows CMS endpoint 400s; values effectively curated, no verifiable source |
| DATA-30 | hospital-quality.json:162-207 | specializations (per-organ center lists) | Which centers are organ specialists | uncited | medium | data-provenance:18 SRTR + press releases, manual; no systematic criteria |
| DATA-31 | hospital-quality.json:208-231 | insuranceAcceptanceRates (per-city 89-99) | Insurance plans accepted | uncited | medium | L-006: field collected but historically unused; values hand-set |
| DATA-32 | hospital-quality.json:6-137 | centerVolumes (per-organ per-city counts) | Annual transplant volume → quality/acceptance | partially_cited | medium | L-010/L-040 real SRTR volumes; hand-maintained not auto-generated; can drift (350 vs 385 noted) |
| DATA-33 | opo-mapping.json | OPO UNOS region assignments | Allocation grouping governing donor pool per center | cited | low | HRSA OPO Service Area by County + FCC Census API; authoritative |

---

## 7. Data-generation scripts

| ID | Location | Assumption | Clinical basis | Status | Risk | Source / Notes |
|----|----------|------------|----------------|--------|------|----------------|
| GEN-01 | parse-srtr-reports.py:218 | Log-normal sigma fallback default 0.8 | Spread of wait-time distribution | assumed | medium | Hand-set in fit_lognormal Strategy 4; also backs out mu from P25 (line 198-199) |
| GEN-02 | parse-srtr-reports.py:221 | Sigma clamp [0.3, 1.2] | Bounds log-normal spread / tail | heuristic_clamp | medium | Arbitrary floor/ceiling on fitted parameter; no citation |
| GEN-03 | parse-srtr-reports.py:209-215 | Log-normal sigma fit (P10-P25 quantile spread, z-divisors) | Estimate spread from LOWER quantiles (SRTR P75 censored) | partially_cited | medium | SRTR PSR Technical Methods (_meta) + standard z-scores; lower-tail rationale is analyst judgment |
| GEN-04 | parse-srtr-reports.py:239-244 | City/center wait-factor clamp [0.3, 3.0] | Center at most 3x slower / 0.3x as fast | heuristic_clamp | medium | Reused at 456-457 (mortality/delisting) and 1139-1140 (all-centers); caps real outliers |
| GEN-05 | parse-srtr-reports.py:249 | Censored-both wait factor fallback 2.5 | "Extremely long" for censored>72mo centers | assumed | medium | Hand-picked to avoid dropping censored centers |
| GEN-06 | parse-srtr-reports.py:348-364 | City wait-factor fallback 1.0 | Missing wait data = national average | assumed | low | Neutral fallback; masks data gaps as "average" |
| GEN-07 | parse-srtr-reports.py:412-415 | 12-mo waitlist outcome as annual mortality/delisting proxy | 12-mo died-on-waitlist % = annual rate; removal grouping | data_derived | high | SRTR Table B7; (a) 12mo-%-as-annual and (b) removal grouping are uncited judgments. removed_improved counted as delisting is debatable |
| GEN-08 | parse-srtr-reports.py:431 | Urgency mortality multipliers default {1:0.7,2:1.0,3:1.4,4:2.0} | Mortality scales with 1-4 urgency tier | uncited | high | _meta "literature estimates" but no citation in docs/paper.bib; L-002/L-003 note 1-4 scale oversimplified |
| GEN-09 | parse-srtr-reports.py:452-494 | Mortality/delisting factor fallback 1.0 | Missing/zero-baseline center = national average | assumed | low | "1.0 if national==0" pattern |
| GEN-10 | parse-srtr-reports.py:534,660-661,1201 | MIN_N_OUTCOMES = 10 | Reliability threshold for survival estimates | assumed | low | Hand-set N≥10 cutoff |
| GEN-11 | parse-srtr-reports.py:556-567 | Performance rating thresholds (HR 95% CI vs 1.0) | Classify center performance | cited | low | Matches SRTR's own Bayesian HR/credible-interval flagging methodology |
| GEN-12 | parse-srtr-reports.py:1011-1016 | Default blood-type multipliers (O+ 1.25 … AB- 0.75) | ABO lengthens (O) / shortens (AB) wait | partially_cited | high | data-provenance:39 OPTN, literature-derived; B10 not stratified; magnitudes uncited; ordering matches reality |
| GEN-13 | generate-srtr-historical.py:29 | RNG seed 42 — whole file is SYNTHETIC data | Entire historical time-series fabricated | assumed | high | _meta "NOT real patient data"; overwritten by parse-srtr-reports.py when real data present. If shipped, all trends synthetic |
| GEN-14 | generate-srtr-historical.py:46-120 | Per-organ national baselines + trends (synthetic) | Baseline outcome rates & secular trends | assumed | high | _meta "calibrated against published SRTR" (no per-value cite); hand-set ORGAN_BASELINES |
| GEN-15 | generate-srtr-historical.py:128-151 | City profiles (size/quality offset/trend) (synthetic) | Per-city size & outcome-quality offsets | uncited | high | Hardcoded per-city quality tiers; no source; drives fabricated quality differences |
| GEN-16 | generate-srtr-historical.py:162-169 | COVID-2020 impact multipliers (synthetic) | Pandemic-year degradation | assumed | medium | Hand-set shock applied to synthetic year 2020 |
| GEN-17 | generate-srtr-historical.py:177-186 | Trend multiplier rates (improving/declining) (synthetic) | Annual quality drift per center class | uncited | low | Synthetic-only |
| GEN-18 | generate-srtr-historical.py:255-309 | Synthetic value clamps (wait/mortality/delisting/survival; patient≥graft+0.005) | Bound synthetic outcomes to plausible ranges | heuristic_clamp | low | Synthetic-data guardrails; patient≥graft is a clinical ordering assumption |
| GEN-19 | generate-srtr-historical.py:154-219 | Small-program null injection + ±20% wait-offset spread (synthetic) | Which centers lack small-organ programs | uncited | low | Synthetic program-existence assumptions hand-listed |
| GEN-20 | compute-acceptance-rates.py:30-37 | National offer acceptance rates per organ | Fraction of offers accepted | partially_cited | high | Hart 2021 (kidney only); liver/heart/lung/pancreas/intestine "SRTR annual reports 2023" no figures — effectively assumed |
| GEN-21 | compute-acceptance-rates.py:42-117 | Acceptance composite weights (VOL 0.6 / UTIL 0.4) | Trust in volume vs utilization for accept-aggressiveness | uncited | medium | Hand-set 60/40; "utilization = 1/(mortality×delisting)" itself an uncited clinical-inference assumption |
| GEN-22 | compute-acceptance-rates.py:124 | Acceptance factor clamp [0.3, 3.0] | Bound per-center acceptance multiplier | heuristic_clamp | low | Same [0.3,3.0] heuristic as wait/mortality factors |
| GEN-23 | compute-acceptance-rates.py:90-95 | Median fallback = 1.0 when no centers report | Normalization denominator default | assumed | low | Triggers only if organ has zero reporting centers |
| GEN-24 | generate-center-health-data.js:36-37 | CKD-rate linear model (ckdRate = 9.0 + 0.5·diabetes) | Impute county CKD from diabetes (CDC PLACES lacks CKD) | data_derived | medium | L-012: linear model fit R²~0.85 on 22 cities; applied to ~248 centers (extrapolation risk) |
| GEN-25 | generate-center-health-data.js:24-77 | Nearest-county haversine health assignment | Center catchment health = nearest county centroid | data_derived | medium | L-012/data-provenance:122: median match 11.8 km; nearest-centroid not catchment-weighted; no distance cap |

---

## 8. Cross-cutting validation evidence (docs)

These are validation/face-validity results rather than parameters, recorded so reviewers can see what evidence exists and its limits.

| ID | Location | Assumption / Result | Status | Risk | Source / Notes |
|----|----------|--------------------|--------|------|----------------|
| EQSP-29 | clinical-backtest-report.md:15 | 250nm circles help small centers (3/3 improved) | data_derived | low | Backtest seed 42, 1000 iters; PASS. Confirms direction only (cross-links EQSP-13) |
| EQSP-30 | center-calibration-report.md:17 | Center calibration Spearman ρ (kidney 0.89 … pancreas 0.46) | data_derived | medium | Internal-consistency (B10/B7 inputs vs B7 tx-rate); pancreas weakest. Substitute for infeasible COMET-Lung |
| MCMC-31 | temporal-validation-report.md:26 | Temporal out-of-sample concordance ρ (kidney 0.77 … intestine 0.29) | data_derived | medium | 15 releases 2018-2025; heart/intestine weak. Varies ground-truth release, not training release |
| MCMC-32 | srtr-ground-truth-comparison.md:35 | Discrepancy thresholds OK/WARN/FLAG (15%/25%) | heuristic_clamp | low | Author-chosen bands. Brier BS<0.001 explicitly convergence-by-construction, not external accuracy |
| DATA-34 | docs/sensitivity-report.md:30 | cPRA dominance (kidney p24 swing 0.271) | data_derived | low | One-way sweep, 500 iters, 10 cities. Confirms cPRA multiplier behavior; heart/pancreas/intestine lack organ-specific scores |
| SCORE-30 | docs/adr-log.md:474 | Trend significance p<0.10 + weighted vote (wait×3, vol×2, surv×2, mort×1) | assumed | low | ADR-022: p<0.10 reasoned for small n; vote weights hand-set, no external basis |
| MCMC-33 | docs/limitations.md:447 | Patient-level covariate effects applied deterministically in MCMC | assumed | medium | L-060 (OPEN): MCMC adds uncertainty/pooling but patient model no richer than MC; needs SRTR SAF |
| SURV-36 | docs/data-provenance.md:131 | Haversine nautical-mile conversion (×0.868976) | cited | low | Standard geodesic constant |
| SURV-37 | docs/limitations.md:420 | Pancreas compound-success → patient survival (96.6%) | data_derived | low | L-057: SRTR doesn't publish adult pancreas graft survival; reasonable proxy with annotation |

---

## Priority to justify (high-risk + uncited/assumed/heuristic_clamp)

These are the entries flagged **high-risk** AND still lacking external justification. Tackle these first for peer review / clinical use:

- [ ] **SCORE-01** scoring.py:20-29 — 8-category top-level weights (`uncited`). No source for the magnitudes that drive every score.
- [ ] **SCORE-03** scoring.py:85-89 — ABO compatibility scores (`uncited`). 40% of medical compatibility, magnitudes hand-set.
- [ ] **SCORE-18** scoring.py:44-47 — VOLUME_THRESHOLDS (`assumed`). 40% of hospital quality; "well-established" asserted but thresholds uncited.
- [ ] **SCORE-24** scoring.py:335-348 — Health-demographics penalty coefficients & baselines (`uncited`). Both baselines and per-point multipliers hand-set.
- [ ] **SURV-01** competing_risks.py:4-9 — Independent exponential competing-risks model (`assumed`). No exponential-vs-Weibull source; understates late deterioration.
- [ ] **SURV-13 / DATA-07** wait-time-distributions.json log_sigma at 1.2 ceiling (`heuristic_clamp`). Ceiling acknowledged to understate dispersion; directly affects tail tx probabilities.
- [ ] **SURV-25** stats_utils.py:44-58 — rate-as-constant-exponential-hazard conversion (`assumed`). High-risk foundational assumption.
- [ ] **BBN-17** bbn_parameterizer.py:662-664 — National competing-outcome synthetic fallback 50/5/5 (`assumed`). Would unground the only fully data-grounded BBN node if triggered.
- [ ] **BBN-22** bbn_parameterizer.py:993-994 — Pediatric age clamping to 18-34 (`assumed`). Systematically misrepresents pediatric candidates.
- [ ] **BBN-26 / docs L-072** bayesian_network.py:439-452 — Hybrid p24 center-AVERAGE competing-loss split (`assumed`). High-acuity patients get average death/delist split.
- [ ] **MCMC-09** mcmc_survival.py:178-184 — Single-aggregate-observation likelihood (`assumed`). Parameter propagation, not independent survival fit — cross-engine agreement must not be framed as validation.
- [x] **MCMC-19** convergence.py — Trace-path mismatch. ✅ FIXED (PR #279): convergence now reads the canonical trace path; test coverage added.
- [x] **MCMC-21** posterior_checks.py — In-sample self-consistency. ✅ Framing addressed (PR #279): docstring relabeled, points to SRTR calibration. (Underlying single-obs limitation remains.)
- [x] **MCMC-23** cross_validation.py — Cross-engine internal-consistency. ✅ Framing addressed (earlier methods pass): docstring relabeled "concordance, not validation".
- [x] **MCMC-24** temporal_validation.py — Synthetic trend-perturbation. ✅ Framing addressed (PR #279): relabeled near-tautological; real out-of-sample work tracked in #237.
- [ ] **MCMC-27** brier_score.py — Self-consistency Brier with independence baked in (`assumed`). Penalizes MC when copula on; external Brier deferred.
- [ ] **EQSP-05** equity.py:228-229 — Demographic mortality NOT stratified in equity (`assumed`). Understates older-patient disparity.
- [ ] **EQSP-19** policy_scenarios.py:408-433 — Travel-subsidy tier magnitudes (`assumed`). Explicitly "not empirically validated".
- [ ] **EQSP-22** allocation_geography.py:94-110 — avg-centers-within-250nm normalizers (`uncited`). Round-number guesses; 2.5x arbitrary.
- [ ] **EQSP-23** allocation_geography.py:140-160 — distance_score weights & transforms (`uncited`). All constants hand-tuned, no source.
- [ ] **DATA-20** acceptance-rates-centers.json:41-48 — National acceptance rates (`uncited`). Round numbers; absent from provenance register.
- [ ] **DATA-21** acceptance-rates-centers.json:4 — Acceptance composite formula (`heuristic_clamp`). Inverse mortality×delisting as "utilization" unvalidated.
- [ ] **DATA-24** competing-risks-centers.json — Per-center mortality/delisting factors on clamp bounds (`heuristic_clamp`). 538 cells pinned; clamp dominates distribution.
- [ ] **DATA-25** wait-time-distributions-centers.json — Per-center wait factors on clamp bounds (`heuristic_clamp`). Rationale undocumented; noisy small-N.
- [ ] **DATA-29** hospital-quality.json:138-161 — centerReputation (`uncited`). CMS API unreachable; no verifiable source; subjective quality judgment.
- [ ] **GEN-07** parse-srtr-reports.py:412-415 — 12-mo outcome as annual proxy + removal grouping (`data_derived` but judgment uncited). removed_improved as delisting debatable.
- [ ] **GEN-08** parse-srtr-reports.py:431 — Urgency mortality multipliers default (`uncited`). "literature estimates" with no findable citation.
- [ ] **GEN-12** parse-srtr-reports.py:1011-1016 — Default blood-type multipliers (`partially_cited`). Magnitudes uncited.
- [ ] **GEN-13/14/15** generate-srtr-historical.py — Synthetic baselines & per-city quality tiers (`assumed`/`uncited`). If shipped instead of parsed real data, all downstream trends are fabricated.
- [ ] **GEN-20** compute-acceptance-rates.py:30-37 — National acceptance rates (`partially_cited`). Only kidney tied to Hart 2021; rest effectively assumed.
- [ ] **DATA-01 → DATA-05, DATA-11, DATA-12** — Clinical ABO/cPRA/MELD/LAS/urgency multiplier tables (`partially_cited`, high-risk). Forms are OPTN/SRTR-grounded but exact magnitudes hand-set; collectively the largest cluster needing a fitted source. (Note DATA-04/EQSP relevant: LAS superseded by CAS in 2023.)
- [ ] **DATA-16** cause-of-death-by-region.json:5-6 — Donor-eligibility Nelder-Mead weights (`data_derived` but unvalidated). Optimization target/validation not cited.
- [ ] **DATA-18** post-transplant-outcomes.json — Performance rating from 1yr HR CI (`data_derived`, high-risk). Patient-facing "worse than expected" label from 1yr HR alone is consequential.
