---
sidebar_position: 3
---

# Testing

TransPlan has two test suites: Jest for JavaScript and pytest for Python.

## JavaScript Tests (Jest)

The JavaScript suite contains **123 tests** (112 passing, 11 skipped) covering the scoring algorithm, COD multiplier, and data utilities.

```bash
npm test
```

### Test Files

`tests/algorithm.test.js` contains 75 tests covering all 8 scoring categories, organ-specific inputs, the COD multiplier, and edge cases. `tests/utils.test.js` contains 23 tests covering `deepMerge`, `writeDataFile`, `mergeDataFile`, and the CITIES list.

### What's Tested

The algorithm tests verify blood type compatibility scoring for all organs, cPRA sensitivity for kidney (0%, 50%, 80%+), MELD scoring for liver (low, medium, high urgency), LAS scoring for lung, BMI/height/weight scoring, all 8 category weight combinations, full integration through `calculateScores()` returning valid scores for all 22 cities, and edge cases including missing fields, extreme values, and null inputs.

The utils tests verify that `deepMerge()` correctly merges nested objects, that `mergeDataFile()` preserves existing data when new data is empty and updates only keys present in new data, and that the `CITIES` array contains exactly the 22 expected cities.

### Running Specific Tests

```bash
# Run a single test file
npx jest tests/algorithm.test.js

# Run tests matching a pattern
npx jest --testNamePattern="blood type"

# Watch mode (re-runs on file change)
npx jest --watch
```

## Python Tests (pytest)

The Python suite contains **800+ tests** covering all three inference engines, sensitivity analysis, equity analysis, spatial interpolation, policy scenarios, and data validation.

```bash
cd backend
python -m pytest
```

### Test Organization

```
backend/tests/
  test_schemas.py               <- Pydantic schema validation
  test_distributions.py         <- Log-normal wait time model
  test_monte_carlo.py           <- Monte Carlo engine
  test_competing_risks.py       <- Mortality/delisting models
  test_copula.py                <- Clayton copula dependence
  test_data_loader.py           <- Data loading and fallbacks
  test_scoring.py               <- 8-category scoring algorithm
  test_bayesian_network.py      <- BBN inference engine
  test_bbn_cross_validation.py  <- BBN vs MC validation
  test_mcmc_inference.py        <- MCMC hierarchical model
  test_sensitivity.py           <- Sensitivity analysis
  test_equity.py                <- Equity analysis (48-profile matrix)
  test_policy_scenarios.py      <- UNOS policy simulations
  test_spatial_interpolation.py <- RBF/IDW interpolation
  test_allocation_geography.py  <- UNOS allocation circles
  test_cross_validation.py      <- Cross-engine comparison
  test_brier_score.py           <- Brier score calibration
  test_acceptance.py            <- Organ acceptance modeling
  test_score_drift.py           <- MELD/LAS score progression
  test_trend_projection.py      <- Historical trend projection
  + 14 more test files
```

### What's Tested

The schema tests validate PatientProfile for all organ and blood type combinations, check cPRA, MELD, and LAS range constraints per organ, and confirm that invalid values raise ValidationError.

The distribution tests verify that LogNormal parameters are loaded for all organ and blood type combinations, that city factor multipliers are applied correctly, that cPRA multipliers increase wait time at 80%+, that MELD multipliers decrease wait time at high scores, and that sampled wait times are always positive.

The Monte Carlo tests confirm that 1,000 iterations complete for all 22 cities, that `p_transplant_*` probabilities fall within [0, 1], that cities are ranked by `p_transplant_24mo` descending, that the 95% CI lower bound does not exceed the point estimate, and that the full run completes in under 2 seconds.

The competing risks tests check that all risk components sum to 1.0 within floating point tolerance (meaning `p_transplant + p_mortality + p_delisting + p_still_waiting = 1.0`), that all components are non-negative, and that organ-specific rates differ appropriately (for example, heart has higher mortality rates than kidney).

The data loader tests confirm that all 10 data files load successfully from `data/`, that wait time distributions and competing risks are parsed for all 6 organs, and that a missing file falls back gracefully without crashing.

### Running Specific Tests

```bash
# Run a single test file
python -m pytest tests/test_monte_carlo.py -v

# Run tests matching a pattern
python -m pytest -k "kidney" -v

# Show test output (stdout)
python -m pytest -s

# Stop on first failure
python -m pytest -x
```

### Stability Tests

Some Monte Carlo tests use relaxed tolerances due to inherent stochasticity:

```python
# 15% relative OR 0.03 absolute tolerance for probability comparisons
assert abs(p - expected) <= max(0.15 * expected, 0.03)
```

This is appropriate for probabilities in sparse regions such as rare blood types or extreme clinical scores.

## Continuous Integration

GitHub Actions runs both test suites on every push to `main`:

```yaml
# .github/workflows/test.yml (if exists)
- run: npm test
- run: cd backend && python -m pytest
```

All tests (123 JS + 800+ Python) must pass before merging.

## What's Not Tested

End-to-end browser tests are handled via manual verification using preview tools. API integration tests are verified manually via curl or the browser. Data fetch scripts are tested implicitly by GitHub Actions dry runs. Leaflet map interactions are CDN-dependent and not unit-testable.
