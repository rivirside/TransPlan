# What is the center ranking actually made of? (L-084)

The scoring UI shows eight category weights and lets users adjust them.
That presentation implies each weight is a lever on the ranking, in
proportion to its size.

A weight is only a lever if its sub-score **varies between centers**. A
category that scores the same everywhere adds the same constant to every
center's total, and no weight on it — however large — can reorder
anything.

This report measures which categories actually vary, and finds that the
largest weight in the model sits on one that does not.

## Method

For each organ's reference patient, score all centers and take the
between-center standard deviation of each category sub-score. The share
of the ranking a category can drive is `weight × SD`, normalised across
the eight categories. Contrast that with the weight alone, which is what
the UI shows.

`scripts/run-category-variance.py`; artifact
`docs-site/static/data/category-variance.json`.

## Result: `medicalCompatibility` is constant across centers

| organ | centers | `medicalCompatibility` SD | distinct values |
|---|---|---|---|
| kidney | 233 | 2.8e-14 | 1 (92.8) |
| liver | 148 | ~0 | 1 |
| heart | 149 | ~0 | 1 |
| lung | 74 | ~0 | 1 |
| pancreas | 99 | ~0 | 1 |
| intestine | 21 | ~0 | 1 |

This is not a data artifact — it is structural.
`_medical_compatibility()` (`backend/services/scoring.py:86`) takes only
the patient profile, and says so:

> *"Pure patient-profile scoring — no geographic data needed."*

It reads blood type, age, urgency and the organ-specific score. No
center argument is passed, so no center can differ. Its weight is
**0.25 — the largest of the eight.**

## What the ranking is really made of

| organ | waitTime | hospitalQuality | donorAvailability | geographic | healthDemographics | policy | socioeconomic | medicalCompatibility |
|---|---|---|---|---|---|---|---|---|
| kidney | 50.6% | 21.2% | 13.4% | 6.0% | 5.9% | 2.0% | 1.0% | **0.0%** |
| liver | 52.9% | 21.0% | 12.3% | 5.6% | 5.3% | 2.0% | 0.9% | **0.0%** |
| heart | 52.3% | 21.5% | 10.3% | 6.6% | 5.9% | 2.3% | 1.1% | **0.0%** |
| lung | 31.4% | 33.2% | 14.7% | 9.5% | 6.6% | 3.1% | 1.5% | **0.0%** |
| pancreas | 54.4% | 14.2% | 12.5% | 8.0% | 7.2% | 2.5% | 1.2% | **0.0%** |
| intestine | 58.0% | 18.1% | 11.2% | 6.4% | 3.9% | 1.6% | 0.8% | **0.0%** |

The advertised weighting says medical compatibility is the primary
consideration at 25% and wait time is secondary at 20%. The ranking says
wait time is the primary consideration at roughly half, and medical
compatibility is not a consideration at all.

## Three consequences

**1. The slider for the highest-weighted category does not work.**
Moving `medicalCompatibility` from 0.25 to 0.0 leaves the kidney ranking
identical at ρ 0.99995. 51 of 233 positions do shift, but they are
near-ties reshuffled by `total` being rounded to one decimal — at the
first difference the two centers score 78.8 and 78.7 — not a
re-ranking. A candidate who decides compatibility matters most to them
and drags the slider up gets the same list back.

**2. The displayed weights misdescribe the output.** This matters more
than the dead slider: a user reading the weight panel forms a belief
about why a center is recommended, and that belief is wrong for the
largest term.

**3. The score range is compressed.** The constant adds 23.2 points to
every center's kidney total. The displayed spread is 57.8–85.3 (27.5
points) where the rank-relevant spread is 46.2–82.8 (36.6 points) —
about a quarter of the apparent differentiation between centers is
removed by a term that is identical for all of them.

## This explains two other findings

**L-082 / the ordinal-simplex study.** Holding the category ordering
fixed and sampling the magnitudes over everything it permits barely
moved the ranking (worst ρ 0.905). Part of the reason is now clear: the
largest weight is spent on a constant, and `waitTime` dominates what is
left, so redistributing magnitude among the top categories has less
purchase than the weight vector suggests.

**L-083 / lung's undetermined top.** Lung is the *only* organ where
`waitTime` does not dominate — `hospitalQuality` (33.2%) actually edges
it (31.4%). Two near-equal drivers mean the leader depends on which the
sampled weights happen to favour, which is exactly why eight different
lung centers take first place across the draws while every other organ's
leader is stable. The anomaly and its mechanism agree.

## What this does not claim

Not that medical compatibility is irrelevant to a candidate: it is a
real property of the patient and belongs in a patient-level match score.
Not that the sub-score is miscomputed. The defect is that a
patient-level constant is presented as a *center* comparison input and
given the largest weight there.

Whether the sub-score *should* vary by center is a separate, genuine
modelling question — center ABO distributions, CPRA handling, size
matching and acceptance thresholds all differ, and #320's offer-
acceptance data is the natural input. That is a change requiring data
and validation, not a relabelling, and is filed separately.
