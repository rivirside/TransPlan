# SRTR Program-Specific Reports

## Overview
- **Organization:** Scientific Registry of Transplant Recipients (SRTR), operated by Hennepin Healthcare Research Institute under HRSA contract
- **URL:** https://www.srtr.org
- **Type:** Statistical reports + public website
- **Coverage:** All 6 solid organs, 248+ centers nationwide
- **Data:** Patient-level OPTN/UNOS registry data (not publicly available at individual level)
- **Last updated:** Semiannual (every 6 months)

## What It Does
SRTR PSRs provide center-level performance metrics including:
- Waitlist mortality rates (Cox regression, risk-adjusted)
- Transplant rates
- Organ offer acceptance rates
- 1-month, 1-year, 3-year post-transplant graft and patient survival
- Expected vs. observed outcomes (O/E ratios)

## Methodology
- **Competing risks:** Fine-Gray subdistribution hazard models
- **Risk adjustment:** Cox proportional hazards with center-specific random effects
- **Data:** Actual patient-level records from OPTN database
- **Validation:** Validated against real outcomes; used for CMS certification decisions

## Strengths vs TransPlan
- Real patient-level data (TransPlan uses aggregate public data)
- Clinically validated and regulatory-approved
- Comprehensive outcome tracking (pre and post-transplant)
- Semiannual updates with latest OPTN data

## Limitations vs TransPlan
- Descriptive (reports outcomes, doesn't simulate alternatives)
- No policy scenario modeling
- No spatial environmental data
- No equity auditing across demographics
- No patient-specific probability estimation
- No interactive simulation tools

## Benchmarking Potential
**High.** Compare TransPlan's predicted center rankings against SRTR-reported waiting times and transplant rates. If TransPlan's rankings correlate with SRTR O/E ratios, it validates the parametric model against real outcomes.

## Key References
- SRTR Technical Methods. https://www.srtr.org/about-the-data/technical-methods-for-the-program-specific-reports/
- Lehr et al. "SRTR Program-Specific Reports on Outcomes: A Guide for the New Reader." AJT 2019.
