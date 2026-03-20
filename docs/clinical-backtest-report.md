# Clinical Pattern Backtest Report

**Generated:** 2026-03-20 02:47 UTC  
**Iterations:** 1000 | **Seed:** 42 | **Total time:** 0.19s

## Summary: 6/6 passed

| # | Test | Result | Time |
|---|------|--------|------|
| 1 | O blood type waits longest, AB shortest | PASS | 0.1s |
| 2 | Kidney has the longest national median wait | PASS | 0.02s |
| 3 | Higher urgency reduces wait time | PASS | 0.04s |
| 4 | High cPRA increases kidney wait time | PASS | 0.02s |
| 5 | Waitlist mortality increases with age | PASS | 0.0s |
| 6 | 250nm circles help small centers | PASS | 0.02s |

## Detailed Results

### O blood type waits longest, AB shortest

**Status:** PASS  
**Time:** 0.1s

```json
{
  "kidney": {
    "p24_by_blood_type": {
      "O+": 0.2815,
      "O-": 0.2569,
      "A+": 0.3879,
      "A-": 0.3543,
      "B+": 0.3111,
      "B-": 0.2854,
      "AB+": 0.5427,
      "AB-": 0.4866
    },
    "AB+_higher_than_O+": true
  },
  "liver": {
    "p24_by_blood_type": {
      "O+": 0.7527,
      "O-": 0.7511,
      "A+": 0.8232,
      "A-": 0.8095,
      "B+": 0.7851,
      "B-": 0.7726,
      "AB+": 0.8617,
      "AB-": 0.8513
    },
    "AB+_higher_than_O+": true
  },
  "heart": {
    "p24_by_blood_type": {
      "O+": 0.9015,
      "O-": 0.8974,
      "A+": 0.9329,
      "A-": 0.9267,
      "B+": 0.9158,
      "B-": 0.9158,
      "AB+": 0.9444,
      "AB-": 0.9401
    },
    "AB+_higher_than_O+": true
  },
  "lung": {
    "p24_by_blood_type": {
      "O+": 0.9604,
      "O-": 0.9599,
      "A+": 0.9656,
      "A-": 0.9628,
      "B+": 0.9623,
      "B-": 0.9587,
      "AB+": 0.9726,
      "AB-": 0.9704
    },
    "AB+_higher_than_O+": true
  }
}
```

### Kidney has the longest national median wait

**Status:** PASS  
**Time:** 0.02s

```json
{
  "p24_by_organ": {
    "kidney": 0.2711,
    "liver": 0.7556,
    "heart": 0.9061,
    "lung": 0.9593,
    "pancreas": 0.2413,
    "intestine": 0.5493
  },
  "kidney_lowest_among_major": true
}
```

### Higher urgency reduces wait time

**Status:** PASS  
**Time:** 0.04s

```json
{
  "kidney": {
    "p24_by_urgency": {
      "1": 0.2845,
      "2": 0.2765,
      "3": 0.274,
      "4": 0.2705
    },
    "urgency1_higher_than_4": true
  },
  "liver": {
    "p24_by_urgency": {
      "1": 0.7696,
      "2": 0.7649,
      "3": 0.7449,
      "4": 0.7354
    },
    "urgency1_higher_than_4": true
  },
  "heart": {
    "p24_by_urgency": {
      "1": 0.9037,
      "2": 0.9017,
      "3": 0.8928,
      "4": 0.8804
    },
    "urgency1_higher_than_4": true
  }
}
```

### High cPRA increases kidney wait time

**Status:** PASS  
**Time:** 0.02s

```json
{
  "p24_by_cpra": {
    "0": 0.2728,
    "30": 0.1846,
    "60": 0.1826,
    "90": 0.092,
    "98": 0.0297
  },
  "cpra0_higher_than_98": true
}
```

### Waitlist mortality increases with age

**Status:** PASS  
**Time:** 0.0s

```json
{
  "kidney": {
    "young_25_median_months": 29.14,
    "old_65_median_months": 33.74,
    "older_waits_longer": true
  },
  "liver": {
    "young_25_median_months": 4.48,
    "old_65_median_months": 5.19,
    "older_waits_longer": true
  },
  "heart": {
    "young_25_median_months": 2.06,
    "old_65_median_months": 2.38,
    "older_waits_longer": true
  }
}
```

### 250nm circles help small centers

**Status:** PASS  
**Time:** 0.02s

```json
{
  "small_center_deltas": {
    "Madison": 0.087,
    "Omaha": 0.104,
    "Rochester": 0.054
  },
  "n_improved": 3
}
```

