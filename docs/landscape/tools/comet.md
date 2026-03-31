# COMET — Computational Open-source Model for Evaluating Transplantation

## Overview
- **Organization:** Cleveland Clinic Quantitative Health Sciences
- **URL:** https://github.com/ClevelandClinicQHS/COMET
- **Type:** Agent-based simulation, modular
- **Coverage:** Lung (COMET-Lung implemented; designed to be extensible)
- **Data:** SRTR/OPTN data, synthetically generated populations
- **Published:** Castleberry et al. JHLT 2024
- **License:** Open source (GitHub)

## What It Does
COMET is a modular agent-based model simulating individual donor-candidate interactions over time. Modules include:
1. **Donor Generation:** Synthetic donors with assigned traits
2. **Candidate Generation:** Synthetic candidates with evolving characteristics
3. **Pre-transplant Risk:** Waitlist mortality and delisting events
4. **Screening:** Identify compatible candidates per donor
5. **Matching:** Implement allocation criteria (current or proposed)
6. **Acceptance:** Model whether candidates accept offered organs
7. **Post-transplant Risk:** Graft and patient survival outcomes

## Methodology
- **Simulation type:** Agent-based, individual-level
- **Competing risks:** Yes (modular — pre-transplant risk module)
- **Population generation:** Data-driven probability models from SRTR
- **Validation:** Reproduced 2018-2019 US lung transplant outcomes and correctly predicted the decrease in type O transplants after CAS adoption

## Strengths vs TransPlan
- Agent-based (individual donor-candidate interactions vs parametric distributions)
- Models organ acceptance decisions
- Validated against real outcomes (2018-2019 lung)
- Modular architecture designed for extension to other organs
- Population trend modeling (accounts for changing donor/candidate demographics)

## Limitations vs TransPlan
- Currently lung-only (not yet extended to other organs)
- No interactive web interface (Python code only)
- No patient-facing tools
- No equity auditing
- No spatial environmental data
- No multi-criteria center scoring
- No multi-engine cross-validation

## Benchmarking Potential
**High (Priority 1).** Both tools are open-source. Extract COMET-Lung's validation patient profiles and predicted center-level outcomes. Run TransPlan for lung with equivalent profiles. Compute Spearman rank correlation between center rankings.

This is the most valuable benchmark because COMET uses a fundamentally different approach (agent-based vs parametric Monte Carlo). Agreement would validate TransPlan's lighter-weight methodology; disagreement would identify areas where parametric assumptions fail.

## Key References
- Castleberry AW, et al. "A modular simulation framework for organ allocation." JHLT 2024. DOI: 10.1016/j.healun.2024.04.074
- GitHub: https://github.com/ClevelandClinicQHS/COMET
