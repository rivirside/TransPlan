---
sidebar_position: 3
---

# Testing

TransPlan has two test suites: Jest (JavaScript) and pytest (Python).

## JavaScript Tests (Jest)

**91 tests** covering the Phase 1 scoring algorithm and data utilities.

```bash
npm test
```

### Test Files

| File | Tests | Coverage |
|------|-------|---------|
| `tests/algorithm.test.js` | 68 | All 8 scoring categories, organ-specific inputs, edge cases |
| `tests/utils.test.js` | 23 | `deepMerge`, `writeDataFile`, `mergeDataFile`, CITIES list |

### What's Tested

**algorithm.test.js** covers blood type compatibility scoring for all organs, cPRA sensitivity for kidney (0%, 50%, 80%+), MELD scoring for liver (low, medium, high urgency), LAS scoring for lung, BMI/height/weight scoring, all 8 category weight combinations, full integration (`calculateScores()` returns valid scores for all 22 cities), and edge cases including missing fields, extreme values, and null inputs.

**utils.test.js** verifies that `deepMerge()` correctly merges nested objects, `mergeDataFile()` preserves existing data when new data is empty, `mergeDataFile()` updates only keys present in new data, and the `CITIES` array contains exactly the 22 expected cities.

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

**120 tests** covering the Phase 2 backend.

```bash
cd backend
python -m pytest
```

### Test Organization

```
backend/tests/
  test_schemas.py           ← Pydantic schema validation (22 tests)
  test_distributions.py     ← Log-normal wait time model (22 tests)
  test_monte_carlo.py       ← Monte Carlo engine (25 tests)
  test_competing_risks.py   ← Mortality/delisting models (17 tests)
  test_data_loader.py       ← Data loading and fallbacks (34 tests)
```

### What's Tested

**test_schemas.py** validates PatientProfile for all organ/blood type combinations, checks cPRA, MELD, and LAS range constraints per organ, and confirms that invalid values raise ValidationError.

**test_distributions.py** verifies that LogNormal parameters are loaded for all (organ, blood_type) combinations, city factor multipliers are applied correctly, cPRA multiplier increases wait time at 80%+, MELD multiplier decreases wait time at high scores, and sampled wait times are always positive.

**test_monte_carlo.py** confirms that 1,000 iterations complete for all 22 cities, `p_transplant_*` probabilities are in [0, 1], cities are ranked by `p_transplant_24mo` descending, the 95% CI lower bound does not exceed the point estimate, and the full run completes in under 2 seconds.

**test_competing_risks.py** checks that competing risks sum to 1.0 within floating point tolerance (i.e., `p_transplant + p_mortality + p_delisting + p_still_waiting = 1.0`), all risk components are non-negative, and organ-specific rates differ appropriately (heart > kidney for mortality).

**test_data_loader.py** confirms that all 8 data files load successfully from `data/`, wait time distributions are parsed for all 6 organs, competing risks are parsed for all 6 organs, and a missing file falls back gracefully without crashing.

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

This is appropriate for probabilities in sparse regions (rare blood types, extreme clinical scores).

## Continuous Integration

GitHub Actions runs both test suites on every push to `main`:

```yaml
# .github/workflows/test.yml (if exists)
- run: npm test
- run: cd backend && python -m pytest
```

All 211 tests (91 JS + 120 Python) must pass before merging.

## What's Not Tested

End-to-end browser tests are handled via manual verification using preview tools. API integration tests are verified manually via curl or the browser. Data fetch scripts are tested implicitly by GitHub Actions dry runs. Leaflet map interactions are CDN-dependent and not unit-testable.
