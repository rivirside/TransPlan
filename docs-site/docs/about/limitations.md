---
sidebar_position: 2
---

# Limitations

TransPlan tracks 48 known limitations in `docs/limitations.md`. This page summarizes the most important ones.

## Model Limitations

### L-009: OPO Boundaries Not Modeled

TransPlan scores cities as geographic locations, but organ allocation follows OPO district boundaries that don't align with city limits. A patient in Phoenix gets access to the entire AZOB (Arizona, New Mexico) OPO's donor pool, not just Phoenix metro donors. This can over- or under-estimate access depending on the city.

**Status**: Deferred (requires GIS data and significant modeling complexity)

### L-017: SRTR Outcomes Not Used for Survival Models

Phase 2 uses wait time distributions (Table B10) and removal reasons (Table B7), but doesn't yet incorporate post-transplant survival outcomes (Tables B20–B25). These would enable modeling long-term graft survival, not just time to transplant.

**Status**: Deferred (Phase 3 feature)

### L-039: False Positive High-Score Cities

Cities with high deterministic scores (Phase 1) don't always have high Monte Carlo probabilities (Phase 2). This is by design. Phase 1 scores include non-time factors (hospital quality, socioeconomic support) that don't directly affect wait time.

**Status**: Won't fix. The two scores measure different things, and the dual-tab UI makes this distinction clear.

## Data Limitations

### L-045: NHTSA FARS API Retired

The NHTSA FARS (traffic fatality) API has been retired. Traffic fatality data is frozen at the last fetched values from 2024. A CSV bulk download alternative exists at NHTSA but is not yet automated.

**Status**: Mitigated (seed data preserved, FIXME comment in fetch-traffic.js)

### L-046: CMS Hospital Quality API Instability

The CMS Provider Data API uses a multi-strategy query (SQL/filter/legacy format). The filter strategy is currently working but the API URL has changed multiple times. May break without warning.

**Status**: Open, monitored weekly

### L-047: CDN Fallback Incomplete

The CDN fallback for Chart.js and Leaflet shows gray containers rather than fully functional alternatives. Charts don't render without Chart.js; the map doesn't render without Leaflet.

**Status**: Open. Known limitation, not critical for offline use since CDN is generally reliable.

### L-048: COL Range Normalization

Cost-of-living scores are normalized against the dynamic min/max of the loaded data. If one city has an extreme outlier value, it compresses all other cities into a narrow score range. A percentile-based normalization would be more robust.

**Status**: Open, low priority

## Clinical Limitations

### Data Age

SRTR publishes Program-Specific Reports biannually. The current data may be 6–18 months old. Allocation policy changes (e.g., the 2023 kidney allocation policy updates) may not yet be reflected in the model.

### Static Clinical Profile

TransPlan models your clinical profile as static. In reality, MELD scores change over time (and can rise rapidly in liver failure), cPRA can change after desensitization therapy, and patients' clinical status may improve or worsen, affecting eligibility.

### No Center-Specific Practice

Centers within the same city vary significantly in their acceptance criteria, risk tolerance, and specializations. TransPlan averages across all centers mapped to a city. A specialized center for highly sensitized kidney patients may be in your city but not reflected in the average.

### No Multi-listing Modeling

Being listed at multiple centers (multi-listing) can significantly improve transplant probability. TransPlan models each city independently. It does not account for the combined probability of being listed at multiple centers simultaneously.

## Ethical Notes

TransPlan is explicitly designed to avoid recommending specific transplant centers (only cities), providing advice on whether to pursue multi-listing (which requires clinical judgment), modeling any strategy to game the allocation system, and using socioeconomic proxies that penalize lower-income patients.

The socioeconomic category uses a transplant-specific support rubric rather than wealth-correlated metrics (see [Scoring Methodology](/theory/scoring-methodology)).

## Full Limitation Tracker

The complete list of 48 tracked issues (L-001 through L-048) is in `docs/limitations.md` in the repository. Statuses:

| Status | Count |
|--------|-------|
| Fixed | 36 |
| Open | 4 |
| Deferred | 3 |
| Won't Fix | 2 |
| **Total** | **48** |
