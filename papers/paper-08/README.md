# Paper 08: Spatial Interpolation for Healthcare Resource Evaluation — Application to Transplant Center Assessment

## Status: 📝 Not Started

## Summary

A methods/applied paper describing the use of RBF (Radial Basis Function, thin-plate spline) and IDW (Inverse Distance Weighting) spatial interpolation to create continuous health environment surfaces from point-source data. Applied to transplant center evaluation using 24 data layers: EPA air quality monitors (~4000 points), CDC PLACES county health metrics (2,956 counties), BLS cost-of-living indices, center-level outcomes, and more. Validates interpolated surfaces against held-out test points.

## Paper Type
**Methods/applied paper** — dual contribution: (1) the interpolation methodology adapted for health resource evaluation, and (2) the 24-layer spatial assessment applied to transplant centers.

## Target Venues (ranked)

| Venue | IF | Fit | Page Limit | Acceptance Rate | Notes |
|-------|-----|-----|------------|-----------------|-------|
| **Int J Health Geographics** | 3.0 | ⭐⭐⭐ | No limit | ~35% | Perfect venue: health + spatial methods. |
| **Spatial & Spatio-temporal Epidemiology** | 3.4 | ⭐⭐⭐ | 10 pages | ~30% | Spatial health methods. |
| **J Geographic Information Science** | 4.3 | ⭐⭐ | 12 pages | ~20% | GIS methods angle. Less health focus. |
| **Health & Place** | 4.8 | ⭐⭐ | 8000 words | ~15% | Health geography. Strong application focus. |
| **GeoHealth** | 4.3 | ⭐⭐ | No limit | ~30% | AGU journal. Open access. |

**Recommended:** Int J Health Geographics (health + spatial methods is the exact scope).

## Likelihood of Acceptance
**Moderate (50%)** — Spatial interpolation is well-established in GIS, but the application to multi-layer transplant center evaluation is novel. The 24-layer stack with heterogeneous data sources (monitors, counties, centers) adds methodological interest.

## Effort Required
🟡 **Medium** — Interpolation code exists. Need formal validation study (held-out test points), comparison of RBF vs IDW accuracy, and visualization of surfaces.

### What exists already
- `backend/services/spatial_interpolation.py` (290 lines): RBF + IDW with auto-selection of dense data
- 24 layer definitions with different data granularities
- Surface caching for performance
- Dense data: EPA AQS monitors, CDC PLACES counties, center-level outcomes
- `/spatial-grid` endpoint: returns interpolated grid at configurable resolution
- `/interpolated-value` endpoint: point query at any lat/lon
- Explorer page with interactive map visualization

### What needs to be done
- [ ] Design hold-out validation (e.g., 80/20 split on monitor data)
- [ ] Compare RBF vs IDW accuracy (RMSE, MAE) per layer type
- [ ] Generate surface maps for key layers (air quality, health demographics, cost-of-living)
- [ ] Cross-validate interpolation accuracy by data density
- [ ] Write manuscript (~4500 words)

## Suggested Structure

1. **Introduction** (500 words)
   - Healthcare decisions have geographic dimensions (access, environment, cost)
   - Point-source data (monitors, centers) needs interpolation for continuous coverage
   - Gap: systematic multi-layer spatial interpolation for transplant evaluation

2. **Methods** (1200 words)
   - 2.1 Data sources and spatial resolutions (table: source, N points, coverage)
   - 2.2 RBF interpolation: thin-plate spline kernel, smoothing parameter selection
   - 2.3 IDW interpolation: power parameter (p=2), exact recovery
   - 2.4 Dense-data preference hierarchy (monitor > county > city fallback)
   - 2.5 Validation design: 5-fold spatial cross-validation

3. **Results** (1200 words)
   - 3.1 Interpolation accuracy by layer and method (RMSE table)
   - 3.2 RBF vs IDW: when does each win? (data density matters)
   - 3.3 Example surfaces: air quality, health demographics, cost-of-living
   - 3.4 Impact on center scoring: how much does spatial layer affect rankings?

4. **Application: Transplant Center Scoring** (800 words)
   - 4.1 Integration into 8-category scoring framework
   - 4.2 Geographic and health demographic categories (10% + 7% of total weight)
   - 4.3 Centers that benefit/suffer most from spatial data inclusion

5. **Discussion** (800 words)
   - Multi-resolution data fusion: monitor-level + county-level + city-level
   - Generalizability to other healthcare geography problems
   - Limitations: interpolation ≠ ground truth, edge effects, temporal lag

6. **Conclusion** (300 words)

## Key Figures
1. Map: EPA air quality interpolated surface (continental US)
2. Map: CDC PLACES diabetes prevalence interpolated surface
3. Validation: predicted vs observed scatter plots (RBF and IDW)
4. RMSE comparison bar chart (RBF vs IDW per layer category)
5. Center scoring impact: spatial layers ON vs OFF ranking changes

## Key Tables
1. Data source inventory (source, N points, spatial resolution, update frequency)
2. 24-layer definitions (name, source, method, data density)
3. Cross-validation RMSE by layer and method
4. Top-10 centers most affected by spatial data inclusion
