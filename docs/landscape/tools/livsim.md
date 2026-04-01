# LivSim — Open-Source Liver Allocation Simulation

## Overview
- **Organization:** Northwestern University (Kilambi, Bui, Mehrotra)
- **URL:** https://github.com/LivSim2017/LivSim-Codes
- **Type:** Discrete-event simulation
- **Coverage:** Liver only (~140 US liver transplant centers)
- **Data:** SRTR/OPTN historical data
- **Published:** Kilambi et al. Transplantation 2018
- **License:** Open source (GitHub)

## What It Does
LivSim is an open-source Python (3.4.2) discrete-event simulation of liver allocation in the US OPTN. Designed as a community alternative to LSAM. Simulates:
- New patient listings and re-listings
- MELD score progression over time
- Status 1 and HCC exception handling
- Organ procurement events
- Allocation sequencing under current or modified rules
- Acceptance/decline decisions

## Methodology
- **Simulation type:** Discrete-event, historical replay
- **Competing risks:** Implicit (candidates removed by transplant, death, delisting)
- **MELD progression:** Dynamic (scores evolve over simulated time)
- **Match run:** Implements OPTN liver allocation algorithm

## Strengths vs TransPlan
- Discrete-event simulation (models individual events over time)
- MELD progression modeling (dynamic, not static)
- Organ acceptance decision modeling
- Closer to real OPTN allocation mechanics

## Limitations vs TransPlan
- Liver only (single organ)
- Python 3.4.2 — significantly outdated, may not run on modern Python
- Not updated since 2018
- No web interface
- No equity auditing
- No spatial data
- No multi-engine comparison
- No patient-facing tools
- No competing risks decomposition (transplant/mortality/delisting as separate outputs)

**Note (March 2026):** TransPlan now models MELD/LAS score progression via piecewise-linear drift with interval-specific clinical multipliers, narrowing the gap with LivSim's dynamic MELD modeling. However, LivSim's discrete-event approach is more mechanistically detailed, tracking individual candidate MELD trajectories and modeling score-dependent allocation sequencing, whereas TransPlan's piecewise approximation applies population-level drift rates to the competing risks framework.

## Benchmarking Potential
**Medium.** Run both tools for liver with equivalent patient profiles and policy scenarios. Compare center rankings and predicted wait times. Note: LivSim may require Python 3.4 compatibility work.

## Key References
- Kilambi V, Bui K, Mehrotra S. "LivSim: An Open-Source Simulation Software Platform for Community Research and Development for Liver Allocation Policies." Transplantation 2018;102(2):e47-e48.
- GitHub: https://github.com/LivSim2017/LivSim-Codes
