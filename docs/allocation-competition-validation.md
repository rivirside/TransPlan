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
- offer-acceptance behaviour per center (Table B11 OARR, #320) — **tested; adds nothing.** See below.

#299 stays open, but for the first time with a measured signal to build on rather than a null to explain.

---

## Shipped: the measure, not yet the display

`opo_competition(lat, lon, organ)` is implemented and returned by
`GET /spatial/allocation-circles` alongside the circle figure, so the two are
visible side by side rather than swapped silently.

A location has no OPO of its own — the shipped mapping is county-based and
runtime geocoding is unavailable — so the query point inherits the OPO of its
**nearest center performing the organ**: the OPO whose match run a patient
listing there would actually enter.

What that changes, concretely:

| location | circle (250 nm) | OPO |
|---|---|---|
| Manhattan | 55 centers, score 2.15 | LiveOnNY, 11 centers, score 2.64 |
| Chicago | 38 centers, score 1.48 | Gift of Hope, 10 centers, score 2.40 |
| **Billings, MT** | **0 centers, score 0.00** | **LifeSource, 8 centers, score 1.92** |

Billings is the case that shows why the circle fails. It reports **zero
competition** — there is no transplant center within 250 nm — when the patient
there is in fact listed into an OPO with eight competing kidney programs.
"Nothing nearby" and "no competition" are not the same statement, and the
circle measure cannot tell them apart.

**The Explorer tile is switched over, and getting there found a worse bug.**

An earlier draft of this section said the score card had "no `.score-grid`
CSS rule anywhere in the stylesheet" and used that to defer the change. That
was wrong: the rule exists, in an inline `<style>` block in `explorer.html`,
which a `--include="*.css"` grep does not reach. The layout is an ordinary
two-column grid and was never an obstacle.

Checking it properly surfaced the real problem. `explorer/spatial-analysis.js`
read `composite_score`, `proximity_score`, `competition_score` and
`donor_pool_score`; `distance_score()` has always returned `composite`,
`proximity`, `competition`, `donor_pool`. **All four tiles rendered `--`,
permanently.** Silent, because the fallback *is* `--`: a card that never
populated is indistinguishable from one waiting for input.

I nearly missed it because the values in the screenshot I had checked the
layout against were ones I injected by hand to photograph the tiles.

Fixed, and `backend/tests/test_distance_score_contract.py` now checks both
sides of the binding against the live response — the field names the card
reads, that the API returns them, and that they are numeric.

`distance_score` now sources competition from the OPO measure
(`competition_basis: "opo"`, with the circle figure retained for comparison),
because a component measured not to predict has no business driving 35% of a
displayed score. Billings is the case that shows what changed: its circle
score of 0.00 gave it a **perfect 100** on that component; it now scores 51.0.

**Verified end to end.** Fronting the browser pane and clicking the map
populates the card for the first time:

> Composite **45.7** · Proximity **45.5** · Competition (OPO) **51.0** · Donor Pool **38.6**

Two false signals on the way there, both in the verification rather than the
code, and both worth knowing about for the next person:

- The map reported 0 px wide. There are **two** `.leaflet-container` elements
  — the hidden Data Layers map and the Spatial Analysis one — and
  `querySelector` returns the first. Index `[1]` is the live map.
- Checking whether the server had the fix returned the *buggy* file, because
  `fetch()` uses the HTTP cache by default. `{cache: 'no-store'}` shows the
  truth. For a moment this looked like the fix had not landed when it had.

---

## Acceptance-weighting the OPO count adds nothing

I called per-center offer acceptance "the most promising remaining addition".
Tested, it is not an addition at all.

The circular version — a center's *own* acceptance against its own transplant
rate — is included as a **control**, because it should be strongly positive if
the OARR data means what it claims:

| organ | n | own OAR (control) | p | rivals' mean OAR | p | rivals' OAR-weighted count | p |
|---|---|---|---|---|---|---|---|
| kidney | 204 | **+0.4192** | <0.0001 | −0.0747 | 0.289 | −0.1916 | 0.006 |
| liver | 119 | **+0.3596** | 0.0001 | −0.1510 | 0.101 | −0.1826 | 0.047 |
| heart | 123 | **+0.4262** | <0.0001 | +0.0760 | 0.403 | −0.0854 | 0.348 |
| lung | 43 | **+0.4232** | 0.0047 | +0.2227 | 0.151 | −0.2880 | 0.061 |

The control lands hard positive on every organ, so the data is sound and the
method reads it correctly.

The substantive question — whether **rivals'** aggressiveness depresses a
center's access — is answered no. Rivals' mean OAR predicts nothing anywhere.
And the OAR-weighted rival count is indistinguishable from the plain count
already shipped: kidney **−0.1916 weighted vs −0.1881 unweighted**, liver
−0.1826 vs −0.1809. The count carries the signal; the weighting is decoration.

Worth stating why the strong control is *not* a finding to act on. A center
that accepts more offers transplants more people — that is close to a
tautology, and offer acceptance already feeds the simulation as an
acceptance-thinning input (#320). It is not a competition measure.

**Three recommendations of mine have now been tested and failed**: candidates
per center (#429), acceptance weighting (here), and — from the other
direction — the claim that a center count is the wrong *unit* when it was the
wrong *shape*. The OPO catchment is the one that survived. That ratio is
worth remembering when reading the "what would actually validate it" section
of any report, including this one.