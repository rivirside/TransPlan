# Paper 01: TransPlan — An Open-Source Decision Support System for Transplant Center Evaluation

## Status: 📝 Not Started

## Summary

A software/tools paper describing the TransPlan platform: an open-source, web-based clinical decision support system for transplant center evaluation. Covers architecture, data sources, three inference engines (Monte Carlo, BBN, MCMC), 248-center coverage, and interactive tools for patients and professionals.

## Paper Type
**Software/Systems paper** — describes an implemented, publicly deployed tool. Heavy on system description, architecture, screenshots, and usage walkthrough. Lighter on novel methods (those go in papers 02-08).

## Target Venues (ranked)

| Venue | IF | Fit | Page Limit | Acceptance Rate | Notes |
|-------|-----|-----|------------|-----------------|-------|
| **JAMIA** (J Am Med Inform Assoc) | 7.9 | ⭐⭐⭐ | 10 pages | ~20% | Primary target. "Systems" paper category. Strong open-source culture. |
| **SoftwareX** | 3.4 | ⭐⭐⭐ | 6 pages | ~45% | Short format, focused on software itself. Requires public repo. |
| **JBI** (J Biomed Inform) | 4.5 | ⭐⭐ | 12 pages | ~22% | Broader informatics scope. Good fallback. |
| **JMIR** (J Med Internet Res) | 7.1 | ⭐⭐ | 8 pages | ~30% | Web-based health tool angle. OA fees ~$2500. |
| **BMC Med Inform Decis Mak** | 3.3 | ⭐⭐ | No limit | ~35% | Open access, faster review. Good if JAMIA rejects. |

**Recommended:** Submit to JAMIA first. If rejected, pivot to SoftwareX (shorter, faster).

## Likelihood of Acceptance
**High (75%+)** — JAMIA regularly publishes open-source clinical tools. Key requirements: public availability, clear clinical utility, technical rigor. TransPlan meets all three.

## Effort Required
🟢 **Low** — The tool is built and deployed. This paper is primarily descriptive writing plus generating screenshots and usage examples.

### What exists already
- Full platform at transplant.today with 248 SRTR centers
- Three inference engines with cross-validation
- 7 interactive tools (simulator, equity, sensitivity, scenarios, explorer, validation, centers)
- Public GitHub repo with 594+ tests
- API documentation (FastAPI auto-generated docs)

### What needs to be done
- [ ] Write manuscript (~4000 words for JAMIA)
- [ ] Generate architecture diagram (backend/frontend/data flow)
- [ ] Capture annotated screenshots of each tool
- [ ] Create comparison table vs existing tools (SRTR website, transplant calculators)
- [ ] Write "Availability" section (GitHub URL, license, deployment)

## Suggested Structure (JAMIA format)

1. **Introduction** (500 words)
   - Gap: patients and clinicians lack multi-factor, probabilistic tools for center selection
   - Existing tools (SRTR reports, simple calculators) don't integrate competing risks, spatial data, equity auditing
   - Contribution: open-source platform with three inference engines, 248-center coverage

2. **System Description** (1500 words)
   - Architecture (FastAPI + vanilla JS, Vercel deployment)
   - Data sources (SRTR, CDC, EPA, BLS, CMS — list all 15+ JSON datasets)
   - Inference engines (MC with competing risks, BBN with exact inference, MCMC with posterior uncertainty)
   - Scoring algorithm (8-category weighted framework)
   - Interactive tools (one paragraph each)

3. **Implementation** (800 words)
   - Technology stack
   - Data pipeline (fetch scripts, JSON normalization)
   - Tier system (web vs local deployment)
   - Reproducibility (seed parametrization, run artifacts)

4. **Evaluation** (800 words)
   - Cross-engine validation (Spearman ρ, top-5 overlap)
   - Calibration (Brier scores)
   - Test coverage (594 pytest + 123 Jest)
   - Performance (response times per engine)

5. **Discussion** (400 words)
   - Limitations (not clinically validated, model-based not empirical)
   - Comparison to related work
   - Future: clinical validation study, MCMC expansion to 248 centers

6. **Conclusion** (200 words)

## Key Figures
1. System architecture diagram
2. Screenshot: Simulator results (map + table)
3. Screenshot: Equity audit heatmap
4. Screenshot: Validation cross-engine comparison
5. Data flow diagram (SRTR → JSON → inference → UI)

## Key Tables
1. Data sources and coverage (source, records, update frequency)
2. Inference engine comparison (speed, accuracy, uncertainty)
3. Comparison with existing transplant decision tools
