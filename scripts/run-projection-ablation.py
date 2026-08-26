#!/usr/bin/env python3
"""Does projecting coordinates improve spatial interpolation? (#266)

`SpatialSurface._fit_gp` fits a Gaussian process directly on (lat, lon)
DEGREES, and its docstring argues the resulting distortion is harmless:

    "Uses an anisotropic RBF kernel (independent length-scales per axis), so
     the distortion from treating lat/lon degrees as Cartesian is absorbed by
     the learned per-axis scales rather than biasing distances."

That argument is half right, and the half it misses is the point. A per-axis
length-scale can absorb a CONSTANT anisotropy, but the degree-to-distance
ratio is not constant — it varies with latitude:

    1 degree of longitude  =  60.0 miles at 30N (Houston)
                              46.3 miles at 48N (Seattle)

So a single pair of length-scales fits the average and is wrong at both ends
of the country, in opposite directions. #266 asked for an Albers Equal-Area
projection for exactly this reason.

Whether it MATTERS is an empirical question, so this measures it instead of
assuming either way: hold out a random fifth of each layer's points, fit on
the rest in both coordinate systems, and compare prediction error on the
held-out points. Repeated over several splits because a single split of a
few hundred points is noisy.

If projecting wins, the surface should project. If it does not, the
docstring's claim earns its keep and #266's projection request can be closed
with evidence rather than opinion.

Outputs: docs/projection-ablation-report.md,
         docs-site/static/data/projection-ablation.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from artifact_meta import stamped_meta  # noqa: E402

from services.data_loader import load_all  # noqa: E402
from services.spatial_interpolation import (_extract_layer_points,  # noqa: E402
                                            available_layers)

N_SPLITS = 5
HOLDOUT_FRAC = 0.2
MAX_FIT = 800          # mirrors SpatialSurface._fit_gp
SEED = 20260826

# Albers Equal-Area Conic, USGS parameters for the contiguous US (EPSG:5070).
ALBERS_LAT_1, ALBERS_LAT_2 = 29.5, 45.5      # standard parallels
ALBERS_LAT_0, ALBERS_LON_0 = 23.0, -96.0     # origin
EARTH_RADIUS_KM = 6371.0


def albers(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Spherical Albers Equal-Area Conic -> (x, y) in kilometres.

    Spherical rather than ellipsoidal: the difference is well under a
    kilometre over CONUS, far below the scale anything here resolves, and it
    avoids adding pyproj as a dependency for a projection that is four lines
    of trigonometry.
    """
    lat_r = np.radians(lat)
    lon_r = np.radians(lon)
    p1, p2 = math.radians(ALBERS_LAT_1), math.radians(ALBERS_LAT_2)
    lat0, lon0 = math.radians(ALBERS_LAT_0), math.radians(ALBERS_LON_0)

    n = 0.5 * (math.sin(p1) + math.sin(p2))
    C = math.cos(p1) ** 2 + 2 * n * math.sin(p1)
    rho0 = EARTH_RADIUS_KM * math.sqrt(C - 2 * n * math.sin(lat0)) / n

    rho = EARTH_RADIUS_KM * np.sqrt(C - 2 * n * np.sin(lat_r)) / n
    theta = n * (lon_r - lon0)
    return np.column_stack([rho * np.sin(theta), rho0 - rho * np.cos(theta)])


def fit_predict(train_xy, train_v, test_xy):
    """Fit the same GP the surface uses, return predictions on test_xy."""
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel

    # Length-scale bounds must suit the units: degrees are O(1-50), Albers
    # kilometres are O(10-5000). Using the degree bounds on kilometres would
    # peg the kernel at its ceiling and lose the comparison on a technicality
    # rather than on the geometry.
    span = float(np.max(np.ptp(train_xy, axis=0)))
    lo, hi = span * 1e-3, span * 10.0
    kernel = (
        ConstantKernel(1.0, (1e-2, 1e3))
        * RBF(length_scale=[span / 10, span / 10], length_scale_bounds=(lo, hi))
        + WhiteKernel(noise_level=1.0, noise_level_bounds=(1e-3, 1e3))
    )
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True)
    gp.fit(train_xy, train_v)
    return gp.predict(test_xy)


def evaluate(layer: str) -> dict | None:
    pts = _extract_layer_points(layer)
    if pts is None:
        return None
    coords, values = pts
    coords = np.asarray(coords, dtype=float)
    values = np.asarray(values, dtype=float)
    if len(coords) < 60:
        return None

    rng = np.random.default_rng(SEED)
    deg_errors, prj_errors = [], []
    for _ in range(N_SPLITS):
        idx = rng.permutation(len(coords))
        n_test = max(10, int(len(coords) * HOLDOUT_FRAC))
        test_i, train_i = idx[:n_test], idx[n_test:]
        if len(train_i) > MAX_FIT:
            train_i = train_i[:MAX_FIT]

        tr_deg, te_deg = coords[train_i], coords[test_i]
        tr_prj = albers(tr_deg[:, 0], tr_deg[:, 1])
        te_prj = albers(te_deg[:, 0], te_deg[:, 1])
        truth = values[test_i]

        deg_pred = fit_predict(tr_deg, values[train_i], te_deg)
        prj_pred = fit_predict(tr_prj, values[train_i], te_prj)
        deg_errors.append(float(np.sqrt(np.mean((deg_pred - truth) ** 2))))
        prj_errors.append(float(np.sqrt(np.mean((prj_pred - truth) ** 2))))

    deg_rmse = float(np.mean(deg_errors))
    prj_rmse = float(np.mean(prj_errors))
    improvement = (deg_rmse - prj_rmse) / deg_rmse if deg_rmse else 0.0
    return {
        "layer": layer,
        "n_points": len(coords),
        "degrees_rmse": round(deg_rmse, 4),
        "albers_rmse": round(prj_rmse, 4),
        "relative_improvement": round(improvement, 4),
        "degrees_rmse_by_split": [round(e, 4) for e in deg_errors],
        "albers_rmse_by_split": [round(e, 4) for e in prj_errors],
    }


