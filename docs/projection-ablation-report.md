# Does projecting coordinates improve interpolation? (#266)

`SpatialSurface._fit_gp` fits directly on (lat, lon) degrees. Its
docstring argues an anisotropic kernel absorbs the distortion. That
holds for a CONSTANT anisotropy, but the degree-to-distance ratio
varies with latitude — 1 degree of longitude is 60.0 miles at 30N and
46.3 miles at 48N — so one pair of length-scales fits the average and
is wrong at both ends of the country.

Whether that matters is measured here rather than argued.

| layer | points | RMSE (degrees) | RMSE (Albers km) | change |
|---|---|---|---|---|
| air_quality | 2768 | 3.774 | 3.774 | -0.0% |
| cost_of_living | 387 | 4.162 | 4.157 | +0.1% |
| health_diabetesRate | 3144 | 1.542 | 1.538 | +0.3% |
| health_obesityRate | 3144 | 3.412 | 3.411 | +0.0% |
| health_hypertensionRate | 3144 | 2.450 | 2.431 | +0.8% |
| health_smokingRate | 3144 | 2.701 | 2.696 | +0.2% |

## Verdict

Projection is better on **0** layer(s), worse on **0**, and indistinguishable on **6**. Mean change in RMSE: **+0.2%** (positive favours projection).

No measurable difference. The anisotropic-kernel argument in
the docstring holds empirically at these layer densities, so
the projection would add a coordinate transform, a
dependency-shaped maintenance burden, and no accuracy. The
honest resolution of #266's projection clause is to record
this result and keep degrees — noting that it could change
for a much denser layer, where the latitude-varying
distortion has more points to bite on.

Method: 5 random 20% holdout splits per layer, identical kernel, length-scale bounds scaled per coordinate system so neither side is handicapped.
