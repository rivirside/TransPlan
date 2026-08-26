# Do delisting multipliers match the observed hazard? (#297)

`build_delisting_risk_cpt` scales delisting by WaitCategory with four
hand-set numbers. The code argues they cannot be fitted because
regressing observed delisting on the wait category is circular.

That is right about the obvious approach and wrong about the
conclusion. Regressing each CENTER's delisting rate on its wait factor
is confounded — and not just circularly: it estimates a BETWEEN-CENTER
contrast where the multiplier encodes a WITHIN-PATIENT one. But SRTR
publishes removals at 6, 12 AND 18 months for the same cohort, which
gives the interval hazard directly with no between-center contrast in
it at all.

| organ | hazard/mo 0-6 | 6-12 | 12-18 | ratio 6-12 | ratio 12-18 |
|---|---|---|---|---|---|
| kidney | 0.00303 | 0.00406 | 0.00454 | 1.34 | 1.50 |
| liver | 0.01068 | 0.00690 | 0.00481 | 0.65 | 0.45 |
| heart | 0.01033 | 0.00347 | 0.00248 | 0.34 | 0.24 |
| lung | 0.00763 | 0.00167 | 0.00090 | 0.22 | 0.12 |
| pancreas | 0.01399 | 0.01404 | 0.01736 | 1.00 | 1.24 |
| intestine | 0.00501 | 0.00649 | 0.00267 | 1.29 | 0.53 |

## The shipped multipliers have the direction wrong

The four values encode one monotonic RISE applied to every organ:
3.6x higher in the last band than the first. The observed hazard does
not behave that way, and does not behave the same way across organs.

Ratios to each organ's own first band, so they are comparable:

| band | shipped | kidney | liver | heart | lung | pancreas | intestine |
|---|---|---|---|---|---|---|---|
| <=6mo | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 6-12mo | 1.60 | 1.34 | 0.65 | 0.34 | 0.22 | 1.00 | 1.29 |
| 12-24mo | 2.40 | 1.50 | 0.45 | 0.24 | 0.12 | 1.24 | 0.53 |
| >24mo | 3.60 | not measurable | not measurable | not measurable | not measurable | not measurable | not measurable |

**Delisting risk FALLS with time on the list for liver, heart, lung, intestine.** Lung's hazard in months 12-18 is 0.12 of its first-six-month hazard. The shipped multiplier for that band is 2.4x the first. That is not a magnitude error — it is the wrong sign.

It rises, as the shipped values assume, only for kidney, pancreas.

This is clinically coherent rather than surprising, which is part of
why it is worth trusting. Candidates most likely to be removed as
'too sick', or to die, are removed EARLY — so the cohort still waiting
at 12 months is systematically healthier than the one that started, a
depletion-of-susceptibles effect. It is strongest exactly where early
mortality is highest (lung, heart) and reverses for kidney, whose
candidates are comparatively stable on dialysis and accumulate
comorbidity the longer they wait.

A single set of multipliers cannot represent both patterns. Whatever
replaces these has to be per organ.

## What this can and cannot settle

Bands 1 and 2 are measured directly. Band 3 is measured over its first
half (12-18 of 12-24). **Band 4 (>24 months) lies beyond every
published horizon** and cannot be grounded from this source, so any
value for it remains an extrapolation however the others are set.

That matters for how this should be used: replacing four hand-set
numbers with two measured ones, one half-measured one, and one still
extrapolated is a real improvement in provenance, but it is not a
fitted model, and the CPT is a discretized tercile summary rather than
a hazard model, so a like-for-like substitution is not automatic.
The measurement is recorded here first; changing the shipped values
is a separate decision that has to clear the calibration gate.

