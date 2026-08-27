# Does the ranking survive a different reasonable weighting? (SCORE-01)

Every center score is a weighted sum of eight categories whose
magnitudes the register records as `uncited`. The existing assumption
sweep perturbs one category by ±20% and finds the ranking stable —
which answers *is it robust to a nudge*, not *does it depend on whose
judgement produced the numbers*.

The alternatives below are defensible positions a real candidate might
hold, not adversarial ones. `reversed order` is the exception and is
marked as a stress test.

| organ | weighting | Spearman vs shipped | top-10 overlap | same #1? |
|---|---|---|---|---|
| kidney | equal (no view on importance) | 0.9241 | 6/10 | **no** |
| kidney | wait-time first | 0.7965 | 3/10 | yes |
| kidney | program-quality first | 0.6239 | 4/10 | yes |
| kidney | medical-compatibility first | 0.9240 | 6/10 | **no** |
| kidney | reversed order (stress test) *(stress test)* | 0.4914 | 4/10 | **no** |
| liver | equal (no view on importance) | 0.9326 | 7/10 | **no** |
| liver | wait-time first | 0.8848 | 5/10 | **no** |
| liver | program-quality first | 0.6707 | 5/10 | yes |
| liver | medical-compatibility first | 0.9325 | 7/10 | **no** |
| liver | reversed order (stress test) *(stress test)* | 0.5036 | 4/10 | **no** |
| heart | equal (no view on importance) | 0.9573 | 8/10 | **no** |
| heart | wait-time first | 0.9561 | 4/10 | **no** |
| heart | program-quality first | 0.8495 | 6/10 | **no** |
| heart | medical-compatibility first | 0.9580 | 8/10 | **no** |
| heart | reversed order (stress test) *(stress test)* | 0.6780 | 6/10 | **no** |
| lung | equal (no view on importance) | 0.9476 | 6/10 | **no** |
| lung | wait-time first | 0.9476 | 8/10 | **no** |
| lung | program-quality first | 0.8200 | 5/10 | **no** |
| lung | medical-compatibility first | 0.9502 | 6/10 | **no** |
| lung | reversed order (stress test) *(stress test)* | 0.6147 | 3/10 | **no** |

## These weights ARE load-bearing

Across defensible alternatives alone, the worst rank correlation is
**0.6239** and the top-10 overlap falls to **3/10**. The top-ranked center changes in **13 of 16** comparisons.

For contrast, every other constant measured this way in this project
was inert: the BBN discretization split moves rankings by ρ 0.9987
even when swung from near-deterministic to barely informative, and
removing the donor-supply effect entirely leaves ρ 0.9957. Those are
constants whose exact value does not matter. **These are not.**

## Why this matters more than the other findings

This is the headline output. The results table sorts by score by
default, so a candidate reading the top of that list is reading a
conclusion that depends materially on eight numbers with no published
source.

It is also NOT covered by the uncertainty the platform already
reports. The rank intervals from #313 bootstrap the *probability*
estimates and rank by `p24` — a different quantity from the composite
score, and an interval that varies the data while holding the weights
fixed. The score ranking currently carries no interval at all.

## What this does and does not say

It does **not** say the shipped weights are wrong. There is no ground
truth here: 'which center is best for me' is a preference, not a fact,
and a weighted composite is a reasonable way to express one.

It says the *choice* is consequential and currently invisible. Two
honest responses, neither of which is picking better numbers:

1. **Make the dependence visible** — the weights are already
   user-adjustable via the weight panel; the ranking should say that
   it reflects a particular weighting, and ideally show how much it
   moves under others.
2. **Report a weight-uncertainty interval** alongside the sampling
   one, so the reported rank reflects both sources.

Sourcing the magnitudes would help but cannot resolve it — there is no
literature that fixes how one candidate should trade program quality
against travel distance.

