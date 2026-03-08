---
sidebar_position: 1
---

# Scoring Methodology

TransPlan's Phase 1 engine computes a weighted composite score (0–100) for each of 22 US cities based on a patient's profile.

## Overview

Eight categories are scored independently and combined with fixed weights:

| # | Category | Weight | Primary Data Sources |
|---|----------|--------|---------------------|
| 1 | Medical Compatibility | 25% | Blood type, age, sex, BMI |
| 2 | Wait Time & Competition | 20% | SRTR Table B10 wait time distributions |
| 3 | Donor Availability | 18% | Donor registration rates, living donor programs |
| 4 | Hospital Quality | 15% | CMS volume data, SRTR center reports |
| 5 | Geographic & Logistical | 10% | BLS cost of living, EPA air quality, climate scores |
| 6 | Health Demographics | 7% | CDC disease prevalence (diabetes, obesity, hypertension) |
| 7 | Policy & Legal | 3% | State donation law tiers |
| 8 | Socioeconomic | 2% | Support system rubric |

**Total: 100%**

## Category Details

### 1. Medical Compatibility (25%)

Scores the biological match between patient profile and the donor pool at each city.

**Inputs:** `organ`, `blood_type`, `age`, `sex`, `weight_lbs`, `height_inches` (for BMI)

**Blood type compatibility** is the primary factor: O- scores highest universally while AB+ is most restricted, and a compatibility matrix is applied per organ. **Age** also affects scoring because pediatric and elderly patients face different wait time patterns relative to the expected donor age distribution. **Organ-specific clinical scores** (cPRA for kidney, MELD for liver, LAS for lung) directly influence the compatibility assessment. **BMI** is also considered because extreme values can disqualify candidates at some centers.

### 2. Wait Time & Competition (20%)

Estimates relative wait time advantage based on city-level SRTR data and patient urgency.

**Inputs:** `urgency` (1–4), organ-specific clinical scores

City wait time factors are derived from SRTR Table B10 log-normal distribution parameters. A urgency multiplier applies for Status 1A/1B patients (heart/liver), significantly reducing expected wait. Competition index reflects the ratio of candidates to donors at each center.

### 3. Donor Availability (18%)

Scores each city's supply of organs relative to demand.

The donor registration rate (state-level, from health demographics data) is the primary input, supplemented by living donor program strength from SRTR center volume data. Population size relative to transplant center capacity and OPO (Organ Procurement Organization) effectiveness scores round out this category.

### 4. Hospital Quality (15%)

Ranks centers by volume and quality indicators.

Annual transplant volume per organ type comes from SRTR biannual reports. Centers are also assessed by their UNOS/OPTN performance tier, specialization (pediatric programs, multi-organ capability), and CMS outcome ratings where available.

### 5. Geographic & Logistical (10%)

Practical livability during transplant workup and recovery.

The cost of living index (BLS, normalized dynamically) is combined with the air quality index (EPA AQS annual average), a climate recovery score (manually curated for temperature extremes, humidity, and UV), and distance from major transplant centers.

### 6. Health Demographics (7%)

Disease prevalence in the local population affects donor pool quality.

This category aggregates CDC SODA data on diabetes prevalence, obesity prevalence, CKD prevalence (relevant to kidney donor viability), hypertension prevalence, and smoking rates. Lower prevalence of disqualifying conditions yields a higher score.

### 7. Policy & Legal (3%)

State-level policies affecting donation rates and patient rights.

Inputs include first-person consent law strength (opt-in vs. opt-out framing), hospital donor conversion rates (HRSA OPO data), and any state-level mandated choice or presumed consent laws.

### 8. Socioeconomic (2%)

Support systems that improve transplant success rates.

This category scores transplant financial assistance programs, housing assistance near medical centers, community support networks, and transportation access to transplant centers.

*Note: This category deliberately avoids wealth-correlated metrics to prevent penalizing patients by income.*

## Score Combination

The final score is a weighted sum:

```
score = Σ(category_score_i × weight_i)  for i in [1..8]
```

Each category is internally normalized to [0, 100] before weighting. The composite score also falls in [0, 100].

## Adjusting Weights

Users can customize category weights via the methodology accordion in the app. Weights must sum to 100%. The algorithm automatically re-normalizes if they don't.

## Limitations

Scores are population-level estimates, not individual predictions. SRTR data is updated biannually, so current data may be 6–18 months old. Some data points are manually curated and may lag real-world changes. OPO boundary effects are not modeled (see `docs/limitations.md` L-009).

See [Phase 2: Monte Carlo Simulation](/theory/monte-carlo) for individual-level probabilistic estimates.
