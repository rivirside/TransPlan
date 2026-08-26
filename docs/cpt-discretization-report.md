# Do the BBN discretization probabilities matter? (#213)

The tercile-to-state mapping uses three fixed vectors, of which
`_CPT_STRONG = [0.70, 0.25, 0.05]` is the headline. #213 filed these
as arbitrary. They now carry a source (Druzdzel & van der Gaag 2000,
a standard weakly-informative parameterisation for expert-elicited
ordinal CPTs) — but a citation answers *where the number came from*,
not *whether it matters*. This measures the second question.

The split is swept far past any defensible disagreement: 90/9/1 is a
near-deterministic discretization, 50/35/15 is barely informative.

| granularity | organ | variant | Spearman vs shipped | max abs delta p24 | top-10 identical |
|---|---|---|---|---|---|
| state | kidney | 90/9/1 (near-deterministic) | 0.99989 | 0.0145 | yes |
| state | kidney | 80/17/3 | 0.99997 | 0.0073 | yes |
| state | kidney | 60/30/10 | 1.00000 | 0.0093 | yes |
| state | kidney | 50/35/15 (barely informative) | 1.00000 | 0.0186 | yes |
| state | liver | 90/9/1 (near-deterministic) | 0.99989 | 0.0126 | yes |
| state | liver | 80/17/3 | 1.00000 | 0.0063 | yes |
| state | liver | 60/30/10 | 0.99982 | 0.0081 | yes |
| state | liver | 50/35/15 (barely informative) | 0.99963 | 0.0161 | yes |
| state | heart | 90/9/1 (near-deterministic) | 0.99948 | 0.0094 | no |
| state | heart | 80/17/3 | 0.99992 | 0.0047 | no |
| state | heart | 60/30/10 | 0.99933 | 0.0060 | no |
| state | heart | 50/35/15 (barely informative) | 0.99926 | 0.0119 | no |
| state | lung | 90/9/1 (near-deterministic) | 0.99979 | 0.0022 | no |
| state | lung | 80/17/3 | 0.99981 | 0.0011 | no |
| state | lung | 60/30/10 | 0.99984 | 0.0014 | yes |
| state | lung | 50/35/15 (barely informative) | 0.99970 | 0.0027 | yes |
| full | kidney | 90/9/1 (near-deterministic) | 0.99999 | 0.0148 | yes |
| full | kidney | 80/17/3 | 1.00000 | 0.0074 | yes |
| full | kidney | 60/30/10 | 0.99999 | 0.0095 | yes |
| full | kidney | 50/35/15 (barely informative) | 0.99998 | 0.0190 | yes |
| full | liver | 90/9/1 (near-deterministic) | 0.99980 | 0.0132 | yes |
| full | liver | 80/17/3 | 0.99992 | 0.0066 | yes |
| full | liver | 60/30/10 | 0.99987 | 0.0084 | no |
| full | liver | 50/35/15 (barely informative) | 0.99973 | 0.0168 | no |
| full | heart | 90/9/1 (near-deterministic) | 0.99983 | 0.0097 | yes |
| full | heart | 80/17/3 | 0.99992 | 0.0049 | yes |
| full | heart | 60/30/10 | 0.99985 | 0.0062 | yes |
| full | heart | 50/35/15 (barely informative) | 0.99968 | 0.0123 | no |
| full | lung | 90/9/1 (near-deterministic) | 0.99924 | 0.0057 | yes |
| full | lung | 80/17/3 | 0.99981 | 0.0029 | yes |
| full | lung | 60/30/10 | 0.99942 | 0.0035 | no |
| full | lung | 50/35/15 (barely informative) | 0.99869 | 0.0071 | no |

## Verdict

Across 32 comparisons spanning 4 organs and both granularities, the worst rank correlation against the shipped values is **0.99869** and the largest absolute change in any center's 24-month probability is **0.0190**.

For scale: #309 measured the recoverable ranking ceiling at rho ~= 0.92, and #311 measured that the shipped intervals needed widening by 1.25x to reach nominal coverage. A perturbation that leaves rho at 0.99869 and moves p24 by at most 0.0190 is well inside uncertainty the model already reports.

These constants are **not load-bearing**. Moving them across a
range no one would seriously argue for changes the ordering
essentially not at all and the probabilities by under a
percentage point or two.

