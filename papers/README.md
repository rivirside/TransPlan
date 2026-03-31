# TransPlan Publication Portfolio

Nine publication-ready subprojects derived from the TransPlan platform ([transplant.today](https://transplant.today)). Each subfolder contains a project README with scope, target venues, structure, and a draft manuscript.

## Overview Matrix

| # | Title (short) | Type | Effort | Top Target | Backup Target | Acceptance Odds |
|---|---------------|------|--------|------------|---------------|-----------------|
| 01 | **TransPlan: Open-Source Tool** | Software/tools | 🟢 Low | JAMIA | SoftwareX, JBI | High (75%+) |
| 02 | **Cross-Engine Validation** | Methods comparison | 🟢 Low | Med Decision Making | Stat Med, JAMA Netw Open | Moderate-High (60%) |
| 03 | **Equity Audit** | Applied/policy | 🟢 Low | Health Affairs | AJPH, AJT | Moderate-High (55%) |
| 04 | **Policy Scenario Modeling** | Applied/policy | 🟢 Low | AJT | Transplantation, JHPPL | Moderate (50%) |
| 05 | **Bayesian Hierarchical Survival** | Statistical methods | 🟡 Medium | Biostatistics | Stat Med, SMMR | Moderate (45%) |
| 06 | **Competing Risks + Copula** | Statistical methods | 🟡 Medium | Lifetime Data Analysis | Stat Med, Biometrics | Moderate (45%) |
| 07 | **Temporal Stability** | Validation study | 🟡 Medium | Med Care | Health Serv Res, MDM | Moderate (50%) |
| 08 | **Spatial Interpolation** | Methods/applied | 🟡 Medium | Int J Health Geographics | Spatial & Spatio-temporal Epi | Moderate (50%) |
| 09 | **Reproducibility Standards** | Commentary/perspective | 🟢 Low | JAMIA (perspective) | BMJ Health & Care Informatics | High (65%) |

**Effort key:** 🟢 Low = mostly writing, code exists · 🟡 Medium = some additional analysis/runs needed

## Submission Strategy

### Phase A — Quick Wins (Month 1-2)
Start with **01** (tools paper) and **03** (equity) simultaneously. Both require minimal new work — just running existing endpoints and writing. Paper 01 anchors the platform in the literature; Paper 03 rides the algorithmic fairness wave.

### Phase B — Methods Core (Month 2-4)
Submit **02** (cross-engine) and **04** (policy scenarios). These use the validation tool built in Phase 4 and the existing policy scenario engine. Tables and figures generated directly from API endpoints.

### Phase C — Deep Methods (Month 4-8)
**05** (Bayesian hierarchy) and **06** (copula) are the heaviest methodologically but also the most novel. These target top-tier statistics journals. **07** (temporal) and **08** (spatial) can run in parallel.

### Phase D — Commentary (Anytime)
**09** (reproducibility) is a short perspective piece — can be written and submitted anytime as a 2000-word commentary.

## Cross-Paper Dependencies

```
01 (tool paper) ← anchors everything, cite in all others
    ├── 02 (cross-engine) ← uses 01's three engines
    ├── 03 (equity) ← uses 01's equity audit tool
    ├── 04 (policy) ← uses 01's scenario engine
    ├── 05 (Bayesian) ← deep-dive on 01's MCMC engine
    ├── 06 (copula) ← deep-dive on 01's competing risks
    ├── 07 (temporal) ← validates 01's predictions over time
    ├── 08 (spatial) ← deep-dive on 01's interpolation layer
    └── 09 (reproducibility) ← uses 01 as case study
```

**Recommendation:** Submit 01 first (or simultaneously with others). All subsequent papers cite it.

## Folder Structure

Each `paper-XX/` folder contains:

```
paper-XX/
├── README.md          # Scope, venue analysis, structure, status
├── draft.md           # Working manuscript draft
├── figures/           # Generated figures (when applicable)
├── tables/            # Generated tables (when applicable)
└── references.bib     # BibTeX references (when applicable)
```

## Shared Resources

- **Data:** All papers draw from `data/` in the main repo (248 SRTR centers, 6 organs, 14 biannual releases)
- **Code:** Backend services in `backend/services/` implement all methods
- **Validation:** `backend/routers/validation.py` provides cross-engine comparison, calibration, and temporal validation endpoints
- **Tests:** 594+ pytest and 123 Jest tests validate implementations
