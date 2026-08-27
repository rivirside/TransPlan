# Should medical compatibility be center-specific? (#390 / #394)

L-084 and L-085 record a structural oddity: `medicalCompatibility` carries the
largest weight in the model (0.25) and is identical at every center, so blood
type produces a **literally identical** center ranking while cPRA — the other
immunological constraint on donor access — reorders at ρ 0.760.

The obvious fix is to make the sub-score center-specific using each program's
waitlist ABO mix. This report is the measurement that decides whether to.

**Answer: no. The premise does not hold in the data, and the term makes the
model measurably worse.**

## What was built

A per-center ABO term, behind a calibration gate:

```
relative_abo_competition(center, abo) = center_share(abo) / national_share(abo)
```

Sourced from SRTR Tables B8-B9 `TPC_B*_NC` (559 center-organ rows), which are
**candidates, not recipients** — `TPC_ALL_NC` sums to 105,857 for kidney
against ~28,000 annual transplants — so the input is a characteristic of the
competition a candidate faces, not an outcome. That check mattered: using
recipient counts would have been circular.

It worked mechanically. Blood type began reordering centers at ρ 0.878
(kidney), 0.858 (liver), 0.902 (heart) — comparable to cPRA's 0.760, which is
exactly what L-085 asks for.

## The gate that could see it

The project's per-center calibration correlates **p12** against observed SRTR
transplant rates. It reported no change at all — and that was a false
reassurance: p12 comes from the Monte Carlo path, and this term lives in the
scoring path. Forcing the ABO factor to its bound moved p12 by **0.000000**.
The metric is structurally blind to the change.

The analogous metric that *is* sensitive is Spearman of the **composite score**
against observed transplant rates:

| organ | O+ | A+ | B+ | AB+ |
|---|---|---|---|---|
| kidney | −0.0296 | −0.0157 | −0.0039 | −0.0444 |
| liver | +0.0002 | −0.0058 | −0.0282 | −0.0469 |
| heart | −0.0147 | +0.0031 | −0.0181 | −0.0299 |

Mean **−0.0195**, improved in **2 of 12** combinations.

## Why: the premise itself is unsupported

The term assumes a center with more same-type candidates offers worse access to
that type. Testing that directly — Spearman between a center's share of a blood
group and its observed transplant rate:

| organ | O | A | B | AB |
|---|---|---|---|---|
| kidney | +0.070 | +0.062 | **−0.143** (p=0.035) | −0.045 |
| liver | +0.023 | −0.013 | +0.038 | +0.006 |
| heart | +0.164 (p=0.063) | −0.136 | −0.052 | −0.064 |

One of twelve reaches p<0.05 in the assumed direction, which is what twelve
comparisons produce by chance. Several run the *opposite* way.

A coherent explanation: allocation is ABO-matched on both sides. A program
serving a population richer in type B also receives more type B donors from its
OPO, so competition and supply move together and largely cancel. If that is
right, waitlist ABO mix is not a proxy for access at all, and no amount of
re-scaling the term would fix it.

## Consequence for L-084 / L-085

The disclosures stand and the model is unchanged. What changes is the outlook:
the cPRA/blood-type asymmetry is **not** obviously fixable with the data
available, so it should be documented as a known structural property rather
than treated as pending work.

What would actually be needed is a center-by-ABO **outcome** measure — observed
transplant rate per center *per blood group* — which SRTR does not publish.
Tables B8-B9 give the mix, not the rate.

## Not shipped

The term, the parser extension and the derived data file were all reverted.
Keeping a data file and generator for a rejected hypothesis is speculative
generality; the numbers above are the durable result. The implementation is
recoverable from the PR that produced this report.

Consistent with #266, #274, #213, #301 and #236: measured, found unsupported,
not built — and in this case, like #274 and #376, the proposed fix would have
made the model worse.