That resolves #213 as asked-and-answered rather than fixed: the
values have a source, and their exact choice provably does not
drive results. Effort is better spent on the assumptions that do —
the priority-to-justify shortlist in the assumptions register.

The reason this needed measuring rather than arguing is that a
citation and a sensitivity are different claims. A cited constant
can still dominate a model; an uncited one can be irrelevant. Only
the second property makes it safe to stop worrying about.


## The donor-supply wait multiplier (#214)

`_DONOR_SUPPLY_WAIT_MULT = [1.2, 1.0, 0.8]` is the other
module-level heuristic in this file. A T6 test already asserted it
does not drive rankings, but only for kidney at one granularity
with one perturbation, and as a hidden pass/fail rather than a
published number. Swept here on the same footing — including the
variant that removes the effect ENTIRELY, which is the informative
one: if rankings survive `[1, 1, 1]`, the node is not carrying the
model.

| granularity | organ | variant | Spearman vs shipped | max abs delta p24 |
|---|---|---|---|---|
| state | kidney | 1.5/1.0/0.5 (stronger) | 0.99987 | 0.0430 |
| state | kidney | 1.05/1.0/0.95 (near-null) | 1.00000 | 0.0270 |
| state | kidney | 1.0/1.0/1.0 (removed entirely) | 0.99997 | 0.0371 |
| state | liver | 1.5/1.0/0.5 (stronger) | 0.99811 | 0.0392 |
| state | liver | 1.05/1.0/0.95 (near-null) | 0.99942 | 0.0240 |
| state | liver | 1.0/1.0/1.0 (removed entirely) | 0.99881 | 0.0327 |
| state | heart | 1.5/1.0/0.5 (stronger) | 0.99661 | 0.0348 |
| state | heart | 1.05/1.0/0.95 (near-null) | 0.99764 | 0.0188 |
| state | heart | 1.0/1.0/1.0 (removed entirely) | 0.99683 | 0.0253 |
| state | lung | 1.5/1.0/0.5 (stronger) | 0.99747 | 0.0106 |
| state | lung | 1.05/1.0/0.95 (near-null) | 0.99926 | 0.0047 |
| state | lung | 1.0/1.0/1.0 (removed entirely) | 0.99880 | 0.0062 |
| full | kidney | 1.5/1.0/0.5 (stronger) | 0.99999 | 0.0446 |
| full | kidney | 1.05/1.0/0.95 (near-null) | 0.99997 | 0.0279 |
| full | kidney | 1.0/1.0/1.0 (removed entirely) | 0.99996 | 0.0382 |
| full | liver | 1.5/1.0/0.5 (stronger) | 0.99861 | 0.0417 |
| full | liver | 1.05/1.0/0.95 (near-null) | 0.99939 | 0.0252 |
| full | liver | 1.0/1.0/1.0 (removed entirely) | 0.99903 | 0.0343 |
| full | heart | 1.5/1.0/0.5 (stronger) | 0.99843 | 0.0360 |
| full | heart | 1.05/1.0/0.95 (near-null) | 0.99939 | 0.0194 |
| full | heart | 1.0/1.0/1.0 (removed entirely) | 0.99893 | 0.0261 |
| full | lung | 1.5/1.0/0.5 (stronger) | 0.99494 | 0.0243 |
| full | lung | 1.05/1.0/0.95 (near-null) | 0.99787 | 0.0118 |
| full | lung | 1.0/1.0/1.0 (removed entirely) | 0.99568 | 0.0156 |

**Removing the donor-supply effect entirely** leaves the worst rank correlation at 0.99568 and moves p24 by at most 0.0382. The multiplier is a documented directional assumption that changes almost nothing — the rankings are carried by the data-grounded factors (observed per-center rates and wait factors), which is what #211 and #206 were for.

This settles the "no sensitivity analysis" half of #214.
The other halves — the DonorSupply composite being an ad-hoc
formula, and MortalityRisk having no interaction terms — are
modelling questions this does not touch, and #214 stays open
for them.

Note: top-10 MEMBERSHIP changed in 1 of 32 comparisons. Where the top-10 order differs but membership does not, that is near-ties reshuffling — which the rank-interval and tie-group feature exists to communicate.

