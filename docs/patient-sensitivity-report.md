# How much of "best center for you" is actually about you? (L-085)

The product asks a candidate for their organ, blood type, age, sex,
urgency, and an organ-specific severity score, then returns a ranked
list of centers. This measures how much of that input reaches the
ranking.

Two questions are kept apart throughout, because they answer
differently and conflating them would overstate the result:

1. **Does the attribute change a candidate's numbers?** Blood type
   very much does — an AB+ candidate's mean 24-month probability runs
   about 23 points above the reference. That part works.
2. **Does it change *which center* is recommended?** This is what the
   results table sorts by, and what "best center for me" claims.

## Method

One attribute at a time, swept across its realistic range (O− vs AB+,
age 20 vs 70, cPRA 0 vs 99, MELD 10 vs 38, …), recording which
sub-scores move at all and whether the resulting center order changes.
`scripts/run-patient-sensitivity.py`; artifact
`docs-site/static/data/patient-sensitivity.json`.

## Result

| organ | attribute | sub-scores reached | ρ vs the other end | order identical |
|---|---|---|---|---|
| kidney | blood_type | `medicalCompatibility` | **1.00000** | **yes** |
| kidney | age | `medicalCompatibility` | 0.99993 | no¹ |
| kidney | sex | **(nothing)** | 1.00000 | **yes** |
| kidney | urgency | `waitTime` | 0.82367 | no |
| kidney | cpra | `waitTime` | **0.76020** | no |
| liver | blood_type | `medicalCompatibility` | **1.00000** | **yes** |
| liver | urgency | **(nothing)** | 1.00000 | **yes** |
| liver | meld | `waitTime` | **0.75998** | no |
| heart | blood_type | `medicalCompatibility` | **1.00000** | **yes** |
| heart | urgency | `waitTime` | 0.95011 | no |
| lung | blood_type | `medicalCompatibility` | **1.00000** | **yes** |
| lung | urgency | **(nothing)** | 1.00000 | **yes** |
| lung | las | `waitTime` | 0.94713 | no |

¹ ρ 0.9999 with the only channel being a center-invariant sub-score:
mathematically it cannot reorder, and the movement is near-ties
reshuffled by rounding the displayed total to one decimal.

## Blood type cannot change the ranking, by construction

Blood type reaches **exactly one** sub-score, `medicalCompatibility`
— and that is precisely the sub-score that is identical at every
center (L-084). Every other category is bit-identical between an O−
and an AB+ candidate; the two orderings are not merely similar but
literally the same list.

So blood type shifts every center's total by the same constant (85.3 →
88.3 for the kidney reference patient) and reorders nothing. The same
holds for age, and for sex wherever it is used at all.

The Monte Carlo path behaves the same way at the ranking level even
though its magnitudes are strongly personalised. Sweeping the same
ranges (values from the artifact, so the two tables are comparable):

| organ | attribute | mean p24 shift | ρ of center order |
|---|---|---|---|
| kidney | blood_type (O− → AB+) | **+0.2524** | 0.99875 |
| kidney | cpra (0 → 99) | −0.3029 | 0.99610 |
| liver | meld (10 → 38) | +0.3020 | 0.94355 |
| liver | blood_type | +0.0969 | 0.99675 |
| lung | las (30 → 80) | +0.1114 | 0.91630 |
| heart | blood_type | +0.0542 | 0.99667 |

A **25-point** swing in absolute probability that moves the ordering by
ρ 0.999 is the finding in one line: **magnitudes are personalised, the
ranking is not.**

### The two engines disagree about how much the patient matters

Worth flagging separately, because both are shown to users in the same
table. For kidney cPRA, the **scoring** path says the patient changes
the ranking a great deal (ρ 0.760) while the **simulation** path says
it barely does (ρ 0.996) — a large disagreement about the same
question. Blood type is the one they agree on, and they agree it
changes nothing.

## Attributes that reach nothing in the scoring path

