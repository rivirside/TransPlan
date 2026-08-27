# The Rh factor in TransPlan's model

**Date:** 2026-08-27
**Trigger:** #180, "Find My Centers: add Rh factor (positive/negative) to blood type input"
**Verdict:** the request is already implemented, and its premise is inverted — the model does not under-use Rh, it over-uses it, via an unsourced hand-set constant.

---

## What the issue asked for

> The Find My Centers page (`find-centers.html`) currently accepts blood type (A, B, AB, O) but does not capture the Rh factor […] **Rh factor significantly affects wait times and donor compatibility.**

Two things are wrong with this as a work item.

**The page does not exist.** `find-centers.html` was merged into the tabbed `centers.html` during the Phase 3 page merge. The live simulator has offered all eight ABO+Rh combinations for some time (`simulator.html`, the blood-type select).

**The premise is backwards.** Solid-organ allocation in the United States is ABO-matched. RhD is a red-cell antigen; it is not part of OPTN's matching for kidney, liver, heart, lung, pancreas or intestine. There is no allocation mechanism by which an Rh-negative candidate waits longer for an organ.

The model nevertheless says they do.

## What the model actually does

Every Rh-negative candidate is given a longer predicted wait and a lower suitability score than an otherwise identical Rh-positive candidate.

### 1. The wait-time multipliers (SURV-14 / DATA-01 / DATA-05 / GEN-12)

`data/wait-time-distributions.json` ships an eight-entry `blood_type_multipliers` table per organ. The Rh-negative entries are uniformly larger:

| organ | Rh-negative wait penalty, by ABO group |
|---|---|
| kidney | O +7.7%, A +11.1%, B +8.7%, AB +18.2% |
| liver | O +4.0%, A +5.6%, B +4.5%, AB +7.1% |
| heart | O +4.2%, A +5.6%, B +4.8%, AB +6.7% |
| lung | O +4.5%, A +5.3%, B +2.9%, AB +5.9% |
| pancreas | O +8.0%, A +5.6%, B +9.1%, AB +16.7% |
| intestine | O +4.3%, A +5.3%, B +4.8%, AB +6.2% |

**Those percentages are an artifact of presentation.** In multiplier space the adjustment is a flat additive constant per organ:

| organ | O | A | B | AB |
|---|---|---|---|---|
| kidney | +0.10 | +0.10 | +0.10 | +0.10 |
| liver | +0.05 | +0.05 | +0.05 | +0.05 |
| heart | +0.05 | +0.05 | +0.05 | +0.05 |
| lung | +0.05 | +0.05 | **+0.03** | +0.05 |
| pancreas | +0.10 | **+0.05** | +0.10 | +0.10 |
| intestine | +0.05 | +0.05 | +0.05 | +0.05 |

Twenty-two of the twenty-four cells are one of two round numbers, and the two that are not (lung B, pancreas A) have no distinguishing feature — they read as slips. The percentage penalty then varies across ABO groups only because the baselines differ; AB gets the largest apparent penalty because AB has the shortest baseline wait, not because anything about AB interacts with Rh.

A quantity derived from data does not come out as the same round number twenty-two times.

### 2. The compatibility score (SCORE-03)

`scoring.py` applies a **second** Rh penalty, through a different and inconsistent convention:

| group | Rh+ | Rh− | gap |
|---|---|---|---|
| O | 85 | 70 | **−15** |
| A | 95 | 88 | −7 |
| B | 90 | 82 | −8 |
| AB | 100 | 92 | −8 |

Nothing reconciles a −15 for O with a −7 for A, and nothing reconciles either with the flat +0.05/+0.10 used in the wait table. These are two independent hand-set conventions for the same claimed phenomenon, and they disagree.

## What it costs the patient

Measured on the shipped data, holding everything else fixed and changing only Rh:

| organ | median wait | p(transplant within 24 mo) |
|---|---|---|
| kidney | 35.62 → 38.36 mo (**+2.74**) | 0.7270 → 0.7087 (**−0.0183**) |
| pancreas | 28.50 → 30.78 mo (**+2.28**) | 0.8720 → 0.8548 (−0.0172) |
| intestine | 13.34 → 13.92 mo (+0.58) | 0.9223 → 0.9177 (−0.0046) |
| liver | 5.75 → 5.98 mo (+0.23) | 0.9718 → 0.9690 (−0.0028) |
| heart | 2.64 → 2.75 mo (+0.11) | 0.9955 → 0.9952 (−0.0003) |
| lung | 1.54 → 1.61 mo (+0.07) | 0.9978 → 0.9975 (−0.0003) |

The suitability score drops by 0.70–1.50 points at *every* center. Consistent with L-084 and L-085, the ranking is unchanged — blood type reaches only the center-invariant sub-score — so the harm is entirely in the magnitudes a candidate reads, not in which center they are pointed to.

An Rh-negative kidney candidate is currently told to expect nearly three additional months of waiting, on no evidence.

## Why no calibration gate can settle this

The usual move here is to sweep the constant and let per-center calibration decide (#274, #376, #213). That is not available:

**SRTR does not publish blood type with Rh.** Tables B8–B9 report candidate counts as O / A / B / AB. The register already records this twice — DATA-46 and EQSP-32 both note that the equity weights have to split each ABO group 84/16 by the US Rh-positive share precisely because the source does not stratify.

So the eight-entry table has four categories of evidence behind it. The Rh half cannot be calibrated, cannot be validated, and cannot be refuted by data the project has or can obtain. It has to be judged on mechanism, and the mechanism is allocation policy, which is ABO-only.

This is the "prove the gate can see your change" lesson in a stronger form: here the gate cannot see it *even in principle*.

## How much of the equity signal is fabricated

The equity audit varies blood type across all eight groups (EQSP-01's 48-profile matrix). Decomposing the variance of the wait multiplier into between-ABO and within-ABO (i.e. Rh):

| organ | Rh share of blood-type variance |
|---|---|
| kidney | 3.0% |
| liver | 1.4% |
| heart | 2.2% |
| lung | 5.6% |
| pancreas | 3.3% |
| intestine | 3.6% |

Small in variance terms — but this is not noise that averages out. It is a **systematic directional penalty** applied to roughly 15% of candidates, so it biases the reported disparity in one direction rather than widening it symmetrically.

## Recommendation

Make the model ABO-only, treating the `+` entries as the ABO-group values and the `−` entries as the adjustment to drop. Rh-positive numbers are unchanged; Rh-negative numbers lose a penalty that nothing supports.

The clean implementation is to canonicalize blood type to its ABO group **once, at the model boundary**, rather than editing eight-entry tables in six places — the wait multipliers, the compatibility score, the BBN's `BLOOD_TYPES` CPT axis, the MCMC index, and the equity matrix all then become Rh-blind together, and the shipped tables stay intact for reference and rollback.

Keep all eight options in the UI. Patients know their full blood type, and being told plainly that Rh does not affect organ allocation is more useful than being asked for it and silently penalized for the answer.

Tracked as **L-088**; the removal is filed separately because it changes patient-visible estimates across six organs and three inference engines.
