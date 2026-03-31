# TransplantCenterSearch.org — Patient Decision Aid

## Overview
- **Organization:** Hennepin Healthcare Research Institute (HHRI) & University of Minnesota
- **URL:** https://transplantcentersearch.org
- **Funding:** Agency for Healthcare Research and Quality (AHRQ)
- **Type:** Patient-facing decision aid (web)
- **Coverage:** Kidney, Liver (heart and lung planned)
- **Data:** SRTR registry data
- **Published:** McKinney et al. Clinical Transplantation 2024

## What It Does
A personalized web tool that helps transplant candidates search for centers matching their individual criteria:
- Patient enters donor type and medical profile
- Tool shows how many recipients at each US center have similar characteristics
- Allows comparison across centers based on patient-relevant factors

## Methodology
- **Approach:** Data lookup (not simulation)
- **Matching:** Filters SRTR outcome data by patient characteristics
- **No modeling:** Descriptive statistics, not predictive
- **Validation:** Evaluated via randomized controlled trial (RCT)

## Strengths vs TransPlan
- **Clinically validated via RCT** (TransPlan has no clinical validation)
- Human-centered design (developed with patient input)
- Uses real SRTR outcome data (not model-derived)
- AHRQ-funded (government credibility)
- Simple, accessible interface for patients

## Limitations vs TransPlan
- No simulation or modeling (descriptive only)
- No competing risks analysis
- No policy scenario comparison
- No spatial or environmental data
- No equity auditing
- No sensitivity analysis
- Limited to kidney and liver (heart/lung pending)
- No probability estimation (shows outcomes, not personalized predictions)

## Benchmarking Potential
**Medium.** For kidney and liver, compare TransPlan's center rankings against TransplantCenterSearch recommendations for equivalent patient profiles. Tests whether a modeling approach and a data-lookup approach converge on similar center recommendations.

## Key References
- McKinney WT, et al. "Randomized Controlled Trial to Evaluate a New Tool to Support Patient Decision-making on Transplant Centers." Clin Transplant 2024.
- Design paper: Peipert JD, et al. "Design of a patient-centered decision support tool when selecting an organ transplant center." PLOS ONE 2021.
