# Population coverage of transplant centers (#113)

Share of the US population living within a given straight-line
distance of a center performing each organ.

| organ | centers | within 50mi | 100mi | 250mi | 288mi (250nm) | pop-weighted median | population beyond 250mi |
|---|---|---|---|---|---|---|---|
| kidney | 233 | 73.3% | 92.5% | 99.2% | 99.5% | 25 mi | 2,575,498 |
| liver | 148 | 63.6% | 84.8% | 97.6% | 98.4% | 30 mi | 8,116,536 |
| heart | 149 | 65.9% | 85.2% | 97.5% | 98.3% | 29 mi | 8,578,607 |
| lung | 74 | 54.9% | 74.1% | 96.2% | 97.6% | 43 mi | 12,953,919 |
| pancreas | 99 | 57.4% | 78.1% | 93.0% | 94.2% | 36 mi | 23,791,311 |
| intestine | 21 | 28.3% | 42.8% | 67.7% | 70.7% | 131 mi | 109,734,634 |

## Reading these numbers

**Distance here is great-circle, not drive time.** That is not a
detail. A county 60 straight-line miles from a center across a
mountain range is a three-hour drive; a county the same distance
along an interstate is under an hour. So every share above is an
OPTIMISTIC bound on real access, and it is optimistic *unevenly* —
rural and mountainous populations are flattered most, which is
exactly the population an access analysis most needs to get right.

Replacing the distance function with a road-network matrix (#323)
turns every statistic here into a drive-time statistic without
changing anything else in this script.

**County centroids are a second simplification.** Everyone in a
county is placed at its centroid, which flatters large rural
counties whose population usually clusters in one town.

**Alaska and Hawaii break the framing entirely.** Every one of the
ten farthest counties is in Alaska, whose nearest program is in
Seattle. For those populations the straight-line figure is not an
optimistic bound on a drive — there is no drive. Access is a
flight, and the relevant burden is cost and scheduling rather than
road distance. A drive-time matrix will not fix this; it will
report no route at all. These counties need to be described
separately rather than folded into a national distance figure.

**Organ coverage differs because program counts differ.** Kidney is
performed at far more centers than intestine, so the intestine
figures describe genuine geographic scarcity rather than a
modelling artifact.

For kidney — the most widely performed organ — 99.2% of the population lives within 250 straight-line miles of a program, leaving 2,575,498 people beyond it even on this optimistic measure.