def main() -> int:
    load_all()
    layers = [l for l in available_layers()]
    results = []
    for layer in layers:
        try:
            res = evaluate(layer)
        except Exception as e:  # a layer that cannot be fit is not a failure
            print(f"  {layer}: skipped ({e})")
            continue
        if not res:
            print(f"  {layer}: too few points")
            continue
        results.append(res)
        verdict = ("projection better" if res["relative_improvement"] > 0.01
                   else "degrees better" if res["relative_improvement"] < -0.01
                   else "no difference")
        print(f"  {layer:26s} n={res['n_points']:5d} "
              f"deg={res['degrees_rmse']:8.3f} albers={res['albers_rmse']:8.3f} "
              f"{res['relative_improvement']:+.1%}  {verdict}")

    if not results:
        print("ERROR: no layer could be evaluated", file=sys.stderr)
        return 1

    mean_improvement = float(np.mean([r["relative_improvement"] for r in results]))
    wins = sum(1 for r in results if r["relative_improvement"] > 0.01)
    losses = sum(1 for r in results if r["relative_improvement"] < -0.01)

    doc = {
        "layers": results,
        "summary": {
            "mean_relative_improvement": round(mean_improvement, 4),
            "layers_projection_better": wins,
            "layers_degrees_better": losses,
            "layers_no_difference": len(results) - wins - losses,
            "n_splits": N_SPLITS,
            "holdout_fraction": HOLDOUT_FRAC,
        },
        "_meta": stamped_meta(
            script="scripts/run-projection-ablation.py",
            method=f"{N_SPLITS} random {int(HOLDOUT_FRAC*100)}% holdout splits "
                   f"per layer; the same GP kernel is fit on raw (lat, lon) "
                   f"degrees and on Albers Equal-Area kilometres, with "
                   f"length-scale bounds scaled to each coordinate system's "
                   f"units so neither is handicapped.",
            question="#266 asked for an Albers projection so GP distances are "
                     "not degree-distorted. This measures whether it changes "
                     "predictive accuracy.",
        ),
    }

    lines = [
        "# Does projecting coordinates improve interpolation? (#266)", "",
        "`SpatialSurface._fit_gp` fits directly on (lat, lon) degrees. Its",
        "docstring argues an anisotropic kernel absorbs the distortion. That",
        "holds for a CONSTANT anisotropy, but the degree-to-distance ratio",
        "varies with latitude — 1 degree of longitude is 60.0 miles at 30N and",
        "46.3 miles at 48N — so one pair of length-scales fits the average and",
        "is wrong at both ends of the country.", "",
        "Whether that matters is measured here rather than argued.", "",
        "| layer | points | RMSE (degrees) | RMSE (Albers km) | change |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['layer']} | {r['n_points']} | {r['degrees_rmse']:.3f} | "
                     f"{r['albers_rmse']:.3f} | {r['relative_improvement']:+.1%} |")
    lines += [
        "", "## Verdict", "",
        f"Projection is better on **{wins}** layer(s), worse on **{losses}**, "
        f"and indistinguishable on **{len(results) - wins - losses}**. Mean "
        f"change in RMSE: **{mean_improvement:+.1%}** (positive favours "
        f"projection).", "",
    ]
    if mean_improvement > 0.02:
        lines += ["The projection earns its place: fit the GP on projected",
                  "coordinates.", ""]
    elif mean_improvement < -0.02:
        lines += ["Projecting makes predictions WORSE here. The anisotropic",
                  "kernel is doing its job, and #266's projection request",
                  "should be closed as measured-and-rejected rather than",
                  "implemented.", ""]
    else:
        lines += ["No measurable difference. The anisotropic-kernel argument in",
                  "the docstring holds empirically at these layer densities, so",
                  "the projection would add a coordinate transform, a",
                  "dependency-shaped maintenance burden, and no accuracy. The",
                  "honest resolution of #266's projection clause is to record",
                  "this result and keep degrees — noting that it could change",
                  "for a much denser layer, where the latitude-varying",
                  "distortion has more points to bite on.", ""]
    lines += [f"Method: {N_SPLITS} random {int(HOLDOUT_FRAC * 100)}% holdout "
              f"splits per layer, identical kernel, length-scale bounds scaled "
              f"per coordinate system so neither side is handicapped.", ""]

    (REPO / "docs" / "projection-ablation-report.md").write_text("\n".join(lines))
    (REPO / "docs-site" / "static" / "data" / "projection-ablation.json").write_text(
        json.dumps(doc, indent=1) + "\n")
    print(f"\nmean improvement {mean_improvement:+.1%} "
          f"({wins} better / {losses} worse / "
          f"{len(results) - wins - losses} same)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
