# Validating the allocation-circle competition proxy

**Date:** 2026-08-27
**Issue:** #299 (backlog F17), limitation L-064
**Verdict:** no detectable relationship with observed outcomes; and there is no weight to downgrade, because the proxy feeds nothing.

---

## What the proxy claims

`allocation_circles()` counts transplant centers within 250 nm of a location and divides by a national average, so that a typical patient scores ~1.0. The implied claim is causal: **more competing centers nearby → more competition for the same donors → worse access.**

An earlier pass (#299, 2026-08-27) found the normalizers were not merely unvalidated but *wrong* — the kidney figure was 15 where the population-weighted truth is 25.6, so the score averaged 1.71 against its own comment's claim of ~1.0. Those are fixed and pinned. This is the deeper half of the issue: **is the proxy measuring anything?**

## The test

The claim is directly falsifiable against data already in the repo. SRTR publishes each center's observed transplant rate. If competition depresses access, a center's competition count should correlate **negatively** with its observed rate.

Restricted to centers with a cohort of n ≥ 10, so the observed rate carries information.

Two forms were tested:

- **raw** — centers within 250 nm
- **supply-normalized** — centers within 250 nm per million people within 250 nm, using the county centroids and populations already shipped. Raw counts confound competition with donor supply: dense regions have more centers *and* more donors, and those effects push in opposite directions.

## Result

| organ | n | ρ(centers, rate) | p | ρ(centers/million, rate) | p |
|---|---|---|---|---|---|
| kidney | 217 | −0.0593 | 0.384 | −0.0545 | 0.425 |
| liver | 134 | −0.1107 | 0.203 | −0.1182 | 0.174 |
| heart | 130 | −0.1189 | 0.178 | **−0.1783** | **0.042** |
| lung | 61 | −0.0162 | 0.901 | +0.0365 | 0.780 |

Pancreas and intestine have too few centers with n ≥ 10 to test.

**Seven of eight comparisons run negative**, which is weakly consistent with the mechanism. But one result at p < 0.05 out of eight tests is what chance produces (≈0.4 expected), and it does not survive a Bonferroni correction (α = 0.00625). Supply-normalizing does not rescue it: kidney and liver are unchanged, and lung flips sign.

**The proxy is not detectably related to observed transplant rates.**

This is the same shape as the ABO-competition result (#405): correct direction, chance-level significance, no effect worth modeling. The likely reason is the same too — allocation is a match-run over patient priority, acceptance behaviour and OPO boundaries, and a center count within a radius captures none of it.

## "Downgrade its weight" does not apply

#299 offered validation *or* downgrading. Neither is available as written, because **the proxy carries no weight**:

- `backend/services/scoring.py` never imports `allocation_geography`.
- The only consumers are `GET /spatial/allocation-circles` and `GET /spatial/distance-score`, rendered on the Explorer's Spatial Analysis tab.
- No center ranking, probability, wait estimate or competing-risk figure depends on it.

So it cannot skew a recommendation. What it *can* do is mislead: a bare number under the label **"Competition"**, sitting beside a "Composite" score, reads as a validated finding about a patient's odds.

## What shipped instead

A note attached to the numbers themselves, rather than buried here:

> Structural geography only. **Competition** counts transplant centers within 250 nm; tested against observed SRTR transplant rates it shows no detectable relationship. These figures describe the map, not your odds, and do not affect the center rankings or probabilities anywhere else in this tool.

The note deliberately does **not** link here. The docs site builds to routes like `/architecture/overview`, so a raw `.md` path from the app root 404s — a caveat that sends the reader nowhere is worse than one that stands on its own.

`backend/tests/test_competition_proxy_scope.py` pins the "affects nothing" half — if the proxy is ever wired into the scoring path, that claim becomes false and the test fails. A disclosure that silently stops being true is worse than none.

## The recommended upgrade was tested, and it fails too

The first version of this report said a center count is the wrong unit and that a defensible measure would need **candidates listed per center** rather than centers per radius. That recommendation is now tested and **not supported**.

SRTR's `Tables B8-B9 Counts Center` sheet carries per-center candidate counts (`TPC_ALL_NC`; 234 kidney centers, 105,857 candidates — the same source #405 used, and candidates rather than recipients, so not circular). Summing them over each center's 250 nm circle gives a competition measure denominated in the people actually competing:

| organ | n | centers in circle | p | **candidates in circle** | p | candidates per center | p |
|---|---|---|---|---|---|---|---|
| kidney | 218 | −0.0512 | 0.452 | **−0.0649** | 0.340 | −0.0325 | 0.633 |
| liver | 135 | −0.1166 | 0.178 | **−0.1036** | 0.232 | −0.0013 | 0.988 |
| heart | 130 | −0.1189 | 0.178 | **−0.1041** | 0.238 | +0.0806 | 0.362 |
| lung | 61 | −0.0162 | 0.901 | **−0.0304** | 0.816 | −0.0783 | 0.549 |

Twelve tests, none significant, and the candidate-weighted version is **no better than the center count it was supposed to improve on**. So the shortfall is not the unit.

**One caveat on the outcome variable**, stated because it bounds the conclusion: SRTR's transplant rate is transplants per patient-year waiting. If regional competition is fully absorbed into how long each center's own listed patients wait, a per-center rate may be a weak instrument for detecting it. That would not rescue the shipped proxy — it would mean this question needs a different outcome (waiting-time percentiles, or offer-level data) rather than a different competition measure.

## The geometry was the problem — OPO catchments do predict

Having ruled out the unit, the remaining suspect was the catchment shape. `data/opo-mapping.json` already maps all 248 centers to their OPO (HRSA county-to-OPO plus FCC geocoding), so this is testable without new data.

Replacing "centers within 250 nm" with "centers in the same OPO":

| organ | n | circle | p | **OPO centers** | p | OPO candidates | p | UNOS region | p |
|---|---|---|---|---|---|---|---|---|---|
| kidney | 218 | −0.0512 | 0.452 | **−0.1853** | **0.006** | −0.1664 | 0.014 | −0.0151 | 0.825 |
| liver | 135 | −0.1166 | 0.178 | **−0.1882** | **0.029** | −0.1209 | 0.162 | −0.1432 | 0.098 |
| lung | 61 | −0.0162 | 0.901 | −0.2384 | 0.064 | −0.2408 | 0.062 | +0.0172 | 0.896 |
| heart | 130 | −0.1189 | 0.178 | −0.0142 | 0.872 | +0.0347 | 0.695 | −0.1048 | 0.235 |

**UNOS region is the control.** It is a coarser grouping of the same centers, and it predicts nothing — so this is not "any grouping works", it is specifically the allocation unit.

### It is not a size confound

The obvious objection is that large OPOs simply contain large centers. Partial Spearman controlling for the center's own observed cohort:

| organ | raw | partial | OPO size vs own cohort |
|---|---|---|---|
| kidney | −0.1853 (p 0.006) | **−0.1881 (p 0.005)** | −0.1022 (p 0.133) |
| liver | −0.1882 (p 0.029) | −0.1809 (p 0.036) | −0.0597 (p 0.491) |
| lung | −0.2384 (p 0.064) | **−0.3612 (p 0.004)** | +0.2504 (p 0.052) |
| heart | −0.0142 (p 0.872) | −0.0818 (p 0.355) | +0.0819 (p 0.355) |

The effect survives for kidney and liver and **strengthens for lung** — there, OPO size correlates positively with a center's own cohort, which was masking the competition signal.

### Multiple comparisons, stated honestly

The pre-specified hypothesis was "OPO geometry beats circle geometry", tested once per organ — four tests, so Bonferroni α = 0.0125. **Kidney (0.005) and lung (0.004) survive; liver (0.036) does not.** All four partials are negative, as the mechanism predicts.

The earlier circle and candidate work was 16 tests with nothing below 0.178, so the contrast is not a threshold artifact.

### How much this explains

ρ ≈ −0.19 is roughly 3.5% of rank variance. **A real effect, and a small one.** It justifies building an OPO-based competition term; it does not justify presenting one as a strong determinant of a patient's odds.

## Where this leaves the ingredients

- ~~candidates listed per center~~ — ruled out; no better than counting centers
- **OPO boundaries rather than circles — CONFIRMED as the missing piece**
- offer-acceptance behaviour per center (Table B11 OARR, #320) — still untested, and now the most promising remaining addition

#299 stays open, but for the first time with a measured signal to build on rather than a null to explain.
