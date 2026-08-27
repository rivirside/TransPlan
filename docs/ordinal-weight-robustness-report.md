# Is it the weight magnitudes or the weight ordering? (L-082 remedy 2)

L-082 records that the eight scoring weights are the model's one
load-bearing judgement call: measured against defensible alternative
weightings, the worst rank correlation is 0.624 and the top-ranked
center changes in 13 of 16 comparisons. Every other constant swept in
this project is inert by comparison.

#386 shipped the first half of the remedy — the results table now
annotates each center with its rank span across the app's four presets.
The second half asked for "a weight-uncertainty interval", and that ran
into a problem: any sampling neighbourhood needs a spread parameter, so
building one would relocate the uncited constant somewhere less visible
rather than resolve it.

This report takes a different route, by noticing that `DEFAULT_WEIGHTS`
contains **two separable claims**:

    medicalCompatibility .25 > waitTime .20 > donorAvailability .18 >
    hospitalQuality .15 > geographic .10 > healthDemographics .07 >
    policy .03 > socioeconomic .02

1. **An ordering.** Medical compatibility matters more than travel,
   which matters more than local socioeconomics. A reader can agree or
   disagree with this, and it is the part that carries actual content.
2. **Magnitudes.** Nothing whatsoever fixes `.25` rather than `.30`, or
   `.07` rather than `.05`. This is what the register marks `uncited`.

The question L-082 should be asking is which of the two the ranking
depends on — and that is answerable with no free parameters at all.

## Method

Keep the ordering; admit total ignorance of the magnitudes. The set of
weight vectors consistent with that state of knowledge is the **ordered
simplex**

    W = { w : w₁ ≥ w₂ ≥ … ≥ w₈ ≥ 0,  Σw = 1 }

and the uniform distribution on `W` is sampled *exactly* by drawing a
uniform point on the simplex — Dirichlet with all-ones concentration —
and sorting it descending. No radius, no spread parameter, no prior to
argue about. This is the standard ordinal-weight robustness setting in
multi-criteria decision analysis.

The sampler is not asserted to be uniform, it is **verified** against a
closed form: for a uniform draw on the k-simplex the expected value of
the i-th largest component is `(1/k)·Σ_{j=i..k} 1/j`, which is exactly
the rank-order-centroid (ROC) formula. Sampler mean and ROC are two
independent routes to the same vector and must agree
(`backend/tests/test_ordinal_weight_sampling.py`, with a negative
control confirming the check rejects a Dirichlet(5,…,5) sampler that is
ordered and normalised but not uniform).

ROC also serves as the canonical **point estimate** when only the
ordering is known, so "shipped vs ROC" measures whether the shipped
magnitudes are unremarkable for their ordering.

200 draws per organ, reference patients from `scripts/reference_patients.py`,
seed 20260826.

## Results

| organ | centers | ρ min vs shipped | ρ median | ROC ρ vs shipped | median 90% rank width | top-10 median width |
|---|---|---|---|---|---|---|
| kidney | 233 | 0.9089 | 0.9893 | 0.9899 | 21.0 | 9.5 |
| liver | 148 | 0.9295 | 0.9929 | 0.9944 | 12.0 | 4.5 |
| heart | 149 | 0.9648 | 0.9963 | 0.9973 | 10.0 | 4.0 |
| lung | 74 | 0.9355 | 0.9898 | 0.9924 | 8.0 | 9.0 |
| pancreas | 99 | 0.9723 | 0.9937 | 0.9955 | 7.0 | 7.0 |
| intestine | 21 | 0.9052 | 0.9935 | 0.9948 | 2.0 | 4.0 |

## The magnitudes are not what L-082 caught

**Worst case across all six organs is ρ = 0.905.** L-082's worst case is
**0.624**. The difference is entirely attributable to what varies:

- L-082's alternative weightings **reorder the categories** — a
  speed-priority candidate puts `waitTime` first, a quality-of-life
  candidate promotes `geographic` from 5th to 2nd.
- This study **holds the ordering fixed** and lets the magnitudes range
  over everything the ordering permits, from near-uniform to almost all
  mass on the first category.

So the uncited magnitudes are *not* the load-bearing part. Sourcing
`.25` versus `.30` would change very little; the ordering is doing the
work, and the ordering is the part that was always defensible and
checkable.

This also reframes the 0.624. It is not evidence of a defect: it is the
measurement of how much **a genuinely different patient preference**
changes the answer. "Which center is best for me" is a preference, not
a fact, and a candidate who ranks travel second is not using the model
wrong — they are using it correctly and getting a different, correct
answer. The presets and weight sliders already expose exactly that
choice.

Corroborating this, the shipped weights and ROC — derived from nothing
but the ordering — agree at ρ 0.9899–0.9973 and pick the **same top
center for all six organs**. The shipped magnitudes are unremarkable
for their ordering.

## The exception worth acting on: lung's top is a near-tie

Rank correlation being high does not mean the *top* is determined, and
lung shows the two coming apart:

| organ | shipped top center | share of draws it leads | distinct centers that lead |
|---|---|---|---|
| kidney | OHCC | **100%** | 1 |
| heart | COUC | **100%** | 1 |
| liver | FLUF | 98% | 3 |
| intestine | OHCC | 86% | 5 |
| pancreas | ILUI | 65% | 4 |
| lung | INIM | **25%** | **8** |

For lung, eight different centers take first place across the draws
while overall ρ stays at 0.99 — the ranking as a whole is stable and its
top is a cluster of near-ties. INIM is still the modal and the ROC
choice, so it is not wrong; it is just not *distinguishable* from seven
others on this evidence. Pancreas is a milder version of the same.

The actionable consequence is that "your #1 center" is a supportable
claim for kidney and heart and an unsupportable one for lung. That is
precisely the distinction the existing tie-group / rank-interval
feature (#313) exists to communicate, and lung is the case where it
matters most.

## An important caveat: part of this result is an artifact (L-084)

A "no effect" result has to be checked for being a false negative, and
this one is partly explained by a defect rather than by robustness.

`medicalCompatibility` — the **first** slot in the ordering, and so the
slot that receives the largest share of sampled mass by construction —
is **identical at every center** (`docs/category-variance-report.md`).
Whatever weight a draw puts there is spent on a constant and cannot
reorder anything.

So the sampling is systematically less potent than it looks: the biggest
component of every draw is inert, and the ranking is left to `waitTime`,
which dominates what remains (50–58% of rank-driving variation for five
of six organs). That damping is not evidence that magnitudes are
harmless in general.

The honest statement of the finding is therefore narrower:

> Given the shipped ordering **and the current sub-scores**, the uncited
> magnitudes do not materially move the ranking.

If `medicalCompatibility` were made center-specific — the modelling
question in #390 — the first slot would stop being inert and this study
would need re-running before its conclusion could be carried over. The
pinned test asserts the current worst case stays above 0.85 precisely so
that change cannot pass unnoticed.

## What this does and does not settle

**Settles:** the "report a weight-uncertainty interval" half of L-082,
for the component that is actually uncited. The interval attributable to
unknown magnitudes is roughly ±5 rank positions in the top 10 and ±10
overall, and it needs no invented constant to state — subject to the
L-084 caveat above.

**Does not settle:** the ordering itself is still uncited — this study
assumes it rather than testing it, by construction. Justifying *that*
is a clinical question (the SCORE-01 register row), and it is now the
sharper target: it is where the sensitivity lives.

**Does not claim** the shipped weights are correct. It claims their
*magnitudes* are not the reason the answer moves.
