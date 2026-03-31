# KPSAM / LSAM / TSAM — SRTR Simulated Allocation Models

## Overview
- **Organization:** SRTR (Scientific Registry of Transplant Recipients)
- **URL:** https://www.srtr.org/requesting-srtr-data/simulated-allocation-models/
- **Type:** Discrete-event simulation (organ-specific)
- **Coverage:** KPSAM (kidney/pancreas), LSAM (liver), TSAM (heart/lung)
- **Data:** Patient-level OPTN/UNOS historical data
- **Access:** Must request from SRTR (not publicly downloadable)

## What They Do
The SAMs are the official UNOS/SRTR tools for evaluating proposed allocation policy changes before implementation. They simulate:
- Candidate arrivals and health status updates (MELD progression, status changes)
- Donor arrivals with organ characteristics
- Allocation sequencing under current or proposed rules
- Offer acceptance/decline decisions based on historical patterns
- Transplant outcomes and waitlist outcomes

## Methodology
- **Simulation type:** Discrete-event, replay of historical populations
- **Competing risks:** Implicit (candidates can be transplanted, die, or be delisted)
- **Acceptance modeling:** Statistical models of historical offer acceptance behavior
- **Time horizon:** Typically 2-5 year simulation windows

## Strengths vs TransPlan
- Patient-level data (individual candidates and donors)
- Models organ acceptance decisions (TransPlan does not)
- Validated against real policy outcomes (e.g., 2021 kidney 250nm, CAS lung)
- Official tool used by OPTN policy committees
- Temporal dynamics (MELD/status progression over time)

## Limitations vs TransPlan
- Not publicly accessible (request-only)
- Not patient-facing (designed for policy analysts)
- Organ-specific (separate tool per organ)
- No equity auditing
- No spatial environmental data
- No multi-engine comparison
- No interactive web interface
- Trained on historical data — may not capture behavioral changes under new policies

## Benchmarking Potential
**Medium.** Difficult to access directly, but published KPSAM/LSAM/TSAM validation studies report predicted outcomes under various scenarios. Compare TransPlan's policy scenario predictions against published SAM results.

## Key References
- KPSAM 2015 User Guide. https://www.srtr.org/media/1295/kpsam-2015-user-guide.pdf
- TSAM 2015 User Guide. https://www.srtr.org/media/1201/tsam.pdf
- Lehr et al. "Validating thoracic simulated allocation model." JHLT 2020.