Stated precisely, because these are claims about **scoring** — the
Monte Carlo path is separate and behaves differently.

- **`sex` reaches no scoring sub-score at all for kidney and liver**,
  and reaches only the inert `medicalCompatibility` for heart and lung.
  In the simulation path it moves kidney p24 by +0.0265 and **liver,
  heart and lung by exactly 0.0000**. So for liver, heart and lung it
  is a required field that changes no output at all; for kidney it
  changes the predicted number and nothing in the score.
- **`urgency` reaches nothing for liver and lung**, because those
  organs are driven by MELD and LAS instead. Defensible as design, but
  the form still asks, and nothing says the answer is ignored.

Both are required form fields.

## The correction: the ranking *is* patient-dependent, but coarsely

A one-at-a-time sweep can say which inputs matter. It cannot say
whether the product is, in aggregate, serving one list to everybody —
and concluding that from the table above would overstate it. So this
walks a grid of realistic patients and counts the distinct rankings
that actually come out.

| organ | patients in grid | distinct rankings | distinct #1 centers | median pairwise ρ | median top-10 overlap |
|---|---|---|---|---|---|
| kidney | 108 | **15** | 2 | 0.8147 | 7/10 |
| liver | 36 | 9 | 1 | 0.9314 | 9/10 |
| heart | 36 | 9 | 1 | 0.9853 | 9/10 |
| lung | 36 | 6 | 3 | **0.9997** | 10/10 |

**Kidney genuinely personalises.** Median pairwise ρ of 0.81 between
two real candidates, with top-10 overlap dropping to 2/10 at the
extremes, is a substantial difference — cPRA is doing real work. Any
reading of this report as "everyone gets the same list" is wrong for
kidney.

**Lung essentially does not.** At ρ 0.9997 and 10/10 top-10 overlap,
36 different lung candidates receive what is effectively one ranking.
Its 3 distinct top centers are not personalisation but the near-tie of
L-083 — the leader flips between indistinguishable programs rather
than in response to the patient.

**But the personalisation is coarse everywhere.** 108 realistic kidney
candidates produce only **15** distinct rankings, and 36 lung
candidates produce 6. That follows directly from the finding above:
only two or three inputs reorder anything, and each reaches the
ranking through a single sub-score. The output is not one list, but it
is a small menu of lists rather than a per-patient result.

## The inconsistency this exposes

Only the organ-specific severity and sensitisation measures change
which center is recommended: cPRA for kidney, MELD for liver, LAS for
lung, urgency for kidney and heart.

That makes the treatment of **cPRA versus blood type** hard to defend:

| | reorders centers? | ρ |
|---|---|---|
| cPRA (0 → 99) | **yes, substantially** | 0.760 |
| blood type (O− → AB+) | **no, not at all** | 1.000 |

Both are immunological constraints on access to the donor pool. Both
plainly interact with a center — a program's sensitised-patient
protocol matters for a high-cPRA candidate, and a center's ABO-specific
donor pool and allocation matter for an O candidate. The model gives
one of them a center interaction and the other none, and no
documentation states a reason.

That asymmetry reads as an artifact of where each attribute happened to
be wired, not as a modelling position.

## What this does and does not claim

**Does not claim** the ranking *should* depend heavily on blood type.
Much of what makes a center good — wait times, program quality, donor
supply — is a property of the center, and it is entirely reasonable
that the best center for one candidate is often the best for another.

**Does claim** that the current behaviour is undisclosed and internally
inconsistent. A candidate entering their blood type reasonably infers
it personalises the recommendation. It changes their predicted
probability substantially and their recommended center not at all, and
nothing in the interface says so.

**What would help:** (1) say plainly which inputs affect the ranking
and which affect only the numbers; (2) stop requiring inputs that reach
nothing, or state that they are recorded for other purposes;
(3) resolve the cPRA/blood-type asymmetry — which means deciding
whether ABO-specific center effects belong in the model, and that is a
measurement (#390), not a relabelling.
