# What the 12→24 month extension actually controls (#233 / BBN-19)

**Date:** 2026-08-28
**Verdict:** it cannot move the headline transplant probability — provably, by cancellation — and it is the *sole* determinant of the displayed waitlist-mortality and removal probabilities, where defensible alternatives span a **4× range**.

---

## The assumption

The BBN's `CompetingOutcome` node is the model's one fully data-grounded node: each cell is a center's **observed** 12-month outcome vector from SRTR Table B7 (#206/#211). But the headline is at **24 months**, and SRTR publishes no such figure. `_extend_12_to_24` bridges the gap by assuming **constant cause-specific hazards**, giving S(24) = S(12)².

The register carries it as BBN-19, `assumed`, uncited. #233 asks for a citation. The more useful question is what it does.

The project has already contradicted the assumption elsewhere: **#297** measured the interval removal hazard within a single cohort and found it *falls* with time on the list for liver, heart, lung and intestine — depletion of susceptibles, since the sickest candidates leave early. If the second-year hazard is lower than the first, S(24) > S(12)² and the shipped extension overstates every terminal outcome.

## The sweep

Generalise the exponent and sweep it:

```
S(24) = S(12) ** alpha
```

| α | meaning |
|---|---|
| 1.0 | no second-year hazard at all |
| 1.5 | second-year hazard ≈ half the first — the direction #297 measured |
| **2.0** | **shipped**: constant hazard |
| 2.5 | second-year hazard higher than the first |
| 3.0 | sharply rising |

Each cause-specific CIF is rescaled by (1 − S(24))/(1 − S(12)), which preserves the simplex for any α. 4 organs × 2 granularities × 4 variants = 32 comparisons.

## Result 1: the headline probability is immune, and not by accident

| α | mean p24 (kidney, state) |
|---|---|
| 1.0 | 0.285982 |
| 1.5 | 0.285982 |
| 2.0 | 0.285982 |
| 2.5 | 0.285982 |
| 3.0 | 0.285982 |

Bit-identical. Across all 32 comparisons the largest |Δp24| is **0.0004**, which is rounding.

This is algebra, not a weak effect. The extension multiplies `tx`, `death` and `removed` by a **common factor**, and the only quantity `p_24` derives from them is

```
q = (death + delist) / (tx + death + delist)
p_24 = time_probs["p24"] * (1 - q)
```

`q` is a ratio of those three, so the common factor cancels exactly. **No hazard-shape assumption expressible this way can reach p24.** The headline number's timing comes entirely from `WaitCategory`; `CompetingOutcome` contributes only the scale-invariant loss share.

That is worth stating plainly because the code describes `CompetingOutcome` as the model's data-grounded foundation (BBN-17), and a reader could reasonably assume the observed vector is what produces the reported probability. It supplies the drain, not the number.

**This also nearly produced a false null.** The first version of this sweep measured p24 alone and reported a perfect null for every variant — worst Spearman 1.00000, top-10 identical 32/32. That reads as "the assumption doesn't matter" when the truth is "the metric cannot see it". Forcing α to 1.0 and confirming the CPT moved by 0.25 while p24 moved by exactly 0.000000 is what separated the two.

## Result 2: it is the sole determinant of the outcome breakdown

The `waiting` component is **not** multiplied by the common factor — it is S(12)^α directly — so it does not cancel, and it drives the split of non-transplant mass.

Kidney, state granularity, means across centers:

| α | mortality | removed | still waiting |
|---|---|---|---|
| 1.0 | 0.0219 | 0.0235 | 0.6686 |
| 1.5 | 0.0363 | 0.0392 | 0.6385 |
| **2.0 (shipped)** | **0.0531** | **0.0578** | **0.6031** |
| 2.5 | 0.0723 | 0.0790 | 0.5627 |
| 3.0 | 0.0935 | 0.1022 | 0.5184 |

Across all 32 comparisons: largest |Δ mortality| **0.149**, and mean mortality ranges **0.41× to 1.76×** of the shipped value.

At α = 1.5 — the direction #297's own measurement supports — the displayed 24-month waitlist mortality would be **0.036 rather than 0.053**, about a third lower.

## What this means for #233

"Add a literature citation" is the wrong remedy for this constant. What it needed was scope:

- **It cannot affect the transplant probability.** Structural, provable, and worth documenting so nobody attempts to tune it for that purpose.
- **It entirely determines the mortality/removal/waiting split**, and across defensible shapes that is a 4× lever on a number shown to patients.
- **The project's own #297 measurement suggests the shipped α = 2.0 is too high** for at least four organs, which would mean the displayed waitlist mortality is overstated.

Changing it is not in scope here: the correct α is organ-specific, #297's hazards are interval estimates within one cohort rather than a fitted second-year hazard, and any substitution has to clear the calibration gate. Filed rather than guessed.

`backend/tests/test_horizon_extension_scope.py` pins both halves — that p24 stays invariant, and that the breakdown stays *sensitive*, so this sweep cannot quietly become vacuous the way its first version was.
