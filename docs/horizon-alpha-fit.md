# The 12→24 month exponent can be fitted, and the shipped value is wrong for five organs

**Date:** 2026-08-28
**Follows:** #233 / BBN-19 / L-095, which established that this constant is the *sole* determinant of the displayed waitlist-mortality and removal figures.
**Status:** measured, **not adopted** — see "Why this is not shipped".

---

## The assumption was thought untestable. It is not.

`_extend_12_to_24` assumes constant cause-specific hazards, giving S(24) = S(12)². SRTR publishes 12-month outcomes, not 24-month, which is why the bridge exists — and why the register carries the exponent as `assumed`.

But **SRTR's Table B7 publishes the same cohort at 6, 12 AND 18 months** (`SAL_*_U6`, `_U12`, `_U18`). Three horizons on one cohort is enough to observe the hazard's *shape*, and shape is exactly what the exponent encodes.

## The hazard falls, monotonically, for five of six organs

Interval hazards from the national still-waiting share, λ = −Δln S / Δt:

| organ | λ(0–6) | λ(6–12) | λ(12–18) | trend |
|---|---|---|---|---|
| kidney | 0.0560 | 0.0375 | 0.0327 | falling |
| liver | 0.1806 | 0.1052 | 0.0714 | falling |
| heart | 0.2258 | 0.0704 | 0.0423 | **falling 5.3×** |
| lung | 0.3168 | 0.1410 | 0.1148 | falling |
| intestine | 0.0936 | 0.0753 | 0.0468 | falling |
| **pancreas** | 0.0407 | 0.0375 | 0.0420 | **flat** |

A constant hazard — the shipped assumption — would give three equal columns. It does so for pancreas and for nothing else.

This is the depletion-of-susceptibles pattern #297 measured independently for removals: the sickest candidates leave the list early, so the surviving cohort is healthier and its hazard drops.

## The implied exponent

Taking the observed 12–18 hazard, extrapolating it across 18–24, and solving S(24) = S(12)^α:

| organ | S(6) | S(12) | S(18) | implied α | shipped |
|---|---|---|---|---|---|
| kidney | 0.7148 | 0.5709 | 0.4692 | **1.700** | 2.0 |
| liver | 0.3383 | 0.1800 | 0.1172 | **1.500** | 2.0 |
| heart | 0.2579 | 0.1691 | 0.1312 | **1.286** | 2.0 |
| lung | 0.1494 | 0.0641 | 0.0322 | **1.501** | 2.0 |
| intestine | 0.5704 | 0.3630 | 0.2741 | **1.554** | 2.0 |
| pancreas | 0.7833 | 0.6254 | 0.4861 | 2.074 | 2.0 |

**The method returns α ≈ 2.07 for pancreas — the one organ whose hazard is genuinely flat.** Recovering the shipped assumption exactly where the shipped assumption holds is what makes the other five values credible rather than an artifact of the arithmetic. (Same role lung's unclamped σ plays as the zero-spread control in `timing-uncertainty-report.md`.)

## What adopting it would change

p24 is untouched — that invariance is algebraic (L-095). The breakdown moves substantially:

| organ | mean mortality | mean removed | change |
|---|---|---|---|
| kidney | 0.0531 → 0.0427 | 0.0578 → 0.0463 | −20% |
| liver | 0.0865 → 0.0666 | 0.1430 → 0.1108 | −23% |
| heart | 0.0415 → 0.0242 | 0.0760 → 0.0453 | **−42%** |
| lung | 0.0326 → 0.0255 | 0.0369 → 0.0295 | −22% |
| intestine | 0.0682 → 0.0483 | 0.0844 → 0.0596 | −29% |
| pancreas | 0.0569 → 0.0590 | 0.1390 → 0.1441 | +4% |

## Why this is not shipped

Three reasons, and the first is the one that decides it.

**It moves a mortality figure downward.** Every other correction this sweep shipped either removed a penalty applied without evidence (#415's Rh) or widened an interval that was too narrow (#420). Those err toward caution. This one makes centers look *safer*, and understating waitlist mortality is the asymmetric-harm direction for someone choosing where to list.

**It rests on an extrapolation, not an observation.** The 18–24 window is unobserved; α is derived by holding the 12–18 hazard flat across it. Since the hazard has been *falling* at every step, that likely still overstates terminal outcomes — so these values are probably conservative, and the true α lower still. "Probably conservative" is a reasonable basis for a recommendation and a poor one for silently changing a clinical number.

**No automated gate can adjudicate it.** The per-center calibration metric correlates p24, and p24 is *algebraically invariant* to α (L-095) — forcing α to 1.0 moves the CompetingOutcome CPT by 0.25 and p24 by exactly 0.000000. So the usual "does it clear calibration?" question has no answer here. The C6/C12/C18 data above is the strongest evidence obtainable, and it is still an extrapolation.

This matches the project's own precedent: #297 measured that the delisting multipliers have the **wrong sign** and did not change them, filing #380 instead.

## Recommendation

Adopt the fitted per-organ α, after a clinician sanity-check that the depletion-of-susceptibles reading is right — this is squarely what #107 (face-validity review with transplant faculty) exists for. The implementation is a per-organ dict replacing the hardcoded square; `_extend_12_to_24` already takes the vector it needs.

If a review says the extrapolation is too aggressive, the conservative middle is to adopt α halfway between fitted and 2.0, which still removes most of the overstatement.

What should **not** happen is leaving α = 2.0 undisturbed on the grounds that it is the status quo. It is contradicted by the registry's own data for five of six organs, and that is now measured rather than suspected.
